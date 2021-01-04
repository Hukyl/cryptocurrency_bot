import time
import random
import re

from telebot import TeleBot

from models.user import DBUser
from utils.translator import translate as _
from configs import TECHSUPPORT_TOKEN



bot = TeleBot(TECHSUPPORT_TOKEN.TOKEN, threaded=True)


def send_message_to_techsupport(message, if_one:bool=False, **kwargs):
    if if_one:
        try:
            staff_user = random.choice(list(DBUser.get_staff_users()))
            bot.send_message(staff_user.user_id, message, **kwargs)
            return True
        except IndexError:
            return False
    else:
        for staff_user in DBUser.get_staff_users():
            bot.send_message(staff_user.user_id, message, **kwargs)
        return True


@bot.message_handler(commands=['start'])
def start_bot(msg):
    user = DBUser(msg.chat.id)
    bot.send_message(
        msg.chat.id,
        _(
            f'Hello! This is tech support!\
            ;To write to us, start your message with ',
            user.language,
            parse_mode='newline'
        ) + ' `ToTechSupport`',
        parse_mode='Markdown'
    )


@bot.message_handler(content_types=['text'])
def accept_message(msg):
    user = DBUser(msg.chat.id)
    if msg.text.startswith('ToTechSupport'):
        msg.text = msg.text[13:]
        tech_msg = f'TechSupport message\nFrom: @{msg.from_user.username}\nMessage: {msg.text}'
        send_message_to_techsupport(tech_msg)
        bot.send_message(msg.chat.id, _('Your message was accepted, thank you for your feedback!', user.language))
    else:
        bot.send_message(msg.chat.id, _('Sorry, can not understand what you said', user.language))


@bot.callback_query_handler(func=lambda call:'_staff_permission_' in call.data)
def ask_for_staff_rank(call):
    if call.message:
        action = bool(call.data.split('_')[0] == 'allow')
        user = DBUser(int(call.data.split('_')[-1]))
        user_username = re.findall(r'@\S+', call.message.text)[0]
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"You {'allowed' if action else 'declined'} staff permission for {user_username}"
        )
        user.update(is_staff=action)
        if action:
            user.init_staff()
        bot.send_message(
            user.user_id,
            _(
                f"⚙ You were {'allowed' if user.is_staff else 'declined'} for a staff permission ⚙",
                user.language
            )
        )


def main():
    return bot.infinity_polling()


if __name__ == '__main__':
    print(f"[INFO] TechSupportBot started at {str(time.strftime('%H:%M:%S'))}")
    main()
    print(f"[INFO] TechSupprtBot stopped at {str(time.strftime('%H:%M:%S'))}")
