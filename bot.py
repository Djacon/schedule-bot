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

bot = Bot(TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Schedule(StatesGroup):
    date = State()
    gearbox = State()
    startTime = State()
    endTime = State()


def getMarkup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    schedule = KeyboardButton('Получить расписание')
    help = KeyboardButton('Настройки')
    markup.add(schedule, help)
    return markup


def today():
    return datetime.now(pytz.timezone('Europe/Moscow')).date()


async def sendErr(message, state, msg='Некорректный ввод!'):
    await state.finish()
    await message.answer(msg, reply_markup=getMarkup())


@dp.message_handler(commands=['start'])
async def start(message: Message):
    greet = 'Привет юзер!\nЗдесь ты можешь легко работать с расписанием ' +\
            'электричек.\n\nПожалуйста, выберите один из этих вариантов, ' +\
            'представленных ниже:'
    await message.answer(greet, reply_markup=getMarkup())


@dp.callback_query_handler(Text(startswith='scheduleF'))
async def scheduleF_page_callback(call):
    page, time, date = parsePageData(call)
    schedule, size = getScheduleForth(FABRICHNAYA, VYKHINO, time, date, page)
    markup = getPaginator(size, time, date, 'F', page)
    await editMessage(schedule, call.message, markup)


@dp.callback_query_handler(Text(startswith='scheduleB'))
async def scheduleB_page_callback(call):
    page, time, date = parsePageData(call)
    schedule, size = getScheduleBack(FABRICHNAYA, VYKHINO, time, date, page)
    markup = getPaginator(size, time, date, 'B', page)
    await editMessage(schedule, call.message, markup)


async def editMessage(schedule, msg, markup):
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
async def message_reply(message):
    if message.text == 'Настройки':
        await message.answer('Здесь ничего нет (пока что)')
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


@dp.message_handler(state=Schedule.date)
async def scheduleDay(message, state):
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
async def manualOrNot(message, state):
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
        return await message.answer('Укажите группу в виде "XXXX-XX-XX":')
    elif match(r'[А-Я]{4}-\d\d-\d\d', message.text):
        group = message.text
        async with state.proxy() as data:
            await getUniSchedule(message, state, data['date'], group)
    else:
        return await sendErr(message, state)


async def getUniSchedule(message, state, date, group):
    datetime = DATE(*map(int, date.split('-')))
    week = (datetime - DATE(2022, 8, 29)).days // 7 + 1
    weekday = str(datetime.weekday() + 1)
    pairs = fetchUni(group, weekday)

    if not len(pairs):
        return await sendErr(message, state, 'Ошибка вывода расписания :(')

    startTime, endTime = 0, 0
    for pair in pairs:
        for v in pair:
            if week in v['weeks'] and 'Дистан' not in v['rooms'][0]:
                if not startTime:
                    startTime = v['time_start']
                endTime = v['time_end']
                break
    if startTime:
        time = [toMinutes(x.split(':')) for x in (startTime, endTime)]
        await getSchedule(message, state, date, *time)
    else:
        dot_date = '.'.join(date.split('-')[::-1])
        await sendErr(message, state, f'Расписание на {dot_date}:\nПар нет')


@dp.message_handler(state=Schedule.startTime)
async def firstPair(message, state):
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
async def lastPair(message, state):
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


async def getSchedule(message, state, date, startTime, endTime):
    await state.finish()
    await message.answer(f"Расписание на {'.'.join(date.split('-')[::-1])}",
                         reply_markup=getMarkup())

    schedule, size = getScheduleForth(FABRICHNAYA, VYKHINO, startTime, date)
    markup = getPaginator(size, startTime, date, 'F')
    await message.answer(schedule, reply_markup=markup)

    schedule, size = getScheduleBack(FABRICHNAYA, VYKHINO, endTime, date)
    markup = getPaginator(size, endTime, date, 'B')
    await message.answer(schedule, reply_markup=markup)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
