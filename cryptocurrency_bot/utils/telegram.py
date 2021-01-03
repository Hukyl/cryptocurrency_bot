from telebot import types

from models.user import DBUser
from .translator import translate as _



def kbs(buttons, one_time_keyboard=True, row_width:int=None):
    """
    Creates a Telegram Keyboard
    :param buttons:
    :param one_time_keyboard:
    :param row_width:
    :return:
    """
    row_width = row_width or len(buttons)//2
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=one_time_keyboard, row_width=row_width)
    if len(buttons) > 1:
        kb.add(*[types.KeyboardButton(i) for i in buttons])
    else:
        kb = None
    return kb


def inline_kbs(buttons:dict, row_width:int=3):
    markup = types.InlineKeyboardMarkup(row_width=row_width)
    buttons = [
        types.InlineKeyboardButton(
            str(i), 
            callback_data=buttons[i]
        )
        for i in buttons
    ]
    markup.add(*buttons)
    return markup


def main_menu(return_func, *outer_args, **outer_kwargs):
    def inner1(func):
        def inner2(*args, **kwargs):
            msg = args[0]
            user = DBUser(msg.chat.id)
            if msg.text == _('Меню', user.language):
                return return_func(msg, *outer_args, **outer_kwargs)
            else:
                return func(*args, **kwargs)
        return inner2
    return inner1
