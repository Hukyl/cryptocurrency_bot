import datetime as dt
from . import prettify_utcoffset



def add_offset(d:dt.datetime, utcoffset:int=0):
    """
    Adds tzinfo to `d` according to `utcoffset` offset
    """
    return d.replace(
            tzinfo=dt.timezone(dt.timedelta(0, utcoffset*60*60)) 
        )


def get_current_datetime(utcoffset:int=0):
    assert utcoffset in range(-11, 13), 'time zones are in range from -11 to +12'
    n = dt.datetime.utcnow()
    n = n.replace(
        day=n.day + ((n.hour + utcoffset) // 24),
        hour=(n.hour + utcoffset) % 24,
        microsecond=0
    )
    return add_offset(n, utcoffset)


def check_datetime_in_future(up_to_date:dt.datetime):
    assert up_to_date.tzinfo is not None, 'can compare only timezone-aware datetime'
    now = get_current_datetime() 
    return up_to_date >= now


def convert_from_country_format(datetime_str:str, country:str, utcoffset:int=0):
    assert utcoffset in range(-11, 13), 'time zones are in range from -11 to +12'
    if country == 'ru':
        check_str = '%d.%m.%Y %H:%M'
    elif country == 'en':
        check_str = '%m-%d-%Y %I:%M %p'
    else:
        check_str = '%Y-%m-%d %H:%M'
    d = dt.datetime.strptime(datetime_str, check_str)
    return add_offset(d, utcoffset)


def convert_to_country_format(d:dt.datetime, country:str, no_offset:bool=False):
    if country == 'ru':
        format_str = '%d.%m.%Y %H:%M'
    elif country == 'en':
        format_str = '%m-%d-%Y %I:%M %p'
    else:
        format_str = '%Y-%m-%d %H:%M'
    if d.tzinfo and (not no_offset):
        format_str += f" UTC{str(d)[-6:]}" # " UTC+02:00"
    return d.strftime(format_str)


def check_check_time_in_rate(user_check_times:list, check_time:str, user_timezone:int=0):
    for t_ in user_check_times:
        t_no_offset = '{}:{:0>2}'.format(int(t_.split(':')[0]) - user_timezone, t_.split(":")[1]) # "17:00", offset=2 -> "15:00"
        if check_time == t_no_offset:
            return True
    return False


def get_country_dt_example(language:str='en'):
    examples = {
        'ru': 'ДД.ММ.ГГГГ ЧЧ:ММ',
        'en': 'MM-DD-YYYY HH:МI AM/PM',
        'default': 'YYYY-MM-DD HH:MI'
    }
    return examples.get(language, examples['default'])