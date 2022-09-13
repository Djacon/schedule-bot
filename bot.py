from turtle import backward
import requests
import json

FABRICHNAYA = 's9600961';
VIKHINO = 's9601627';


def toValidTime(x):
  return [int(n) for n in x[x.find('T')+1:x.find('+')].split(':')[:2]]


def toMinutes(arr):
  return arr[0] * 60 + arr[1]


def toTime(min):
  return [int(min / 60), min % 60]


def time(x):
  return f"{x[0]}:{str(x[1]).zfill(2)}"


def fetch(from_, to_, date):
  url = f'https://api.rasp.yandex.net/v3.0/search/?apikey=e2a18fc8-ef88-4955-9d98-9434eecc04de&format=json&from={from_}&to={to_}&lang=ru_RU&page=1&date={date}';

  res = requests.get(url)
  data = [[toValidTime(x['departure']), f"{int(x['duration'] / 60)} минут", x['thread']['transport_subtype']['title']] for x in json.loads(res.text)['segments']]
  return data


def getSchedule(from_, to_):
  date = '2022-09-13'

  startTime = 540
  endTime = 1070

  forth = fetch(from_, to_, date)
  back = fetch(to_, from_, date)

  forth = [x for x in forth if toMinutes(x[0]) <= startTime - 120][-3:]
  back = [x for x in back if toMinutes(x[0]) >= endTime + 60][:3]

  for x in forth:
    print(f"{time(toTime(toMinutes(x[0])-20))} - {time(x[0])}; В пути {x[1]} минут")

  print()

  for x in back:
    print(f"{time(toTime(toMinutes(x[0])-60))} - {time(x[0])}; В пути {x[1]} минут")



from telebot import TeleBot, types

TOKEN = '5617111071:AAHPzChNvG67FoU6tZPZ7Np2Az4KRgtyS1g'

bot = TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
  schedule = types.KeyboardButton('Get schedule')
  help = types.KeyboardButton('Help')
  markup.add(schedule, help)

  greet = 'Hi user!\nHere you can easily\nwork with schedule.\nPlease select one of this options:'

  bot.send_message(message.chat.id, greet, reply_markup=markup)

@bot.message_handler(content_types='text')
def message_reply(message):
  if message.text == 'Help':
    bot.send_message(message.chat.id, 'There is nothing here (yet)')
  elif message.text == 'Get schedule':
    schedule = getSchedule(FABRICHNAYA, VIKHINO)
    bot.send_message(message.chat.id, 'There is nothing schedule here (yet)')

bot.infinity_polling()