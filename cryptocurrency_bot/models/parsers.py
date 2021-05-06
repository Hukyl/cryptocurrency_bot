import abc

import requests
from bs4 import BeautifulSoup as bs

from utils.agent import get_useragent
from utils.translator import translate as _
from utils import get_default_rates, prettify_float
from configs import settings
from . import exceptions


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

    def __init__(self, link:str, css_selector:str, iso:str, *, start_value:float=None, proxy_list:list=None):
        self.link = link
        self.css_selector = css_selector
        self.iso = iso
        self.proxy_list = proxy_list
        try:
            self.start_value = start_value or self.get_rate().get('USD')
        except ValueError:
            self.start_value = get_default_rates(iso or '')

    def to_string(self, *, to_update:bool=True):
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
        lambda_get = lambda x, p: requests.get(
            x, headers={"Connection": "Close", "User-Agent": get_useragent()}, 
            proxies={'http': 'http://' + p} if p else None
        )
        if self.proxy_list:
            for proxy in self.proxy_list:
                q = lambda_get(link, proxy)
                if q.ok:
                    break
        else:
            for _i in range(5):
                q = lambda_get(link, None)
                if q.ok:
                    break
        return q

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

    def __init__(self, *args, **kwargs):
        link = "https://www.investing.com/indices/rts-cash-settled-futures-chart"
        css_selector = "#last_last"
        super().__init__(
            link=link, css_selector=css_selector, 
            iso=self.iso, *args, **kwargs
        )



class BitcoinParser(CurrencyParser):
    iso = "BTC"

    def __init__(self, *args, **kwargs):
        link = "https://www.coindesk.com/price/bitcoin"
        css_selector = "#export-chart-element > div > section > \
                        div.coin-info-list.price-list > div:nth-child(1) > \
                        div.data-definition > div"
        super().__init__(
            link=link, css_selector=css_selector, 
            iso=self.iso, *args, **kwargs
        )



class FreecurrencyratesParser(CurrencyParser):
    def __init__(self, *, proxy_list:list=None):
        self.link = "https://freecurrencyrates.com/ru/%s-exchange-rate-calculator"
        self.proxy_list = proxy_list

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
        'Gold': 'gold', 
        'Silver': 'silver', 
        'Palladium': 'palladium', 
        'Copper': 'copper', 
        'Platinum': 'platinum', 
        'BRENT': 'brent-oil', 
        'CRUDE': 'crude-oil', 
        'GAS': 'natural-gas', 
        'GAS-OIL': 'london-gas-oil'
    }

    def __init__(self, market_product:str, *args, **kwargs):
        assert (
            market_product in self.AVAILABLE_PRODUCTS
        ), 'not supported market product - {}'.format(repr(market_product))
        link = "https://m.investing.com/commodities/{}".format(self.AVAILABLE_PRODUCTS[market_product])
        css_selector = '#last_last'
        super().__init__(
            link=link, css_selector=css_selector, 
            iso=market_product, *args, **kwargs
        )



class CurrencyExchanger(CurrencyParser):
    def __init__(self, *, proxy_list:list=None):
        self.parsers = {
            parser.iso: parser 
            for parser in [
                RTSParser(proxy_list=proxy_list), BitcoinParser(proxy_list=proxy_list), 
                *[InvestingParser(x, proxy_list=proxy_list) for x in InvestingParser.AVAILABLE_PRODUCTS]
            ]
        }
        self.default_parser = FreecurrencyratesParser(proxy_list=proxy_list)

    def get_rate(self, iso_from, iso_to):
        if not self.check_rate_exists(iso_from, iso_to):
            raise exceptions.CurrencyDoesNotExistError("some of the currencies do not exist", cause="iso")        
        p_from = self.parsers.get(iso_from, self.default_parser)
        p_to = self.parsers.get(iso_to, self.default_parser)
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
        for curr in self.parsers:
            self.parsers[curr].update_start_value()

    def check_delta(self, iso_from:str, iso_to:str, old:float, percent_delta:float=0.01):
        new = self.get_rate(iso_from, iso_to).get(iso_to)
        rate = self.calculate_difference(old, new)
        rate['currency_from'] = iso_from
        rate['currency_to'] = iso_to
        if abs(rate.get('percentage_difference')) < percent_delta:
            del rate['new'], rate['percentage_difference'], rate['difference']
        return rate

    def check_rate_exists(self, iso_from:str, iso_to:str):
        return all(
            x in self.parsers or self.default_parser.check_currency_exists(x)
            for x in [iso_from, iso_to]
        )

    def to_string(self, *, to_update:bool=False):
        return '\n'.join([
            f"{parser.iso} = {prettify_float(parser.start_value if not to_update else parser.rate)} USD" 
            for parser in self.parsers.values()
        ])

    def to_telegram_string(self, user_language:str):
        main_currs = sorted(settings.MAIN_CURRENCIES)
        other_currs = sorted(list(set(self.parsers) - set(settings.MAIN_CURRENCIES)))
        biggest_length = len(max(self.parsers, key=lambda x: len(x)))
        start_string = "`{:<{max_length}s}".format(_("Price", user_language), max_length=biggest_length + 1) + "($)`\n"
        return start_string + '\n'.join([
            '`{}`'.format(
                "{:<{max_length}s}".format(
                    (curr if curr in main_currs else curr.title()), max_length=biggest_length + 2
                ) + f"= {prettify_float(self.parsers[curr].start_value)}"
            )
            for curr in main_currs + other_currs
        ])
