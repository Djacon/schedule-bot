import json
from math import ceil
from os import environ
from typing import Any, List
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


def toValidTime(x: str) -> List:
    return x[x.find('T')+1:x.find('+')].split(':')[:2]


def toMinutes(arr: List) -> int:
    return int(arr[0]) * 60 + int(arr[1])


def toTime(min: int) -> List:
    return [int(min / 60) % 24, min % 60]


def time(arr: List) -> str:
    return f"{arr[0]}:{str(arr[1]).zfill(2)}"


def addTime(arr: List, min: int) -> str:
    return time(toTime(toMinutes(arr) + min))


def startIdxToMinutes(idx: int) -> int:
    return [540, 640, 760, 860, 980, 1080][int(idx)-1]


def endIdxToMinutes(idx: int) -> int:
    return [630, 730, 850, 950, 1070, 1170][int(idx)-1]


def fetch(from_: str, to_: str, date: str) -> List:
    url = f'https://api.rasp.yandex.net/v3.0/search/?apikey={KEY}' +\
          f'&format=json&from={from_}&to={to_}&lang=ru_RU&page=1&date={date}'

    res = rget(url)
    return [[
        toValidTime(x['departure']), x['thread']['transport_subtype']['title']]
        for x in json.loads(res.text)['segments']]


def fetchUni(group: str, weekday: str) -> List:
    if weekday == '7':
        return [[]]
    url = f'https://schedule.mirea.ninja/api/schedule/{group}/full_schedule'
    res = rget(url)
    if res.status_code == 404:
        return []
    return json.loads(res.text)['schedule'][weekday]['lessons']


def isOnTime(time: List, startTime: int) -> bool:
    return (toMinutes(time) + TOTAL_TIME_TO_WORK -
            FROM_HOME_TO_TRAIN <= startTime)


def getInfo(from_: str, to_: str, date: str) -> List:
    if f'{from_}-{to_}:{date}' in TEMP:
        return TEMP[f'{from_}-{to_}:{date}']

    info = fetch(from_, to_, date)
    TEMP[f'{from_}-{to_}:{date}'] = info
    return info


def getLine(index: int, page: int, exitTime: int, name: str, totalTime: int,
            timeToTrain: int) -> str:
    return f"{index + 1 + COUNT_OF_ITEMS * (page - 1)}. {name}\n" +\
           f"{addTime(exitTime, -timeToTrain)} - {time(exitTime)} " +\
           f"(прибытие в {addTime(exitTime, totalTime - timeToTrain)})\n\n"


def getScheduleForth(from_: str, to_: str, startTime: int, date: str,
                     page: int = 1) -> tuple[str, int]:
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


def getScheduleBack(from_: str, to_: str, endTime: int, date: str,
                    page: int = 1) -> tuple[str, int]:
    back = getInfo(to_, from_, date)
    back = [x for x in back if toMinutes(x[0]) - FROM_WORK_TO_TRAIN >= endTime]
    size = ceil(len(back) / COUNT_OF_ITEMS)
    back = back[COUNT_OF_ITEMS * (page-1): COUNT_OF_ITEMS * page]

    schedule = 'Обратно:\nВремя выхода - посадки\n\n'
    for i, x in enumerate(back):
        schedule += getLine(i, page, *x, TOTAL_TIME_TO_HOME,
                            FROM_WORK_TO_TRAIN)
    return schedule, size


def parsePageData(call) -> tuple[int, int, str]:
    data = call.data.split(':')
    return int(data[1]), int(data[2]), data[3]


def getPaginator(size: int, time: str, date: int, dir: str, page: int = 1):
    return InlineKeyboardPaginator(size, current_page=page,
                                   data_pattern="schedule"+dir+":{page}:"
                                   f'{time}:{date}').markup
