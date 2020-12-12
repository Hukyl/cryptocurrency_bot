from google_trans_new import google_translator 

translator = google_translator()


def translate(message:str, destination:str='ru'):
    new_message = translator.translate(message, lang_tgt=destination)
    return new_message.strip()  # .strip() because sometimes it returns useless spaces