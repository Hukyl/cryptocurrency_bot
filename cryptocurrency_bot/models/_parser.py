import json
import abc

import requests
from bs4 import BeautifulSoup as bs

from utils.agent import get_useragent
from utils import get_default_values_from_config



class CurrencyParser(abc.ABC):
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
        if span is not None:
            return float(span[0].text.strip().replace(",", "."))
        raise ValueError(f'can not parse currency of "{self.iso}"')

    def check_delta(self, start_value:float=None, percent_delta:float=1):
        return self.calculate_differences(
            self.iso,
            start_value or self.start_value,
            self.rate,
            percent=percent_delta
        )

    def update_start_value(self, start_value:float=None):
        start_value = start_value or self.get_rate()
        self.start_value = start_value

    @staticmethod
    def calculate_differences(iso:str, old:float, new:float, percent:float):
        percent = percent * 0.01
        lower_limit, upper_limit = old * (1 - percent), old * (1 + percent)
        dct = {"old": old, "currency": iso}
        if not (lower_limit < new < upper_limit):
            dct["new"] = new
            dct["percentage_difference"] = round((max(new, old) - min(new, old)) / min(new, old), 5)
            dct["difference"] = round(abs(old - new), 2)
        return dct


class BrentParser(CurrencyParser):
    iso = "BRENT"

    def __init__(self, start_value:float=None):
        link = "https://m.investing.com/commodities/brent-oil"
        css_selector = "#siteWrapper > div.wrapper > section.boxItemInstrument.boxItem > div.quotesBox > \
            div.quotesBoxTop > span.lastInst.pid-8833-last"
        super().__init__(link, css_selector, start_value, self.iso)

    def get_rate(self):
        try:
            super().get_rate()
        except Exception:
            return get_default_values_from_config(self.iso).get(self.iso)



class RTSParser(CurrencyParser):
    iso = "RTS"

    def __init__(self, start_value:float=None):
        link = "https://m.ru.investing.com/indices/rts-cash-settled-futures"
        css_selector = "#siteWrapper > div.wrapper > section.boxItemInstrument.boxItem > div.quotesBox > div.quotesBoxTop > span.lastInst.pid-104396-last"
        super().__init__(link, css_selector, start_value, self.iso)

    def get_rate(self):
        try:
            super().get_rate()
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
                try:
                return {
                    iso_from: 1,
                    iso_to: float(
                        soup.find("input", {"id": f"rate-iso-{iso_to}"})
                        .get("value")
                        .strip()
                        .replace(",", ".")
                    ),
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

    def check_delta(self, iso_from:str, iso_to:str, start_value:float=1, percent_delta:float=1):
        old, new = start_value, self.get_rate(iso_from, iso_to).get(iso_to)
        return self.calculate_differences(None, old, new, percent_delta)


if __name__ == "__main__":
    pass
