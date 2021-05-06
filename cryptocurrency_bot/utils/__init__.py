import json
import os
import sys

from configs import settings
from . import decorators, agent, dt, telegram, translator



__all__ = [
    'merge_dicts', 'prettify_utcoffset', 'get_json_config', 'substract_percent',
    'get_default_rates', 'prettify_float', 'prettify_percent',
    'catch_exc', 'decorators', 'agent', 'dt', 'telegram', 'translator'
]


def merge_dicts(*dicts):
    assert len(dicts) > 0, 'you must pass minimum one dictionary'
    start_dct = dicts[0]
    for dct in dicts[1:]:
        start_dct = {**start_dct, **dct}
    return start_dct


@decorators.rangetest(strict_range=False, utcoffset=(-11, 12))
def prettify_utcoffset(utcoffset: int = 0):
    return "UTC" + ('' if utcoffset == 0 else '{:0=+3d}:00'.format(utcoffset))


def get_json_config():
    with open(os.path.join('configs', 'config.json'), 'r', encoding='utf-8') as f:
        return json.load(f)


def get_default_rates(*args, to_print: bool = True):
    if len(args) == 0:
        return None
    if to_print:
        print('[ERROR] Default value was used for: ' + ', '.join(args))
    json_config = get_json_config()
    return {curr: json_config.get('initialValue' + curr, 1) for curr in args}


def prettify_float(num: float):
    round_num = settings.PRECISION_NUMBER + (0 if num // 1 > 0 else 3)
    return int(num) if num % 1 == 0 else round(num, round_num)


def prettify_percent(n: float, to_sign: bool = False):
    res = n*100
    res = round(res, settings.PERCENT_PRECISION_NUMBER if res > 1 else 6)
    return ("{:+}%" if to_sign else "{}%").format(int(res) if res % 1 == 0 else res) 


@decorators.rangetest(strict_range=False, percent=(0.0, 1.0))
def substract_percent(value:float, percent:float):
    return prettify_float(value - (value * percent))


def catch_exc(to_print: bool = True):
    def on_func(func):
        def on_args(*args, **kwargs):
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
        return on_args
    return on_func


def infinite_loop(func, *args, **kwargs):
    func = catch_exc(to_print=True)(func)
    while True:
        func(*args, **kwargs)
