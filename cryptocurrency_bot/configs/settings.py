CHECK_TIMES = [
    '05:00', '07:00', '09:00', '11:00', '13:00', 
    '15:00', '17:00', '19:00', '21:00', '23:00'
]
DEFAULT_CHECK_TIMES = ['9:00', '15:00', '21:00']
PERCENTAGES = ['0.2', '0.4', '0.6', '0.8', '1.0', '1.2', '1.4', '1.6', '1.8', '2.0']
CURRENCIES = ['BTC', 'BRENT', 'RTS', 'Gold', 'Silver', 'Platinum'] 
MAIN_CURRENCIES = CURRENCIES[:3]
ACCEPTABLE_CURRENCIES_CONVERTION = {
    **{'BRENT futures': "BRENT-USD", 'RTS futures': "RTS-USD"}, 
    **{f"{curr}-USD": f"{curr}-USD" for curr in CURRENCIES if curr != "RTS" and curr != "BRENT"}
}
CURRENCY_RATES_CHANGE_AMOUNTS = ['Reset', '...']
UNSUBSCIRBED_USER_CHECK_TIMES = 3
SUBSCIRBED_USER_CHECK_TIMES = len(CHECK_TIMES)
PRECISION_NUMBER = 2
PERCENT_PRECISION_NUMBER = 1
DB_NAME = 'db.sqlite3' # production use - 'db.sqlite3', tests - 'test.sqlite3'
