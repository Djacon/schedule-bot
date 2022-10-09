import json
from math import ceil
from os import environ
from requests import get as rget
from telegram_bot_pagination import InlineKeyboardPaginator

TEMP = {}

KEY = environ['KEY']
TOKEN = environ['TOKEN']


def toValidTime(x: str) -> list:
    return x[x.find('T') + 1: x.find('+')].split(':')[:2]


def toMinutes(arr: list) -> int:
    return int(arr[0]) * 60 + int(arr[1])


def toTime(min: int) -> list:
    return [int(min / 60) % 24, min % 60]


def time(arr: list) -> str:
    return f"{arr[0]}:{str(arr[1]).zfill(2)}"


def addTime(arr: list, min: int) -> str:
    return time(toTime(toMinutes(arr) + min))


def startIdxToMinutes(idx: int) -> int:
    return [540, 640, 760, 860, 980, 1080][int(idx)-1]


def endIdxToMinutes(idx: int) -> int:
    return [630, 730, 850, 950, 1070, 1170][int(idx)-1]


def fetch(from_: str, to_: str, date: str) -> list:
    url = f'https://api.rasp.yandex.net/v3.0/search/?apikey={KEY}' +\
          f'&format=json&from={from_}&to={to_}&lang=ru_RU&page=1&date={date}'

    res = rget(url)
    return [[
        toValidTime(x['departure']), x['thread']['transport_subtype']['title'],
        int(x['duration'] / 60)] for x in json.loads(res.text)['segments']]


def fetchUni(group: str, weekday: str) -> list:
    if weekday == '7':
        return [[]]
    url = f'https://schedule.mirea.ninja/api/schedule/{group}/full_schedule'
    res = rget(url)
    if res.status_code == 404:
        return []
    return json.loads(res.text)['schedule'][weekday]['lessons']


def isOnTime(time: list, startTime: int, departure: int,
             timeToWork: int) -> bool:
    return (toMinutes(time) + departure + timeToWork <= startTime)


def getInfo(from_: str, to_: str, date: str) -> list:
    if f'{from_}-{to_}:{date}' in TEMP:
        return TEMP[f'{from_}-{to_}:{date}']

    info = fetch(from_, to_, date)
    TEMP[f'{from_}-{to_}:{date}'] = info
    return info


def getLine(index: int, page: int, exitTime: int, name: str, departure: int,
            timeToTrain: int, timeFromTrain, countOfItems: int) -> str:
    return f"{index + 1 + countOfItems * (page - 1)}. {name}\n" +\
           f"{addTime(exitTime, -timeToTrain)} - {time(exitTime)} " +\
           f"(прибытие в {addTime(exitTime, departure + timeFromTrain)})\n\n"


def getScheduleForth(user: list, startTime: int, date: str,
                     page: int = 1) -> tuple:
    homeS, workS, homeT, workT, count = user
    forth = getInfo(homeS, workS, date)
    forth = [x for x in forth if toMinutes(x[0]) + x[2] +
             workT + 40 >= startTime]
    size = ceil(len(forth) / count)
    forth = forth[count * (page-1): count * page]

    schedule = 'Туда:\nВремя выхода - посадки\n\n'
    for i, x in enumerate(forth):
        mark = '❌✅'[isOnTime(x[0], startTime, x[2], workT)]
        schedule += f'{mark} ' + getLine(i, page, *x, homeT, workT, count)
    return schedule, size


def getScheduleBack(user: list, endTime: int, date: str,
                    page: int = 1) -> tuple:
    homeS, workS, homeT, workT, count = user
    back = getInfo(workS, homeS, date)
    back = [x for x in back if toMinutes(x[0]) - workT >= endTime]
    size = ceil(len(back) / count)
    back = back[count * (page-1): count * page]

    schedule = 'Обратно:\nВремя выхода - посадки\n\n'
    for i, x in enumerate(back):
        schedule += getLine(i, page, *x, workT, homeT, count)
    return schedule, size


def parsePageData(call) -> tuple:
    data = call.data.split(':')
    return (int(data[1]), int(data[2]), *data[3:6],
            int(data[6]), int(data[7]), int(data[8]))


def getPaginator(size: int, time: str, date: int, user: list, dir: str,
                 page: int = 1):
    homeS, workS, homeT, workT, count = user
    return InlineKeyboardPaginator(size, current_page=page,
                                   data_pattern="schedule"+dir+":{page}:"
                                   f'{time}:{date}:{homeS}:{workS}:{homeT}:'
                                   f'{workT}:{count}').markup


def getStartEndTimes(pairs: list, week: int) -> list:
    stime, etime = 0, 0
    for pair in pairs:
        for v in pair:
            if week in v['weeks'] and 'Дистан' not in v['rooms'][0]:
                if not stime:
                    stime = v['time_start']
                etime = v['time_end']
                break
    if stime:
        return [toMinutes(x.split(':')) for x in (stime, etime)]
    return [stime, etime]


def getStations() -> dict:
    with open('stations.json', 'r', encoding='utf-8') as f:
        stations = json.loads(f.read())
        return stations


def getStationsCodes(forth: str, back: str) -> tuple:
    stations = getStations()
    return stations[forth], stations[back]


def isAdmin(message) -> bool:
    return message.from_user.id in [915782472]
