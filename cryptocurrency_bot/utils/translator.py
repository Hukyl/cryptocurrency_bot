from googletrans import Translator

gt_t = Translator()


translation_dict = {
    'I am <b>{}</b>, your personal shareholder bot, and I will keep you updated on important trading events!': {
        'en': 'I am <b>{}</b>, your personal shareholder bot, and I will keep you updated on important trading events!',
        'ru': 'Я - {}, твой личный бот акционер, и буду держать тебя в курсе важных событий трейдинга!'
    },
    ' none': {
        'en': ' none',
        'ru': ' нету'
    },
    'Amount on {}-{} changed to {}': {
        'en': 'Amount on {}-{} changed to {}',
        'ru': 'Сумма по {}-{} изменена на {}'
    },
    'Are you sure you want to delete this prediction:\n{}?': {
        'en': 'Are you sure you want to delete this prediction:\n{}?', 
        'ru': 'Вы уверены что хотите удалить этот прогноз:\n{}?'
    },
    'At the moment, the service has two languages: Russian 🇷🇺 and English 🇬🇧': {
        'en': 'At the moment, the service has two languages: Russian 🇷🇺 and English 🇬🇧',
        'ru': 'На данный момент, есть два языка: Русский 🇷🇺 и Английский 🇬🇧'
    },
    'Back': {
        'en': 'Back',
        'ru': 'Назад'
    },
    'Change alarm percent': {
        'en': 'Change alarm percent',
        'ru': 'Изменить процент оповещений'
    },
    'Change alarm time': {
        'en': 'Change alarm time',
        'ru': 'Изменить время оповещений'
    },
    'Change time zone': {
        'en': 'Change time zone',
        'ru': ''
    },
    'Choose from the following:': {
        'en': 'Choose from the following:',
        'ru': 'Выберите из предложенного:'
    },
    'Choose option': {
        'en': 'Choose option', 
        'ru': 'Выберите опцию'
    },
    'Conversion by {}:\n{} {} - {} {}': {
        'en': 'Conversion by {}:\n{} {} - {} {}',
        'ru': 'Обмен на {}:\n{} {} - {} {}'
    },
    'Convert': {
        'en': 'Convert',
        'ru': 'Обменник'
    },
    'Delete': {
        'en': 'Delete',
        'ru': 'Удалить'
    },
    'English 🇬🇧'  : {
        'en': 'English 🇬🇧', 
        'ru': 'Английский 🇬🇧'
    },
    'Enter more {} date(s)': {
        'en': 'Enter more {} date(s)', 
        'ru': 'Введите ещё {} дату(ы)'
    },
    'Enter new amount': {
        'en': 'Enter new amount', 
        'ru': 'Введите новую сумму'
    },
    'Enter the forecast result (for example, 27.50, 22300)': {
        'en': 'Enter the forecast result (for example, 27.50, 22300)', 
        'ru': 'Введите результат прогноза (например, 27.50, 22300)'
    },
    'Enter the iso-code of the forecast currency `<isocode> - <isocode>`\nFor example, USD-RUB': {
        'en': 'Enter the iso-code of the forecast currency `<isocode> - <isocode>`\nFor example, USD-RUB',
        'ru': 'Введите iso-код валюты прогноза `<изо-код>-<изо-код>`\nНапример, USD-RUB'
    },
    'Enter the iso-code of the new currency': {
        'en': 'Enter the iso-code of the new currency', 
        'ru': 'Введите iso-код новой валюты'
    },
    'Forecast not created': {
        'en': 'Forecast not created', 
        'ru': 'Прогноз не создан'
    },
    'Here are your predictions': {
        'en': 'Here are your predictions', 
        'ru': 'Вот ваши прогнозы'
    },
    'Here is the forecast data:\nForecast period: {}\nCurrency: {} - {}\nValue: {}\n.\nConfirm forecast creation?': {
        'en': 'Here is the forecast data:\nForecast period: {}\nCurrency: {} - {}\nValue: {}\n.\nConfirm forecast creation?',
        'ru': 'Вот данные прогноза: \nПериод прогноза: {} \nВалюта: {} - {} \nЗначение: {}\n. \nПодтвердить создание прогноза?'
    },
    "I don't quite understand your answer, I'm returning to the main menu...": {
        'en': "I don't quite understand your answer, I'm returning to the main menu...",
        'ru': 'Не совсем понял ваш ответ, возвращаюсь в главное меню...'
    },
    'Language': {
        'en': 'Language', 
        'ru': 'Язык'
    },
    'Language changed successfully': {
        'en': 'Language changed successfully', 
        'ru': 'Язык успешно сменён'
    },
    'Main menu': {
        'en': 'Main menu', 
        'ru': 'Главное меню'
    },
    'Make a prediction': {
        'en': 'Make a prediction', 
        'ru': 'Создать прогноз'
    },
    'My predictions': {
        'en': 'My predictions', 
        'ru': 'Мои прогнозы'
    },
    'New currency has been created successfully!\nNow the rate is {} - {} USD, or 1 USD - {} {}': {
        'en': 'New currency has been created successfully!\nNow the rate is {} - {} USD, or 1 USD - {} {}',
        'ru': 'Новая валюта успешно создана!\nСейчас курс {} - {} USD, или 1 USD - {} {}'
    },
    'No': {
        'en': 'No', 
        'ru': 'Нет'
    },
    'No, thanks': {
        'en': 'No, thanks', 
        'ru': 'Нет, спасибо'
    },
    'Notifications': {
        'en': 'Notifications', 
        'ru': 'Оповещения'
    },
    'Notifications {}': {
        'en': 'Notifications {}',
        'ru': 'Оповещения {}'
    },
    'Now your time zone is {}': {
        'en': 'Now your time zone is {}',
        'ru': 'Теперь ваш часовой пояс - {}'
    },
    "Okay, we'll wait!": {
        'en': "Okay, we'll wait!",
        'ru': 'Хорошо, мы подождём!'
    },
    'Oops, some error occurred, please try again later': {
        'en': 'Oops, some error occurred, please try again later', 
        'ru': 'Ой, возникла какая-то ошибка, попробуйте снова позже'
    },
    'Other predictions': {
        'en': 'Other predictions', 
        'ru': 'Другие прогнозы'
    },
    'Prediction {} was deleted': {
        'en': 'Prediction {} was deleted', 
        'ru': 'Прогноз {} был удалён'
    },
    'Price ** {} ** - ** {} USD **, or ** 1 USD - {} {} **\nThe change was ** {} **, or ** {}% **\nPrevious price ** {} - {} USD **, or ** 1 USD - {} {} ** ': {
        'en': 'Price ** {} ** - ** {} USD **, or ** 1 USD - {} {} **\nThe change was ** {} **, or ** {}% **\nPrevious price ** {} - {} USD **, or ** 1 USD - {} {} ** ',
        'ru': "Цена **{}** - **{} USD**, или **1 USD - {} {}**\nИзменение составило **{}**, или **{}%**\nПредыдущая цена **{} - {} USD**, или **1 USD - {} {}**"
    },
    'Quotes': {
        'en': 'Quotes', 
        'ru': 'Котировки'
    },
    'Reset': {
        'en': 'Reset', 
        'ru': 'Reset'
    },
    'Response not processed': {
        'en': 'Response not processed',
        'ru': 'Ответ не обработан'
    },
    'Results of `{}`:\n**Predicted value:** {}\n**Real value:** {}\n**Percentage difference:** {}%': {
        'en': 'Results of `{}`:\n**Predicted value:** {}\n**Real value:** {}\n**Percentage difference:** {}%',
        'ru': 'Результат `{}`:\n**Прогнозируемое значение:** {}\n**Настоящее значение:** {}\n**Разница в процентах:** {}%'
    },
    'Russian 🇷🇺': {
        'en': 'Russian 🇷🇺', 
        'ru': 'Русский 🇷🇺'
    },
    'Select the currency of the alert time change': {
        'en': 'Select the currency of the alert time change', 
        'ru': 'Выберите валюту для изменения времени оповещения'
    },
    'Select the currency to change percentage': {
        'en': 'Select the currency to change percentage', 
        'ru': 'Выберите валюту для изменения процента оповещений'
    },
    'Select the forecast validity period in the format `{}`\nFor example, {}': {
        'en': 'Select the forecast validity period in the format `{}`\nFor example, {}',
        'ru': 'Выберите период действия прогноза в формате `{}`\nНапример, {}'
    },
    'Select {} date(s)': {
        'en': 'Select {} date(s)', 
        'ru': 'Выберите {} дату(ы)'
    },
    'Send message to Techsupport': {
        'en': 'Send message to Techsupport', 
        'ru': 'Отправить сообщение техподдержке'
    },
    'Some error occurred': {
        'en': 'Some error occurred', 
        'ru': 'Возникла какая-то ошибка'
    },
    'Subscription': {
        'en': 'Subscription', 
        'ru': 'Подписка'
    },
    'Technical support': {
        'en': 'Technical support', 
        'ru': 'Техподдержка'
    },
    'The forecast has been created!': {
        'en': 'The forecast has been created!', 
        'ru': 'Прогноз создан!'
    },
    'There are no predictions to like yet, you can create one!': {
        'en': 'There are no predictions to like yet, you can create one!',
        'ru': 'Прогнозов, которые бы понравились, пока нет, их можно создать!'
    },
    'To exit anywhere, enter {}': {
        'en': 'To exit anywhere, enter {}', 
        'ru': 'Чтобы выйти, введите {}'
    },
    'Toggle alarms': {
        'en': 'Toggle alarms', 
        'ru': 'Включить/выключить оповещения'
    },
    'View info': {
        'en': 'View info', 
        'ru': 'Посмотреть информацию'
    },
    'View predictions': {
        'en': 'View predictions', 
        'ru': 'Посмотреть прогнозы'
    },
    'Wait a little, please': {
        'en': 'Wait a little, please', 
        'ru': 'Подождите немного, пожалуйста'
    },
    'Welcome, {}!': {
        'en': 'Welcome, {}!', 
        'ru': 'Добро пожаловать, {}!'
    },
    'When buying a Subscription, you get access to:\n1. Unlimited number of alerts per day\n2. Forecasts from experts\n3. Adding your currencies to alerts\nAnd more! \n\nBuy a Subscription today, and you will not regret it': {
        'en': 'When buying a Subscription, you get access to:\n1. Unlimited number of alerts per day\n2. Forecasts from experts\n3. Adding your currencies to alerts\nAnd more! \n\nBuy a Subscription today, and you will not regret it',
        'ru': 'Покупая Подписку, вы получаете доступ к:\n\t1. Неограниченому количеству оповещений в день\n\t2. Прогнозам от экспертов\n\t3. Добавлению своих валют к оповещения\n\tИ другому!\n\nПокупайте Подписку уже сегодня, и вы об этом не пожалеете'
    },
    'Write your message to technical support ({} to go to the menu)': {
        'en': 'Write your message to technical support ({} to go to the menu)',
        'ru': 'Напишите ваше сообщение техподдержке ({} чтобы выйти в меню)'
    },
    'Yes': {
        'en': 'Yes', 
        'ru': 'Да'
    },
    'Yes, I want to!': {
        'en': 'Yes, I want to!', 
        'ru': 'Да, я хочу!'
    },
    'You have activated the Subscription before {}\nHappy trades!': {
        'en': 'You have activated the Subscription before {}\nHappy trades!',
        'ru': 'Вы активировали подписку до {}\nУдачных трейдов!'
    },
    'You have already subscribed!': {
        'en': 'You have already subscribed!', 
        'ru': 'Вы уже подписаны!'
    },
    'You have no predictions so far, create one!': {
        'en': 'You have no predictions so far, create one!', 
        'ru': 'У вас ещё нету прогнозов, создайте их!'
    },
    'You pay for a Subscription for {} month(s)': {
        'en': 'You pay for a Subscription for {} month(s)', 
        'ru': 'Вы платите за подписку на протяжении {} месяца(ов)'
    },
    'You subscribed ⚜ and you are presented with all possible alert times!': {
        'en': 'You subscribed ⚜ and you are presented with all possible alert times!',
        'ru': "Вы офоромили ⚜ подписку ⚜, и вам предоставляются все возможные времена оповещений!"
    },
    'Your alert times for {} - {}': {
        'en': 'Your alert times for {} - {}', 
        'ru': 'Ваше время оповещений для {} - {}'
    },
    'Your current time zone is {}\nPlease select your time zone': {
        'en': 'Your current time zone is {}\nPlease select your time zone',
        'ru': 'Ваш текущий часовой пояс - {}\nВыберите ваш часовой пояс '
    },
    'Your interest on {} - {}%\nSelect the amount of interest': {
        'en': 'Your interest on {} - {}%\nSelect the amount of interest',
        'ru': 'Ваш процент на {} - {}%\nВыберите новый процент'
    },
    'You liked this prediction': {
        'en': 'You liked this prediction',
        'ru': 'Вам понравился этот прогноз'
    },
    'You disliked this prediction': {
        'en': 'You disliked this prediction',
        'ru': 'Вам не понравился этот прогноз'
    },
    'Your message was recieved': {
        'en': 'Your message was recieved',
        'ru': 'Ваше сообщение было получено'
    },
    'Your percentage is now {}%': {
        'en': 'Your percentage is now {}%',
        'ru': 'Ваш процент сейчас - {}%'
    },
    'Your premium has expired, but you can always refresh it!': {
        'en': 'Your premium has expired, but you can always refresh it!',
        'ru': 'Ваша подписка истекла, но вы можете купить новую!'
    },
    '⚙ This is techsupport of @{} ⚙\nFeel free to send us any feedbacks about this bot, we are always grateful for your help!': {
        'en': '⚙ This is techsupport of @{} ⚙\nFeel free to send us any feedbacks about this bot, we are always grateful for your help!',
        'ru': '⚙ Это техподдержка @{} ⚙\nНе стесняйтесь присылать нам любые отзывы об этом боте, мы всегда благодарны за вашу помощь!'
    },
    '⚙ You are already a staff member ⚙': {
        'en': '⚙ You are already a staff member ⚙', 
        'ru': '⚙ Вы уже являетесь сотрудником техподдержки ⚙'
    },
    '⚙ You have received a technical support status ⚙': {
        'en': '⚙ You have received a technical support status ⚙',
        'ru': '⚙ Вы получили статус техподдержки ⚙'
    },
    '⚜ Add your own currency ⚜': {
        'en': '⚜ Add your own currency ⚜', 
        'ru': '⚜ Добавить новую валюту ⚜'
    },
    '⚜ Experts predictions ⚜ are:': {
        'en': '⚜ Experts predictions ⚜ are:', 
        'ru': '⚜ Прогнозы экспертов ⚜: '
    },
    '❗ Choose only from the suggested languages ❗': {
        'en': '❗ Choose only from the suggested languages ❗', 
        'ru': '❗ Выберите только из предложенных языков ❗'
    },
    '❗ Choose only from the suggestions ❗': {
        'en': '❗ Choose only from the suggestions ❗', 
        'ru': '❗ Выберите только из предложенного ❗'
    },
    '❗ Enter currency iso codes only in the specified format ❗': {
        'en': '❗ Enter currency iso codes only in the specified format ❗',
        'ru': '❗ Вводите изо-коды валют только в указаном формате ❗'
    },
    '❗ Enter only numbers ❗': {
        'en': '❗ Enter only numbers ❗', 
        'ru': '❗ Вводите только числа ❗'
    },
    "❗ I can't understand your request, please try again ❗": {
        'en': "❗ I can't understand your request, please try again ❗", 
        'ru': '❗ Не могу вас понять, попробуйте ещё раз ❗'
    },
    '❗ Please enter only available dates ❗': {
        'en': '❗ Please enter only available dates ❗', 
        'ru': '❗ Вводите только доступные даты ❗'
    },
    '❗ Please enter only suggested time zones ❗': {
        'en': '❗ Please enter only suggested time zones ❗', 
        'ru': '❗ Выберите только из предложенных часовых поясов ❗'
    },
    '❗ Please enter only suggested values ❗': {
        'en': '❗ Please enter only suggested values ❗',
        'ru': '❗ Вводите только предложенные значение ❗'
    },
    '❗ Please enter only valid currencies ❗': {
        'en': '❗ Please enter only valid currencies ❗', 
        'ru': '❗ Вводите только допустимые валюты ❗'
    },
    '❗ Please enter the date only in the specified format ❗': {
        'en': '❗ Please enter the date only in the specified format ❗', 
        'ru': '❗ Вводите дату только в указаном формате ❗'
    },
    '❗ The converter did not find such currencies, please try again ❗': {
        'en': '❗ The converter did not find such currencies, please try again ❗',
        'ru': '❗ Конвертер не нашёл таких валют, попробуйте ещё раз ❗'
    },
    '❗ The currency is already on your currency list ❗': {
        'en': '❗ The currency is already on your currency list ❗',
        'ru': '❗ Валюта уже в вашем списке валют ❗'
    },
    '❗ This currency does not exist or is not supported, please try another one ❗': {
        'en': '❗ This currency does not exist or is not supported by the server, please try another one ❗',
        'ru': '❗ Эта валюта не существует или не поддерживается, попробуйте другую ❗'
    },
    '❗ You cannot enter a past date ❗': {
        'en': '❗ You cannot enter a past date ❗', 
        'ru': '❗ Вы не можете ввести уже прошедшую дату ❗'
    }
}


def translate(text:str, dest:str='ru', parse_mode:str='casual'):
    res = translation_dict.get(text, None)
    assert parse_mode in ['casual', 'newline']
    if res is None:
        res = gt_t.translate(text, dest=dest).text
        return text.replace('; ', '\n').replace(';', '\n') if parse_mode == 'newline' else text
    else:
        res = res.get(dest, text)
    return res.replace('; ', '\n').replace(';', '\n') if parse_mode == 'newline' else res
