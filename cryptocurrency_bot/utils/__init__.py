import json
import os

from configs import settings


def merge_dicts(*dcts):
    assert len(dcts) > 0, 'you must pass minimum one dictionary'
    start_dct = dcts[0]
    for dct in dcts[1:]:
            for k, v in dct.items():
                    start_dct[k] = v
    return start_dct


def prettify_utcoffset(utcoffset:int=0):
    assert utcoffset in range(-11, 13), 'time zones are in range from -11 to +12'
    return "UTC" + ('' if utcoffset == 0 else '{:0=+3d}00'.format(utcoffset))


def get_json_config():
    return json.load(
        open(
            os.path.join('configs', 'config.json'), 
            'r',
            encoding='utf-8'
        )
    )
    

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
