# Settings for cryptocurrency_bot
# Author: Hukyl
# Email: a.shalaev7125@gmail.com


TOKEN = '1421475661:AAFR0vGFtWo4rmd7eq-MMZctr2rxfzfqf1c'
PAYMENT_TOKEN = '401643678:TEST:36b3e5b5-0ab7-4fbd-beca-8a11ce7100d8'  # test token from Sberbank


ACCESSIBLE_LINK = "https://t.me/{}?start=support" # {} - bot username


DB_NAME = 'db.sqlite3' # 'db.sqlite3' - for production use, 'test.sqlite3' -  for tests


CHECK_TIMES = [
    '05:00', '07:00', '09:00', '11:00', '13:00', 
    '15:00', '17:00', '19:00', '21:00', '23:00'
]
DEFAULT_CHECK_TIMES = ['9:00', '15:00', '21:00']


PERCENTAGES = ['0.2', '0.4', '0.6', '0.8', '1.0', '1.2', '1.4', '1.6', '1.8', '2.0']


# Currencies supported
CURRENCIES = ['BTC', 'BRENT', 'RTS', 'Gold', 'Silver', 'Platinum'] 
MAIN_CURRENCIES = CURRENCIES[:3]


# Currency exchange
ACCEPTABLE_CURRENCIES_CONVERTION = {
    **{'BRENT futures': "BRENT-USD", 'RTS futures': "RTS-USD"}, 
    **{f"{curr}-USD": f"{curr}-USD" for curr in CURRENCIES if curr != "RTS" and curr != "BRENT"}
}
CURRENCY_RATES_CHANGE_AMOUNTS = ['Reset', '...']


UNSUBSCIRBED_USER_CHECK_TIMES = 3
SUBSCIRBED_USER_CHECK_TIMES = len(CHECK_TIMES)


# Precisions
PRECISION_NUMBER = 2
PERCENT_PRECISION_NUMBER = 1


# Sessions
DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER = 10
