from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def getMainKb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    schedule = KeyboardButton('Получить расписание')
    help = KeyboardButton('Настройки')
    return markup.add(schedule).row(help)


def getBackKb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    back = KeyboardButton('<- Назад')
    return markup.add(back)


def getPanelKb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    homeS = KeyboardButton('Станция у дома')
    workS = KeyboardButton('Станция у вуза')
    homeT = KeyboardButton('Время от дома до станции')
    workT = KeyboardButton('Время от вуза до станции')
    count = KeyboardButton('Количество выводимых электричек')
    back = KeyboardButton('<- Назад')
    return markup.add(homeS, workS, homeT, workT, count, back)


def getScheduleKb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    today = KeyboardButton('Сегодня')
    tmrrw = KeyboardButton('Завтра')
    other = KeyboardButton('Другой день')
    return markup.add(today, tmrrw).row(other)


def getGearboxKb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    bypair = KeyboardButton('Расписание по группе')
    manual = KeyboardButton('Вручную')
    return markup.add(bypair, manual)


def getPairsKb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=6)
    return markup.add(*[KeyboardButton(str(i)) for i in range(1, 7)])


def getGroupsKb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    first = KeyboardButton('КББО-01-22')
    second = KeyboardButton('ИВБО-04-22')
    other = KeyboardButton('Другая')
    return markup.add(first, second).row(other)


mainKb = getMainKb()
backKb = getBackKb()
panelKb = getPanelKb()
scheduleKb = getScheduleKb()
gearboxKb = getGearboxKb()
pairsKb = getPairsKb()
groupKb = getGroupsKb()
