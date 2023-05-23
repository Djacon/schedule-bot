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
    count = KeyboardButton('Кол-во выводимых электричек')
    group = KeyboardButton('Группа в вузе')
    back = KeyboardButton('<- Назад')
    return markup.add(homeS, workS, homeT, workT, count, group).row(back)


def getScheduleKb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    today = KeyboardButton('Сегодня')
    tmrrw = KeyboardButton('Завтра')
    other = KeyboardButton('Другой день')
    return markup.add(today, tmrrw).row(other)


def getGearboxKb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    bygroup = KeyboardButton('Расписание по группе')
    manual = KeyboardButton('Вручную')
    return markup.add(bygroup).row(manual)


def getPairsKb():
    keys = '123456❎'
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=7)
    return markup.add(*[KeyboardButton(str(i)) for i in keys])


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
