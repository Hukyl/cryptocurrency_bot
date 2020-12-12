import json
from time import sleep

import requests
from bs4 import BeautifulSoup as bs

from agent import get_useragent



class CurrencyParser(object):
    def __init__(self, link, css_selector, initial_value=None):
        self.link = link
        self.css_selector = css_selector
        try:
            self.initial_value = initial_value or self.get_rate()
        except ValueError:
            self.initial_value = json.load(open("config.json", "r")).get('initialValue')

    @property
    def rate(self):
        return self.get_rate()

    def get_html(self):
        headers = {
            "Connection": "Close",
            "User-Agent": get_useragent()
        }
        return requests.get(self.link, headers=headers).text

    def get_soup(self):
        return bs(self.get_html(), 'html.parser')

    def get_rate(self):
        soup = self.get_soup()
        span = soup.select(self.css_selector)
        if span is not None:
            return float(span[0].text.strip())
        raise ValueError(f'can not parse currency of "{self.link}"')

    def check_delta(self, percent_delta=None):
        perc = (percent_delta or json.load(open("config.json", "r")).get('percentDelta')) * 0.01
        new_rate = self.rate
        lower_limit, upper_limit = self.initial_value * (1 + perc), self.initial_value * (1 - perc)
        dct = {'old': self.initial_value}
        if not (lower_limit < new_rate < upper_limit): 
            dct['new'] = new_rate
            self.initial_value = new_rate
        return dct


class BrentParser(CurrencyParser):
    def __init__(self, initial_value=None):
        self.link = 'https://m.investing.com/commodities/brent-oil'
        self.css_selector = '#siteWrapper > div.wrapper > section.boxItemInstrument.boxItem > div.quotesBox > \
            div.quotesBoxTop > span.lastInst.pid-8833-last'
        try:
            self.initial_value = initial_value or self.get_rate()
        except ValueError:
            self.initial_value = json.load(open("config.json", "r")).get('initialValue')



if __name__ == '__main__':
    p = BrentParser()
    print(p.rate)
    print(p.check_delta(0.01))