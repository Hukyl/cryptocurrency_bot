import json
import os
import sys

from configs import settings


__all__ = [
    'merge_dicts', 'prettify_utcoffset', 'get_json_config', 
    'get_default_values_from_config', 'prettify_float', 'prettify_percent', 'catch_exc'
]


def merge_dicts(*dcts):
    assert len(dcts) > 0, 'you must pass minimum one dictionary'
    start_dct = dcts[0]
    for dct in dcts[1:]:
        start_dct = {**start_dct, **dct}
    return start_dct


def prettify_utcoffset(utcoffset:int=0):
    assert utcoffset in range(-11, 13), 'time zones are in range from -11 to +12'
    return "UTC" + ('' if utcoffset == 0 else '{:0=+3d}:00'.format(utcoffset))


def get_json_config():
    with open(os.path.join('configs', 'config.json'), 'r', encoding='utf-8') as f:
        return json.load(f)
    

def get_default_values_from_config(*args):
    if len(args) == 0:
        return None
    print('[ERROR] Default value was used for: ' + ', '.join(args))
    json_config = get_json_config()
    return {curr: json_config.get('initialValue' + curr, 1) for curr in args}



def prettify_float(num:float):
    round_num = settings.PRECISION_NUMBER + (0 if num // 1 > 0 else 3)
    return round(num, round_num)


def prettify_percent(n:float):
    res = round(n*100, settings.PRECISION_NUMBER)
    return str(int(res) if res % 1 == 0 else res) + '%'


def catch_exc(func):
    def inner(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
        except Exception:
            print(f'\nException\nFunc name: {func.__name__}\nType: {sys.exc_info()[0].__name__}\nMessage: {str(sys.exc_info()[1])}\n')
        else:
            return res
    return inner
