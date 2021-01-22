import json

import requests
from bs4 import BeautifulSoup as bs

from utils.agent import get_useragent
from utils import get_default_values_from_config, prettify_float



class CurrencyParser(object):
    """
    Universal abstract class for parsing the currency
    All rates returned according to USD
    """

    def __init__(self, link:str, css_selector:str, start_value:float=None, iso:str=None):
        self.link = link
        self.css_selector = css_selector
        self.iso = iso
        try:
            self.start_value = start_value or self.get_rate()
        except ValueError:
            self.start_value = get_default_values_from_config(iso or '')

    def to_string(self, to_update:bool=True):
        iso_str = self.iso or ""
        rate = self.get_rate() if to_update else self.start_value
        if iso_str:
            return f"{iso_str} = ${rate}"
        return f"${rate}"

    @property
    def rate(self):
        return self.get_rate()

    def get_response(self, link:str=None):
        link = link or self.link
        headers = {"Connection": "Close", "User-Agent": get_useragent()}
        return requests.get(link, headers=headers)

    def get_html(self, link:str=None):
        link = link or self.link
        return self.get_response(link).text

    def get_soup(self, link:str=None):
        link = link or self.link
        return bs(self.get_html(link), "html.parser")

    def get_rate(self):
        soup = self.get_soup()
        span = soup.select(self.css_selector)
        if len(span) != 0:
            rate = span[0].text.strip()
            # support both `1,812.35` and `1812,34` formats
            return float(rate.replace(",", ".") if '.' not in rate else rate.replace(",", "")) 
        raise ValueError(f'can not parse currency of "{self.iso}"')

    def check_delta(self, old:float=None, new:float=None, percent_delta:float=0.01):
        res = self.calculate_difference(
            old or self.start_value,
            new or self.get_rate()
        )
        res['currency'] = self.iso
        if abs(res.get('percentage_difference')) < percent_delta:
            del res['new'], res['percentage_difference'], res['difference']
        return res

    def update_start_value(self, start_value:float=None):
        start_value = start_value or self.get_rate()
        self.start_value = start_value

    @staticmethod
    def calculate_difference(old:float, new:float):
        return {
            'old': old,
            'new': new,
            'percentage_difference': -prettify_float(
                (old - new) / old
            ),
            "difference": prettify_float(abs(old - new))
        }



class RTSParser(CurrencyParser):
    iso = "RTS"

    def __init__(self, start_value:float=None):
        link = "https://m.ru.investing.com/indices/rts-cash-settled-futures"
        css_selector = "#siteWrapper > div.wrapper > section.boxItemInstrument.boxItem > div.quotesBox > div.quotesBoxTop > span.lastInst.pid-104396-last"
        super().__init__(link, css_selector, start_value, self.iso)

    def get_rate(self):
        try:
            return super().get_rate()
        except Exception:
            return get_default_values_from_config(self.iso).get(self.iso)



class BitcoinParser(CurrencyParser):
    iso = "BTC"

    def __init__(self, start_value:float=None):
        link = "https://www.coindesk.com/price/bitcoin"
        css_selector = "#export-chart-element > div > section > div.coin-info-list.price-list > \
                             div:nth-child(1) > div.data-definition > div"
        super().__init__(link, css_selector, start_value, self.iso)

    def get_rate(self):
        try:
            soup = self.get_soup()
            span = soup.select(self.css_selector)
            if span is not None:
                sign, *number = span[0].text.strip()
                number = float("".join(number).replace(",", ""))
                return number
            raise ValueError(f'can not parse currency of "{self.iso}"')
        except Exception:
            return get_default_values_from_config(self.iso).get(self.iso)


class FreecurrencyratesParser(CurrencyParser):
    def __init__(self):
        self.link = "https://freecurrencyrates.com/ru/%s-exchange-rate-calculator"

    def get_rate(self, iso_from:str, iso_to:str="USD"):
        try:
            link = self.link % iso_from.upper()
            soup = self.get_soup(link)
            rate = soup.select(f"#rate-iso-{iso_to.upper()}")
            if rate:
                return {
                    iso_from: 1,
                    iso_to: float(
                        soup.find("input", {"id": f"rate-iso-{iso_to}"})
                        .get("value")
                        .strip()
                        .replace(",", ".")
                    )
                }
            raise ValueError("second iso code is invalid")
        except Exception as e:    
            if str(e) == "second iso code is invalid":
                raise ValueError(e)
            else:
                return get_default_values_from_config(iso_from).get(iso_from)

    def check_currency_exists(self, currency:str):
        try:
            res = self.get_response(self.link % currency.upper())
            return res.ok
        except Exception:
            return False

    def check_delta(self, iso_from:str, iso_to:str, start_value:float=1, percent_delta:float=0.01):
        old, new = start_value, self.get_rate(iso_from, iso_to).get(iso_to)
        res = self.calculate_difference(None, old, new, percent_delta)
        del res['currency']
        res['currency_from'] = iso_from
        res['currency_to'] = iso_to
        if abs(res.get('percentage_difference')) < percent_delta:
            del res['new'], res['percentage_difference'], res['difference']


class InvestingParser(CurrencyParser):
    """
    Parser for 'https://m.ru.investing.com/commodities/<some-market-product>'
    Can parse only from AVAILABLE_PRODUCTS list
    """
    AVAILABLE_PRODUCTS = [
        'gold', 
        'silver', 
        'palladium', 
        'copper', 
        'platinum', 
        'brent-oil', 
        'crude-oil',
        'natural-gas',
        'london-gas-oil'
    ]

    def __init__(self, market_product:str, start_value:float=None):
        assert market_product in self.AVAILABLE_PRODUCTS, 'not supported market product - {}'.format(repr(market_product))
        link = "https://m.investing.com/commodities/{}".format(market_product)
        # link = "https://www.exchangerates.org.uk/commodities/live-oil-prices/BRT-USD.html"
        css_selector = '#siteWrapper > div.wrapper > \
                        section.boxItemInstrument.boxItem > \
                        div.quotesBox > div.quotesBoxTop > span.lastInst'
        # css_selector = "#value_BRTUSD"
        super().__init__(link, css_selector, start_value, market_product)

    def get_rate(self):
        try:
            return super().get_rate()
        except Exception:
            return get_default_values_from_config(self.iso).get(self.iso)

    def to_string(self, to_update:bool=True):
        iso_str = (self.iso or "").replace('-', ' ').title()
        rate = self.get_rate() if to_update else self.start_value
        return f"{iso_str} = ${rate}"

    # TODO: override `get_rate` method


if __name__ == "__main__":
    pass
