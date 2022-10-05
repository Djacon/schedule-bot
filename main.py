import pytz
from re import match
from datetime import date as DATE, datetime, timedelta

from aiogram.dispatcher.filters import Text
from aiogram import Bot, Dispatcher, executor
from aiogram.utils.exceptions import MessageNotModified
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message

from functions import *
from database import *
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


def getMain():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    schedule = KeyboardButton('Получить расписание')
    help = KeyboardButton('Настройки')
    markup.add(schedule, help)
    return markup


def getBack():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    back = KeyboardButton('<- Назад')
    markup.add(back)
    return markup


def today():
    return datetime.now(pytz.timezone('Europe/Moscow')).date()


async def sendErr(message: Message, state, msg: str = 'Некорректный ввод!'):
    await state.finish()
    await message.answer(msg, reply_markup=getMain())


async def getSettings(message: Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    homeS = KeyboardButton('Станция у дома')
    workS = KeyboardButton('Станция у вуза')
    homeT = KeyboardButton('Время от дома до станции')
    workT = KeyboardButton('Время от вуза до станции')
    count = KeyboardButton('Количество выводимых электричек')
    back = KeyboardButton('<- Назад')
    markup.add(homeS, workS, homeT, workT, count, back)

    user = DB.getUser(message.from_user.id)
    info = f"Станция у дома: *{user[0].capitalize()}*,\n"\
           f"Станция у вуза: *{user[1].capitalize()}*,\n"\
           f"Время от дома до станции: *{user[2]} мин*,\n"\
           f"Время от вуза до станции: *{user[3]} мин*,\n"\
           f"Количество выводимых электричек: *{user[4]}*"

    await Settings.settings.set()
    await message.answer(info, parse_mode='markdown', reply_markup=markup)


# Admin panel (info)
@dp.message_handler(commands=['info'])
async def info(message: Message):
    if message.from_user.id != 915782472:
        await message.answer('Извините, команда доступна только админу!',
                             reply_markup=getMain())
        return
    greet = 'Информация о боте:\n'\
            f"Кол-во сохраненных расписаний: {len(TEMP)}\n"\
            f"Кол-во пользователей в БД: {DB.userCount()}"
    await message.answer(greet)


# Admin panel (clear)
@dp.message_handler(commands=['clear'])
async def clear(message: Message):
    if message.from_user.id != 915782472:
        await message.answer('Извините, команда доступна только админу!')
        return
    TEMP.clear()
    await message.answer('Сохраненные расписания успешно удалены!')


@dp.message_handler(commands=['start'])
async def start(message: Message):
    user = message.from_user.first_name
    greet = f'Привет {user}!\nЗдесь ты можешь легко работать с расписанием ' +\
            'электричек.\n\nПожалуйста, выбери один из этих вариантов, ' +\
            'представленных ниже:'
    await message.answer(greet, reply_markup=getMain())


@dp.callback_query_handler(Text(startswith='scheduleF'))
async def scheduleF_page_callback(call):
    page, time, date, *user = parsePageData(call)
    schedule, size = getScheduleForth(user, time, date, page)
    markup = getPaginator(size, time, date, user, 'F', page)
    await editMessage(schedule, call.message, markup)


@dp.callback_query_handler(Text(startswith='scheduleB'))
async def scheduleB_page_callback(call):
    page, time, date, *user = parsePageData(call)
    schedule, size = getScheduleBack(user, time, date, page)
    markup = getPaginator(size, time, date, user, 'B', page)
    await editMessage(schedule, call.message, markup)


async def editMessage(schedule: str, msg, markup):
    await bot.edit_message_text(
        schedule,
        msg.chat.id,
        msg.message_id,
        reply_markup=markup
    )


@dp.errors_handler(exception=MessageNotModified)
async def message_not_modified_handler(*_):
    return True


@dp.message_handler(content_types='text')
async def message_reply(message: Message):
    if message.text == 'Настройки':
        await message.answer('Что бы вы хотели изменить?')
        await getSettings(message)
    elif message.text == 'Получить расписание':
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        today = KeyboardButton('Сегодня')
        tmrrw = KeyboardButton('Завтра')
        other = KeyboardButton('Другой день')
        markup.add(today, tmrrw, other)

        await Schedule.date.set()
        await message.answer('Укажите день:', reply_markup=markup)
    else:
        await message.answer('Команда не распознана')


@dp.message_handler(state=Settings.settings)
async def settings(message: Message, state):
    if message.text == 'Станция у дома':
        await Settings.homeStation.set()
        await message.answer('Укажите название станции:',
                             reply_markup=getBack())
    elif message.text == 'Станция у вуза':
        await Settings.workStation.set()
        await message.answer('Укажите название станции:',
                             reply_markup=getBack())
    elif message.text == 'Время от дома до станции':
        await Settings.timeToHome.set()
        await message.answer('Укажите время (в минутах):',
                             reply_markup=getBack())
    elif message.text == 'Время от вуза до станции':
        await Settings.timeToWork.set()
        await message.answer('Укажите время (в минутах):',
                             reply_markup=getBack())
    elif message.text == 'Количество выводимых электричек':
        await Settings.countOfItems.set()
        await message.answer('Укажите количество выводимых электричек:',
                             reply_markup=getBack())
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

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    bypair = KeyboardButton('Расписание по группе')
    manual = KeyboardButton('Вручную')
    markup.add(bypair, manual)
    await message.answer('Выберите что-то из списка:', reply_markup=markup)


@dp.message_handler(state=Schedule.gearbox)
async def manualOrNot(message: Message, state):
    if message.text == 'Вручную':
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=6)
        markup.add(*[KeyboardButton(str(i)) for i in range(1, 7)])

        await Schedule.next()
        await message.answer('Укажите время или номер начала '
                             '<u>первой пары</u>:\n(Время пишется в виде: '
                             'XX:XX, номер пары: число 1-6)',
                             parse_mode='HTML', reply_markup=markup)
    elif message.text == 'Расписание по группе':
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        first = KeyboardButton('КББО-01-22')
        second = KeyboardButton('ИВБО-04-22')
        other = KeyboardButton('Другая')
        markup.add(first, second, other)
        await message.answer('Укажите вашу группу:', reply_markup=markup)
    elif message.text == 'Другая':
        await message.answer('Укажите группу в виде "XXXX-XX-XX":')
    elif match(r'[А-Я]{4}-\d\d-\d\d', message.text):
        group = message.text
        async with state.proxy() as data:
            await getUniSchedule(message, state, data['date'], group)
    else:
        await sendErr(message, state)


async def getUniSchedule(message: Message, state, date: str, group: str):
    datetime = DATE(*map(int, date.split('-')))
    week = (datetime - DATE(2022, 8, 29)).days // 7 + 1
    weekday = str(datetime.weekday() + 1)
    pairs = fetchUni(group, weekday)

    if not len(pairs):
        return await sendErr(message, state, 'Ошибка вывода расписания :(')

    startTime, endTime = getStartEndTimes(pairs, week)
    if startTime:
        await getSchedule(message, state, date, startTime, endTime)
    else:
        dot_date = '.'.join(date.split('-')[::-1])
        await sendErr(message, state, f'Расписание на {dot_date}:\nПар нет')


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

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    today = KeyboardButton('Сегодня')
    tmrrw = KeyboardButton('Завтра')
    other = KeyboardButton('Другой день')
    markup.add(today, tmrrw, other)

    async with state.proxy() as data:
        await getSchedule(message, state, data['date'], data['startTime'],
                          endTime)


async def getSchedule(message: Message, state, date: str, startTime: int,
                      endTime: int):
    await state.finish()
    await message.answer(f"Расписание на {'.'.join(date.split('-')[::-1])}",
                         reply_markup=getMain())
    usr = DB.getUser(message.from_user.id)
    user = [*getStationsCodes(usr[0], usr[1]), *usr[2:]]
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
