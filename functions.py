import json
from math import ceil
from os import environ
from requests import get as rget
from telegram_bot_pagination import InlineKeyboardPaginator

FABRICHNAYA = 's9600961'
VYKHINO = 's9601627'

FROM_HOME_TO_TRAIN = 20
FROM_WORK_TO_TRAIN = 60

TOTAL_TIME_TO_WORK = 130
TOTAL_TIME_TO_HOME = 130

COUNT_OF_ITEMS = 4

TEMP = {}

KEY = environ['KEY']
TOKEN = environ['TOKEN']


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

    res = rget(url)
    return [[
        toValidTime(x['departure']), x['thread']['transport_subtype']['title']]
        for x in json.loads(res.text)['segments']]


def fetchUni(group, weekday):
    if weekday == '7':
        return []
    url = f'https://schedule.mirea.ninja/api/schedule/{group}/full_schedule'
    res = rget(url)
    if res.status_code == 404:
        return 404
    return json.loads(res.text)['schedule'][weekday]['lessons']


def isOnTime(time, startTime):
    return (toMinutes(time) + TOTAL_TIME_TO_WORK -
            FROM_HOME_TO_TRAIN <= startTime)


def getInfo(from_, to_, date):
    if f'{from_}-{to_}:{date}' in TEMP:
        return TEMP[f'{from_}-{to_}:{date}']

    info = fetch(from_, to_, date)
    TEMP[f'{from_}-{to_}:{date}'] = info
    return info


def getLine(index, page, exitTime, name, totalTime, timeToTrain):
    arrival = addTime(exitTime, totalTime - timeToTrain)
    return f"{index + 1 + COUNT_OF_ITEMS * (page-1)}. {name}\n" +\
           f"{addTime(exitTime, -timeToTrain)} - {time(exitTime)} " +\
           f"(прибытие в {arrival})\n\n"


def getScheduleForth(from_, to_, startTime, date, page=1):
    forth = getInfo(from_, to_, date)
    forth = [x for x in forth if toMinutes(x[0]) + TOTAL_TIME_TO_WORK -
             FROM_HOME_TO_TRAIN + 40 >= startTime]
    size = ceil(len(forth) / COUNT_OF_ITEMS)
    forth = forth[COUNT_OF_ITEMS * (page-1): COUNT_OF_ITEMS * page]

    schedule = 'Туда:\nВремя выхода - посадки\n\n'
    for i, x in enumerate(forth):
        mark = '✅' if isOnTime(x[0], startTime) else '❌'
        schedule += f'{mark} ' + getLine(i, page, *x, TOTAL_TIME_TO_WORK,
                                         FROM_HOME_TO_TRAIN)
    return schedule, size


def getScheduleBack(from_, to_, endTime, date, page=1):
    back = getInfo(to_, from_, date)
    back = [x for x in back if toMinutes(x[0]) - FROM_WORK_TO_TRAIN >= endTime]
    size = ceil(len(back) / COUNT_OF_ITEMS)
    back = back[COUNT_OF_ITEMS * (page-1): COUNT_OF_ITEMS * page]

    schedule = 'Обратно:\nВремя выхода - посадки\n\n'
    for i, x in enumerate(back):
        schedule += getLine(i, page, *x, TOTAL_TIME_TO_HOME,
                            FROM_WORK_TO_TRAIN)
    return schedule, size


def parsePageData(call):
    data = call.data.split(':')
    return int(data[1]), int(data[2]), data[3]


def getPaginator(size, time, date, dir, page=1):
    return InlineKeyboardPaginator(size, current_page=page,
                                   data_pattern="schedule"+dir+":{page}:"
                                   f'{time}:{date}').markup
