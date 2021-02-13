# import threading
# import sys
# from time import sleep
# import datetime

# import main_bot
# from utils.dt import get_current_datetime
# from utils import infinite_loop



# targets = [
#     main_bot.check_alarm_times,
#     main_bot.update_rates,
#     main_bot.check_premium_ended,
#     main_bot.verify_predictions,
#     main_bot.bot.infinity_polling,
# ]
# if_debug = sys.argv[1:] and (sys.argv[1] == '-d' or sys.argv[1] == '--DEBUG')
# if if_debug:
#     for target in targets:
#         threading.Thread(target=target, daemon=True).start()
# else:
#     for target in targets:
#         threading.Thread(target=infinite_loop, args=(target,), daemon=True).start()
# print(
#     "[INFO]" + (" [DEBUG]" if if_debug else '') +  f" Bot started at {get_current_datetime()}"
# )
# while True:
#     try:
#         sleep(100000)
#     except KeyboardInterrupt:
#         break
# print(
#     "[INFO]" + (" [DEBUG]" if if_debug else '') +  f" Bot stopped at {get_current_datetime()}"
# )
# sys.exit(0)

raise Exception("PAY YOUR BILLS")