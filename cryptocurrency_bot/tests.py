import os

os.system('del db.sqlite3')

import main_bot
import main
import models
import configs
import utils

#################### WARNING: DELETE DB BEFORE TESTING ############################

# utils/__init__.py
assert utils.merge_dicts({'1': 1, '2':2, '3':3}, {'2':4}) == {'1': 1, '2':4, '3':3}, 'wrong merging in merge_dicts'
assert utils.merge_dicts({'1': 1}) == {'1':1}, 'wrong merging for one dict in merge_dicts'
try:
    utils.merge_dicts()
except AssertionError:
    pass
else:
    assert False, 'merge_dicts works with no dictionaries'

assert utils.prettify_utcoffset(3) == 'UTC+0300', 'wrong normalizing utcoffset'
assert utils.prettify_utcoffset(0) == 'UTC', 'wrong normalizing utcoffset'
assert utils.prettify_utcoffset(-11) == 'UTC-1100', 'wrong normalizing utcoffset'
try:
    utils.prettify_utcoffset(-15)
    utils.prettify_utcoffset(18)
except AssertionError:
    pass
else:
    assert False, 'prettify_utcoffset works with invalid parameters'

assert isinstance(utils.get_json_config(), dict), 'can\'t get json config'

assert all(
    x != 1 
    for x in utils.get_default_values_from_config(*configs.settings.CURRENCIES).values()
), 'can\'t get default values for currencies that ARE present in config'
assert all(
    x == 1 
    for x in utils.get_default_values_from_config('UAH', 'RUB', 'EUR').values()
), 'doesn\'t get default values for currencies that ARE NOT present in config'

assert utils.prettify_float(1.123456) == 1.123, 'wrong prettify_float'
assert utils.prettify_float(0.1234567) == 0.123457, 'wrong prettify_float'

assert utils.prettify_percent(0.15) == '15%'
assert utils.prettify_percent(0.155) == '15.5%'
assert utils.prettify_percent(0.001) == '0.1%'

print('Passed utils/__init__.py tests')

# utils/translator.py
assert utils.translator.translate('Back', 'ru') == 'Назад' # written
assert utils.translator.translate('Path', 'ru') == 'Путь' # api

print('Passed utils/translator.py tests')

# models/_parser.py
assert models._parser.CurrencyParser.calculate_difference( 
        old=55, new=54.85
    ).get('percentage_difference') == -0.002727

print('Passed models/_parser.py tests')


# models/user.py
user = models.user.DBUser(0)
assert len(user.rates) == len(configs.settings.CURRENCIES)
assert sorted(user.get_currencies_by_check_time(configs.settings.DEFAULT_CHECK_TIMES[0])) == sorted(configs.settings.CURRENCIES)
user.update(language='oops')
assert user.language == 'oops'
assert user.db.get_user(user.user_id)[-1] == 'oops'

user.update(is_active=True)

user.create_prediction(
    utils._datetime.get_current_datetime().replace(hour=23, minute=59, second=59),
    'BRENT', 
    'USD',
    50
)
try:
    user.create_prediction(
        utils._datetime.get_current_datetime().replace(hour=0, minute=0),
        'BRENT', 
        'USD',
        50
    )
except AssertionError:
    pass
else:
    assert False

predictions = list(user.get_predictions(if_all=True))
assert len(predictions) == 1
pred = predictions[0]

user.update_rates(
    configs.settings.CURRENCIES[0], 
    check_times=['00:01', '00:02', '00:03']
)
assert user.rates[configs.settings.CURRENCIES[0]]['check_times'] == ['00:01', '00:02', '00:03']
assert len(
        [
            rate 
            for rate in user.db.get_user(user.user_id)[-3] 
            if rate[-1].split(',') == ['00:01', '00:02', '00:03']
        ]
    ) == 1
user.add_rate('UAH')
assert len(user.rates) == len(configs.settings.CURRENCIES) + 1
assert len(user.db.get_user(user.user_id)[-3]) == len(configs.settings.CURRENCIES) + 1
assert list(user.db.get_users_by_check_time('00:01'))[0][1] == user.user_id

user.init_premium(
    utils._datetime.get_current_datetime().replace(hour=23, minute=59, second=59)
)
assert user.is_pro != None
assert len(list(user.db.get_pro_users())) == 1

user.delete_premium()
assert user.is_pro == None
assert len(list(user.db.get_pro_users())) == 0

user.init_staff()
assert user.is_pro != None and user.is_staff == True
assert len(list(user.db.get_pro_users())) == 1
assert len(list(user.db.get_users_by_check_time(configs.settings.CHECK_TIMES[-1]))) == 1

user.delete_staff()
assert user.is_pro == None and user.is_staff == False
assert len(list(user.db.get_pro_users())) == 0
assert len(list(user.db.get_users_by_check_time(configs.settings.CHECK_TIMES[-1]))) == 0

pred.toggle_like(0, True)
assert pred.likes == 1


pred.toggle_like(0, False)
assert pred.likes == 0 and pred.dislikes == 1
assert pred.db.get_number_likes(pred.id) == 0 and pred.db.get_number_dislikes(pred.id) == 1

assert pred.is_actual

pred.update(
    up_to_date=utils._datetime.get_current_datetime().replace(
        hour=0, 
        minute=0, 
        second=0
    )
)
assert len(list(models.user.DBCurrencyPrediction.get_unverified_predictions())) == 1

assert models.user.DBCurrencyPrediction.get_all_prediction_number() == 1

assert models.user.DBCurrencyPrediction.get_random_prediction() == pred.id

assert not pred.is_actual

assert pred.real_value == None
assert pred.db.get_prediction(pred.id)[-1] == None
pred.update(real_value=51)
assert pred.real_value == 51
assert pred.db.get_prediction(pred.id)[-1] == 51


pred.update(is_by_experts=True)
assert len(list(pred.get_experts_predictions(True))) == 1
assert len(list(models.user.DBCurrencyPrediction.get_experts_predictions(True))) == 1

pred.delete()

assert len(list(user.get_predictions(if_all=True))) == 0

print('Passed models/user.py tests')