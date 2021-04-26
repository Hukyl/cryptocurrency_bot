import abc

import requests
from bs4 import BeautifulSoup as bs

from utils.agent import get_useragent
from utils import get_default_rates, prettify_float, merge_dicts, get_random_proxy
from configs import settings


__all__ = ['CurrencyExchanger']



class CurrencyParser(abc.ABC):
    """
    Universal abstract class for parsing the currency
    All rates returned according to USD

    Methods returning format:
        get_rate:
            {`iso`: 1, 'USD': `rate`}
        check_delta:
            {'currency_from': `iso`, 'currency_to': 'USD', 'old':`old`}
            Optional keys:
                'new': `new`,
                'percentage_difference': `percentage_difference`,
                'difference': `difference`
    """

    def __init__(self, link:str, css_selector:str, iso:str, start_value:float=None):
        self.link = link
        self.css_selector = css_selector
        self.iso = iso
        try:
            self.start_value = start_value or self.get_rate().get('USD')
        except ValueError:
            self.start_value = get_default_rates(iso or '')

    def to_string(self, to_update:bool=True):
        iso_str = self.iso or ""
        rate = self.get_rate().get('USD') if to_update else self.start_value
        if iso_str:
            return f"{iso_str} = {rate} USD"
        return f"{rate} USD"

    @property
    def rate(self):
        return self.get_rate()

    def get_response(self, link:str=None):
        link = link or self.link
        headers = {"Connection": "Close", "User-Agent": get_useragent()}
        return requests.get(link, headers=headers, proxies={'http': get_random_proxy()})

    def get_html(self, link:str=None):
        return self.get_response(link or self.link).text

    def get_soup(self, link:str=None):
        link = link or self.link
        return bs(self.get_html(link), "html.parser")

    def get_rate(self):
        try:
            soup = self.get_soup()
            span = soup.select_one(self.css_selector)
            if span is not None:
                rate = span.text.strip()
                rate = rate.replace('$', '')  # since default is USD, sometimes $ sign occurs
                # support both `1,812.35` and `1812,34` formats
                number = float(rate.replace(",", ".") if '.' not in rate else rate.replace(",", ""))
            else:
                raise ValueError(f'can not parse currency of "{self.iso}"')
        except Exception:
            number = get_default_rates(self.iso).get(self.iso)
        finally:
            return {self.iso: 1, 'USD': number}

    def check_delta(self, old:float=None, new:float=None, percent_delta:float=0.01):
        res = self.calculate_difference(old or self.start_value, new or self.get_rate().get('USD'))
        res['currency_from'] = self.iso
        res['currency_to'] = 'USD'
        if abs(res.get('percentage_difference')) < percent_delta:
            del res['new'], res['percentage_difference'], res['difference']
        return res

    def update_start_value(self, start_value:float=None):
        start_value = start_value or self.get_rate().get('USD')
        self.start_value = start_value

    @staticmethod
    def calculate_difference(old:float, new:float):
        return {
            'old': old,
            'new': new,
            'percentage_difference': -prettify_float(
                (old - new) / max(old, new)
            ),
            "difference": prettify_float(-(old - new))
        }



class RTSParser(CurrencyParser):
    iso = "RTS"

    def __init__(self, start_value:float=None):
        link = "https://www.investing.com/indices/rts-cash-settled-futures-chart"
        css_selector = "#last_last"
        super().__init__(
            link=link, css_selector=css_selector, 
            iso=self.iso, start_value=start_value
        )



class BitcoinParser(CurrencyParser):
    iso = "BTC"

    def __init__(self, start_value:float=None):
        link = "https://www.coindesk.com/price/bitcoin"
        # link = "https://ru.investing.com/crypto/bitcoin/btc-usd-converter"
        css_selector = "#export-chart-element > div > section > \
                        div.coin-info-list.price-list > div:nth-child(1) > \
                        div.data-definition > div"
        # css_selector = "#amount2"
        super().__init__(
            link=link, css_selector=css_selector, 
            iso=self.iso, start_value=start_value
        )



class FreecurrencyratesParser(CurrencyParser):
    def __init__(self):
        self.link = "https://freecurrencyrates.com/ru/%s-exchange-rate-calculator"

    def get_rate(self, iso_from:str, iso_to:str="USD"):
        iso_from, iso_to = iso_from.upper(), iso_to.upper()
        if iso_from == iso_to:
            return {iso_from: 1}
        try:
            rate = self.get_soup(self.link % iso_from).select_one(f"#rate-iso-{iso_to}")
            if rate is not None:
                number = float(rate.get("value").strip().replace(",", "."))
            else:
                raise ValueError("second iso code is invalid")
        except Exception as e:
            if str(e) == "second iso code is invalid":
                raise ValueError(e)
            else:
                number = get_default_rates(iso_from).get(iso_from)
        return {iso_from: 1, iso_to: number}

    def check_currency_exists(self, currency:str):
        try:
            res = self.get_response(self.link % currency.upper())
            return res.ok
        except Exception:
            return False

    def check_delta(self, iso_from:str, iso_to:str, start_value:float=1, percent_delta:float=0.01):
        old, new = start_value, self.get_rate(iso_from, iso_to).get(iso_to)
        res = self.calculate_difference(old, new)
        res['currency_from'] = iso_from
        res['currency_to'] = iso_to
        if abs(res.get('percentage_difference')) < percent_delta:
            del res['new'], res['percentage_difference'], res['difference']
        return res

    def update_start_value(self, *args, **kwargs):
        raise NotImplementedError()

    def to_string(self, iso_from, iso_to):
        rate = self.get_rate(iso_from, iso_to)
        return f"{iso_from} - {rate.get(iso_to)} {iso_to}"



class InvestingParser(CurrencyParser):
    """
    Parser for 'https://m.ru.investing.com/commodities/<some-market-product>'
    Can parse only from AVAILABLE_PRODUCTS dict's keys
    """
    AVAILABLE_PRODUCTS = {
        'gold': 'Gold', 
        'silver': 'Silver', 
        'palladium': 'Palladium', 
        'copper': 'Copper', 
        'platinum': 'Platinum', 
        'brent-oil': 'BRENT', 
        'crude-oil': 'CRUDE',
        'natural-gas': 'GAS',
        'london-gas-oil': 'GAS-OIL'
    }

    def __init__(self, market_product:str, start_value:float=None):
        assert (
            market_product in self.AVAILABLE_PRODUCTS
        ), 'not supported market product - {}'.format(repr(market_product))
        link = "https://m.investing.com/commodities/{}".format(market_product)
        css_selector = '#last_last'
        super().__init__(
            link=link, css_selector=css_selector, 
            iso=self.AVAILABLE_PRODUCTS[market_product], start_value=start_value
        )



class CurrencyExchanger(CurrencyParser):
    def __init__(self):
        self.PARSERS = merge_dicts(
            {parser.iso: parser for parser in [RTSParser(), BitcoinParser()]},
            {
                InvestingParser.AVAILABLE_PRODUCTS[x]: InvestingParser(x)
                for x in list(InvestingParser.AVAILABLE_PRODUCTS)
            }
        )
        self.DEFAULT_PARSER = FreecurrencyratesParser()

    def get_rate(self, iso_from, iso_to):
        p_from = self.PARSERS.get(iso_from, self.DEFAULT_PARSER)
        p_to = self.PARSERS.get(iso_to, self.DEFAULT_PARSER)
        try:
            rate_from = (
                p_from.get_rate(iso_from) 
                if getattr(p_from, 'iso', None) is None else 
                p_from.get_rate()
            )
            rate_to = (
                p_to.get_rate(iso_to) 
                if getattr(p_to, 'iso', None) is None else 
                p_to.get_rate()
            )
            return {
                iso_from: 1, 
                iso_to: prettify_float((1 / rate_to["USD"]) * rate_from.get("USD"))
            }
        except Exception:
            raise ValueError(
                "`iso_from` or `iso_to` is invalid or network cannot be reached"
            ) from None

    def update_start_value(self):
        for curr in self.PARSERS:
            self.PARSERS[curr].update_start_value()

    def check_delta(self, iso_from:str, iso_to:str, old:float, percent_delta:float=0.01):
        new = self.get_rate(iso_from, iso_to).get(iso_to)
        rate = self.calculate_difference(old, new)
        rate['currency_from'] = iso_from
        rate['currency_to'] = iso_to
        if abs(rate.get('percentage_difference')) < percent_delta:
            del rate['new'], rate['percentage_difference'], rate['difference']
        return rate

    def check_rate_exists(self, iso_from, iso_to):
        return all(
            x in self.PARSERS or self.DEFAULT_PARSER.check_currency_exists(x)
            for x in [iso_from, iso_to]
        )

    def __str__(self):
        return '\n'.join([
            f"{curr} = {prettify_float(self.PARSERS[curr].start_value)} USD" 
            for curr in sorted(self.PARSERS)
        ])

    def to_telegram_string(self):
        main_currs = sorted(settings.MAIN_CURRENCIES)
        other_currs = sorted(list(set(self.PARSERS) - set(settings.MAIN_CURRENCIES)))
        return '\n'.join([
            ('*{}*' if curr in main_currs else '{}').format(
                f"{curr} = {prettify_float(self.PARSERS[curr].start_value)} USD"
            )
            for curr in main_currs + other_currs
        ])
