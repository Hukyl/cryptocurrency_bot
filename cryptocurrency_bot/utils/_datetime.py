import datetime


def get_current_datetime(utcoffset:int=0):
    n = datetime.datetime.utcnow()
    n = n.replace(
        day=n.day + ((n.hour + utcoffset) // 24),
        hour=(n.hour + utcoffset) % 24,
        tzinfo=datetime.timezone(datetime.timedelta(0, utcoffset*60*60)) 
    )
    return n


def check_datetime_in_future(up_to_date:datetime.datetime, utcoffset:int=0):
    return (get_current_datetime(utcoffset) - up_to_date).total_seconds() <= 0


def convert_from_country_format(datetime_str:str, country:str):
    if country == 'ru':
        check_str = '%d.%m.%Y %H:%M'
    elif country == 'en':
        check_str = '%m-%d-%Y %I:%M %p'
    else:
        check_str = '%Y-%m-%d %H:%M'
    return datetime.datetime.strptime(datetime_str, check_str)


def convert_to_country_format(datetime_:datetime.datetime, country:str):
    if country == 'ru':
        format_str = '%d.%m.%Y %H:%M'
    elif country == 'en':
        format_str = '%m-%d-%Y %I:%M %p'
    else:
        format_str = '%Y-%m-%d %H:%M'
    return datetime_.strftime(format_str)