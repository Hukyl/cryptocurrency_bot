from concurrent import futures
import datetime
import threading
import time
import json

from telebot import TeleBot
from telebot.types import LabeledPrice
from telebot import apihelper

from configs import _globals, MAIN_TOKEN
from models._parser import *
from models.user import DBUser, DBCurrencyPrediction
from utils import merge_dicts, prettify_utcoffset
from utils.translator import translate as _
from utils.telegram import kbs, inline_kbs
from utils._datetime import (
    check_datetime_in_future,
    convert_from_country_format,
    convert_to_country_format,
    get_current_datetime
)
from techsupport_bot import bot as support_bot, send_message_to_techsupport

# !!!!!!!!!!!!!!!!!!! ALL COMMENTED CODE IN ALL FILES IS IMPLEMENTATION OF LIKING SYSTEM !!!!!!!!!!!!!!!!!!!!!!!!!!
###################################################################################################################
apihelper.ENABLE_MIDDLEWARE = True

bot = TeleBot(MAIN_TOKEN.TOKEN) # threaded=True
bot.bot_commands = {
    '/start': 'Start the bot',
    '/me': 'See your info',
    '/today': 'Get exchange rates today',
    '/change_checktime': 'Change the check time of the currency rate changes',
    '/change_delta': 'Change percent delta at which to notify',
    '/change_timezone': 'Change your timezone',
    '/toggle_alarms': 'Enable/disable notifications',
    '/make_prediction': 'Make a prediction',
    '/get_predictions': 'Get to predictions menu',
    '/convert': 'Currency converter',
    '/menu': 'Go to menu',
    '/subscription': 'Go to subsciption section',
    '/language': 'Change language',
    '/help': 'See help'
}


brent_parser = BrentParser()
bitcoin_parser = BitcoinParser()
rts_parser = RTSParser()
currency_parser = FreecurrencyratesParser()

###################################################################################################################



@bot.middleware_handler(update_types=['message'])
def check_if_command(bot_instance, message):
    is_command = bot_instance.bot_commands.get(message.text, None) is not None
    if is_command:
        bot_instance.clear_step_handler(message)




@bot.message_handler(commands=['start'])
def start_message(msg):
    user = DBUser(msg.chat.id)
    bot.send_photo(msg.chat.id, 'https://minfin.com.ua/img/2020/41845791/d9aebb8711b9b0f6261f9abbc18032a0.jpeg?1584112216')
    bot.send_message(msg.chat.id, _(f'Добро пожаловать, {msg.from_user.first_name}!', user.language))
    bot.send_message(msg.chat.id, _(f"Я - <b>{bot.get_me().first_name}</b>, твой личный бот акционер, и буду держать тебя в курсе важных событий трейдинга! 💼⚖📊", user.language), parse_mode='html')
    return start_bot(msg)



@bot.message_handler(commands=['menu'])
def start_bot(msg):
    user = DBUser(msg.chat.id)
    buttons = [
        _('Курсы сегодня ⚖', user.language),
        _('Оповещения 🕒', user.language),
        _('Подписка 💰', user.language),
        _('Язык 🇬🇧', user.language),
        _('Техподдержка ⚙', user.language)
    ]   
    kb = kbs(buttons, one_time_keyboard=False)
    bot.send_message(msg.chat.id, _(f"К вашим услугам!", user.language), reply_markup=kb)
    bot.register_next_step_handler(msg, choose_option, user=user, buttons=buttons)



def choose_option(msg, user=None, buttons=None):
    buttons = buttons or []
    user = user or DBUser(msg.chat.id)
    if buttons[0] == msg.text:
        # see exchange rates for today
        return get_currency_rates_today(msg, user)
    elif buttons[1] == msg.text:
        # go to notifications section
        buttons = {
            _("Посмотреть информацию 📄", user.language): see_user_info,
            _('Изменить время оповещений 🕒', user.language): change_user_rate_check_times,
            _('Изменить процент оповещений 󠀥󠀥󠀥💯', user.language):change_user_rate_percent_delta,
            _('Включить/отключить оповещения ▶', user.language): toggle_user_alarms,
            _('Изменить часовой пояс 🌐', user.language): change_user_timezone,
            _('В главное меню', user.language): start_bot
        }
        if user.is_pro:
            buttons[ _('⚜ Добавить свою валюту ⚜', user.language)] = add_new_currency
        kb = kbs(list(buttons), one_time_keyboard=False, row_width=2)
        bot.send_message(
            msg.chat.id,
            _('Выберите опцию', user.language),
            reply_markup=kb
        )
        return bot.register_next_step_handler(msg, change_alarms, user, buttons)
    elif buttons[2] == msg.text:
        return buy_subscription(msg)
    elif buttons[-2] == msg.text:
        # change system language
        return change_language(msg)
    elif buttons[-1] == msg.text:
        return send_techsupport_message(msg)
    else:
        bot.send_message(
            msg.chat.id,
            _(
                "❗ Я не понял ваш ответ, попробуйте что-то другое ❗",
                user.language
            ),
            reply_markup=kbs(list(buttons))
        )
        return bot.register_next_step_handler(msg, choose_option, user, buttons)



@bot.message_handler(commands=['today'])
def get_currency_rates_today(msg, user=None):
    user = user or DBUser(msg.chat.id)
    buttons_dct = {
            _('Сделать прогноз 📈📉', user.language): make_user_currency_prediction,
            _('Посмотреть прогнозы 📊', user.language): see_users_currency_predicitions,
            _('Узнать курс валюты ⚖', user.language): convert_currency,
            _('В главное меню', user.language): start_bot
        }

    def choose_option_inner(msg):
        if buttons_dct.get(msg.text, None) is None:
            bot.send_message(msg.chat.id, _('❗ Выберите только из предложенного ❗', user.language))
            bot.register_next_step_handler(msg, choose_option_inner)
        else:
            # bot.send_message(
            #     msg.chat.id,
            #     _(
            #         f"❗ Please aware, that time of alerts and forecasts is in UTC+0300 only, which now is {convert_to_country_format(get_current_datetime(user.timezone), user.language)} ❗",
            #         user.language
            #     )
            # )
            return buttons_dct.get(msg.text)(msg)

    bot.send_message(
        msg.chat.id,
        f"{brent_parser.to_string(to_update=False)}\n"
        f"{bitcoin_parser.to_string(to_update=False)}\n"
        f"{rts_parser.to_string(to_update=False)}",
        reply_markup=kbs(list(buttons_dct))
    )
    bot.register_next_step_handler(msg, choose_option_inner)



@bot.message_handler(commands=['make_prediction'])
def make_user_currency_prediction(msg):
    user = DBUser(msg.chat.id)
    date = None
    iso_from = iso_to = None
    value = None


    def get_date(msg):
        nonlocal date
        try:
            up_to_date = convert_from_country_format(msg.text, user.language)
            assert check_datetime_in_future(up_to_date)
        except ValueError:
            bot.send_message(msg.chat.id, _('❗ Вводите дату только в указаном формате ❗', user.language))
            bot.register_next_step_handler(msg, get_date)
        except AssertionError:
            bot.send_message(msg.chat.id, _('❗ Вы не можете ввести уже прошедшую дату ❗', user.language))
            bot.register_next_step_handler(msg, get_date)
        else:
            date = up_to_date
            bot.send_message(
                msg.chat.id,
                _(
                    'Введите iso-код валюты прогноза <b><code>&#60;изо-код&#62;-&#60;изо-код&#62;</code></b>',
                    user.language
                ),
                parse_mode='html',
                reply_markup=kbs(_globals.ACCEPTABLE_CURRENCIES_CONVERTION)
            )
            bot.register_next_step_handler(msg, get_iso)


    def get_iso(msg):
        nonlocal iso_from, iso_to
        iso_from, iso_to = [x.strip() for x in msg.text.split('-')]
        if currency_parser.check_currency_exists(iso_from) and currency_parser.check_currency_exists(iso_to) or (
                msg.text in _globals.ACCEPTABLE_CURRENCIES_CONVERTION
            ):
            bot.send_message(msg.chat.id, _("Введите результат прогноза (например, 27.50, 22300)", user.language))
            bot.register_next_step_handler(msg, get_value)
        else:
            bot.send_message(
                msg.chat.id,
                _("❗ Такой валюты не существует или она не поддерживается, выберите другую ❗", user.language)
            )
            bot.register_next_step_handler(msg, get_iso)


    def get_value(msg):
        nonlocal value
        try:
            value = float(msg.text.replace(',', '.'))
        except ValueError:
            bot.send_message(msg.chat.id, _('❗ Вводите только числа ❗', user.language))
            bot.register_next_step_handler(msg, get_value)
        else:
            bot.send_message(
                msg.chat.id, 
                _(
                    f'Вот данные проноза:;Период прогноза: {convert_to_country_format(date, user.language)};Валюта: {iso_from}-{iso_to};Значение: {value};.;Подтвердить создание прогноза?',
                    user.language,
                    parse_mode='newline'
                ),
                reply_markup=kbs([_('Да ✔', user.language), _('Нет ❌', user.language)])
            )
            bot.register_next_step_handler(msg, confirm_prediction)

    def confirm_prediction(msg):
        if msg.text == _('Да ✔', user.language):
            user.create_prediction(date, iso_from, iso_to, value)
            bot.send_message(msg.chat.id, _('Прогноз создан!', user.language))
            return start_bot(msg)
        elif msg.text ==  _('Нет ❌', user.language):
            bot.send_message(msg.chat.id, _('Прогноз не создан', user.language))
            return start_bot(msg)
        else:
            bot.send_message(msg.chat.id, _('Ответ не обработан', user.language))
            return start_bot(msg)

    bot.send_message(
        msg.chat.id,
        _('Для выхода в любом месте введите <b><code>Меню</code></b>', user.language),
        parse_mode='html'
    )
    datetime_check_str = 'ДД.ММ.ГГГГ ЧЧ:ММ' if user.language ==  'ru' else 'MM-DD-YYYY HH:ММ AM/PM'
    datetime_example = '30.12.2021 22:00' if user.language == 'ru' else '12-30-2021 10:00 PM'
    bot.send_message(
        msg.chat.id, 
        _(
            'Выберите период действия прогноза в формате <b><code>{check_str} </code></b>;Например, {example}', 
            user.language,
            parse_mode='newline'
        ).format(check_str=datetime_check_str, example=datetime_example),
        parse_mode='html'
    )
    bot.register_next_step_handler(msg, get_date)



@bot.message_handler(commands=['get_predictions'])
def see_users_currency_predicitions(msg):
    user = DBUser(msg.chat.id)

    def see_self_predictions(msg):
        preds = {
                repr(x): f'get_prediction_{x.id}'
                for x in user.get_predictions()
            }
        kb_inline = inline_kbs(preds, row_width=1)
        if len(preds) == 0:
            bot.send_message(msg.chat.id, _('You have no predictions so far, create one!', user.language))
        else:
            bot.send_message(msg.chat.id, _('Here are your predictions', user.language), reply_markup=kb_inline)
        return see_users_currency_predicitions(msg)

    def see_other_users_predictions(msg):
        if user.is_pro:
            experts_str = '⚜ Experts predictions ⚜ are:'
            experts_iter = iter(DBCurrencyPrediction.get_experts_predictions(if_all=True))
            for _n in range(5):
                try:
                    expert_pred = next(experts_iter)
                except StopIteration:
                    break
                experts_str += f'\n\n{str(expert_pred)}'
            if experts_str.endswith(':'):
                experts_str += ' none'
            bot.send_message(
                msg.chat.id, 
                _(
                    experts_str.replace('\n', ';'),
                    user.language,
                    parse_mode='newline'
                ),
            )

        # predictions_str = 'Most liked predictions are:'
        # i = iter(DBCurrencyPrediction.get_most_liked_predictions())
        # for _n in range(5):
        #     try:
        #         pred = next(i)
        #     except StopIteration:
        #         break
        #     predictions_str += f'\n\n{str(pred)}'
        # if predictions_str.endswith(':'):
        #     predictions_str += ' none'
        # bot.send_message(
        #     msg.chat.id, 
        #     _(
        #         predictions_str.replace('\n', ';'),
        #         user.language,
        #         parse_mode='newline'
        #     ),
        # )
        return see_users_currency_predicitions(msg)

    def like_system(msg):
        try:
            random_id = DBCurrencyPrediction.get_random_prediction()
        except IndexError: # if no prediction are there
            bot.send_message(msg.chat.id, _('There are no predictions to like yet, you can create one!', user.language))
            return start_bot(msg)
        else:
            prediction = DBCurrencyPrediction(random_id)
            closest = prediction.get_closest_neighbours()
            previous, next = closest['previous'], closest['next']
            inline_buttons = {
                '👍': f'like_prediction_{prediction.id}',
                '👎': f'dislike_prediction_{prediction.id}'
            }
            if previous:
                inline_buttons['<<'] = f'previous_prediction_to_{prediction.id}'
            if next:
                inline_buttons['>>'] = f'next_prediction_to_{prediction.id}'
            inline_kb = inline_kbs(inline_buttons, row_width=2)
            bot.send_message(
                msg.chat.id,
                _(
                    str(prediction).replace('\n', ';'),
                    user.language,
                    parse_mode='newline'
                ),
                reply_markup=inline_kb
            )
            return see_users_currency_predicitions(msg)

    def choose_option_inner(msg):
        res_func = buttons.get(msg.text, None)
        if res_func is not None:
            return res_func(msg)
        else:
            bot.send_message(
                msg.chat.id,
                _('❗ Выберите только из предложенного ❗', user.language),
                reply_markup=kbs(list(buttons))
            )
            bot.register_next_step_handler(msg, choose_option_inner)

    buttons = {
        _('Мои прогнозы', user.language): see_self_predictions,
        _('Другие прогнозы', user.language): see_other_users_predictions,
        # _('Учавствовать в оценивании', user.language): like_system,
        _('Главное меню', user.language): start_bot
    }
    bot.send_message(
        msg.chat.id,
        _('Лайкайте чужие посты, и тогда другие будут лайкать ваши!', user.language),
        reply_markup=kbs(list(buttons))
    )
    bot.register_next_step_handler(msg, choose_option_inner)



def __get_prediction_inline_kb_for_liking(pred):
    closest = pred.get_closest_neighbours()
    previous, next = closest['previous'], closest['next']
    inline_buttons = {
        '👍': f'like_prediction_{pred.id}',
        '👎': f'dislike_prediction_{pred.id}'
    }
    if previous:
        inline_buttons['<<'] = f'previous_prediction_to_{pred.id}'
    if next:
        inline_buttons['>>'] = f'next_prediction_to_{pred.id}'
    inline_kb = inline_kbs(inline_buttons, row_width=2)
    return inline_kb



@bot.callback_query_handler(lambda call: 'next_prediction_to_' in call.data or 'previous_prediction_to_' in call.data)
def get_closest_prediction(call):
    action, *data, pred_id = call.data.split('_')
    pred_id = int(pred_id) - (-1 if action == 'next' else 1)
    prediction = DBCurrencyPrediction(pred_id)
    user = DBUser(call.message.chat.id)
    inline_kb = __get_prediction_inline_kb_for_liking(prediction)
    bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=_(
                    str(prediction).replace('\n', ';'),
                    user.language,
                    parse_mode='newline'
                ),
            reply_markup=inline_kb
        )



@bot.callback_query_handler(lambda call: 'like_prediction_' in call.data or 'dislike_prediction_' in call.data)
def toggle_user_reaction(call):
    action, *some_data, pred_id = call.data.split('_')
    prediction = DBCurrencyPrediction(int(pred_id))
    user = DBUser(call.message.chat.id)
    reaction = True if action == 'like' else False
    prediction.toggle_like(call.message.chat.id, reaction)
    bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=_(
                    str(prediction).replace('\n', ';'),
                    user.language,
                    parse_mode='newline'
                ),
            reply_markup=__get_prediction_inline_kb_for_liking(prediction)
        )
    bot.answer_callback_query(
        callback_query_id=call.id,
        show_alert=False,
        text=_(f'You {action}d this prediction', user.language)
    )



@bot.callback_query_handler(lambda call: 'get_prediction_' in call.data)
def get_prediction_details(call):
    pred_id = int(call.data.split('_')[-1])
    prediction = DBCurrencyPrediction(pred_id)
    user = DBUser(prediction.user_id)
    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id, 
        text=_(
            str(prediction).replace('\n', ';'),
            user.language,
            parse_mode='newline'
        ),
        reply_markup=inline_kbs({
            _('Удалить прогноз', user.language): f'ask_delete_prediction_{pred_id}',
            _('Назад к списку прогнозов', user.language): f'get_user_predictions_{prediction.user_id}'
        }, row_width=1)
    )



@bot.callback_query_handler(lambda call: 'ask_delete_prediction_' in call.data)
def ask_delete_prediction(call):
    pred_id = int(call.data.split('_')[-1])
    prediction = DBCurrencyPrediction(pred_id)
    user = DBUser(prediction.user_id)
    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id, 
        text=_(
            f"Are you sure you want to delete this prediction:;{repr(prediction)}?",
            user.language,
            parse_mode='newline'
        ),
        reply_markup=inline_kbs({
            _('Yes ✔', user.language): f'delete_prediction_{pred_id}',
            _('No ❌', user.language): f'get_user_predictions_{prediction.user_id}'
        })
    )



@bot.callback_query_handler(lambda call: 'delete_prediction_' in call.data)
def delete_prediction(call):
    pred_id = int(call.data.split('_')[-1])
    prediction = DBCurrencyPrediction(pred_id)
    user = DBUser(prediction.user_id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    if prediction.is_actual:
        prediction.delete()
    bot.answer_callback_query(callback_query_id=call.id, show_alert=False,
        text=_(f"Prediction ({repr(prediction)}) was deleted", user.language))



@bot.callback_query_handler(lambda call: 'get_user_predictions_' in call.data)
def get_user_predictions(call):
    user_id = int(call.data.split('_')[-1])
    user = DBUser(user_id)
    kb_inline = inline_kbs({
        repr(x): f'get_prediction_{x.id}'
        for x in DBUser(user_id).get_predictions()
    }, row_width=1)
    return bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=_(
                    'Here are your predictions:',
                    user.language
                ),
            reply_markup=kb_inline
        )



@bot.message_handler(commands=['convert'])
def convert_currency(msg):
    user = DBUser(msg.chat.id)
    iso_from = None
    iso_to = None


    def get_isos(msg):
        nonlocal iso_from, iso_to
        try:
            iso_from, iso_to = [x.upper() for x in msg.text.split('-')]
        except ValueError:
            bot.send_message(msg.chat.id, _('❗ Вводите iso-коды валют только в указаном формате ❗'))
            return bot.register_next_step_handler(msg, get_isos)
        else:
            return print_convertation(msg)

    def print_convertation(msg):
        nonlocal iso_from, iso_to
        try:
            rate = currency_parser.get_rate(iso_from, iso_to)
        except Exception:
            bot.send_message(
                msg.chat.id, 
                _("❗ Конвертер не нашёл таких валют, попробуйте ещё раз ❗", user.language)
            )
            return bot.register_next_step_handler(msg, get_isos)
        else:
            markup = inline_kbs(
                {i: f"change_currency_converter_amount_to_{i}" for i in _globals.CURRENCY_RATES_CHANGE_AMOUNTS}
            )
            bot.send_message(
                msg.chat.id,
                _(
                    f"Конвертация на {convert_to_country_format(get_current_datetime(user.timezone), user.language)}:\
                    ;{rate[iso_from]} {iso_from} - {rate[iso_to]} {iso_to}",
                    user.language,
                    parse_mode='newline'
                ),
                reply_markup=markup
            )
            return start_bot(msg)
    bot.send_message(
        msg.chat.id,
        _(
            'Введите валюты в формате <b><code>&#60;изо-код&#62;-&#60;изо-код&#62;</code></b>',
            user.language
        ),
        parse_mode='html'
    )
    bot.register_next_step_handler(msg, get_isos)



@bot.callback_query_handler(lambda call: 'change_currency_converter_amount_to_' in call.data)
def get_callback_for_change_currency_converter_amount(call):
    user = DBUser(call.message.chat.id)

    def change_currency_converter_amount(call):
        try:
            if call.message:
                change_amount = call.data.split('_')[-1]
                change_amount = float(change_amount)
                iso_from, iso_to = [x.split() for x in call.message.text.split(':')[-1].split('-')]
                rate = float(iso_to[0].replace(',', '.')) / float(iso_from[0].replace(',', '.'))
                new_amount = round(rate * change_amount, _globals.PRECISION_NUMBER)
                markup = inline_kbs(
                    {i: f"change_currency_converter_amount_to_{i}" for i in _globals.CURRENCY_RATES_CHANGE_AMOUNTS}
                )
                if change_amount == float(iso_from[0]): # if we try to set the same text as before, TG throws error
                    return bot.answer_callback_query(callback_query_id=call.id, show_alert=False,
                    text=_(f"Amount is already {change_amount}", user.language))
                else:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id, 
                        message_id=call.message.message_id, 
                        text=_(
                            f"Конвертация на {convert_to_country_format(get_current_datetime(user.timezone), user.language)}:\
                            ;{change_amount} {iso_from[1]} - {new_amount} {iso_to[1]}",
                            user.language,
                            parse_mode='newline'
                        ),
                        reply_markup=markup
                    )
                    bot.answer_callback_query(callback_query_id=call.id, show_alert=False,
                        text=_(f"Amount on {iso_from[1]}-{iso_to[1]} changed to {change_amount}", user.language))
        except Exception as e:
            print(repr(e))

    def ask_sum(msg, call, *msg_to_delete):
        try:
            value = float(msg.text.replace(',', '.'))
        except ValueError:
            warning_msg = bot.send_message(msg.chat.id, _('❗ Вводите только числовые значения ❗', user.language))
            msg_to_delete = list(msg_to_delete) + [msg, warning_msg]
            bot.register_next_step_handler(msg, ask_sum, call, *msg_to_delete)
        else:
            call.data = f"change_currency_converter_amount_to_{value}"
            try:
                # delete messages
                for msg_ in msg_to_delete:
                    bot.delete_message(msg_.chat.id, msg_.message_id)
                bot.delete_message(msg.chat.id, msg.message_id)
            except Exception as e:
                # permission to delete messages was not recieved
                print(repr(e))
            return change_currency_converter_amount(call)

    def set_amount_to_1(call):
        call.data = f"change_currency_converter_amount_to_{1}"
        return change_currency_converter_amount(call)

    if call.message:
        change_amount = call.data.split('_')[-1]
        if change_amount == '...':
            msg_to_delete = bot.send_message(call.message.chat.id, _('Введите вашу сумму', user.language))
            return bot.register_next_step_handler(call.message, ask_sum, call, msg_to_delete)
        elif change_amount == 'Reset':
            return set_amount_to_1(call)



def change_alarms(msg, user, buttons):
    func = buttons.get(msg.text, None)
    if func is None:
        bot.send_message(
            msg.chat.id,
            _(
                "❗ Не могу понять ваш запрос, повторите ещё раз ❗",
                user.language
            ),
            reply_markup=kbs(list(buttons), row_width=2)
        )
        return bot.register_next_step_handler(
            msg,
            change_alarms,
            DBUser(msg.chat.id),
            buttons
        )
    else:
        return func(msg)



@bot.message_handler(commands=['toggle_alarms'])
def toggle_user_alarms(msg):
    user = DBUser(msg.chat.id)
    user.update(is_active=not user.is_active)
    bot.send_message(
        msg.chat.id,
        _(
            f"Уведомления {'включены ▶' if user.is_active else 'отключены ⏸'}",
            user.language
        )
    )
    return start_bot(msg)



@bot.message_handler(commands=['me'])
def see_user_info(msg):
    user = DBUser(msg.chat.id)
    info = f"Пользователь @{msg.from_user.username}\
            ;ID на сервисе: {user.id}\
            ;Telegram ID: {user.user_id}\
            ;Подписка: {f'до {convert_to_country_format(user.is_pro, user.language)}' if user.is_pro else 'нет'}\
            ;Персонал: {'да' if user.is_staff else 'нет'}\
            ;Часовой пояс: {prettify_utcoffset(user.timezone)}\
            ;Оповещения: {'включены' if user.is_active else 'отключены'}\
            ;Оповещения:\
            ;{DBUser.prettify_rates(user.rates)}"
    bot.send_message(msg.chat.id, _(info, user.language, parse_mode='newline'))
    return start_bot(msg)



@bot.message_handler(commands=['change_delta'])
def change_user_rate_percent_delta(msg, user=None):
    user = user or DBUser(msg.chat.id)
    currency = None

    def inner1(msg):
        nonlocal currency
        if msg.text in user.rates:
            currency = msg.text
            currency_str = f"Ваш процент на {currency} - {user.rates.get(currency).get('percent_delta')}%" 
            bot.send_message(
                msg.chat.id, 
                _(
                    f"{currency_str};Выберите количество процентов",
                    user.language,
                    parse_mode='newline'
                ),
                reply_markup=kbs(_globals.PERCENTAGES)
            )
            bot.register_next_step_handler(msg, inner2)
        else:
            bot.send_message(msg.chat.id, 'Вводите только допустимые валюты', reply_markup=kbs(_globals.CURRENCIES))
            bot.register_next_step_handler(msg, inner1)

    def inner2(msg):
        nonlocal currency
        try:
            if 'inf' not in msg.text:
                delta = float(msg.text)
            else:
                raise ValueError
        except ValueError:
            bot.send_message(msg.chat.id, _("❗ Вводите только числа ❗", user.language))
            return bot.register_next_step_handler(msg, inner2)
        user.update_rates(currency, percent_delta=delta)
        bot.send_message(msg.chat.id, _(f"Ваш процент теперь стал {delta}%", user.language))
        return start_bot(msg)

    kb = kbs(list(user.rates))
    bot.send_message(msg.chat.id, _("Выберите валюту изменения процентов", user.language), reply_markup=kb)
    return bot.register_next_step_handler(msg, inner1)



@bot.message_handler(commands=['change_checktime'])
def change_user_rate_check_times(msg, user=None):
    user = user or DBUser(msg.chat.id)
    available_times = _globals.CHECK_TIMES
    chosen_times = []
    start = _globals.UNSUBSCIRBED_USER_CHECK_TIMES if not user.is_pro else _globals.SUBSCIRBED_USER_CHECK_TIMES
    currency = None


    def inner1(msg):
        nonlocal currency
        if msg.text in user.rates:
            currency = msg.text
            curr_str = f"Ваши времена оповещения на {currency} - {', '.join(user.rates.get(currency).get('check_times'))};"
            if user.is_pro:
                bot.send_message(
                    msg.chat.id, 
                    _(
                        "Вы офоромили ⚜ подписку ⚜, и вам предоставляются все возможные времена оповещений!",
                        user.language
                    )
                )
                return start_bot(msg)
            else:
                bot.send_message(
                    msg.chat.id,
                    _(  
                        curr_str + f'Выберите {start} {"дат" if start > 4 else "даты" if 1 < start <= 4 else "дату"}',
                        user.language,
                        parse_mode='newline'
                    ),
                    reply_markup=kbs(available_times))
                bot.register_next_step_handler(msg, inner2, start)
        else:
            bot.send_message(
                msg.chat.id,
                _('Вводите только допустимые валюты', user.language),
                reply_markup=kbs(_globals.CURRENCIES)
            )
            bot.register_next_step_handler(msg, inner1)


    def inner2(msg, iteration_num):
        nonlocal chosen_times, available_times
        try:
            if msg.text in available_times: # _globals.CHECK_TIMES
                time.strptime(msg.text, '%H:%M')
                iteration_num -= 1
                available_times.remove(msg.text)
                chosen_times.append(msg.text)
            else:
                raise ValueError
            if iteration_num == 0:
                user.update_rates(currency, check_times=chosen_times)
                bot.send_message(
                    msg.chat.id,
                    _(f"Ваши времена проверки {currency} такие: " + ", ".join(chosen_times), user.language)
                )
                return start_bot(msg)
        except ValueError: # if time not in CHECK_TIMES or time is not valid
            bot.send_message(msg.chat.id, _("❗ Вводите только доступные даты ❗", user.language))
            return bot.register_next_step_handler(msg, inner2, iteration_num)
        else:
            date_word = "дат" if iteration_num > 4 else "даты" if 1 < iteration_num <= 4 else "дату"
            bot.send_message(
                msg.chat.id,
                _(
                    f"Введите ещё {iteration_num} {date_word}",
                    user.language),
                reply_markup=kbs(available_times)
            )
            bot.register_next_step_handler(msg, inner2, iteration_num)        
    kb = kbs(list(user.rates))
    bot.send_message(msg.chat.id, _("Выберите валюту изменения времени оповещения", user.language), reply_markup=kb)
    return bot.register_next_step_handler(msg, inner1)



@bot.message_handler(commands=['change_timezone'])
def change_user_timezone(msg):
    user = DBUser(msg.chat.id)
    timezones = merge_dicts(
        {
            prettify_utcoffset(zone): zone
            for zone in range(-11, 13)
        },
        {'UTC': 0}
    )

    def accept_input(msg):
        res_timezone = timezones.get(msg.text, None)
        if res_timezone is None:
            bot.send_message(
                msg.chat.id,
                _(
                    '❗ Вводите только предложеные часовые пояса ❗',
                    user.language,
                ),
                reply_markup=kbs(list(timezones), row_width=2)
            )
            bot.register_next_step_handler(msg, accept_input)
        else:
            user.update(timezone=res_timezone)
            bot.send_message(
                msg.chat.id,
                _(
                    f"Теперь ваш часовой пояс - {prettify_utcoffset(user.timezone)}",
                    user.language
                )
            )
            return start_bot(msg)

    bot.send_message(
        msg.chat.id,
        _(
            f'Ваш текущий часовой пояс: {prettify_utcoffset(user.timezone)}\
            ;Выберите ваш часовой пояс',
            user.language,
            parse_mode='newline'
        ),
        reply_markup=kbs(list(timezones), row_width=2)
    )
    bot.register_next_step_handler(msg, accept_input)



def add_new_currency(msg):
    user = DBUser(msg.chat.id)


    def ask_new_iso(msg):
        iso = msg.text
        if not currency_parser.check_currency_exists(iso):
            bot.send_message(
                msg.chat.id,
                _(
                    '❗ Данная валюта не существует либо не поддердивается сервисом, попробуйте другую ❗',
                    user.language
                )
            )
            bot.register_next_step_handler(msg, ask_new_iso)
        elif iso in user.rates:
            bot.send_message(msg.chat.id, 'Валюта уже есть в вашем списке валют')
            return start_bot(msg)
        elif user.is_pro:
            rate = round(
                currency_parser.get_rate(iso).get('USD'),
                _globals.PRECISION_NUMBER
            )
            reverse_rate = round(1/rate, _globals.PRECISION_NUMBER+3)
            user.add_rate(iso, start_value=rate, check_times=_globals.CHECK_TIMES)
            bot.send_message(
                msg.chat.id, 
                _(
                    f'Новая валюта успешно создана!\
                    ;Сейчас курс {iso} - {rate} USD, или 1 USD - {reverse_rate} {iso}',
                    user.language,
                    parse_mode='newline'
                )
            )
            return start_bot(msg)

    bot.send_message(
        msg.chat.id,
        _('Введите iso-код новой валюты', user.language),
        reply_markup=kbs(['UAH', 'RUB', 'EUR'])
    )
    bot.register_next_step_handler(msg, ask_new_iso)



@bot.message_handler(commands=['subsription'])
def buy_subscription(msg):
    user = DBUser(msg.chat.id)
    json_config = json.load(open('configs\\config.json', 'r', encoding='utf-8'))
    prices_json_list = json_config.get('subsriptionPrices')
    start_price = json_config.get('subsriptionStartPrice')
    prices = [
        [
            LabeledPrice(
                label=_(
                    f"Cost of subsription for {price.get('period')} month" + ('s' if price.get('period') > 1 else ''),
                    user.language
                ),
                amount=int(round(start_price * price.get('period'), 2) * 100)
                # * 100 because amount in cents
            )
        ] + ([
            LabeledPrice(
                label=_(
                        f'Discount {price.get("discount")}%',
                        user.language
                    ),
                amount=-int(round(start_price * price.get('period') * price.get('discount')/100 * 100, 2))
            )
        ] if price.get('discount') > 0 else [])
        for price in prices_json_list
    ]
    prices_easy = {
        price.get('period'): price.get('discount')
        for price in prices_json_list
    }

    def confirm_payment(msg):
        if msg.text == _('Да, хочу!', user.language):
            prices_str = ''
            for price in prices_json_list:
                period = price.get('period')
                word_ending = '' if period == 1 else 'a' if period in range(2, 5) else 'ов'
                total_sum = int(round(start_price * period * (100 - price.get('discount')) / 100, 2))
                prices_str += f';{period} месяц{word_ending} - ${total_sum}'
            bot.send_message(
                msg.chat.id,
                _(
                    'Отлично!\
                    ;Выберите длительность Подписки (в месяцах)' + prices_str,
                    user.language,
                    parse_mode='newline'
                ),
                reply_markup=kbs(list(prices_easy))
            )
            bot.register_next_step_handler(msg, get_months_number)
        elif msg.text == _('Нет, спасибо', user.language):
            bot.send_message(msg.chat.id, _('Хорошо, мы подождём!', user.language))
            return start_bot(msg)
        else:
            bot.send_message(msg.chat.id, _('Не совсем понял ваш ответ, возвращаю в главное меню...', user.language))
            return start_bot(msg)

    def get_months_number(msg):
        months = msg.text
        if not (months.isdigit() and (int(msg.text) in list(prices_easy))):
            bot.send_message(
                msg.chat.id,
                _('❗ Вводите только предложенные значения ❗', user.language),
                reply_markup=kbs(list(prices_easy))
            )
            bot.register_next_step_handler(msg, get_months_number)
        else:
            price = [(y, x) for x, y in zip(list(prices_easy), prices) if x == int(months)][0]
            return command_pay(msg, *price)

    def command_pay(msg, prices, n_months:int=None):
        bot.send_invoice(
            msg.chat.id,
            title=_(f'Подписка', user.language),
            description=_(
                f"Вы оплачиваете Подписку на {n_months} месяца(ов)",
                user.language
            ),
            provider_token=MAIN_TOKEN.PAYMENT_TOKEN,
            currency='usd',
            photo_url='https://i1.wp.com/bestservices.reviews/wp-content/uploads/2019/09/Subscription-Billing.jpg?w=1200&ssl=1',
            photo_height=300,  # !=0/None or picture won't be shown
            photo_width=600,
            photo_size=512,
            start_parameter='subsription-telegram-bot',
            is_flexible=False,  # True If you need to set up Shipping Fee
            prices=prices,
            invoice_payload=f"{n_months}"
        )

    if not user.is_pro:
        bot.send_message(
                msg.chat.id,
                _(
                    'Покупая ⚜ Подписку ⚜, вы получаете доступ к:\
                    ;    1. Неограниченому количеству оповещений в день\
                    ;    2. Прогнозам от экспертов\
                    ;    3. Добавлению своих валют к оповещениям\
                    ;    И другому!\
                    ;;Покупайте Подписку уже сегодня, и вы об этом не пожалеете',
                    user.language,
                    parse_mode='newline'
                ),
                reply_markup=kbs([_('Да, хочу!', user.language), _('Нет, спасибо', user.language)])
            )
        bot.register_next_step_handler(msg, confirm_payment)
    else:
        bot.send_message(msg.chat.id, _('⚜ Вы уже оформили подписку! ⚜', user.language))
        return start_bot(msg)


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout_handler(pre_checkout_query):
    user = DBUser(pre_checkout_query.from_user.id)
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                  error_message=_("Oops, some error occurred, please try again later", user.language))



@bot.message_handler(content_types=['successful_payment'])
def subsription_payment_success(msg):
    user = DBUser(msg.chat.id)
    n_months = int(msg.successful_payment.invoice_payload)
    datetime_expires = get_current_datetime(user.timezone) + datetime.timedelta(days=n_months*31)
    user.init_premium(datetime_expires)
    bot.send_message(
        msg.chat.id,
        _(
            f"Вы активировали Подписку до {convert_to_country_format(datetime_expires, user.language)}\
            ;Удачных трейдов!",
            user.language,
            parse_mode='newline'
        )
    )
    return start_bot(msg)



@bot.message_handler(commands=['language'])
def change_language(msg):
    user = DBUser(msg.chat.id)


    def confirm_language(msg):
        if _('Русский 🇷🇺', user.language) == msg.text:
            user.update(language='ru')
        elif _('Английский 🇬🇧', user.language) == msg.text:
            user.update(language='en')
        else:
            bot.send_message(
                msg.chat.id, 
                _("❗ Выбирайте только из предложенных языков ❗", user.language),
                reply_markup=kbs([_('Русский 🇷🇺', user.language), _('Английский 🇬🇧', user.language)])
            )
            return bot.register_next_step_handler(msg, confirm_language, user)
        bot.send_message(msg.chat.id, _("Язык успешно сменён", user.language))
        return start_bot(msg)

    bot.send_message(
        msg.chat.id,
        _(
            'На данный момент, на сервисе присутствует два языка: Русский 🇷🇺 и Английский 🇬🇧',
            user.language
        ),
        reply_markup=kbs([
            _('Русский 🇷🇺', user.language),
            _('Английский 🇬🇧', user.language)
        ])
    )
    bot.register_next_step_handler(msg, confirm_language)



@bot.message_handler(commands=['techsupport'])
def send_techsupport_message(msg):
    user = DBUser(msg.chat.id)
    if not user.is_staff:
        bot.send_message(
            msg.chat.id,
            _(
                f'⚙ This is techsupport of @{bot.get_me().username} ⚙\
                ;You can contact us in @{support_bot.get_me().username}\
                ;Feel free to send us any feedbacks about this bot, we are always grateful for your help!',
                user.language,
                parse_mode='newline'
            ),
            reply_markup=inline_kbs({_('Ask for staff rank', user.language): 'ask_for_staff_rank'})
        )
        # bot.send_message(
        #     msg.chat.id,
        #     _(
        #         "❗ Please aware, that time of alerts and forecasts is in UTC+0300 only ❗",
        #         user.language
        #     )
        # )
    else:
        bot.send_message(
            msg.chat.id, 
            _(
                f'⚙ You are already a staff member ⚙;Staff bot: @{support_bot.get_me().username}',
                user.language,
                parse_mode='newline'
            )
        )
    return start_bot(msg)



@bot.callback_query_handler(func=lambda call: call.data == 'ask_for_staff_rank')
def ask_for_staff_rank(call):
    if call.message:
        user = DBUser(call.message.chat.id)
        if len(list(DBUser.get_staff_users())) == 0:
            user.init_staff()
            msg = '⚙ You are now a member of staff, congratulations! ⚙'
            send_message_to_techsupport(msg, if_one=True)
        else:
            res = send_message_to_techsupport(
                f'TechSupport\nFrom: @{call.message.chat.username}\nTopic: request for staff rank',
                if_one=True,
                reply_markup=inline_kbs({
                    'Yes': f'allow_staff_permission_{user.user_id}',
                    'No': f'decline_staff_permission_{user.user_id}'
                })
            )
            msg = (
                'Your request was accepted, wait for the callback'
                if res else
                'Sorry, some error occurred, try again later'
            )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text
        )
        bot.answer_callback_query(
            callback_query_id=call.id,
            show_alert=False,
            text=_(msg, user.language)
        )



@bot.message_handler(commands=['help'])
def send_bot_help(msg):
    user = DBUser(msg.chat.id)
    help_message = 'Here are bot\'s commands:;'
    for k, v in bot.bot_commands.items():
        help_message += '{} - %s;' % v
    bot.send_message(
        msg.chat.id,
        _(
            help_message,
            user.language,
            parse_mode='newline'
        ).format(*list(bot.bot_commands))
    )
    return start_bot(msg)



###################################################################################################################


def update_rates():
    while True:
        for parser in [brent_parser, bitcoin_parser, rts_parser]:
            parser.update_start_value()
        time.sleep(53)



def check_premium_ended():
    def check_user_premium_ended(user):
        if get_current_datetime(user.timezone) > user.is_pro:
            bot.send_message(
                user.user_id,
                _('Your premium has expired 😢😢😢, but you can always refresh it!', user.language)
            )
            user.delete_premium()

    while True:
        with futures.ThreadPoolExecutor(max_workers=50) as executor:
            for user in DBUser.get_pro_users():
                executor.submit(check_user_premium_ended, user)
        time.sleep(180) # 3 min



def verify_predictions():
    parsers = {
        parser.iso: parser
        for parser in [brent_parser, bitcoin_parser, rts_parser]
    }
    while True:
        for prediction in DBCurrencyPrediction.get_unverified_predictions():
            parser = parsers.get(prediction.iso_from, currency_parser)
            real_value = parser.get_rate()
            prediction.update(real_value=real_value)
            user = DBUser(prediction.user_id)
            perc_diff = round(
                abs(prediction.value-prediction.real_value)/prediction.value*100,
                _globals.PRECISION_NUMBER
            )
            bot.send_message(
                prediction.user_id, 
                _(
                    'Results of `{}`:\
                    ;**Predicted value:** {}\
                    ;**Real value:** {}\
                    ;**Percentage difference:** {}%',
                    user.language,
                    parse_mode='newline'
                ).format(
                    repr(prediction),
                    prediction.value,
                    prediction.real_value,
                    perc_diff
                ),
                parse_mode='markdown'
            )



def check_alarm_times():
    previous_minute = 0
    while True:
        t_ = get_current_datetime(0).time()
        some_time = str(t_.strftime('%H:%M'))
        if some_time in _globals.CHECK_TIMES and t_.minute != previous_minute:
            previous_minute = t_.minute
            thread = threading.Thread(target=start_alarms, args=(some_time,), daemon=True)
            thread.start()
        time.sleep(59.9) # 0.1 sec for this code to pass



def start_alarms(time_):
    with futures.ThreadPoolExecutor(max_workers=50) as executor:
        for user in DBUser.get_users_by_check_time(time_):
            executor.submit(send_alarm, user, time_)



def send_alarm(user, time_):
    parsers = {
        parser.iso: parser
        for parser in [brent_parser, bitcoin_parser, rts_parser]
    }
    for k, v in user.rates.items():
        if time_ in v.get('check_times'):
            parser = parsers.get(k, currency_parser)
            try:
                if getattr(parser, 'iso', None) is not None:
                    rate = parser.check_delta(
                        start_value=v.get('start_value'),
                        percent_delta=v.get('percent_delta')
                    )
                else:
                    # if parser is `FreecurrencyratesParser`
                    rate = parser.check_delta(
                        iso=k,
                        start_value=v.get('start_value'), 
                        percent_delta=v.get('percent_delta')
                    )
            except Exception:
                # if network can not be reached or somewhat
                json_config = json.load(open('configs\\config.json', 'r', encoding='utf-8'))
                initial_values = {k: value for key, value in json_config if isinstance(value, float) and k in key}
                rate = CurrencyParser.calculate_differences(
                    k,
                    v.get('start_value'),
                    initial_values.get(k, 1),
                    v.get('percent_delta')
                )
            if rate.get('new', None): # WARNING: CAN BE DELETED
                new, old = rate.get('new'), rate.get('old')
                usd_to_iso_new = round(1/new, 6)
                usd_to_iso_old = round(1/old, 6)
                user.update_rates(k, start_value=new)
                perc_delta = round(rate.get('percentage_difference'), _globals.PRECISION_NUMBER)
                delta = round(rate.get('difference'), _globals.PRECISION_NUMBER)
                bot.send_message(
                    user.user_id,
                    _(
                        "Цена **{}** - **{} USD**, или **1 USD - {} {}**\
                        ;Изменение составило **{}**, или **{}%**\
                        ;Предыдущая цена **{} - {} USD**, или **1 USD - {} {}**",
                        user.language,
                        parse_mode='newline'
                    ).format(
                        k, new, usd_to_iso_new, k, delta, perc_delta, k, old, usd_to_iso_old, k
                    ),
                    parse_mode='markdown'
                )



def start_checking_threads():
    for target in [check_alarm_times, update_rates, check_premium_ended, verify_predictions]:
        threading.Thread(target=target, daemon=True).start()



def main():
    start_checking_threads()
    print(f"[INFO] Bot started at {str(get_current_datetime(+2).time().strftime('%H:%M:%S'))}")
    bot.polling()
    print(f"[INFO] Bot stopped at {str(get_current_datetime(+2).time().strftime('%H:%M:%S'))}")


###################################################################################################################


if __name__ == '__main__':
    main()
