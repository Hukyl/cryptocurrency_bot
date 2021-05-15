import random

import requests
from bs4 import BeautifulSoup as bs

from utils.agent import get_useragent
from utils.translator import translate as _
from utils import get_default_rates, prettify_float, get_proxy_list
from configs import settings
from . import exceptions


__all__ = ['CurrencyExchanger']



class Parser(object):
    def __init__(self, link:str, css_selector:str, *, proxy_list:list=get_proxy_list()):
        self.session = requests.Session()
        self.link = link
        self.css_selector = css_selector
        self.proxy_list = proxy_list

    def get_response(self):
        lambda_get = lambda x, p: self.session.get(
            x, headers={"User-Agent": get_useragent()}, 
            proxies={'http': 'http://' + p} if p else None
        )
        if self.proxy_list:
            proxies = self.proxy_list
            random.shuffle(proxies)
        else:
            proxies = [None] * 5
        for proxy in proxies:
            try:
                q = lambda_get(self.link, proxy)
                if q.ok:
                    break
            except requests.ConnectionError:
                self.session = requests.Session()
        return q

    def get_html(self):
        return self.get_response().text

    def get_soup(self):
        return bs(self.get_html(), "html.parser")

    def get_element(self):
        return self.get_soup().select_one(self.css_selector)


class CurrencyParser(Parser):
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

    def __init__(self, iso:str, *args, default_value:float=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.iso = iso
        self.default_value = default_value or get_default_rates(iso or '', to_print=False).get(iso)
        self.value = None
        self.update_value(safe=True)

    def to_string(self, *, to_update:bool=True):
        iso_str = self.iso or ""
        rate = self.get_rate().get('USD') if to_update else self.value
        if iso_str:
            return f"{iso_str} = {rate} USD"
        return f"{rate} USD"

    @property
    def rate(self):
        return self.get_rate()

    def get_rate(self):
        span = self.get_element()
        if span is None:
            raise exceptions.ParsingError(f'can not parse currency of "{self.iso}"', cause="empty soup")
        rate = span.text.strip()
        rate = rate.replace('$', '')  # since default is USD, sometimes $ sign occurs
        # support both `1,812.35` and `1812,34` formats
        number = float(rate.replace(",", ".") if '.' not in rate else rate.replace(",", ""))
        return {self.iso: 1, 'USD': number}

    def check_delta(self, old:float=None, new:float=None, percent_delta:float=0.01):
        res = self.calculate_difference(old or self.value, new or self.get_rate().get('USD'))
        res['currency_from'] = self.iso
        res['currency_to'] = 'USD'
        if abs(res.get('percentage_difference')) < percent_delta:
            del res['new'], res['percentage_difference'], res['difference']
        return res

    def update_value(self, *, safe:bool=False):
        try:
            self.value = self.get_rate().get('USD')
        except exceptions.ParsingError as e:
            if not safe:
                raise e from None
            print(f"[ERROR] Default value was used for currency {self.iso if self.iso else ''}")
            self.value = self.default_value

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



class FreecurrencyratesParser(Parser):
    def __init__(self, *args, **kwargs):
        self.start_link = "https://freecurrencyrates.com/ru/{}-exchange-rate-calculator"
        self.start_css_selector = "#rate-iso-{}"
        super().__init__(link=None, css_selector=None, *args, **kwargs)

    def get_rate(self, iso_from:str, iso_to:str="USD"):
        iso_from, iso_to = iso_from.upper(), iso_to.upper()
        if iso_from == iso_to:
            return {iso_from: 1}
        self.link = self.start_link.format(iso_from)
        self.css_selector = self.start_css_selector.format(iso_to)
        rate = self.get_element()
        if rate is None:
            raise exceptions.CurrencyDoesNotExistError("some of the currencies do not exist", cause="iso")
        number = float(rate.get("value").strip().replace(",", "."))
        return {iso_from: 1, iso_to: number}

    def check_currency_exists(self, currency:str):
        try:
            self.link = self.start_link.format(currency.upper())
            res = self.get_response()
            return res.ok
        except Exception:
            return False
        finally:
            self.link = None

    def check_delta(self, iso_from:str, iso_to:str, value:float=1, percent_delta:float=0.01):
        old, new = value, self.get_rate(iso_from, iso_to).get(iso_to)
        res = self.calculate_difference(old, new)
        res['currency_from'] = iso_from
        res['currency_to'] = iso_to
        if abs(res.get('percentage_difference')) < percent_delta:
            del res['new'], res['percentage_difference'], res['difference']
        return res

    @staticmethod
    def calculate_difference(*args, **kwargs):
        return CurrencyParser.calculate_difference(*args, **kwargs)

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
    def __init__(self, *, proxy_list:list=get_proxy_list()):
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

    def update_value(self, *args, **kwargs):
        for curr in self.parsers:
            self.parsers[curr].update_value(*args, **kwargs)

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
            f"{parser.iso} = {prettify_float(parser.value if not to_update else parser.rate)} USD" 
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
                ) + f"= {prettify_float(self.parsers[curr].value)}"
            )
            for curr in main_currs + other_currs
        ])
