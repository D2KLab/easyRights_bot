import telebot
import requests
import logging
import json
import re

from datetime import datetime
from geopy.geocoders import Nominatim

from data.config import LANGUAGES, PILOTS, SERVICES, PROCEDURES, MESSAGES, MUNICIPALITIES
from data.api_keys import TELEGRAM_API_TOKEN, CAPEESH_API_TOKEN
from telebot import types
from googletrans import Translator

bot = telebot.TeleBot(TELEGRAM_API_TOKEN, parse_mode=None)

translator = Translator()

translations_file = open('./data/message_translation.json', 'r')
translations = json.loads(translations_file.read())
translations_file.close()

pathways_file = open('./data/pathways.json', 'r')
pathways = json.loads(pathways_file.read())
pathways_file.close()

users_file = open('./data/users.json', 'r')
users = json.loads(users_file.read())
users_file.close()

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

######## MESSAGE HANDLERS ########

@bot.message_handler(commands=['help'])
def help_message(message):
    msg = MESSAGES['help']
    
    user = retrieve_user(message.from_user.id)

    bot.send_message(chat_id=message.chat.id, text=translate(user['selected_language'], msg))

@bot.message_handler(commands=['pathway'])
def pathway(message):
    user = retrieve_user(message.from_user.id)
    action = user['action']
    user['action'] = 'pathway'

    if action == 'localisation':
        pilot_selection(message)
    else:
        language_selection(message)

@bot.message_handler(commands=['capeesh'])
def capeesh(message):
    user = retrieve_user(message.from_user.id)
    user['action'] = 'capeesh'

    if not user['selected_pilot']:
        language_selection(message)
    else:
        service_selection(message)

@bot.message_handler(commands=['calst'])
def pronunciation_exercise(message):
    msg = 'Hi! CALST is a platform designed to practice pronunciation in a foreign language, with exercises specifically designed based on the combination of your native language and the one you need to practice.\n\n You can access the tool using the following link: https://www.ntnu.edu/isl/calst'
    user = retrieve_user(message.from_user.id)

    bot.send_message(chat_id=message.chat.id, text=translate(user['selected_language'], msg))

@bot.message_handler(commands=['start'])
def start(message):
    user = retrieve_user(message.from_user.id)
    user['action'] = 'localisation'
    language_selection(message)

@bot.message_handler(content_types=['location'])
def location_handler(message):
    # Instatiate and retrieve the address based on the position sent by the user
    geolocator = Nominatim(user_agent="easyRights")
    position = str(message.location.latitude) + ', ' + str(message.location.longitude)
    location = geolocator.reverse(position, language='en')
    
    # Trim the address in order to select only the municipality
    municipality = location.raw['address']['city']

    user = retrieve_user(message.from_user.id)

    if municipality in MUNICIPALITIES:
        user['selected_pilot'] = municipality
        auto_localisation(message)
    else:
        # The country is not supported
        pathway(message)    

######## QUERY HANDLERS ########
@bot.callback_query_handler(lambda query: query.data in LANGUAGES.keys())
def language_handler(query, loc=False):
    user = retrieve_user(query.from_user.id)
    user['selected_language'] = LANGUAGES[query.data]
    
    if user['action'] == 'capeesh':
        user['capeesh_command'] = True
        pilot_selection(query)
    elif user['action'] == 'pathway':
        user['capeesh_command'] = False
        pilot_selection(query)
    elif user['action'] == 'localisation':
        user['capeesh_command'] = False
        geolocalisation(query)

@bot.callback_query_handler(lambda query: query.data in PILOTS.keys())
def pilot_handler(query):
    user = retrieve_user(query.from_user.id)
    user['selected_pilot'] = PILOTS[query.data]

    service_selection(query)

@bot.callback_query_handler(lambda query: query.data in SERVICES[retrieve_user(query.from_user.id)['selected_pilot']])
def call_service_api(query):
    user = retrieve_user(query.from_user.id)
    user['selected_service'] = query.data

    if user['capeesh_command']:
        user['capeesh_command'] = False
        language_course(query)
        return

    files = {'data': (None, '{"pilot":"' + user['selected_pilot'] +'","service":"' + user['selected_service'] + '"}'),}

    url = 'http://easyrights.linksfoundation.com/v0.3/generate'

    try:
        response = requests.post(url, files=files)

        pathway = json.loads(response.text)

        message = ''
        for step in pathway:
            step_trs = translator.translate(step, src='en', dest=user['selected_language']).text
            message = message + '*'+step_trs+'*' + '\n'
            for block in pathway[step]['labels']:
                if not block.endswith('-'):
                #    if block.startswith(PROCEDURES[user['selected_language']]):
                #        message = re.sub(step_trs, step_trs + ' - ' + re.sub(PROCEDURES[user['selected_language']]+':', '', block), message)
                #    else:
                    message = message + block + '\n'

        bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=pathway_retrieve(message, query))

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text=translate(user['selected_language'], 'Yes') + ' \U0001F44D', callback_data='Useful'))
        markup.add(types.InlineKeyboardButton(text=translate(user['selected_language'], 'No') + ' \U0001F44E', callback_data='Not Useful'))
        bot.send_message(chat_id=query.from_user.id, text=translate(user['selected_language'], MESSAGES['rating']), reply_markup=markup, parse_mode='HTML')
    except KeyError as e:
        bot.send_message(chat_id=query.from_user.id, text=translate(user['selected_language'], MESSAGES['error']))

@bot.callback_query_handler(lambda query: "Useful" in query.data)
def store_rating(query):
    user = retrieve_user(query.from_user.id)
    rating_file = open('./data/ratings.csv', 'a')

    # store also the handle of the user
    handle_user = query.from_user.username
    date_msg = datetime.fromtimestamp(query.message.date)

    string_to_store = handle_user + ',' + str(date_msg) + ',' + user['selected_pilot'] + ',' + user['selected_service'] + ',' + user['selected_language'] + ','
    if query.data == 'Useful':
        string_to_store = string_to_store + str(True) + '\n'
    else:
        string_to_store = string_to_store + str(False) + '\n'

    rating_file.write(string_to_store)
    rating_file.close()
    bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=translate(user['selected_language'], MESSAGES['rating_submission']))

@bot.callback_query_handler(lambda query: "capeesh" in query.data)
def sign_up_to_capeesh(query):
    user = retrieve_user(query.from_user.id)
    msg = bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=translate(user['selected_language'], 'Please, enter your email address:'))
    bot.register_next_step_handler(msg, add_email)

def add_email(message):
    user = retrieve_user(message.from_user.id)    
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email = message.text

    if not re.match(regex, email):
        msg = bot.send_message(chat_id=message.from_user.id, text=translate(user['selected_language'], 'Please, insert a VALID email address.'), parse_mode='html')
        bot.register_next_step_handler(msg, add_email)
        return

    api_key = CAPEESH_API_TOKEN
    api_key_get_headers = {
        "X-API-KEY": api_key
    }

    add_user_url = 'https://api.capeesh.com/api/easyrights/user/add/'
    user_data = {
        "Email": email,
        "Tag": user['selected_service'].lower()
    }
    response = requests.post(add_user_url, headers=api_key_get_headers, json=user_data)

    if response.status_code == 200:
        pass

    text ="You have been invited by easyRights to a specially tailored language course about <b>%s</b> in the Capeesh app.\nThe Capeesh app contains language lessons, quizzes and challenges made just for you!\neasyRights is looking forward having you onboard with Capeesh, and we have created a simple four-step guide to make it as easy as possible for you to get started.\nHow to get started now:\n\n 1)	Download the capeesh app from the Apple App Store or Google Play Store. If it does not appear when you search for it, please contact support@capeesh.com for further assistance. \n\n 2)	Open the app, select your native language and click continue \n\n 3)	Then register your account by entering the email %s and clicking continue \n\n 4)	Finally, choose your own password and click Create user." % (user['selected_service'], email)

    bot.send_message(chat_id=message.from_user.id, text=translate(user['selected_language'], text), parse_mode='html')

######## OTHER FUNCTIONS ########
def auto_localisation(message):
    text = MESSAGES['service_selection']
    user = retrieve_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()
    for service in SERVICES['palermo']:
       markup.add(types.InlineKeyboardButton(text=service, callback_data=service)) 

    bot.send_message(chat_id=message.chat.id, text=translate(user['selected_language'], text), reply_markup=markup, parse_mode='HTML')

def language_selection(message):
    text = MESSAGES['lang_selection']
    user = retrieve_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup(row_width=1)
    for language in LANGUAGES.keys():
        markup.add(types.InlineKeyboardButton(text=language, callback_data=language))

    bot.send_message(chat_id=message.chat.id, text=text, reply_markup=markup, parse_mode='HTML')

def pilot_selection(message):
    text = MESSAGES['pilot_selection']
    user = retrieve_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()
    for pilot in PILOTS.keys():
        markup.add(types.InlineKeyboardButton(text=pilot, callback_data=pilot))

    try:
        bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message.id, text=translate(user['selected_language'], text), reply_markup=markup, parse_mode='HTML')
    except AttributeError:
        bot.send_message(chat_id=message.chat.id, text=translate(user['selected_language'], text), reply_markup=markup, parse_mode='HTML')

def service_selection(message):
    text = MESSAGES['service_selection']
    user = retrieve_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()
    for service in SERVICES[user['selected_pilot']]:
       markup.add(types.InlineKeyboardButton(text=service, callback_data=service)) 

    try:
        bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message.id, text=translate(user['selected_language'], text), reply_markup=markup, parse_mode='HTML')
    except AttributeError:
        bot.send_message(chat_id=message.chat.id, text=translate(user['selected_language'], text), reply_markup=markup, parse_mode='HTML')

def language_course(message):
    user = retrieve_user(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=translate(user['selected_language'], 'Yes') + ' \U0001F44D', callback_data='capeesh'))
    markup.add(types.InlineKeyboardButton(text=translate(user['selected_language'], 'No') + ' \U0001F44E', callback_data='Not capeesh'))
    bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message.id, text=translate(user['selected_language'], MESSAGES['capeesh']), reply_markup=markup, parse_mode='HTML')

def translate(language, text):
    try:
        return translations[language][text]
    except KeyError:
        if language not in translations.keys():
            translations[language] = {}
        new_translation = translator.translate(text, src='en', dest=language).text
        translations[language][text] = new_translation
    
        translations_file = open('./data/message_translation.json', 'w')
        json.dump(translations, translations_file, indent=4)
        translations_file.close()
        return new_translation

def pathway_retrieve(text, message):
    user = retrieve_user(message.from_user.id)
    try:
        return pathways[user['selected_pilot']][user['selected_service']][user['selected_language']]
    except KeyError:
        if user['selected_pilot'] not in pathways.keys():
            pathways[user['selected_pilot']] = {}
        if user['selected_service'] not in pathways[user['selected_pilot']].keys():
            pathways[user['selected_pilot']][user['selected_service']] = {}
        if user['selected_language'] not in pathways[user['selected_pilot']][user['selected_service']].keys():
            pathways[user['selected_pilot']][user['selected_service']][user['selected_language']] = {}

        new_pathway_translation = translator.translate(text, src=translator.detect(text).lang, dest=user['selected_language']).text
        pathways[user['selected_pilot']][user['selected_service']][user['selected_language']] = new_pathway_translation

        pathways_file = open('./data/pathways.json', 'w')
        json.dump(pathways, pathways_file, indent=4)
        pathways_file.close()
        return new_pathway_translation        

def geolocalisation(message):
    user = retrieve_user(message.from_user.id)
    # Create a button that ask the user for the location 
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_geo = types.KeyboardButton(text=translate(user['selected_language'], "Share your location!"), request_location=True)
    keyboard.add(button_geo)

    user['action'] = 'localisation'

    # WARNING: IS THIS WORKING ALSO ON TELEGRAM WEB AND DESKTOP????
    bot.send_message(chat_id=message.from_user.id, text=translate(user['selected_language'], "In order to better select services, please, let us know where you are"), reply_markup=keyboard, parse_mode='HTML')

def retrieve_user(user_id):
    try:
        return users[user_id]
    except KeyError:
        users[user_id] = {
            "selected_language" : 'en',
            "selected_pilot" : '',
            "selected_service" : '',
            "capeesh_command" : False,
            "action" : 'localisation'
        }
        users_file = open('./data/users.json', 'w')
        json.dump(users, users_file, indent=4)
        users_file.close()
        return users[user_id]

def update_users():
    users_file = open('./data/users.json', 'r')
    json.dump(users, users_file)
    users_file.close()

######## POLLING ########
#bot.infinity_polling()
bot.polling()