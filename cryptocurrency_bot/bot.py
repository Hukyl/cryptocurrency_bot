import json
import time
import copy
import threading
from concurrent import futures

from telebot import TeleBot
from telebot import types

from _parser import BrentParser
from TOKEN import TOKEN
from db import TelegramUserDBHandler, get_user_db, get_user
from translator import translate as _
import _globals

###################################################################################################################

bot = TeleBot(TOKEN)

db = TelegramUserDBHandler()

brent_parser = BrentParser()

###################################################################################################################

def kbs(buttons, one_time_keyboard=True):
    """
    Creates a Telegram Keybord
    :param buttons:
    :param one_time_keyboard:
    :return keyboard:
    """
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=one_time_keyboard, row_width=len(buttons)//2)
    kb.add(*[types.KeyboardButton(i) for i in buttons])
    return kb


###################################################################################################################

@bot.message_handler(commands=['start'])
def start_message(message):
    if not db.check_user(message.chat.id):
        db.add_user(message.chat.id, False, percent_delta=1)
    user = get_user_db(db, message.chat.id)
    kb = kbs([
        _('Курсы сегодня ⚖', user.language),
        _('Оповещения 🕒', user.language),
        _('Подписка 💰', user.language),
        _('Язык 🇬🇧', user.language)
    ])
    bot.send_message(message.chat.id, _(f"Привет, Я - твой личный бот акционер, и буду держать тебя в курсе самых важных частей трейдов! 💼📈📉📊", user.language), reply_markup=kb)
    bot.register_next_step_handler(message, choose_option, user)


@bot.message_handler(commands=['show_keyboard'])
def start_bot(message):
    user = get_user_db(db, message.chat.id)
    kb = kbs([
        _('Курсы сегодня ⚖', user.language),
        _('Оповещения 🕒', user.language),
        _('Подписка 💰', user.language),
        _('Язык 🇬🇧', user.language)
    ], one_time_keyboard=False)
    bot.send_message(message.chat.id, _(f"К вашим услугам!", user.language), reply_markup=kb)
    bot.register_next_step_handler(message, choose_option, user)


def choose_option(message, user=None):
    user = user or get_user_db(db, message.chat.id)
    if _('Курсы сегодня ⚖', user.language) == message.text:
        bot.send_message(message.chat.id, _(f"Курс BRENT - {brent_parser.rate} USD", user.language))
    elif _('Оповещения 🕒', user.language) == message.text:
        kb = kbs([
                _("Посмотреть информацию 📄", user.language),
                _('Изменить время оповещений 🕒', user.language),
                _('Изменить процент оповещений 󠀥󠀥󠀥💯', user.language),
                _('Включить/отключить оповещения ▶', user.language),
                _('В главное меню', user.language),
            ], one_time_keyboard=False)
        bot.send_message(message.chat.id, _('Выберите опцию', user.language), reply_markup=kb)
        return bot.register_next_step_handler(message, change_alarms, user)
    elif _('Подписка 💰', user.language) == message.text:
        bot.send_message(message.chat.id, _(f"Извините, подписка пока не реализована"))
    elif _('Язык 🇬🇧', user.language) in message.text:
        bot.send_message(
            message.chat.id, 
            _('На данный момент, на сервисе присутствует два языка: Русский 🇷🇺 и Английский 🇬🇧', user.language),
            reply_markup=kbs([_('Русский 🇷🇺', user.language), _('Английский 🇬🇧', user.language)]))
        return bot.register_next_step_handler(message, confirm_language, user)
    return bot.register_next_step_handler(message, choose_option, user)


def confirm_language(message, user):
    if _('Русский 🇷🇺', user.language) == message.text:
        db.change_user(user.user_id, language='ru')
    elif _('Английский 🇬🇧', user.language) == message.text:
        db.change_user(user.user_id, language='en')
    bot.send_message(message.chat.id, _("Язык успешно сменён", user.language))
    return start_bot(message)


def change_alarms(message, user):
    if _('Включить/отключить оповещения ▶', user.language) == message.text:
        db.change_user(user.user_id, is_active=not user.is_active)
        bot.send_message(
            message.chat.id,
            _(f"Уведомления {'включены ▶' if user.is_active else 'отключены ⏸'}", user.language))
    elif _('Изменить время оповещений 🕒', user.language) == message.text:
        return change_check_times(message, user)
    elif _('Изменить процент оповещений 󠀥󠀥󠀥💯', user.language) == message.text:
        kb = kbs(_globals.PERCENTAGES)
        bot.send_message(message.chat.id, _("Введите кол-во процентов", user.language), reply_markup=kb)
        return bot.register_next_step_handler(message, change_percent_delta, user)
    elif _("Посмотреть информацию 📄", user.language) == message.text:
        info = f"Пользователь @{message.from_user.username};ID на сервисе: {user.id};Telegram ID: {user.user_id};Подписка: {'есть' if user.is_pro else 'нету'};Оповещения: {'включены' if user.is_active else 'отключены'};Процент оповещений: {user.percent_delta}%;Время оповещений: {', '.join(user.check_times)}"
        bot.send_message(message.chat.id, _(info, user.language).replace(';', '\n'))
    elif _('В главное меню', user.language) in message.text:
        return start_bot(message)
    return bot.register_next_step_handler(message, change_alarms, user)


def change_percent_delta(message, user):
    try:
        if 'inf' not in message.text:
            delta = float(message.text)
        else:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, _("Пожалуйста, вводите только числа", user.language))
        return bot.register_next_step_handler(message, change_percent_delta, user)
    db.change_user(user.user_id, percent_delta=delta)
    bot.send_message(message.chat.id, _(f"Ваш процент теперь стал {delta}%", user.language))
    return start_bot(message)


def change_check_times(message, user):
    available_times = copy.deepcopy(_globals.CHECK_TIMES)
    chosen_times = []
    start = _globals.UNSUBSCIRBED_USER_CHECK_TIMES if not user.is_pro else _globals.SUBSCIRBED_USER_CHECK_TIMES

    def inner(message, iteration_num):
        nonlocal chosen_times, available_times
        try:
            if message.text in _globals.CHECK_TIMES:
                time.strptime(message.text, '%H:%M')
                iteration_num -= 1
                available_times.remove(message.text)
                chosen_times.append(message.text)
            else:
                raise ValueError

            if iteration_num == 0:
                db.change_user(user.user_id, check_times=','.join(chosen_times))
                bot.send_message(message.chat.id, _("Ваши времена проверки такие: " + ", ".join(chosen_times), user.language))
                return start_bot(message)
        except ValueError: # if time not in CHECK_TIMES or time is not valid
            bot.send_message(message.chat.id, _("Вводите только доступные даты", user.language))
            return bot.register_next_step_handler(message, inner, iteration_num)
        else:
            date_word = "дат" if iteration_num > 4 else "даты" if 1 < iteration_num <= 4 else "дату"
            bot.send_message(
                message.chat.id,
                _(
                    f"Введите ещё {iteration_num} {date_word}",
                    user.language),
                reply_markup=kbs(available_times)
            )
            bot.register_next_step_handler(message, inner, iteration_num)
    bot.send_message(
        message.chat.id,
        _(
            f'Выберите {start} {"дат" if start > 4 else "даты" if 1 < start <= 4 else "дату"}',
            user.language
        ),
        reply_markup=kbs(available_times))
    bot.register_next_step_handler(message, inner, start)


def buy_subscription(message):
    ...



###################################################################################################################


def check_time():
    while True:
        t = str(time.strftime('%H:%M'))
        if t in _globals.CHECK_TIMES:
            thread = threading.Thread(target=start_alarms, args=(t,), daemon=True)
            thread.start()
        time.sleep(60)


def start_alarms(time_):
    active_users = db.get_users_by_check_time(time_)
    with futures.ThreadPoolExecutor(max_workers=50) as executor:
        for user in active_users:
            user = get_user(*user)
            executor.submit(send_alarm, user)


def send_alarm(user):
    p = BrentParser(initial_value=user.initial_value)
    res = p.check_delta(percent_delta=user.percent_delta)
    if res.get('new', None): # WARNING: CAN BE DELETED, MAKE AN AGREEMENT WITH CLIENT
        new, old = res.get('new'), res.get('old')
        db.change_user(user.user_id, initial_value=new)
        real_perc_delta = round((max(new, old) - min(new, old)) / min(new, old) * 100, _globals.PRECISION_NUMBER)
        bot.send_message(
            user.user_id,
            _(
                f"Цена BRENT - {new} USD\nИзменение составило {round(abs(old - new), _globals.PRECISION_NUMBER)}, или {real_perc_delta}%\nПредыдущая цена BRENT - {old} USD",
                user.language
            )
        )



###################################################################################################################

if __name__ == '__main__':
    check_thread = threading.Thread(target=check_time, daemon=True)
    check_thread.start()
    print(f"[INFO] Bot started at {str(time.strftime('%H:%M:%S'))}")
    bot.polling()
    print(f"[INFO] Bot stopped at {str(time.strftime('%H:%M:%S'))}")
