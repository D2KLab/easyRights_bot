import telebot
import requests
import logging
import json
import re

from datetime import datetime
from geopy.geocoders import Nominatim

from config import TOKEN, LANGUAGES, PILOTS, SERVICES, PROCEDURES, MESSAGES, NATIONS
from telebot import types
from googletrans import Translator

bot = telebot.TeleBot(TOKEN, parse_mode=None)

translator = Translator()

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

class UserInfo:
    def __init__(self):
        self.selected_language = 'en'
        self.selected_pilot = ''
        self.selected_service = ''

user = UserInfo()

######## MESSAGE HANDLERS ########

@bot.message_handler(commands=['help'])
def help_message(message):
    msg = MESSAGES['help']

    bot.send_message(chat_id=message.chat.id, text=translator.translate(msg, src='en', dest=user.selected_language).text)

@bot.message_handler(commands=['pathway'])
def pathway(message):
    markup = types.InlineKeyboardMarkup()

    for language in LANGUAGES.keys():
        markup.add(types.InlineKeyboardButton(text=language, callback_data=language))

    bot.send_message(chat_id=message.chat.id, text=MESSAGES['lang_selection'], reply_markup=markup, parse_mode='HTML')

@bot.message_handler(commands=['capeesh'])
def language_course(message):
    msg = 'Hi! Capeesh is an application that allows you to learn the basics of a foreign language quickly and intuitively!\n\n Use the following link to access the application: https://www.capeesh.com'

    bot.send_message(chat_id=message.chat.id, text=translator.translate(msg, src='en', dest=user.selected_language).text)

@bot.message_handler(commands=['calst'])
def pronunciation_exercise(message):
    msg = 'Hi! CALST is a platform designed to practice pronunciation in a foreign language, with exercises specifically designed based on the combination of your native language and the one you need to practice.\n\n You can access the tool using the following link: https://www.ntnu.edu/isl/calst'

    bot.send_message(chat_id=message.chat.id, text=translator.translate(msg, src='en', dest=user.selected_language).text)

#TODO: HAS THIS TO BE THE STARTING POINT OF THE USER EXPERIENCE?
@bot.message_handler(commands=['start'])
def geolocalisation(message):
    # Create a button that ask the user for the location 
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_geo = types.KeyboardButton(text="Share your location!", request_location=True)
    keyboard.add(button_geo)

    # WARNING: IS THIS WORKING ALSO ON TELEGRAM WEB AND DESKTOP????
    bot.send_message(message.chat.id, "In order to better select services, please, let us know where you are", reply_markup=keyboard)

@bot.message_handler(content_types=['location'])
def location_handler(message):
    # Instatiate and retrieve the address based on the position sent by the user
    geolocator = Nominatim(user_agent="easyRigths")
    position = str(message.location.latitude) + ', ' + str(message.location.longitude)
    location = geolocator.reverse(position, language='en')
    print(location)
    # Trim the address in order to select only the nation
    nation = location.address.split(',')[-1].strip()
    try:
        user.selected_language, user.selected_pilot = NATIONS[nation][0], NATIONS[nation][1]
        auto_localisation(message.chat.id)
    except KeyError:
        # The country is not supported
        pathway(message)

######## QUERY HANDLERS ########
@bot.callback_query_handler(lambda query: query.data in LANGUAGES.keys())
def language_handler(query):
    msg = MESSAGES['pilot_selection']
    user.selected_language = LANGUAGES[query.data]

    markup = types.InlineKeyboardMarkup()
    for pilot in PILOTS.keys():
        markup.add(types.InlineKeyboardButton(text=pilot, callback_data=pilot))

    bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=translator.translate(msg, src='en', dest=user.selected_language).text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(lambda query: query.data in PILOTS.keys())
def pilot_handler(query):
    msg = MESSAGES['service_selection']
    user.selected_pilot = PILOTS[query.data]

    markup = types.InlineKeyboardMarkup()
    for service in SERVICES[user.selected_pilot]:
       markup.add(types.InlineKeyboardButton(text=service, callback_data=service)) 

    bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=translator.translate(msg, src='en', dest=user.selected_language).text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(lambda query: query.data in SERVICES[user.selected_pilot])
def call_service_api(query):
    user.selected_service = query.data

    files = {'data': (None, '{"pilot":"' + user.selected_pilot +'","service":"' + user.selected_service + '"}'),}

    url = 'http://easyrights.linksfoundation.com/v0.3/generate'

    response = requests.post(url, files=files)

    pathway = json.loads(response.text)

    message = ''
    for step in pathway:
        step_trs = translator.translate(step, src='en', dest=user.selected_language).text
        message = message + '*'+step_trs+'*' + '\n'
        for block in pathway[step]['labels']:
            if not block.endswith('-'):
            #    if block.startswith(PROCEDURES[user.selected_language]):
            #        message = re.sub(step_trs, step_trs + ' - ' + re.sub(PROCEDURES[user.selected_language]+':', '', block), message)
            #    else:
                message = message + block + '\n'

    bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=message)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=translator.translate('Yes', src='en', dest=user.selected_language).text + ' \U0001F44D', callback_data='Useful'))
    markup.add(types.InlineKeyboardButton(text=translator.translate('No', src='en', dest=user.selected_language).text + ' \U0001F44E', callback_data='Not Useful'))
    bot.send_message(chat_id=query.from_user.id, text=translator.translate(MESSAGES['rating'], src='en', dest=user.selected_language).text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(lambda query: "Useful" in query.data)
def store_rating(query):
    rating_file = open('./ratings.csv', 'a')

    # store also the handle of the user
    handle_user = query.from_user.username
    date_msg = datetime.fromtimestamp(query.message.date)

    string_to_store = handle_user + ',' + str(date_msg) + ',' + user.selected_pilot + ',' + user.selected_service + ',' + user.selected_language + ','
    if query.data == 'Useful':
        string_to_store = string_to_store + str(True) + '\n'
    else:
        string_to_store = string_to_store + str(False) + '\n'

    rating_file.write(string_to_store)
    rating_file.close()
    bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=translator.translate(MESSAGES['rating_submission'], src='en', dest=user.selected_language).text)

######## OTHER FUNCTIONS ########
def auto_localisation(chat_id):
    msg = MESSAGES['service_selection']

    markup = types.InlineKeyboardMarkup()
    for service in SERVICES[user.selected_pilot]:
       markup.add(types.InlineKeyboardButton(text=service, callback_data=service)) 

    bot.send_message(chat_id=chat_id, text=translator.translate(msg, src='en', dest=user.selected_language).text, reply_markup=markup, parse_mode='HTML')

######## POLLING ########

bot.polling()