import json
import os
import sys

from configs import settings
from .decorators import rangetest


__all__ = [
    'merge_dicts', 'prettify_utcoffset', 'get_json_config', 
    'get_default_rates', 'prettify_float', 'prettify_percent', 'catch_exc'
]


def merge_dicts(*dcts):
    assert len(dcts) > 0, 'you must pass minimum one dictionary'
    start_dct = dcts[0]
    for dct in dcts[1:]:
        start_dct = {**start_dct, **dct}
    return start_dct


@rangetest(_strict_comp=False, utcoffset=(-11, 12))
def prettify_utcoffset(utcoffset:int=0):
    return "UTC" + ('' if utcoffset == 0 else '{:0=+3d}:00'.format(utcoffset))


def get_json_config():
    with open(os.path.join('configs', 'config.json'), 'r', encoding='utf-8') as f:
        return json.load(f)
    

def get_default_rates(*args, to_print:bool=True):
    if len(args) == 0:
        return None
    if to_print:
        print('[ERROR] Default value was used for: ' + ', '.join(args))
    json_config = get_json_config()
    return {curr: json_config.get('initialValue' + curr, 1) for curr in args}


def prettify_float(num:float):
    round_num = settings.PRECISION_NUMBER + (0 if num // 1 > 0 else 3)
    return round(num, round_num)


@rangetest(_strict_comp=False, n=(0.00001, 1))
def prettify_percent(n:float, to_sign:bool=False):
    res = n*100
    res = round(res, settings.PERCENT_PRECISION_NUMBER if res > 1 else 6)
    return ("{:+}%" if to_sign else "{}%").format(int(res) if res % 1 == 0 else res) 


def catch_exc(to_print:bool=True):
    def onFunc(func):
        def onArgs(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
            except Exception:
                if to_print:
                    print('\n'.join([
                        "Exception", f"Func name: {func.__name__}", 
                        f"Type: {sys.exc_info()[0].__name__}",
                        f"Message: {str(sys.exc_info()[1])}"
                    ]) + '\n')
            else:
                return res
        return onArgs
    return onFunc


def infinite_loop(func, *args, **kwargs):
    func = catch_exc(to_print=True)(func)
    while True:
        func(*args, **kwargs)
