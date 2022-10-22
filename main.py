import pytz
from re import match
from datetime import date as DATE, datetime, timedelta

from aiogram.types import Message
from aiogram import Bot, Dispatcher, executor
from aiogram.utils.exceptions import MessageNotModified
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

from functions import *
from keyboards import *
from database import DB

bot = Bot(TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Schedule(StatesGroup):
    date = State()
    gearbox = State()
    startTime = State()
    endTime = State()


class Settings(StatesGroup):
    settings = State()
    homeStation = State()
    workStation = State()
    timeToHome = State()
    timeToWork = State()
    countOfItems = State()
    group = State()


def today():
    return datetime.now(pytz.timezone('Europe/Moscow')).date()


def getUser(message: Message) -> list:
    usr = DB.getUser(message.from_user.id)
    return [*getStationsCodes(usr[0], usr[1]), *usr[2:-1]]


async def sendErr(message: Message, state, msg: str = 'Некорректный ввод!'):
    await state.finish()
    await message.answer(msg, reply_markup=mainKb)


async def getSettings(message: Message):
    user = DB.getUser(message.from_user.id)
    info = f"Станция у дома: *{user[0].capitalize()}*,\n"\
           f"Станция у вуза: *{user[1].capitalize()}*,\n"\
           f"Время от дома до станции: *{user[2]} мин*,\n"\
           f"Время от вуза до станции: *{user[3]} мин*,\n"\
           f"Кол-во выводимых электричек: *{user[4]}*,\n"\
           f"Группа в вузе: *{user[5]}*"
    await Settings.settings.set()
    await message.answer(info, parse_mode='markdown', reply_markup=panelKb)


# Admin panel (info)
@dp.message_handler(commands='info')
async def info(message: Message):
    if not isAdmin(message):
        await message.answer('Извините, команда доступна только админу!')
        return
    greet = 'Информация о боте:\n'\
            f"Кол-во сохраненных расписаний: {len(TEMP)}\n"\
            f"Кол-во пользователей в БД: {DB.userCount()}"
    await message.answer(greet)


# Admin panel (clear)
@dp.message_handler(commands='clear')
async def clear(message: Message):
    if not isAdmin(message):
        await message.answer('Извините, команда доступна только админу!')
        return
    TEMP.clear()
    await message.answer('Сохраненные расписания успешно удалены!')


@dp.message_handler(commands='start')
async def start(message: Message):
    user = message.from_user.first_name
    greet = f'Привет {user}!\nЗдесь ты можешь легко работать с расписанием ' +\
            'электричек.\n\nПожалуйста, выбери один из этих вариантов, ' +\
            'представленных ниже:'
    await message.answer(greet, reply_markup=mainKb)


@dp.message_handler(commands='today')
async def todayS(message: Message):
    group = DB.getUser(message.from_user.id)[5]
    if group == 'Не указана':
        return await message.answer('Вы не указывали свою группу!')
    await getUniSchedule(message, str(today()), group)


@dp.message_handler(commands='tomorrow')
async def tmmrwS(message: Message):
    group = DB.getUser(message.from_user.id)[5]
    if group == 'Не указана':
        return await message.answer('Вы не указывали свою группу!')
    await getUniSchedule(message, str(today() + timedelta(days=1)), group)


@dp.message_handler(commands='now')
async def nowS(message: Message):
    date = datetime.now(pytz.timezone('Europe/Moscow'))
    user = getUser(message)
    time = toMinutes([date.hour, date.minute]) - user[3] - 5
    date = str(today())
    await message.answer(f"Расписание на {'.'.join(date.split('-')[::-1])}",
                         reply_markup=mainKb)
    try:
        schedule, size = getScheduleNow([*user[:2][::-1], *user[2:]], time,
                                        date, 1, 'Туда')
        markup = getPaginator(size, time, date, user, 'B')
        await message.answer(schedule, reply_markup=markup)

        schedule, size = getScheduleBack(user, time, date)
        markup = getPaginator(size, time, date, user, 'B')
        await message.answer(schedule, reply_markup=markup)
    except KeyError:
        await message.answer('Ошибка вывода расписания :(')


@dp.callback_query_handler(lambda c: c.data.startswith('scheduleF'))
async def scheduleF_page_callback(call):
    page, time, date, *user = parsePageData(call)
    schedule, size = getScheduleForth(user, time, date, page)
    markup = getPaginator(size, time, date, user, 'F', page)
    await bot.answer_callback_query(call.id)
    await editMessage(schedule, call.message, markup)


@dp.callback_query_handler(lambda c: c.data.startswith('scheduleB'))
async def scheduleB_page_callback(call):
    page, time, date, *user = parsePageData(call)
    schedule, size = getScheduleBack(user, time, date, page)
    markup = getPaginator(size, time, date, user, 'B', page)
    await bot.answer_callback_query(call.id)
    await editMessage(schedule, call.message, markup)


async def editMessage(schedule: str, message, markup):
    await message.edit_text(schedule, reply_markup=markup)


@dp.errors_handler(exception=MessageNotModified)
async def message_not_modified_handler(*_):
    return True


@dp.message_handler(content_types='text')
async def message_reply(message: Message):
    if message.text == 'Настройки':
        await message.answer('Что бы вы хотели изменить?')
        await getSettings(message)
    elif message.text == 'Получить расписание':
        await Schedule.date.set()
        await message.answer('Укажите день:', reply_markup=scheduleKb)
    else:
        await message.answer('Команда не распознана', reply_markup=mainKb)


@dp.message_handler(state=Settings.settings)
async def settings(message: Message, state):
    if message.text == 'Станция у дома':
        await Settings.homeStation.set()
        await message.answer('Укажите название станции:', reply_markup=backKb)
    elif message.text == 'Станция у вуза':
        await Settings.workStation.set()
        await message.answer('Укажите название станции:', reply_markup=backKb)
    elif message.text == 'Время от дома до станции':
        await Settings.timeToHome.set()
        await message.answer('Укажите время (в минутах):', reply_markup=backKb)
    elif message.text == 'Время от вуза до станции':
        await Settings.timeToWork.set()
        await message.answer('Укажите время (в минутах):', reply_markup=backKb)
    elif message.text == 'Количество выводимых электричек':
        await Settings.countOfItems.set()
        await message.answer('Укажите количество выводимых электричек:',
                             reply_markup=backKb)
    elif message.text == 'Группа в вузе':
        await Settings.group.set()
        await message.answer('Укажите группу в виде "XXXX-XX-XX":',
                             reply_markup=backKb)
    elif message.text == '<- Назад':
        await sendErr(message, state, 'Хорошо')
    else:
        await sendErr(message, state)


async def handleStation(message: Message, state, index: int):
    stations = getStations()
    station = message.text.lower()
    if station in stations:
        DB.editUser(message.from_user.id, index, station)
        await sendErr(message, state, 'Изменено')
    elif message.text != '<- Назад':
        return await sendErr(message, state, 'Станция не найдена')
    await getSettings(message)


async def handleTime(message: Message, state, index: int):
    if match(r'^[1-9]\d*$', message.text):
        count = int(message.text)
        if count > 600:
            return await sendErr(message, state, 'Слишком большое число!')
        DB.editUser(message.from_user.id, index, count)
        await sendErr(message, state, 'Изменено!')
    elif message.text != '<- Назад':
        return await sendErr(message, state)
    await getSettings(message)


@dp.message_handler(state=Settings.homeStation)
async def homeStation(message: Message, state):
    await handleStation(message, state, 0)


@dp.message_handler(state=Settings.workStation)
async def workStation(message: Message, state):
    await handleStation(message, state, 1)


@dp.message_handler(state=Settings.timeToHome)
async def timeToHome(message: Message, state):
    await handleTime(message, state, 2)


@dp.message_handler(state=Settings.timeToWork)
async def timeToWork(message: Message, state):
    await handleTime(message, state, 3)


@dp.message_handler(state=Settings.countOfItems)
async def countOfItems(message: Message, state):
    if match(r'^[1-9]\d*$', message.text):
        count = int(message.text)
        if count > 10:
            return await sendErr(message, state,
                                 'Не поддерживается вывод более 10 значений!')
        DB.editUser(message.from_user.id, 4, count)
        await sendErr(message, state, 'Изменено!')
    elif message.text != '<- Назад':
        return await sendErr(message, state)
    await getSettings(message)


@dp.message_handler(state=Settings.group)
async def uniGroup(message: Message, state):
    if match(r'[А-Я]{4}-\d\d-\d\d', message.text):
        DB.editUser(message.from_user.id, 5, message.text)
        await sendErr(message, state, 'Изменено!')
    elif message.text != '<- Назад':
        return await sendErr(message, state)
    await getSettings(message)


@dp.message_handler(state=Schedule.date)
async def scheduleDay(message: Message, state):
    if message.text == 'Сегодня':
        date = today()
    elif message.text == 'Завтра':
        date = today() + timedelta(days=1)
    elif match(r'^\d\d\.\d\d$', message.text):
        date = '2022-' + '-'.join(message.text.split('.')[::-1])
    elif message.text == 'Другой день':
        return await message.answer('Укажите день в виде "dd.mm":')
    else:
        return await sendErr(message, state)

    async with state.proxy() as data:
        data['date'] = str(date)

    await Schedule.next()
    await message.answer('Выберите что-то из списка:', reply_markup=gearboxKb)


@dp.message_handler(state=Schedule.gearbox)
async def manualOrNot(message: Message, state):
    if message.text == 'Вручную':
        await Schedule.next()
        await message.answer('Укажите время или номер начала '
                             '<u>первой пары</u>:\n(Время пишется в виде: '
                             'XX:XX, номер пары: число 1-6)',
                             parse_mode='HTML', reply_markup=pairsKb)
    elif message.text == 'Расписание по группе':
        await message.answer('Укажите группу:', reply_markup=groupKb)
    elif message.text == 'Другая':
        await message.answer('Укажите группу в виде "XXXX-XX-XX":')
    elif match(r'[А-Я]{4}-\d\d-\d\d', message.text):
        group = message.text
        async with state.proxy() as data:
            await getUniSchedule(message, data['date'], group)
        await state.finish()
    else:
        await sendErr(message, state)


async def getUniSchedule(message: Message, date: str, group: str):
    datetime = DATE(*map(int, date.split('-')))
    week = (datetime - DATE(2022, 8, 29)).days // 7 + 1
    weekday = str(datetime.weekday() + 1)
    pairs = fetchUni(group, weekday)

    if not len(pairs):
        await message.answer('Ведутся временные работы в mirea.api\n'
                             'Пожалуйста, воспользуйтесь ручным режимом',
                             reply_markup=mainKb)
        return

    startTime, endTime = getStartEndTimes(pairs, week)
    if startTime:
        await getSchedule(message, date, startTime, endTime)
    else:
        dot_date = '.'.join(date.split('-')[::-1])
        await message.answer(f'Расписание на {dot_date}:\nПар нет',
                             reply_markup=mainKb)


@dp.message_handler(state=Schedule.startTime)
async def firstPair(message: Message, state):
    if match(r'^[1-6]$', message.text):
        startTime = startIdxToMinutes(message.text)
    elif match(r'^(0?\d|1\d|2[0-3]):([0-5]\d)$', message.text):
        startTime = toMinutes(message.text.split(':'))
    else:
        return await sendErr(message, state)

    async with state.proxy() as data:
        data['startTime'] = startTime

    await Schedule.next()
    await message.answer('Укажите время или номер конца <u>'
                         'последней пары</u>:\n(Время пишется в виде: XX:XX, '
                         'номер пары: число 1-6)', parse_mode='HTML')


@dp.message_handler(state=Schedule.endTime)
async def lastPair(message: Message, state):
    if match(r'^[1-6]$', message.text):
        endTime = endIdxToMinutes(message.text)
    elif match(r'^(0?\d|1\d|2[0-3]):([0-5]\d)$', message.text):
        endTime = toMinutes(message.text.split(':'))
    else:
        return await sendErr(message, state)

    async with state.proxy() as data:
        await getSchedule(message, data['date'], data['startTime'], endTime)
    await state.finish()


async def getSchedule(message: Message, date: str, startTime: int,
                      endTime: int):
    await message.answer(f"Расписание на {'.'.join(date.split('-')[::-1])}",
                         reply_markup=mainKb)
    user = getUser(message)
    try:
        schedule, size = getScheduleForth(user, startTime, date)
        markup = getPaginator(size, startTime, date, user, 'F')
        await message.answer(schedule, reply_markup=markup)

        schedule, size = getScheduleBack(user, endTime, date)
        markup = getPaginator(size, endTime, date, user, 'B')
        await message.answer(schedule, reply_markup=markup)
    except KeyError:
        await message.answer('Ошибка вывода расписания :(')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
