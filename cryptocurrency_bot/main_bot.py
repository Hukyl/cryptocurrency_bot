from concurrent import futures
import copy
import datetime
import threading
import time

import telebot
from telebot.types import LabeledPrice

from configs import settings, MAIN_TOKEN, TECHSUPPORT_TOKEN
from models.parsers import *
from models.user import DBUser, DBPrediction
from utils import *
from utils.translator import translate as _
from utils.telegram import kbs, inline_kbs
from utils.dt import *


telebot.apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(MAIN_TOKEN.TOKEN, threaded=False) # RecursionError
bot.full_bot_commands = {
    '/start': 'запустить бота', # Start the bot
    '/me': 'ваша информация', # Your info
    '/today': 'котировки', # Quotes
    '/change_checktime': 'сменить время оповещений', # Change check times
    '/change_delta': 'сменить разницу в процентах, при которой оповещать',
    # Change percent delta at which to notify
    '/change_timezone': 'сменить ваш часовой пояс', # change your timezone
    '/toggle_alarms': 'включить/выключить оповещения', # Toggle alarms
    '/make_prediction': 'сделать прогноз', # Make a prediction
    '/get_predictions': 'прогнозы', # Go to "Predictions" section
    '/convert': 'конвертер валют', # Currency Converter
    '/menu': 'главное меню', # Main menu
    '/subscription': 'подписка', # Go to "Subscription" section
    '/language': 'сменить язык', # Change language
    '/techsupport': 'техподдержка', # Go to "Techsupport" section
    '/help': 'помощь по командам', # Help with commands
}
bot.short_bot_commands = {
    k: bot.full_bot_commands.get(k)
    for k in ['/start', '/me', '/today', '/subscription', '/language', '/help']
}
bot.skip_pending = True

currency_parser = CurrencyExchanger()

USERS_SESSIONS = {}

####################################################################################################


@bot.middleware_handler(update_types=['message'])
def check_if_command(bot_instance, message):
    # answer for command, even if the `register_next_step_handler` is used
    if message.entities:
        is_bot_command = message.entities[0].type == 'bot_command' and message.text in bot_instance.full_bot_commands
        if is_bot_command:
            try:
                bot_instance.clear_step_handler(message)
            except Exception:
                pass



def get_or_create_session(chat_id):
    global USERS_SESSIONS
    try:
        USERS_SESSIONS[chat_id] = USERS_SESSIONS.get(chat_id, {'user': DBUser(chat_id)})
    except MemoryError:
        for i in range(50):
            USERS_SESSIONS.pop()
        return get_or_create_session(chat_id)
    else:
        return USERS_SESSIONS[chat_id]


# Used not to initialize the user every time, just save their state
@bot.middleware_handler(update_types=['message'])
def set_session(bot_instance, message):
    bot_instance.session = get_or_create_session(message.chat.id)


# Used not to initialize the user every time, just save their state
@bot.middleware_handler(update_types=['callback_query'])
def set_session(bot_instance, call):
    bot_instance.session = get_or_create_session(call.message.chat.id)


####################################################################################################


@catch_exc(to_print=True)
@bot.message_handler(commands=['start'])
def start_message(msg):
    user = bot.session['user']
    tech_support_recognizer = TECHSUPPORT_TOKEN.ACCESSIBLE_LINK.split('=')[1]
    add_info = msg.text.split()[1:]
    bot.send_message(
        msg.chat.id,
        _(
            'Welcome, {}!',
            user.language
        ).format(msg.from_user.first_name)
    )
    bot.send_message(
        msg.chat.id,
        _(
            "I am <b>{}</b>, your personal shareholder bot, and I will keep you updated on important trading events!", 
            user.language
        ).format(bot.get_me().first_name),
        parse_mode='html'
    )
    if (add_info and (tech_support_recognizer in add_info)) or not list(DBUser.get_staff_users()):
        # if user started bot with techsupport link or there are not support users
        user.init_staff()
        bot.send_message(
            msg.chat.id,
            _(
                '⚙ You have received a technical support status ⚙',
                user.language
            )
        )    
    return start_bot(msg)



@bot.message_handler(commands=['menu'])
def start_bot(msg, to_show_commands:bool=True):
    user = bot.session['user']
    buttons = [
        _('Quotes', user.language),
        _('Notifications', user.language),
        _('Subscription', user.language),
        _('Language', user.language),
        _('Technical support', user.language)
    ]
    kb = kbs(buttons, one_time_keyboard=False)
    if to_show_commands:
        str_ = ';'.join(['{} - %s' % v for k, v in bot.short_bot_commands.items()])
        bot.send_message(
            msg.chat.id,
            _(
                str_, 
                user.language,
                parse_mode='newline'
            ).format(*list(bot.short_bot_commands)),
            reply_markup=kb
        )
    else:
        bot.send_message(msg.chat.id, _("Main menu", user.language), reply_markup=kb)
    bot.register_next_step_handler(msg, choose_option, buttons=buttons)



def choose_option(msg, buttons=None):
    buttons = buttons or []
    user = bot.session['user']
    if buttons[0] == msg.text:
        # see exchange rates for today
        return get_currency_rates_today(msg)
    elif buttons[1] == msg.text:
        # go to notifications section
        buttons = {
            _("Your info", user.language): see_user_info, 
            _('Change alarm time', user.language): change_user_rate_check_times, 
            _('Change alarm percent', user.language):change_user_rate_percent_delta,
            _('Toggle alarms', user.language): toggle_user_alarms,
            _('Change time zone', user.language): change_user_timezone,
            _('Main menu', user.language): start_bot 
        }
        if user.is_pro:
            buttons[_('⚜ Other currencies ⚜', user.language)] = other_user_currencies_menu
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
        return bot.register_next_step_handler(msg, choose_option, buttons)



@bot.message_handler(commands=['today'])
def get_currency_rates_today(msg):
    user = bot.session['user']
    buttons_dct = {
            _('Make a prediction', user.language): make_user_currency_prediction,
            _('View predictions', user.language): see_users_currency_predicitions,
            _('Convert', user.language): convert_currency,
            _('Main menu', user.language): start_bot
        }

    def choose_option_inner(msg):
        if buttons_dct.get(msg.text, None) is None:
            bot.send_message(
                msg.chat.id,
                _(
                    '❗ Choose only from the suggestions ❗',
                    user.language
                )
            )
            bot.register_next_step_handler(msg, choose_option_inner)
        else:
            return buttons_dct.get(msg.text)(msg)

    bot.send_message(
        msg.chat.id,
        currency_parser.to_telegram_string(),
        parse_mode='Markdown',
        reply_markup=kbs(list(buttons_dct))
    )
    bot.register_next_step_handler(msg, choose_option_inner)



@bot.message_handler(commands=['make_prediction'])
def make_user_currency_prediction(msg):
    user = bot.session['user']
    date = None
    iso_from = iso_to = None
    value = None

    def get_date(msg):
        nonlocal date
        try:
            up_to_date = convert_from_country_format(
                msg.text,
                user.language,
                user.timezone
            )
            assert check_datetime_in_future(up_to_date)
        except ValueError:
            bot.send_message(
                msg.chat.id, 
                _('❗ Please enter the date only in the specified format ❗', user.language)
            )
            bot.register_next_step_handler(msg, get_date)
        except AssertionError:
            bot.send_message(msg.chat.id, _('❗ You cannot enter a past date ❗', user.language))
            bot.register_next_step_handler(msg, get_date)
        else:
            date = up_to_date
            bot.send_message(
                msg.chat.id,
                _(
                    'Enter the ISO-codes of the forecast currency `<ISO>-<ISO>`\nFor example, USD-RUB',
                    user.language                    
                ),
                parse_mode='Markdown',
                reply_markup=kbs(list(settings.ACCEPTABLE_CURRENCIES_CONVERTION))
            )
            bot.register_next_step_handler(msg, get_iso)

    def get_iso(msg):
        nonlocal iso_from, iso_to
        msg.text = settings.ACCEPTABLE_CURRENCIES_CONVERTION.get(msg.text, msg.text)
        try:
            iso_from, iso_to = [x.strip() for x in msg.text.split('-')]
        except ValueError:
            bot.send_message(
                msg.chat.id,
                _('❗ Enter currency iso codes only in the specified format ❗', user.language)
            )
        else:
            try:
                _r = currency_parser.get_rate(iso_from, iso_to)
            except ValueError:
                bot.send_message(
                    msg.chat.id,
                    _(
                        "❗ This currency does not exist or is not supported, please try another one ❗", 
                        user.language
                    )
                )
            else:
                bot.send_message(
                    msg.chat.id,
                    _("Enter the forecast result (for example, 27.50, 22300)", user.language)
                )
                return bot.register_next_step_handler(msg, get_value)
        return bot.register_next_step_handler(msg, get_iso)

    def get_value(msg):
        nonlocal value
        try:
            value = float(msg.text.replace(',', '.'))
        except ValueError:
            bot.send_message(msg.chat.id, _('❗ Enter only numbers ❗', user.language))
            bot.register_next_step_handler(msg, get_value)
        else:
            buttons = [_('Yes', user.language), _('No', user.language)]
            bot.send_message(
                msg.chat.id, 
                _(
                    'Here is the forecast data:\nForecast period: {}\nCurrency: {} - {}\nValue: {}\n.\nConfirm forecast creation?',
                    user.language
                ).format(
                    convert_to_country_format(date, user.language),
                    iso_from, 
                    iso_to,
                    value
                ),
                reply_markup=kbs(buttons)
            )
            bot.register_next_step_handler(msg, confirm_prediction, buttons)

    def confirm_prediction(msg, buttons):
        if msg.text == buttons[0]:
            user.create_prediction(iso_from, iso_to, value, date)
            bot.send_message(msg.chat.id, _('The forecast has been created!', user.language))
            return start_bot(msg)
        elif msg.text ==  buttons[1]:
            bot.send_message(msg.chat.id, _('Forecast not created', user.language))
            return start_bot(msg)
        else:
            bot.send_message(msg.chat.id, _('Response not processed', user.language))
            return start_bot(msg)

    bot.send_message(
        msg.chat.id,
        _('To exit anywhere, enter {}', user.language).format('/menu')
    )
    datetime_check_str = get_country_dt_example(user.language)
    datetime_example = convert_to_country_format(
        get_current_datetime(utcoffset=user.timezone),
        user.language,
        no_offset=True
    )
    bot.send_message(
        msg.chat.id, 
        _(
            'Select the forecast validity period in the format `{}`\nFor example, {}', 
            user.language
        ).format(datetime_check_str, datetime_example),
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, get_date)



@bot.message_handler(commands=['get_predictions'])
def see_users_currency_predicitions(msg):
    user = bot.session['user']

    def see_self_predictions(msg):
        preds = {repr(x): f'get_prediction_{x.id}' for x in user.get_predictions()}
        kb_inline = inline_kbs(preds, row_width=1)
        if len(preds) == 0:
            bot.send_message(
                msg.chat.id, 
                _('You have no predictions so far, create one!', user.language)
            )
        else:
            bot.send_message(
                msg.chat.id, 
                _('Here are your predictions', user.language), 
                reply_markup=kb_inline
            )
        return see_users_currency_predicitions(msg)

    def see_other_users_predictions(msg):
        if user.is_pro:
            experts_str = (
                '⚜ Experts predictions ⚜ are:\n'
                +
                ('\n\n'.join([str(x) for x in DBPrediction.get_experts_predictions()][:5]) or ' none')
            )
            if experts_str.endswith('none'):
                # if no predictions were concatenated to prefix
                experts_str = experts_str.replace('\n', '')
            bot.send_message(
                msg.chat.id, 
                _(experts_str.replace('\n', ';'), user.language, parse_mode='newline'),
            )

        liked_preds_str = (
            'Most liked predictions are:\n'
            +
            ('\n\n'.join([str(x) for x in DBPrediction.get_most_liked_predictions()][:5]) or ' none')
        )
        if liked_preds_str.endswith('none'):
            # if no predictions were concatenated to prefix
            liked_preds_str = liked_preds_str.replace('\n', '')
        bot.send_message(
            msg.chat.id, 
            _(
                liked_preds_str.replace('\n', ';'),
                user.language,
                parse_mode='newline'
            ),
        )
        return see_users_currency_predicitions(msg)

    def liking_system(msg):
        random_pred = DBPrediction.get_random_prediction()
        if random_pred is None:
            # if no predictions are there
            bot.send_message(
                msg.chat.id, 
                _(
                    'There are no predictions to like yet, you can create one!', 
                    user.language
                )
            )
            return start_bot(msg)
        else:
            closest = random_pred.get_closest_neighbours()
            previous, next = closest['previous'], closest['next']
            inline_buttons = {
                '👍': f'like_prediction_{random_pred.id}',
                '👎': f'dislike_prediction_{random_pred.id}'
            }
            if previous:
                inline_buttons['<<'] = f'previous_prediction_to_{random_pred.id}'
            if next:
                inline_buttons['>>'] = f'next_prediction_to_{random_pred.id}'
            inline_kb = inline_kbs(inline_buttons, row_width=2)
            bot.send_message(
                msg.chat.id,
                _(str(random_pred).replace('\n', ';'), user.language, parse_mode='newline'),
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
                _('❗ Choose only from the suggestions ❗', user.language),
                reply_markup=kbs(list(buttons))
            )
            bot.register_next_step_handler(msg, choose_option_inner)

    buttons = {
        _('My predictions', user.language): see_self_predictions,
        _('Other predictions', user.language): see_other_users_predictions, 
        _('Participate in the assessment', user.language): liking_system,
        _('Main menu', user.language): start_bot
    }
    bot.send_message(
        msg.chat.id,
        _('Choose from the following:', user.language),
        reply_markup=kbs(list(buttons))
    )
    bot.register_next_step_handler(msg, choose_option_inner)



def get_prediction_inline_kb_for_liking(pred):
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



@bot.callback_query_handler(
    lambda call: 'next_prediction_to_' in call.data or 'previous_prediction_to_' in call.data
)
def get_closest_prediction(call):
    action, *data, pred_id = call.data.split('_')
    start_pred = DBPrediction(int(pred_id))
    following_pred = start_pred.get_closest_neighbours()[action]
    user = bot.session['user']
    inline_kb = get_prediction_inline_kb_for_liking(following_pred)
    bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=_(str(following_pred).replace('\n', ';'), user.language, parse_mode='newline'),
            reply_markup=inline_kb
        )



@bot.callback_query_handler(
    lambda call: 'like_prediction_' in call.data or 'dislike_prediction_' in call.data
)
def toggle_user_reaction(call):
    action, *some_data, pred_id = call.data.split('_')
    prediction = DBPrediction(int(pred_id))
    user = bot.session['user']
    reaction = True if action == 'like' else False
    prediction.toggle_like(call.message.chat.id, reaction)
    bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=_(str(prediction).replace('\n', ';'), user.language, parse_mode='newline'),
            reply_markup=get_prediction_inline_kb_for_liking(prediction)
        )
    bot.answer_callback_query(
        callback_query_id=call.id,
        show_alert=False,
        text=_(f'You {action}d this prediction', user.language)
    )



@bot.callback_query_handler(lambda call: 'get_prediction_' in call.data)
def get_prediction_details(call):
    pred_id = int(call.data.split('_')[-1])
    prediction = DBPrediction(pred_id)
    user = bot.session['user']
    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id, 
        text=_(str(prediction).replace('\n', ';'), user.language, parse_mode='newline'),
        reply_markup=inline_kbs({
            _('Delete', user.language): f'ask_delete_prediction_{pred_id}',
            _('Back', user.language): f'get_user_predictions_{prediction.user_id}'
        }, row_width=1)
    )



@bot.callback_query_handler(lambda call: 'ask_delete_prediction_' in call.data)
def ask_delete_prediction(call):
    pred_id = int(call.data.split('_')[-1])
    prediction = DBPrediction(pred_id)
    user = bot.session['user']
    if prediction.is_actual:
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=_(
                "Are you sure you want to delete this prediction:\n{}?",
                user.language
            ).format(repr(prediction)),
            reply_markup=inline_kbs({
                _('Yes', user.language): f'delete_prediction_{pred_id}',
                _('No', user.language): f'get_user_predictions_{prediction.user_id}'
            })
        )
    else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=_('You cannot delete a verified prediction!', user.language),
            reply_markup=inline_kbs({
                    _('Back', user.language): f'get_user_predictions_{prediction.user_id}'
            })
        )



@bot.callback_query_handler(lambda call: 'delete_prediction_' in call.data)
def delete_prediction(call):
    pred_id = int(call.data.split('_')[-1])
    prediction = DBPrediction(pred_id)
    user = bot.session['user']
    bot.delete_message(call.message.chat.id, call.message.message_id)
    if prediction.is_actual:
        prediction.delete()
        answer_msg = _(
            "Prediction ({}) was deleted",
            user.language
        ).format(repr(prediction))
    else:
        answer_msg = _('You cannot delete a verified prediction!', user.language)
    bot.answer_callback_query(
        callback_query_id=call.id,
        show_alert=False,
        text=answer_msg
    )
    


@bot.callback_query_handler(lambda call: 'get_user_predictions_' in call.data)
def get_user_predictions(call):
    user_id = int(call.data.split('_')[-1])
    user = bot.session['user']
    kb_inline = inline_kbs({
        repr(x): f'get_prediction_{x.id}'
        for x in user.get_predictions()
    }, row_width=1)
    return bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=_('Here are your predictions', user.language),
            reply_markup=kb_inline
        )



@bot.message_handler(commands=['convert'])
def convert_currency(msg):
    user = bot.session['user']
    iso_from = None
    iso_to = None

    def get_isos(msg):
        nonlocal iso_from, iso_to
        try:
            iso_from, iso_to = [x.upper() for x in msg.text.split('-')]
        except ValueError:
            bot.send_message(
                msg.chat.id, 
                _('❗ Enter currency iso codes only in the specified format ❗', user.language)
            )
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
                _(
                    "❗ The converter did not find such currencies, please try again ❗",
                    user.language
                )
            )
            return bot.register_next_step_handler(msg, get_isos)
        else:
            markup = inline_kbs(
                {
                    i: f"change_currency_converter_amount_to_{i}" 
                    for i in settings.CURRENCY_RATES_CHANGE_AMOUNTS
                }
            )
            bot.send_message(
                msg.chat.id,
                _(
                    'Conversion by {}:\n{} {} - {} {}',
                    user.language
                ).format(
                    convert_to_country_format(
                        get_current_datetime(utcoffset=user.timezone),
                        user.language
                    ),
                    rate[iso_from],
                    iso_from,
                    rate[iso_to],
                    iso_to
                ),
                reply_markup=markup
            )
            return start_bot(msg)
    bot.send_message(
        msg.chat.id,
        _(
            'Enter the ISO-codes of currencies `<ISO>-<ISO>`\nFor example, USD-RUB',
            user.language
        ),
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, get_isos)



@bot.callback_query_handler(lambda call: 'change_currency_converter_amount_to_' in call.data)
def get_callback_for_change_currency_converter_amount(call):
    user = bot.session['user']

    def change_currency_converter_amount(call):
        try:
            if call.message:
                change_amount = call.data.split('_')[-1]
                change_amount = float(change_amount)
                iso_from, iso_to = [x.split() for x in call.message.text.split(':')[-1].split('-')]
                rate = float(iso_to[0].replace(',', '.')) / float(iso_from[0].replace(',', '.'))
                new_amount = round(rate * change_amount, settings.PRECISION_NUMBER)
                markup = inline_kbs(
                    {
                        i: f"change_currency_converter_amount_to_{i}" 
                        for i in settings.CURRENCY_RATES_CHANGE_AMOUNTS
                    }
                )
                if change_amount == float(iso_from[0]): 
                    # if we try to set the same text as before, an error occurs
                    return bot.answer_callback_query(
                        callback_query_id=call.id, 
                        show_alert=False,
                        text=_(f"Amount is already {change_amount}", user.language)
                    )
                else:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id, 
                        message_id=call.message.message_id, 
                        text=_(
                            'Conversion by {}:\n{} {} - {} {}',
                            user.language
                        ).format(
                            convert_to_country_format(
                                get_current_datetime(utcoffset=user.timezone),
                                user.language
                            ),
                            change_amount,
                            iso_from[1],
                            new_amount,
                            iso_to[1]
                        ),
                        reply_markup=markup
                    )
                    bot.answer_callback_query(callback_query_id=call.id, show_alert=False,
                        text=_(
                            "Amount on {}-{} changed to {}",
                            user.language
                        ).format(iso_from[1], iso_to[1], change_amount)
                    )
        except Exception as e:
            print(repr(e))

    def ask_sum(msg, call, *msg_to_delete):
        try:
            value = float(msg.text.replace(',', '.'))
        except ValueError:
            warning_msg = bot.send_message(
                msg.chat.id, _('❗ Enter only numbers ❗', user.language)
            )
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
            # bot.clear_step_handler(call.message)
            msg_to_delete = bot.send_message(
                    call.message.chat.id, 
                    _(
                        'Enter new amount',
                        user.language
                    )
                )
            return bot.register_next_step_handler(call.message, ask_sum, call, msg_to_delete)
        elif change_amount == 'Reset':
            return set_amount_to_1(call)



def change_alarms(msg, user, buttons):
    func = buttons.get(msg.text, None)
    if func is None:
        bot.send_message(
            msg.chat.id,
            _(
                "❗ I can't understand your request, please try again ❗", 
                user.language
            ),
            reply_markup=kbs(list(buttons), row_width=2)
        )
        return bot.register_next_step_handler(
            msg,
            change_alarms,
            bot.session['user'],
            buttons
        )
    else:
        return func(msg)



@bot.message_handler(commands=['toggle_alarms'])
def toggle_user_alarms(msg):
    user = bot.session['user']
    user.update(is_active=not user.is_active)
    bot.send_message(
        msg.chat.id,
        _(
            f"Notifications {'en' if user.is_active else 'dis'}abled",
            user.language
        )
    )
    return start_bot(msg)



@bot.message_handler(commands=['me'])
def see_user_info(msg):
    user = bot.session['user']
    info = f"Пользователь @{msg.from_user.username}\
            ;Telegram ID: {user.user_id}\
            ;Подписка: {f'до {convert_to_country_format(user.is_pro, user.language)}' if user.is_pro else 'нет'}\
            ;Персонал: {'да' if user.is_staff else 'нет'}\
            ;Часовой пояс: {prettify_utcoffset(user.timezone)}\
            ;Оповещения: {'включены' if user.is_active else 'отключены'}\
            ;Оповещения:\
            ;{DBUser.prettify_rates(user.rates)}"
    bot.send_message(msg.chat.id, _(info, user.language, parse_mode='newline'))
    return start_bot(msg)



@catch_exc(to_print=True)
@bot.message_handler(commands=['change_delta'])
def change_user_rate_percent_delta(msg):
    user = bot.session['user']
    currency = None

    def inner1(msg):
        nonlocal currency
        if msg.text in user.rates:
            currency = msg.text
            bot.send_message(
                msg.chat.id, 
                _(
                    "Your interest on {} - {}\nSelect the amount of interest",
                    user.language
                ).format(
                    currency, 
                    prettify_percent(user.rates.get(currency).get('percent_delta'))
                ),
                reply_markup=kbs(settings.PERCENTAGES)
            )
            bot.register_next_step_handler(msg, inner2)
        else:
            bot.send_message(
                msg.chat.id, 
                '❗ Please enter only valid currencies ❗',
                reply_markup=kbs(settings.CURRENCIES)
            )
            bot.register_next_step_handler(msg, inner1)

    def inner2(msg):
        nonlocal currency
        try:
            if 'inf' not in msg.text:
                delta = float(msg.text) / 100
                assert 0 < delta < 1
            else:
                raise ValueError
        except ValueError:
            bot.send_message(msg.chat.id, _("❗ Enter only numbers ❗", user.language))
            return bot.register_next_step_handler(msg, inner2)
        except AssertionError:
            bot.send_message(msg.chat.id, _("❗ Percent must be in range from 0 to 100 ❗", user.language))
            return bot.register_next_step_handler(msg, inner2)            
        user.update_rates(currency, percent_delta=delta)
        bot.send_message(
            msg.chat.id,
            _("Your percentage is now {}", user.language).format(
                prettify_percent(delta)
            )
        )
        return start_bot(msg)

    kb = kbs(list(user.rates))
    bot.send_message(
        msg.chat.id, 
        _("Выберите валюту изменения процентов", user.language), 
        reply_markup=kb
    )
    return bot.register_next_step_handler(msg, inner1)



@catch_exc(to_print=True)
@bot.message_handler(commands=['change_checktime'])
def change_user_rate_check_times(msg):
    user = bot.session['user']
    available_times = copy.deepcopy(settings.CHECK_TIMES)
    chosen_times = []
    start = (
        settings.UNSUBSCIRBED_USER_CHECK_TIMES 
        if not user.is_pro else 
        settings.SUBSCIRBED_USER_CHECK_TIMES
    )
    currency = None

    def inner1(msg):
        nonlocal currency
        if msg.text in user.rates:
            currency = msg.text
            if user.is_pro:
                bot.send_message(
                    msg.chat.id, 
                    _(
                        "You subscribed ⚜ and you are presented with all possible alert times!",
                        user.language
                    )
                )
                return start_bot(msg)
            else:
                bot.send_message(
                    msg.chat.id,
                    _(
                        'Your alert times for {} - {}',
                        user.language
                    ).format(
                        currency, 
                        ', '.join(user.rates.get(currency).get('check_times'))
                    )
                )
                bot.send_message(
                    msg.chat.id,
                    _(  
                        'Select {} time(s)',
                        user.language
                    ).format(start),
                    reply_markup=kbs(available_times))
                bot.register_next_step_handler(msg, inner2, start)
        else:
            bot.send_message(
                msg.chat.id,
                _('❗ Please enter only valid currencies ❗', user.language),
                reply_markup=kbs(settings.CURRENCIES)
            )
            bot.register_next_step_handler(msg, inner1)

    def inner2(msg, iteration_num):
        nonlocal chosen_times, available_times
        try:
            if msg.text in available_times: # settings.CHECK_TIMES
                time.strptime(msg.text, '%H:%M')
                iteration_num -= 1
                available_times.remove(msg.text)
                chosen_times.append(msg.text)
            else:
                raise ValueError
            if iteration_num == 0:
                chosen_times = sorted(
                    chosen_times, 
                    key=lambda x: int(x.split(':')[0])
                )
                user.update_rates(currency, check_times=chosen_times)
                bot.send_message(
                    msg.chat.id,
                    _(
                        'Your alert times for {} - {}', 
                    user.language
                    ).format(
                        currency,
                        ", ".join(chosen_times)
                    )
                )
                return start_bot(msg)
        except ValueError: # if time not in CHECK_TIMES or time is not valid
            bot.send_message(
                msg.chat.id,
                _(
                    "❗ Please enter only available dates ❗", 
                    user.language
                )
            )
            return bot.register_next_step_handler(msg, inner2, iteration_num)
        else:
            bot.send_message(
                msg.chat.id,
                _(
                    f"Enter more {iteration_num} time(s)",
                    user.language),
                reply_markup=kbs(available_times)
            )
            bot.register_next_step_handler(msg, inner2, iteration_num)        
    kb = kbs(list(user.rates))
    bot.send_message(
        msg.chat.id, 
        _("Select the currency of the alert time change", user.language), 
        reply_markup=kb
    )
    return bot.register_next_step_handler(msg, inner1)



@catch_exc(to_print=True)
@bot.message_handler(commands=['change_timezone'])
def change_user_timezone(msg):
    user = bot.session['user']
    timezones = {
        prettify_utcoffset(zone): zone
        for zone in range(-11, 13)
    }

    def accept_input(msg):
        res_timezone = timezones.get(msg.text, None)
        if res_timezone is None:
            bot.send_message(
                msg.chat.id,
                _(
                    '❗ Please enter only suggested time zones ❗',
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
                    'Now your time zone is {}',
                    user.language
                ).format(prettify_utcoffset(user.timezone))
            )
            return start_bot(msg)

    bot.send_message(
        msg.chat.id,
        _(
            'Your current time zone is {}\nPlease select your time zone',
            user.language
        ).format(prettify_utcoffset(user.timezone)),
        reply_markup=kbs(list(timezones), row_width=2)
    )
    bot.register_next_step_handler(msg, accept_input)



def other_user_currencies_menu(msg):
    user = bot.session['user']
    buttons = {
        _("Add new currency", user.language): add_new_currency,
        _("Delete currency", user.language): delete_user_currency,
        _("Back", user.language): start_bot 
    }

    def next_step(msg):
        option = buttons.get(msg.text, None)
        if option is None:
            bot.send_message(msg.chat.id, _('❗ Choose only from the suggestions ❗', user.language))
            bot.register_next_step_handler(msg, next_step)
        else:
            return option(msg)

    bot.send_message(
        msg.chat.id, 
        _('Choose from the following:', user.language),
        reply_markup=kbs(list(buttons), row_width=3)
    )
    bot.register_next_step_handler(msg, next_step)



@catch_exc(to_print=True)
def delete_user_currency(msg):
    user = bot.session['user']
    curr = None
    deletable_currencies = list(set(user.rates).difference(set(settings.CURRENCIES)))
    answer_options = {_("Yes", user.language): True, _("No", user.language): False}

    def confirm_deletion(msg):
        option = answer_options.get(msg.text, None)
        if option is True:
            user.delete_rate(curr)
            bot.send_message(
                msg.chat.id, 
                _("Currency {} was deleted", user.language).format(curr)
            )
        elif option is False:
            bot.send_message(
                msg.chat.id, 
                _("Currency {} wasn't deleted", user.language).format(curr)
            )
        elif option is None:
            bot.send_message(
                msg.chat.id, 
                _("I don't understand your answer, returning to the main menu...", user.language)
            )
        return start_bot(msg)

    def choose_currency_to_delete(msg):
        nonlocal curr
        curr = msg.text
        if curr in deletable_currencies:
            bot.send_message(
                msg.chat.id, 
                _("Are you sure you want to delete this currency: {}?", user.language).format(curr),
                reply_markup=kbs(list(answer_options))
            )
            bot.register_next_step_handler(msg, confirm_deletion)
        else:
            if curr == _("Back", user.language):
                return start_bot(msg)
            elif curr in settings.CURRENCIES:
                bot.send_message(
                    msg.chat.id, 
                    _("❗ You can't delete default currencies ❗", user.language)
                )
            else:
                bot.send_message(
                    msg.chat.id, 
                    _("❗ This currency is not supported ❗", user.language)
                )
            bot.register_next_step_handler(msg, choose_currency_to_delete)

    if len(deletable_currencies) > 0:
        bot.send_message(
            msg.chat.id, 
            _("Choose currency to delete", user.language),
            reply_markup=kbs(
                deletable_currencies + [_("Back", user.language)], 
                one_time_keyboard=False
            )
        )
        bot.register_next_step_handler(msg, choose_currency_to_delete)
    else:
        bot.send_message(msg.chat.id, _("You have no extra currencies to delete", user.language))
        return start_bot(msg)



@catch_exc(to_print=True)
def add_new_currency(msg):
    user = bot.session['user']

    def ask_new_iso(msg):
        iso = msg.text
        try:
            rate = currency_parser.get_rate(iso, "USD").get("USD")
        except ValueError:
            bot.send_message(
                msg.chat.id,
                _(
                    '❗ This currency does not exist or is not supported, please try another one ❗', 
                    user.language
                )
            )
            bot.register_next_step_handler(msg, ask_new_iso)
        else:
            if iso in user.rates:
                bot.send_message(
                    msg.chat.id, 
                    _('❗ The currency is already on your currency list ❗', user.language)
                )
                return start_bot(msg)
            elif user.is_pro:
                user.add_rate(iso, start_value=rate, check_times=settings.CHECK_TIMES)
                bot.send_message(
                    msg.chat.id,
                    _(
                        'New currency has been created successfully!\nNow the rate is {} - {} USD',
                        user.language
                    ).format(iso, rate)
                )
                return start_bot(msg)

    bot.send_message(
        msg.chat.id,
        _('Enter the ISO-code of the new currency', user.language),
        reply_markup=kbs(['RUB', 'EUR', 'UAH', 'BYN'])
    )
    bot.register_next_step_handler(msg, ask_new_iso)



@catch_exc(to_print=True)
@bot.message_handler(commands=['subscription'])
def buy_subscription(msg):
    user = bot.session['user']
    json_config = get_json_config()
    prices_json_list = json_config.get('subscriptionPrices')
    start_price = json_config.get('subscriptionStartPrice')
    prices = [
        [
            LabeledPrice(
                label=f"Cost of subscription for {price.get('period')} month" + ('s' if price.get('period') > 1 else ''),
                amount=int(round(start_price * price.get('period'), 2) * 100)                
            )
        ] + ([
            LabeledPrice(
                label=f'Discount {price.get("discount")*100}%',
                amount=-int(round(start_price * price.get('period') * price.get('discount') * 100, 2))
                # * 100 because `amount` is interpreted in cents
            )
        ] if price.get('discount') > 0 else [])
        for price in prices_json_list
    ]
    prices_easy = {
        price.get('period'): price.get('discount')
        for price in prices_json_list
    }

    def confirm_payment(msg):
        if msg.text == _('Yes, I want to!', user.language):
            prices_str = ''
            for price in prices_json_list:
                period = price.get('period')
                word_ending = '' if period == 1 else 'a' if period in range(2, 5) else 'ов'
                total_sum = int(round(start_price * period * (100 - price.get('discount')) / 100, 2))
                prices_str += f';{period} месяц{word_ending} - {total_sum} USD'
            bot.send_message(
                msg.chat.id,
                _(
                    f'Отлично!\
                    ;Выберите длительность Подписки (в месяцах)\
                    ;{prices_str}',
                    user.language,
                    parse_mode='newline'
                ),
                reply_markup=kbs(list(prices_easy))
            )
            bot.register_next_step_handler(msg, get_months_number)
        elif msg.text == _('No, thanks', user.language):
            bot.send_message(msg.chat.id, _('Okay, we\'ll wait!', user.language))
            return start_bot(msg)
        else:
            bot.send_message(
                msg.chat.id, 
                _(
                    "I don't understand your answer, returning to the main menu...", 
                    user.language
                )
            )
            return start_bot(msg)

    def get_months_number(msg):
        months = msg.text
        if not (months.isdigit() and (int(msg.text) in list(prices_easy))):
            bot.send_message(
                msg.chat.id,
                _('❗ Please enter only suggested values ❗', user.language),
                reply_markup=kbs(list(prices_easy))
            )
            bot.register_next_step_handler(msg, get_months_number)
        else:
            price = [(y, x) for x, y in zip(list(prices_easy), prices) if x == int(months)][0]
            bot.send_message(
                msg.chat.id,
                _(
                    '❗ Pay just as you recieve invoice, otherwise payemt can be not recieved ❗', 
                    user.language
                )
            )
            return command_pay(msg, *price)

    def command_pay(msg, prices, n_months:int=None):
        bot.send_invoice(
            msg.chat.id,
            title=_(f'Подписка', user.language),
            description=_(
                "You pay for a Subscription for {} month(s)",
                user.language
            ).format(n_months),
            provider_token=MAIN_TOKEN.PAYMENT_TOKEN,
            currency='usd',
            photo_url='https://i1.wp.com/bestservices.reviews/wp-content/uploads/2019/09/Subscription-Billing.jpg?w=1200&ssl=1',
            photo_height=300,  # !=0/None or picture won't be shown
            photo_width=600,
            photo_size=512,
            start_parameter='subscription-telegram-bot',
            is_flexible=False,  # True If you need to set up Shipping Fee
            prices=prices,
            invoice_payload=f"{n_months}"
        )

    if not user.is_pro:
        bot.send_message(
                msg.chat.id,
                _(
                    'When buying a Subscription, you get access to:\n1. Unlimited number of alerts per day\n2. Forecasts from experts\n3. Adding your currencies to alerts\nAnd more! \n\nBuy a Subscription today, and you will not regret it',
                    user.language
                ),
                reply_markup=kbs([
                    _('Yes, I want to!', user.language), 
                    _('No, thanks', user.language)
                ])
            )
        bot.register_next_step_handler(msg, confirm_payment)
    else:
        bot.send_message(
            msg.chat.id, 
            _('You have already subscribed!', user.language)
        )
        return start_bot(msg)


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout_handler(pre_checkout_query):
    user = DBUser(pre_checkout_query.from_user.id)
    bot.answer_pre_checkout_query(
        pre_checkout_query.id, 
        ok=True,
        error_message=_(
            "Oops, some error occurred, please try again later", 
            user.language
        )
    )



@bot.message_handler(content_types=['successful_payment'])
def subscription_payment_success(msg):
    user = bot.session['user']
    n_months = int(msg.successful_payment.invoice_payload)
    datetime_expires = (
        get_current_datetime(utcoffset=user.timezone) + 
        datetime.timedelta(days=n_months*31)
    )
    user.init_premium(datetime_expires)
    bot.send_message(
        msg.chat.id,
        _(
            "You have activated the Subscription until {}\nHappy trades!",
            user.language
        ).format(convert_to_country_format(datetime_expires, user.language))
    )
    return start_bot(msg)



@bot.message_handler(commands=['language'])
def change_language(msg):
    user = bot.session['user']
    buttons = [_('Russian 🇷🇺', user.language), _('English 🇬🇧', user.language)]

    def confirm_language(msg):
        if buttons[0] == msg.text:
            user.update(language='ru')
        elif buttons[1] == msg.text:
            user.update(language='en')
        else:
            bot.send_message(
                msg.chat.id, 
                _("❗ Choose only from the suggested languages ❗", user.language),
                reply_markup=kbs(buttons)
            )
            return bot.register_next_step_handler(msg, confirm_language, user)
        bot.send_message(
            msg.chat.id, 
            _("Language changed successfully", user.language)
        )
        return start_bot(msg)

    bot.send_message(
        msg.chat.id,
        _(
            'At the moment, the service has two languages: Russian 🇷🇺 and English 🇬🇧',
            user.language
        ),
        reply_markup=kbs(buttons)
    )
    bot.register_next_step_handler(msg, confirm_language)



@bot.message_handler(commands=['techsupport'])
def send_techsupport_message(msg):
    user = bot.session['user']
    if not user.is_staff:
        bot.send_message(
            msg.chat.id,
            _(
                '⚙ This is techsupport of @{} ⚙\nFeel free to send us any feedbacks about this bot, we are always grateful for your help!',
                user.language
            ).format(bot.get_me().username),
            reply_markup=inline_kbs(
                {_('Send message to Techsupport', user.language): 'send_message_to_techsupport'}
            )
        )
    else:
        bot.send_message(
            msg.chat.id, 
            _(f'⚙ You are already a staff member ⚙', user.language)
        )
    return start_bot(msg)



@bot.callback_query_handler(func=lambda call: call.data == 'send_message_to_techsupport')
def send_message_to_techsupport(call):
    def send_message(msg):
        try:
            for support_id in get_json_config().get('techsupportIds'):
                bot.forward_message(
                    chat_id=support_id, 
                    from_chat_id=msg.chat.id, 
                    message_id=msg.message_id
                )
        except Exception:
            answer_msg = _("Some error occurred", user.language)
            print(f"ERROR: cannot send support message to {support_id}")
        else:
            answer_msg = _("Your message was recieved", user.language)
        finally:
            bot.send_message(msg.chat.id, answer_msg)
            return start_bot(msg)

    if call.message:
        user = bot.session['user']
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text
        ) # make the button disappear
        bot.send_message(
            user.user_id,
            _(
                'Напишите сообщение техподдержке ({} - возврат в меню)',
                user.language,
                parse_mode='newline'
            ).format('/menu', bot.get_me().username)
        )
        bot.register_next_step_handler(call.message, send_message)



@bot.message_handler(commands=['help'])
def send_bot_help(msg):
    user = bot.session['user']
    help_message = 'Bot\'s commands:;' + ';'.join([
        '{} - %s' % v for k, v in bot.full_bot_commands.items()
    ])
    bot.send_message(
        msg.chat.id,
        _(
            help_message,
            user.language,
            parse_mode='newline'
        ).replace('{ }', '{}').format(*list(bot.full_bot_commands.keys()))
    )
    return start_bot(msg, to_show_commands=False)



#################################################################################################################


def update_rates():
    while True:
        currency_parser.update_start_value()
        time.sleep(53)



@catch_exc(to_print=True)
def check_premium_ended():
    def check_user_premium_ended(user):
        if get_current_datetime(utcoffset=user.timezone) > user.is_pro:
            bot.send_message(
                user.user_id,
                _('Your premium has expired, but you can always refresh it!', user.language)
            )
            user.delete_premium()

    while True:
        with futures.ThreadPoolExecutor(max_workers=50) as executor:
            for user in DBUser.get_pro_users():
                executor.submit(check_user_premium_ended, user)
        time.sleep(180) # 3 min



@catch_exc(to_print=True)
def verify_predictions():
    while True:
        for pred in DBPrediction.get_unverified_predictions():
            try:
                pred_res = currency_parser.get_rate(pred.iso_from, pred.iso_to)
            except ValueError:
                user = DBUser(pred.user_id)
                user.create_prediction(
                    pred.iso_from, 
                    pred.iso_to, 
                    pred.value,
                    pred.up_to_date + datetime.timedelta(0, 5*60) # 5 minutes
                )
                bot.send_messsage(
                    pred.user_id, 
                    _(
                        "The quotes are unreachable, the prediction {} was scheduled for 5 minutes later", 
                        user.language
                    ).format(repr(pred))
                )
                pred.delete(force=True)
            else:
                pred.update(real_value=pred_res.get(pred.iso_to))
                user = DBUser(pred.user_id)
                diff = currency_parser.calculate_difference(old=pred.value, new=pred.real_value)
                bot.send_message(
                    pred.user_id, 
                    _(
                        'Results of `{}`:\n*Predicted value:* {}\n*Real value:* {}\n*Percentage difference:* {}',
                        user.language
                    ).format(
                        repr(pred),
                        prettify_float(pred.value),
                        prettify_float(pred.real_value),
                        prettify_percent(diff.get('percentage_difference'), to_sign=True)
                    ),
                    parse_mode='Markdown'
                )



@catch_exc(to_print=True)
def check_alarm_times():
    while True:
        t_ = get_current_datetime(utcoffset=0).time()
        if t_.minute == 0:
            thread = threading.Thread(
                target=start_alarms, 
                args=(str(t_.strftime('%H:%M')),), 
                daemon=True
            )
            thread.start()
        time.sleep(59.9) 



@catch_exc(to_print=True)
def start_alarms(time_):
    with futures.ThreadPoolExecutor(max_workers=50) as executor:
        for user in DBUser.get_users_by_check_time(time_):
            executor.submit(send_alarm, user, time_)



@catch_exc(to_print=True)
def send_alarm(user, t):
    for k, v in user.get_currencies_by_check_time(t).items():
        try:
            rate = currency_parser.check_delta(
                k, 'USD', 
                v.get('start_value'), v.get('percent_delta')
            )
        except ValueError:
            bot.send_message(
                user.user_id, 
                _("The quotes are not available, the notification can not be sent", user.language)
            )
        else:
            if rate.get('new', None) is not None: # WARNING: CAN BE DELETED
                new, old = rate.get('new'), rate.get('old')
                user.update_rates(k, start_value=new)
                try:
                    bot.send_message(
                        user.user_id,
                        _(
                            '*Notification*\n*{}* = *{} USD*\nThe change: *{:+} ({})*\nPrevious: *{} = {} USD *',
                            user.language
                        ).format(
                            k, 
                            prettify_float(new), 
                            prettify_float(rate.get('difference')), 
                            prettify_percent(rate.get('percentage_difference'), to_sign=True), 
                            k, 
                            prettify_float(old)
                        ),
                        parse_mode='Markdown'
                    )
                except telebot.apihelper.ApiTelegramException:
                    # from traceback: "Bad Request: chat not found"
                    user.update(is_active=0) 
                    # not to sent notifications anymore, since chat is not reachable



def start_checking_threads():
    for target in [check_alarm_times, update_rates, check_premium_ended, verify_predictions]:
        threading.Thread(target=target, daemon=True).start()



def main():
    import logging
    telebot.logger.setLevel(logging.DEBUG)
    start_checking_threads()
    print(f"[INFO] [FULL DEBUG] Bot started at {str(get_current_datetime())}")
    bot.polling()
    print(f"[INFO] [FULL DEBUG] Bot stopped at {str(get_current_datetime())}")


####################################################################################################


if __name__ == '__main__':
    main()
