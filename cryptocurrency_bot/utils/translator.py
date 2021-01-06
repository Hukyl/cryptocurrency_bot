from google_trans_new import google_translator
from google_trans_new.google_trans_new import google_new_transError 


translator = google_translator()


def translate(message:str, destination:str='ru', parse_mode='casual'):
    try:
        new_message = translator.translate(message, lang_tgt=destination)
    except google_new_transError:
        new_message = message
    assert parse_mode in ['casual', 'newline']
    if parse_mode == 'newline':
        new_message = new_message.replace('; ', '\n').replace(';', '\n')
    return new_message.strip()  # .strip() because sometimes it returns useless spaces
