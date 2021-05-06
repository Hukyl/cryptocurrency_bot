import threading
import sys
from time import sleep

from models.user import *
from utils import dt
from utils import infinite_loop


def get_ints_safe(args):
    try:
        args = [int(x) for x in args]
    except ValueError:
        print(f"FAILURE: Enter only valid integers for user ids: {', '.join(args)}")
        sys.exit(1)
    return args

#########################################################################################


def runbot(*args):
    import main_bot
    if_debug = '-d' in args or '--DEBUG' in args
    targets = [
        *main_bot.THREAD_LIST,
        main_bot.bot.infinity_polling,
    ]
    if if_debug:
        for target in targets:
            threading.Thread(target=target, daemon=True).start()
    else:
        for target in targets:
            threading.Thread(target=infinite_loop, args=(target,), daemon=True).start()
    print(
        f"[INFO]{' [DEBUG]' if if_debug else ''} Bot started at {dt.get_now()}"
    )
    while True:
        try:
            sleep(100000)
        except KeyboardInterrupt:
            break
    print(
        f"[INFO]{' [DEBUG]' if if_debug else ''} Bot stopped at {dt.get_now()}"
    )


def check_subscribed(*args):
    args = get_ints_safe(args)
    for user_id in args:
        if not User.db.check_user_exists(user_id):
            print(f"FAILURE: No user found by id: {user_id}")
            continue
        user = User(user_id)
        if user.is_pro:
            print(f"SUCCESS: User {user_id} IS subscribed until {dt.convert_to_country_format(user.is_pro, 'ru')} UTC")
        else:
            print(f"SUCCESS: User {user_id} IS NOT subscribed")


def give_staff(*args):
    args = get_ints_safe(args)
    for user_id in args:
        if not User.db.check_user_exists(user_id):
            print(f"FAILURE: No user found by id: {user_id}")
            continue
        user = User(user_id)
        if user.is_staff:
            print(f"FAILURE: User {user_id} already has a staff membership")
        else:
            user.init_staff()
            print(f"SUCCESS: User {user_id} received a staff membership")


def remove_staff(*args):
    args = get_ints_safe(args)
    for user_id in args:
        if not User.db.check_user_exists(user_id):
            print(f"FAILURE: No user found by id: {user_id}")
            continue
        user = User(user_id)
        if not user.is_staff:
            print(f"FAILURE: User {user_id} has no staff membership")
        else:
            user.delete_staff()
            print(f"SUCCESS: User {user_id} doesn't have a staff membership now")


def get_notification_count(*args):
    args = get_ints_safe(args)
    for user_id in args:
        if not User.db.check_user_exists(user_id):
            print(f"FAILURE: No user found by id: {user_id}")
            continue
        session = Session(user_id)
        print(f"SUCCESS: User {user_id} has {session.free_notifications_count} notifications left")


def set_notification_count(*args):
    args = get_ints_safe(args)
    if len(args) != 2:
        print(f"FAILURE: unsupported number of operands: {len(args)}")
        sys.exit(1)
    user_id, new_count = args
    if not User.db.check_user_exists(user_id):
        print(f"FAILURE: No user found by id: {user_id}")
        sys.exit(1)
    session = Session(user_id)
    session.set_count(new_count)
    print(f"SUCCESS: User {user_id} notification count has been set to {new_count}")



def help_message():
    message = """Utility for bot managing

commands:
    run [-d, --DEBUG] - run bot with(-out) debug flag.
    give-staff [user_id] [user_id] [...] - give staff membership to users.
    remove-staff [user_id] [user_id] [...] - remove staff from users.
    check-subscribed [user_id] [user_id] [...] - check whether users are subscribed.
    get-notification-count [user_id] [user_id] [...] - get notifications count for users.
    set-notification-count [user_id] [count] - set new notifications count.
    help - see help.
"""
    print(message)


if __name__ == '__main__':
    commands = {
        'remove-staff': remove_staff,
        'give-staff': give_staff,
        'check-subscribed': check_subscribed,
        'run': runbot,
        'get-notification-count': get_notification_count,
        'set-notification-count': set_notification_count,
        'help': help_message
    }
    filename, *args = sys.argv[:]
    if len(args) == 0:
        help_message()
        sys.exit(0)
    else:
        func, *args = args
        func = commands.get(func, None)
        if func is None:
            print("FAILURE: Unknown command.")
            help_message()
        else:
            func(*args)
            sys.exit(0)
