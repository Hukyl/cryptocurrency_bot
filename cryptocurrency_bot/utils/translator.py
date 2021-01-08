from googletrans import Translator


gt_t = Translator()


def translate(text:str, dest:str='ru', parse_mode='casual'):
    try:
        trans_text = gt_t.translate(text, dest=dest).text
    except google_new_transError:
        trans_text = text
    assert parse_mode in ['casual', 'newline']
    if parse_mode == 'newline':
        trans_text = trans_text.replace('; ', '\n').replace(';', '\n')
    return trans_text.strip()  # .strip() because sometimes it returns useless spaces
