import json
import requests
from math import ceil
from telebot import TeleBot
from telegram_bot_pagination import InlineKeyboardPaginator
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

FABRICHNAYA = 's9600961';
VIKHINO = 's9601627';

TEMP = {}

with open('Token.txt', 'r') as f:
  bot = TeleBot(f.read())

with open('KEY.txt', 'r') as f:
  KEY = f.read()

def toValidTime(x):
  return [int(n) for n in x[x.find('T')+1:x.find('+')].split(':')[:2]]


def toMinutes(arr):
  return arr[0] * 60 + arr[1]


def toTime(min):
  return [int(min / 60), min % 60]


def time(x):
  return f"{x[0]}:{str(x[1]).zfill(2)}"


def fetch(from_, to_, date):
  url = f'https://api.rasp.yandex.net/v3.0/search/?apikey={KEY}&format=json&from={from_}&to={to_}&lang=ru_RU&page=1&date={date}'

  res = requests.get(url)
  return [[toValidTime(x['departure']), int(x['duration'] / 60), x['thread']['transport_subtype']['title']] for x in json.loads(res.text)['segments']]

def getScheduleForth(from_, to_, page=1):
  date = '2022-09-14'

  startTime = 540 # need edit

  if f'{from_}-{to_}' in TEMP:
    forth = TEMP[f'{from_}-{to_}']
  else:
    forth = fetch(from_, to_, date)
    TEMP[f'{from_}-{to_}'] = forth

  forth = [x for x in forth if toMinutes(x[0]) <= startTime - 100]
  size = ceil(len(forth) / 4)
  forth = forth[::-1][4*page-4:4*page]

  schedule = 'Туда:\n'
  for i, x in enumerate(forth):
    schedule += f"{i+1 + 4*page-4}. {x[2]}\n{time(toTime(toMinutes(x[0])-20))} - {time(x[0])} ({x[1]} минут в пути)\n\n"
  return schedule, size

def getScheduleBack(from_, to_, page=1):
  date = '2022-09-14'

  endTime = 1070 # need edit

  if f'{to_}-{from_}' in TEMP:
    back = TEMP[f'{to_}-{from_}']
  else:
    back = fetch(to_, from_, date)
    TEMP[f'{to_}-{from_}'] = back

  back = [x for x in back if toMinutes(x[0]) >= endTime + 60]
  size = ceil(len(back) / 4)
  back = back[4*page-4:4*page]

  schedule = 'Обратно:\n'
  for i, x in enumerate(back):
    schedule += f"{i+1 + 4*page-4}. {x[2]}\n{time(toTime(toMinutes(x[0])-60))} - {time(x[0])} ({x[1]} минут в пути)\n\n"
  return schedule, size


@bot.message_handler(commands=['start'])
def start(message):
  markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
  schedule = KeyboardButton('Получить расписание')
  help = KeyboardButton('Настройки')
  markup.add(schedule, help)

  greet = 'Hi user!\nHere you can easily\nwork with schedule.\nPlease select one of this options:'

  bot.send_message(message.chat.id, greet, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.split('#')[0]=='scheduleF')
def characters_page_callback(call):
  page = int(call.data.split('#')[1])
  schedule, size = getScheduleForth(FABRICHNAYA, VIKHINO, page)
  paginator = InlineKeyboardPaginator(size, current_page=page, data_pattern="scheduleF#{page}#")

  bot.edit_message_text(
    schedule,
    call.message.chat.id,
    call.message.message_id,
    reply_markup=paginator.markup
  )

@bot.callback_query_handler(func=lambda call: call.data.split('#')[0]=='scheduleB')
def characters_page_callback(call):
  page = int(call.data.split('#')[1])
  schedule, size = getScheduleBack(FABRICHNAYA, VIKHINO, page)
  paginator = InlineKeyboardPaginator(size, current_page=page, data_pattern="scheduleB#{page}#")

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
    schedule, size = getScheduleForth(FABRICHNAYA, VIKHINO)
    paginator = InlineKeyboardPaginator(size, data_pattern="scheduleF#{page}#")
    bot.send_message(message.chat.id, schedule, reply_markup=paginator.markup)

    schedule, size = getScheduleBack(FABRICHNAYA, VIKHINO)
    paginator = InlineKeyboardPaginator(size, data_pattern="scheduleB#{page}#")
    bot.send_message(message.chat.id, schedule, reply_markup=paginator.markup)

bot.infinity_polling()