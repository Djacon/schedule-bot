import json
import requests
from re import match
from math import ceil
from telebot import TeleBot
from datetime import date as DATE, timedelta
from telegram_bot_pagination import InlineKeyboardPaginator
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

FABRICHNAYA = 's9600961'
VYKHINO = 's9601627'

FROM_HOME_TO_TRAIN = 20
FROM_WORK_TO_TRAIN = 60

TOTAL_TIME_TO_WORK = 130
TOTAL_TIME_TO_HOME = 130

COUNT_OF_ITEMS = 4

TEMP = {}

with open('Token.txt', 'r') as f:
    bot = TeleBot(f.read())

with open('KEY.txt', 'r') as f:
    KEY = f.read()


def toValidTime(x):
    return x[x.find('T')+1:x.find('+')].split(':')[:2]


def toMinutes(arr):
    return int(arr[0]) * 60 + int(arr[1])


def toTime(min):
    return [int(min / 60) % 24, min % 60]


def time(x):
    return f"{x[0]}:{str(x[1]).zfill(2)}"


def addTime(arr, min):
    return time(toTime(toMinutes(arr) + min))


def startIdxToMinutes(idx):
    return [540, 640, 760, 860, 980, 1080][int(idx)-1]


def endIdxToMinutes(idx):
    return [630, 730, 850, 950, 1070, 1170][int(idx)-1]


def fetch(from_, to_, date):
    url = f'https://api.rasp.yandex.net/v3.0/search/?apikey={KEY}' +\
          f'&format=json&from={from_}&to={to_}&lang=ru_RU&page=1&date={date}'

    res = requests.get(url)
    return [[
        toValidTime(x['departure']), x['thread']['transport_subtype']['title']]
        for x in json.loads(res.text)['segments']]


def getScheduleForth(from_, to_, startTime, date, page=1):
    if f'{from_}-{to_}:{date}' in TEMP:
        forth = TEMP[f'{from_}-{to_}:{date}']
    else:
        forth = fetch(from_, to_, date)
        TEMP[f'{from_}-{to_}:{date}'] = forth

    forth = [x for x in forth if toMinutes(x[0]) + TOTAL_TIME_TO_WORK -
             FROM_HOME_TO_TRAIN <= startTime]
    size = ceil(len(forth) / COUNT_OF_ITEMS)
    forth = forth[::-1][COUNT_OF_ITEMS * (page-1): COUNT_OF_ITEMS * page]

    schedule = 'Туда:\nВремя выхода - посадки\n\n'
    for i, x in enumerate(forth):
        schedule += f"{i+1 + COUNT_OF_ITEMS * (page-1)}. {x[1]}\n" +\
                    f"{addTime(x[0], -FROM_HOME_TO_TRAIN)} - {time(x[0])} \
(прибытие в {addTime(x[0], TOTAL_TIME_TO_WORK-FROM_HOME_TO_TRAIN)})\n\n"
    return schedule, size


def getScheduleBack(from_, to_, endTime, date, page=1):
    if f'{to_}-{from_}:{date}' in TEMP:
        back = TEMP[f'{to_}-{from_}:{date}']
    else:
        back = fetch(to_, from_, date)
        TEMP[f'{to_}-{from_}:{date}'] = back

    back = [x for x in back if toMinutes(x[0]) >= endTime + FROM_WORK_TO_TRAIN]
    size = ceil(len(back) / COUNT_OF_ITEMS)
    back = back[COUNT_OF_ITEMS * (page-1): COUNT_OF_ITEMS * page]

    schedule = 'Обратно:\nВремя выхода - посадки\n\n'
    for i, x in enumerate(back):
        schedule += f"{i+1 + COUNT_OF_ITEMS * (page-1)}. {x[1]}\n" +\
                    f"{addTime(x[0], -FROM_WORK_TO_TRAIN)} - {time(x[0])} \
(прибытие в {addTime(x[0], TOTAL_TIME_TO_HOME-FROM_WORK_TO_TRAIN)})\n\n"
    return schedule, size


def getMarkup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    schedule = KeyboardButton('Получить расписание')
    help = KeyboardButton('Настройки')
    markup.add(schedule, help)
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    greet = 'Привет юзер!\nЗдесь ты можешь легко работать с расписанием ' +\
            'электричек.\n\nПожалуйста, выберите один из этих вариантов, ' +\
            'представленных ниже:'
    bot.send_message(message.chat.id, greet, reply_markup=getMarkup())


@bot.callback_query_handler(func=lambda c: c.data.split('#')[0] == 'scheduleF')
def scheduleF_page_callback(call):
    data = call.data.split('#')
    page = int(data[1])
    time = int(data[2])
    date = data[3]
    schedule, size = getScheduleForth(FABRICHNAYA, VYKHINO, time, date, page)
    paginator = InlineKeyboardPaginator(size, current_page=page,
                                        data_pattern="scheduleF#{page}#" +
                                        f'{time}#{date}')

    bot.edit_message_text(
        schedule,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=paginator.markup
    )


@bot.callback_query_handler(func=lambda c: c.data.split('#')[0] == 'scheduleB')
def scheduleB_page_callback(call):
    data = call.data.split('#')
    page = int(data[1])
    time = int(data[2])
    date = data[3]
    schedule, size = getScheduleBack(FABRICHNAYA, VYKHINO, time, date, page)
    paginator = InlineKeyboardPaginator(size, current_page=page,
                                        data_pattern="scheduleB#{page}#" +
                                        f'{time}#{date}')

    bot.edit_message_text(
        schedule,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=paginator.markup
    )


@bot.message_handler(content_types='text')
def message_reply(message):
    if message.text == 'Настройки':
        bot.send_message(message.chat.id, 'Здесь ничего нет (пока что)')

    elif message.text == 'Получить расписание':
        bot.send_message(message.chat.id, 'Укажите время или номер начала '
                         '<u>первой пары</u>:\n(Время пишется в виде: XX:XX, '
                         'номер пары: число 1-6)', parse_mode='HTML')
        bot.register_next_step_handler(message, firstPair)
    else:
        bot.send_message(message.chat.id, 'Команда не распознана')


def firstPair(message):
    if message.text.isdigit() and 0 < int(message.text) < 7:
        startTime = startIdxToMinutes(message.text)
    elif match(r'^(0?\d|1\d|2[0-3]):([0-5]\d)$', message.text):
        startTime = toMinutes(message.text.split(':'))
    else:
        bot.send_message(message.chat.id, 'Неправильный ввод!')
        return

    bot.send_message(message.chat.id, 'Укажите время или номер конца <u>'
                     'последней пары</u>:\n(Время пишется в виде: XX:XX, '
                     'номер пары: число 1-6)', parse_mode='HTML')
    bot.register_next_step_handler(message, lastPair, startTime)


def lastPair(message, startTime):
    if message.text.isdigit() and 0 < int(message.text) < 7:
        endTime = endIdxToMinutes(message.text)
    elif match(r'^(0?\d|1\d|2[0-3]):([0-5]\d)$', message.text):
        endTime = toMinutes(message.text.split(':'))
    else:
        bot.send_message(message.chat.id, 'Неправильный ввод!')
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    today = KeyboardButton('Сегодня')
    tmrrw = KeyboardButton('Завтра')
    other = KeyboardButton('Другой день')
    markup.add(today, tmrrw, other)

    bot.send_message(message.chat.id, 'Укажите день:', reply_markup=markup)
    bot.register_next_step_handler(message, scheduleDay, startTime, endTime)


def scheduleDay(message, startTime, endTime):
    if str(DATE.today()) == 'Сегодня':
        date = str(DATE.today())
    elif message.text == 'Завтра':
        date = str(DATE.today() + timedelta(days=1))
    elif message.text == 'Другой день':
        bot.send_message(message.chat.id, 'Укажите день в виде "dd.mm":',
                         reply_markup=getMarkup())
        bot.register_next_step_handler(message, otherDay, startTime, endTime)
        return
    else:
        bot.send_message(message.chat.id, 'Неправильный ввод!',
                         reply_markup=getMarkup())
        return

    getSchedule(message, startTime, endTime, date)


def otherDay(message, startTime, endTime):
    if not match(r'^\d\d\.\d\d$', message.text):
        bot.send_message(message.chat.id, 'Неправильный ввод!')
        return
    date = '2022-' + '-'.join(message.text.split('.')[::-1])
    getSchedule(message, startTime, endTime, date)


def getSchedule(message, startTime, endTime, date):
    bot.send_message(message.chat.id,
                     f"Расписание на {'.'.join(date.split('-')[::-1])}",
                     reply_markup=getMarkup())

    schedule, size = getScheduleForth(FABRICHNAYA, VYKHINO, startTime, date)
    paginator = InlineKeyboardPaginator(size, data_pattern="scheduleF#{page}#"
                                        f'{startTime}#{date}')
    bot.send_message(message.chat.id, schedule, reply_markup=paginator.markup)

    schedule, size = getScheduleBack(FABRICHNAYA, VYKHINO, endTime, date)
    paginator = InlineKeyboardPaginator(size, data_pattern="scheduleB#{page}#"
                                        f'{endTime}#{date}')
    bot.send_message(message.chat.id, schedule, reply_markup=paginator.markup)


bot.infinity_polling()
