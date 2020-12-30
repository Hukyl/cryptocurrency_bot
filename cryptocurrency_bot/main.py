import threading
import sys
from time import sleep
import datetime

import main_bot
import techsupport_bot



def infinite_loop(func, *args, **kwargs):
    while True:
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(repr(e))
        else:
            break



if __name__ == '__main__':
    targets = [
        main_bot.check_alarm_times,
        main_bot.update_rates,
        main_bot.check_premium_ended,
        main_bot.verify_predictions,
        main_bot.bot.infinity_polling,
        techsupport_bot.bot.infinity_polling
    ]
    for target in targets:
        threading.Thread(target=target, daemon=True).start()
    print(f"[INFO] Bot started at {str(datetime.datetime.utcnow().time().strftime('%H:%M:%S'))}")
    while True:
        try:
            sleep(100000)
        except KeyboardInterrupt:
            print(f"[INFO] Bot stopped at {str(datetime.datetime.utcnow().time().strftime('%H:%M:%S'))}")
            sys.exit(0)
