from concurrent import futures
import datetime
import threading
import time

import telebot
from telebot.types import LabeledPrice


from configs import _globals, MAIN_TOKEN, TECHSUPPORT_TOKEN
from models._parser import *
from models.user import DBUser, DBCurrencyPrediction
from utils import *
from utils.translator import translate as _
from utils.telegram import kbs, inline_kbs
from utils._datetime import (
    check_datetime_in_future,
    convert_from_country_format,
    convert_to_country_format,
    get_current_datetime
)
from utils.mail import send_mail

# ! ALL COMMENTED CODE IN ALL FILES IS IMPLEMENTATION OF LIKING SYSTEM !
########################################################################
telebot.apihelper.ENABLE_MIDDLEWARE = True

bot = telebot.TeleBot(MAIN_TOKEN.TOKEN, threaded=False) # RecursionError
bot.full_bot_commands = {
    '/start': 'запустить бота', # Start the bot
    '/me': 'просмотреть вашу информация', # See your info
    '/today': 'котировки', # Quotes
    '/change_checktime': 'сменить время оповещений', # Change check times
    '/change_delta': 'сменить разницу в процентах, при которой оповещать',
    # Change percent delta at which to notify
    '/change_timezone': 'сменить ваш часовой пояс', # change your timezone
    '/toggle_alarms': 'включить/выключить оповещения', # Toggle alarms
    '/make_prediction': 'сделать прогноз', # Make a prediction
    '/get_predictions': 'перейти в раздел "Прогнозы"', # Go to "Predictions" section
    '/convert': 'конвертер валют', # Currency Converter
    '/menu': 'главное меню', # Main menu
    '/subscription': 'перейти в раздел "Подписка"', # Go to "Subscription" section
    '/language': 'сменить язык', # Change language
    '/techsupport': 'перейти в раздел "Техподдержка"', # Go to "Techsupport" section
    '/help': 'помощь по командам' # Help with commands
}
bot.short_bot_commands = {
    k: bot.full_bot_commands.get(k)
    for k in ['/start', '/me', '/today', '/subscription', '/language', '/help']
}


brent_parser = BrentParser()
bitcoin_parser = BitcoinParser()
rts_parser = RTSParser()
currency_parser = FreecurrencyratesParser()

########################################################################



@bot.middleware_handler(update_types=['message'])
def check_if_command(bot_instance, message):
    is_bot_command = message.entities and message.entities[0].type == 'bot_command'
    if is_bot_command:
        try:    
            bot_instance.clear_step_handler(message)
        except Exception:
            pass



@bot.message_handler(commands=['start'])
def start_message(msg):
    tech_support_recognizer = TECHSUPPORT_TOKEN.ACCESSIBLE_LINK.split('=')[1]
    args = msg.text.split()[1:]
    user = DBUser(msg.chat.id)
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
            # I'm Bot, your personal shareholder bot, and I'm going to keep you in touch with all importnant trading events
            user.language
        ).format(bot.get_me().first_name),
        parse_mode='html'
    )
    if args and tech_support_recognizer in args or not list(DBUser.get_staff_users()):
        # if user got in bot with techsupport link or there are not support users
        user.init_staff()
        bot.send_message(
            msg.chat.id,
            _(
                '⚙ You have received a technical support status ⚙',
                user.language
            ) # "You recieved staff status"
        )    
    return start_bot(msg)



@bot.message_handler(commands=['menu'])
def start_bot(msg, to_show_commands:bool=True):
    user = DBUser(msg.chat.id)
    buttons = [
        _('Quotes', user.language), # "quotes"
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
            _("View info", user.language): see_user_info, # See your info
            _('Change alarm time', user.language): change_user_rate_check_times, # change notifications time
            _('Change alarm percent', user.language):change_user_rate_percent_delta, # change percent delta
            _('Toggle alarms', user.language): toggle_user_alarms,
            _('Change time zone', user.language): change_user_timezone, # change time zone
            _('Main menu', user.language): start_bot # main menu
        }
        if user.is_pro:
            buttons[_('⚜ Add your own currency ⚜', user.language)] = add_new_currency # add your currency
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
        # bot.send_message(
        #     msg.chat.id,
        #     _(
        #         "❗ Я не понял ваш ответ, попробуйте что-то другое ❗",
        #         user.language
        #     ),
        #     reply_markup=kbs(list(buttons))
        # )
        return bot.register_next_step_handler(msg, choose_option, user, buttons)



@bot.message_handler(commands=['today'])
def get_currency_rates_today(msg, user=None):
    user = user or DBUser(msg.chat.id)
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
                    '❗ Choose only from the suggestions ❗', # choose only from offered
                    user.language
                )
            )
            bot.register_next_step_handler(msg, choose_option_inner)
        else:
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
            up_to_date = convert_from_country_format(
                msg.text,
                user.language,
                user.timezone
            )
            assert check_datetime_in_future(up_to_date)
        except ValueError:
            bot.send_message(
                msg.chat.id, 
                _(
                    '❗ Please enter the date only in the specified format ❗',
                    user.language
                )
            )
            bot.register_next_step_handler(msg, get_date)
        except AssertionError:
            bot.send_message(
                msg.chat.id,
                _(
                    '❗ You cannot enter a past date ❗',
                    user.language
                )
            )
            bot.register_next_step_handler(msg, get_date)
        else:
            date = up_to_date
            bot.send_message(
                msg.chat.id,
                _(
                    'Enter the iso-code of the forecast currency `<isocode> - <isocode>`\nFor example, USD-RUB',
                    user.language
                    
                ),
                parse_mode='markdown',
                reply_markup=kbs(list(_globals.ACCEPTABLE_CURRENCIES_CONVERTION))
            )
            bot.register_next_step_handler(msg, get_iso)

    def get_iso(msg):
        nonlocal iso_from, iso_to
        msg.text = _globals.ACCEPTABLE_CURRENCIES_CONVERTION.get(msg.text, msg.text)
        iso_from, iso_to = [x.strip() for x in msg.text.split('-')] 
        if currency_parser.check_currency_exists(iso_from) and currency_parser.check_currency_exists(iso_to) or (
                msg.text in _globals.ACCEPTABLE_CURRENCIES_CONVERTION.values()
            ):
            bot.send_message(
                msg.chat.id,
                _(
                    "Enter the forecast result (for example, 27.50, 22300)", # Enter predictable value
                    user.language
                )
            )
            bot.register_next_step_handler(msg, get_value)
        else:
            bot.send_message(
                msg.chat.id,
                _(
                    "❗ This currency does not exist or is not supported, please try another one ❗",
                    user.language
                )
            )
            bot.register_next_step_handler(msg, get_iso)


    def get_value(msg):
        nonlocal value
        try:
            value = float(msg.text.replace(',', '.'))
        except ValueError:
            bot.send_message(
                msg.chat.id,
                _(
                    '❗ Enter only numbers ❗', # Enter only numbers
                    user.language
                )
            )
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
            user.create_prediction(date, iso_from, iso_to, value)
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
        _(
            'To exit anywhere, enter {}',
            user.language
        ).format('/menu')
    )
    datetime_check_str = 'ДД.ММ.ГГГГ ЧЧ:ММ' if user.language ==  'ru' else 'MM-DD-YYYY HH:ММ AM/PM'
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
        parse_mode='markdown'
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
        #         
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
                _(
                    '❗ Choose only from the suggestions ❗',
                    user.language
                ),
                reply_markup=kbs(list(buttons))
            )
            bot.register_next_step_handler(msg, choose_option_inner)

    buttons = {
        _('My predictions', user.language): see_self_predictions, # My prediction
        _('Other predictions', user.language): see_other_users_predictions, # Other predictions
        # _('Учавствовать в оценивании', user.language): like_system,
        _('Main menu', user.language): start_bot # main menu
    }
    bot.send_message(
        msg.chat.id,
        _('Choose from the following:', user.language),
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
            
        ),
        reply_markup=inline_kbs({
            _('Delete', user.language): f'ask_delete_prediction_{pred_id}',
            _('Back', user.language): f'get_user_predictions_{prediction.user_id}'
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
            "Are you sure you want to delete this prediction:\n{}?",
            user.language,
            
        ).format(repr(prediction)),
        reply_markup=inline_kbs({
            _('Yes', user.language): f'delete_prediction_{pred_id}',
            _('No', user.language): f'get_user_predictions_{prediction.user_id}'
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
    bot.answer_callback_query(
        callback_query_id=call.id, 
        show_alert=False,
        text=_(
                "Prediction ({}) was deleted",
                user.language
            ).format(repr(prediction))
    )



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
                    'Here are your predictions',
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
            bot.send_message(
                msg.chat.id, 
                _(
                    '❗ Enter currency iso codes only in the specified format ❗',
                    user.language
                )
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
                    # Converter has not found these currencies, try again
                    user.language
                )
            )
            return bot.register_next_step_handler(msg, get_isos)
        else:
            markup = inline_kbs(
                {i: f"change_currency_converter_amount_to_{i}" for i in _globals.CURRENCY_RATES_CHANGE_AMOUNTS}
            )
            bot.send_message(
                msg.chat.id,
                _(
                    'Conversion by {}:\n{} {} - {} {}',
                    user.language,
                    
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
            'Enter the iso-code of the forecast currency `<isocode> - <isocode>`\nFor example, USD-RUB',
            user.language,
            
        ),
        parse_mode='markdown'
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
                        'Enter new amount', # Enter new amount
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
                # Cant respond, try again
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
            "Notifications {}",
            # Notifications enabled/disabled
            user.language
        ).format('включены' if user.is_active else 'отключены')
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
            bot.send_message(
                msg.chat.id, 
                _(
                    "Your interest on {} - {}%\nSelect the amount of interest",
                    user.language,
                    
                ).format(currency, user.rates.get(currency).get('percent_delta')),
                reply_markup=kbs(_globals.PERCENTAGES)
            )
            bot.register_next_step_handler(msg, inner2)
        else:
            bot.send_message(
                msg.chat.id, 
                '❗ Please enter only valid currencies ❗', 
                reply_markup=kbs(_globals.CURRENCIES)
            )
            bot.register_next_step_handler(msg, inner1)

    def inner2(msg):
        nonlocal currency
        try:
            if 'inf' not in msg.text:
                delta = float(msg.text)
            else:
                raise ValueError
        except ValueError:
            bot.send_message(msg.chat.id, _("❗ Enter only numbers ❗", user.language))
            return bot.register_next_step_handler(msg, inner2)
        user.update_rates(currency, percent_delta=delta)
        bot.send_message(
            msg.chat.id,
            _("Your percentage is now {}%", user.language).format(delta)
        )
        return start_bot(msg)

    kb = kbs(list(user.rates))
    bot.send_message(
        msg.chat.id, 
        _("Выберите валюту изменения процентов", user.language), 
        reply_markup=kb
    )
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
                        'Select {} date(s)',
                        user.language
                    ).format(start),
                    reply_markup=kbs(available_times))
                bot.register_next_step_handler(msg, inner2, start)
        else:
            bot.send_message(
                msg.chat.id,
                _('❗ Please enter only valid currencies ❗', user.language),
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
                    f"Enter more {iteration_num} date(s)",
                    user.language),
                reply_markup=kbs(available_times)
            )
            bot.register_next_step_handler(msg, inner2, iteration_num)        
    kb = kbs(list(user.rates))
    bot.send_message(msg.chat.id, _("Select the currency of the alert time change", user.language), reply_markup=kb)
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



def add_new_currency(msg):
    user = DBUser(msg.chat.id)


    def ask_new_iso(msg):
        iso = msg.text
        if not currency_parser.check_currency_exists(iso):
            bot.send_message(
                msg.chat.id,
                _(
                    '❗ This currency does not exist or is not supported, please try another one ❗',
                    user.language
                )
            )
            bot.register_next_step_handler(msg, ask_new_iso)
        elif iso in user.rates:
            bot.send_message(
                msg.chat.id, 
                _(
                    '❗ The currency is already on your currency list ❗',
                    user.language
                )
            )
            return start_bot(msg)
        elif user.is_pro:
            rate = prettify_float(currency_parser.get_rate(iso).get('USD'))
            reverse_rate = prettify_float(1/rate)
            user.add_rate(iso, start_value=rate, check_times=_globals.CHECK_TIMES)
            bot.send_message(
                msg.chat.id, 
                _(
                    'New currency has been created successfully!\nNow the rate is {} - {} USD, or 1 USD - {} {}',
                    user.language
                ).format(iso, rate, reverse_rate, iso)
            )
            return start_bot(msg)

    bot.send_message(
        msg.chat.id,
        _('Enter the iso-code of the new currency', user.language),
        reply_markup=kbs(['UAH', 'RUB', 'EUR'])
    )
    bot.register_next_step_handler(msg, ask_new_iso)



@bot.message_handler(commands=['subscription'])
def buy_subscription(msg):
    user = DBUser(msg.chat.id)
    json_config = get_json_config()
    prices_json_list = json_config.get('subscriptionPrices')
    start_price = json_config.get('subscriptionStartPrice')
    prices = [
        [
            LabeledPrice(
                label=f"Cost of subscription for {price.get('period')} month" + ('s' if price.get('period') > 1 else ''),
                amount=int(round(start_price * price.get('period'), 2) * 100)
                # * 100 because amount in cents
            )
        ] + ([
            LabeledPrice(
                label=f'Discount {price.get("discount")}%',
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
        if msg.text == _('Yes, I want to!', user.language):
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
        elif msg.text == _('No, thanks', user.language):
            bot.send_message(msg.chat.id, _('Okay, we\'ll wait!', user.language))
            return start_bot(msg)
        else:
            bot.send_message(
                msg.chat.id, 
                _(
                    "I don't quite understand your answer, I'm returning to the main menu...", 
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
    user = DBUser(msg.chat.id)
    n_months = int(msg.successful_payment.invoice_payload)
    datetime_expires = get_current_datetime(utcoffset=user.timezone) + datetime.timedelta(days=n_months*31)
    user.init_premium(datetime_expires)
    bot.send_message(
        msg.chat.id,
        _(
            "You have activated the Subscription before {}\nHappy trades!",
            user.language
        ).format(convert_to_country_format(datetime_expires, user.language))
    )
    return start_bot(msg)



@bot.message_handler(commands=['language'])
def change_language(msg):
    user = DBUser(msg.chat.id)
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
    user = DBUser(msg.chat.id)
    if not user.is_staff:
        bot.send_message(
            msg.chat.id,
            _(
                '⚙ This is techsupport of @{} ⚙\nFeel free to send us any feedbacks about this bot, we are always grateful for your help!',
                user.language
            ).format(bot.get_me().username),
            reply_markup=inline_kbs({_('Send message to Techsupport', user.language): 'send_message_to_techsupport'})
        )
    else:
        bot.send_message(
            msg.chat.id, 
            _(
                f'⚙ You are already a staff member ⚙',
                user.language,
                
            )
        )
    return start_bot(msg)



@bot.callback_query_handler(func=lambda call: call.data == 'send_message_to_techsupport')
def ask_for_staff_rank(call):
    def send_message(msg):
        bot.send_message(msg.chat.id, _("Wait a little, please", user.language))
        text = msg.text
        try:
            template = 'Feedback (@%s)\nFrom:%s\nMessage:%s'
            username = msg.from_user.username
            first_name = msg.from_user.first_name
            message = template % (
                bot.get_me().username,
                f"@{username}" if username else first_name,
                text
            )
            send_mail(message) # send email from self to self
        except Exception:
            answer_msg = _("Some error occurred", user.language)
        else:
            answer_msg = _("Your message was recieved", user.language)
        finally:
            bot.send_message(msg.chat.id, answer_msg)
            return start_bot(msg)

    if call.message:
        user = DBUser(call.message.chat.id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text
        ) # make the button disappear
        bot.send_message(
            user.user_id,
            _(
                'Напишите ваше сообщение техподдержке ({} чтобы выйти в меню)',
                user.language,
            ).format('/menu')
        )
        bot.register_next_step_handler(call.message, send_message)
        # bot.answer_callback_query(
        #     callback_query_id=call.id,
        #     show_alert=False,
        #     text=_(msg, user.language)
        # )



@bot.message_handler(commands=['help'])
def send_bot_help(msg):
    user = DBUser(msg.chat.id)
    help_message = 'Bot\'s commands:;'
    for k, v in bot.full_bot_commands.items():
        help_message += '{} - %s;' % v
    bot.send_message(
        msg.chat.id,
        _(
            help_message,
            user.language,
            parse_mode='newline'
        ).replace('{ }', '{}').format(*list(bot.full_bot_commands))
    )
    return start_bot(msg, to_show_commands=False)



#########################################################################


def update_rates():
    while True:
        for parser in [brent_parser, bitcoin_parser, rts_parser]:
            parser.update_start_value()
        time.sleep(53)



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



def verify_predictions():
    parsers = {
        parser.iso: parser
        for parser in [brent_parser, bitcoin_parser, rts_parser]
    }
    while True:
        for prediction in DBCurrencyPrediction.get_unverified_predictions():
            real_value = get_rate_safe(
                prediction.iso_from, 
                prediction.iso_to,
                1,
                0.0000000001
            ).get('new') 
            prediction.update(real_value=real_value)
            user = DBUser(prediction.user_id)
            perc_diff = round(
                abs(prediction.value-prediction.real_value)/prediction.value*100,
                _globals.PERCENT_PRECISION_NUMBER
            )
            bot.send_message(
                prediction.user_id, 
                _(
                    'Results of `{}`:\n**Predicted value:** {}\n**Real value:** {}\n**Percentage difference:** {}%',
                    user.language,
                    
                ).format(
                    repr(prediction),
                    prediction.value,
                    prediction.real_value,
                    perc_diff
                ),
                parse_mode='markdown'
            )



def check_alarm_times():
    previous_time = ''
    while True:
        t_ = get_current_datetime().time()
        some_time = str(t_.strftime('%H:%M'))
        if some_time != previous_time and t_.minute == 0:
            previous_time = some_time
            thread = threading.Thread(
                target=start_alarms, 
                args=(some_time,), 
                daemon=True
            )
            thread.start()
        time.sleep(50) 



def start_alarms(time_):
    with futures.ThreadPoolExecutor(max_workers=50) as executor:
        for user in DBUser.get_users_by_check_time(time_):
            executor.submit(send_alarm, user)



def get_rate_safe(iso_from, iso_to, start_value, percent_delta):
    parsers = {
        parser.iso: parser
        for parser in [brent_parser, bitcoin_parser, rts_parser]
    }
    parser = parsers.get(iso_from, currency_parser)
    try:
        if getattr(parser, 'iso', None) is not None:
            rate = parser.check_delta(
                start_value=start_value,
                percent_delta=percent_delta
            )
        else:
            # if parser is `FreecurrencyratesParser`
            rate = parser.check_delta(
                iso_from=iso_from,
                iso_to=iso_to,
                start_value=start_value, 
                percent_delta=percent_delta
            )
    except Exception:
        # if network can not be reached or somewhat
        default_value = get_default_values_from_config(iso_from)
        rate = CurrencyParser.calculate_differences(
            iso=iso_from,
            old=start_value,
            new=default_value,
            percent=percent_delta
        )
    return rate



def send_alarm(user):
    for k, v in user.rates.items():
        rate = get_rate_safe(k, 'USD', v.get('start_value'), v.get('percent_delta'))
        if rate.get('new', None): # WARNING: CAN BE DELETED
            new, old = rate.get('new'), rate.get('old')
            usd_to_iso_new = prettify_float(1/new)
            usd_to_iso_old = prettify_float(1/old)
            user.update_rates(k, start_value=new)
            perc_delta = round(
                rate.get('percentage_difference') * 100, 
                _globals.PERCENT_PRECISION_NUMBER
            )
            delta = prettify_float(rate.get('difference'))
            bot.send_message(
                user.user_id,
                _(
                    'Price ** {} ** - ** {} USD **, or ** 1 USD - {} {} **\nThe change was ** {} **, or ** {}% **\nPrevious price ** {} - {} USD **, or ** 1 USD - {} {} ** ',
                    user.language
                ).format(
                    k, new, usd_to_iso_new, k, delta, perc_delta, k, old, usd_to_iso_old, k
                ),
                parse_mode='markdown'
            )



def start_checking_threads():
    for target in [check_alarm_times, update_rates, check_premium_ended, verify_predictions]:
        threading.Thread(target=target, daemon=True).start()



def main():
    import logging
    telebot.logger.setLevel(logging.DEBUG)
    start_checking_threads()
    print(f"[INFO] [FULL DEBUG] Bot started at {str(get_current_datetime(utcoffset=0).time().strftime('%H:%M:%S'))} UTC")
    bot.infinity_polling()
    print(f"[INFO] [FULL DEBUG] Bot stopped at {str(get_current_datetime(utcoffset=0).time().strftime('%H:%M:%S'))} UTC")


#######################################################################


if __name__ == '__main__':
    main()
