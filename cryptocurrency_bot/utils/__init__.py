import json


def merge_dicts(*dcts):
    assert len(dcts) > 1, 'you can pass minimum one dictionary'
    start_dct = dcts[0]
    for dct in dcts[1:]:
            for k, v in dct.items():
                    start_dct[k] = v
    return start_dct


def prettify_utcoffset(utcoffset:int=0):
    sign = '+' if utcoffset >= 0 else '-'
    return "UTC" if utcoffset == 0 else "UTC" + sign + "{:0>2}00".format(str(abs(utcoffset)))


def get_json_config():
    return json.load(open('configs\\config.json', 'r', encoding='utf-8'))
    

def get_default_values_from_config(*args):
    json_config = get_json_config()
    return {curr: json_config.get('initialValue' + curr, 1) for curr in args}



def prettify_float(num:float):
    return round(num, 3) if num // 1 > 0 else round(num, 6)
