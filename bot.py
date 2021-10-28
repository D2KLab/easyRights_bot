import telebot
import requests
import logging
import json
import re
import os

from datetime import datetime
from geopy.geocoders import Nominatim
from dotenv import dotenv_values
from data.config import LANGUAGES, PILOTS, SERVICES, COMMANDS
from telebot import types
from googletrans import Translator

import i18n

for folder in os.listdir('./locale/'):
    i18n.load_path.append('./locale/' + folder)

config = dotenv_values(".env")

bot = telebot.TeleBot(config['TELEGRAM_API_TOKEN'], parse_mode=None)

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

##################################
######## COMMAND HANDLERS ########
##################################

@bot.message_handler(commands=['pathway'])
def pathway(message):
    user = retrieve_user(message.from_user.id)
    user['action'] = 'pathway'

    ask_for_position(message)

@bot.message_handler(commands=['capeesh'])
def capeesh(message):
    users[str(message.from_user.id)]['action'] = 'capeesh'

    pilot_selection(message)

@bot.message_handler(commands=['calst'])
def calst(message):
    user = retrieve_user(message.from_user.id)
    user['action'] = 'calst'

    return_markup = restart(message)
    bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message.id, text=i18n.t('messages.calst', locale=user['selected_language']), reply_markup=return_markup, parse_mode='HTML')

@bot.message_handler(commands=['start'])
def start(message):
    user = retrieve_user(message.from_user.id)
    user['action'] = 'help'
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

    if municipality.lower() in PILOTS:
        user['selected_pilot'] = municipality
        auto_localisation(message)
    else:
        # The country is not supported
        pilot_selection(message)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def help(message):
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=COMMANDS, language=user['selected_language'])
    try:
        bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message.id, text=i18n.t('messages.help', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')
    except Exception:
        bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.help', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

################################
######## QUERY HANDLERS ########
################################

@bot.callback_query_handler(lambda query: query.data in COMMANDS)
def command_handler(query):
    globals()[query.data](query)

@bot.callback_query_handler(lambda query: query.data in LANGUAGES)
def language_handler(query):
    user = retrieve_user(query.from_user.id)
    user['selected_language'] = query.data
    
    if user['action'] == 'capeesh':
        pilot_selection(query)
    elif user['action'] == 'pathway':
        pilot_selection(query)
    elif user['action'] == 'localisation':
        geolocalisation(query)
    elif user['action'] == 'help':
        help(query)

@bot.callback_query_handler(lambda query: query.data in PILOTS)
def pilot_handler(query):
    user = retrieve_user(query.from_user.id)
    user['selected_pilot'] = query.data

    service_selection(query)

@bot.callback_query_handler(lambda query: "Useful" in query.data)
def store_rating(query):
    user = retrieve_user(query.from_user.id)
    rating_file = open('./data/ratings.csv', 'a')

    # store also the handle of the user
    handle_user = query.from_user.username
    date_msg = datetime.fromtimestamp(query.message.date)

    try:
        string_to_store = handle_user + ',' + str(date_msg) + ',' + user['selected_pilot'] + ',' + user['selected_service'] + ',' + user['selected_language'] + ','
        if query.data == 'Useful':
            string_to_store = string_to_store + str(True) + '\n'
        else:
            string_to_store = string_to_store + str(False) + '\n'
    except Exception as e:
        print(e)
        string_to_store = ''

    rating_file.write(string_to_store)
    rating_file.close()
    return_markup = restart(query)
    bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=i18n.t('messages.rating_submission', locale=user['selected_language']), reply_markup=return_markup)

@bot.callback_query_handler(lambda query: "course" in query.data)
def sign_up_to_capeesh(query):
    user = retrieve_user(query.from_user.id)
    msg = bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=i18n.t('messages.capeesh_mail_insertion', locale=user['selected_language']))
    bot.register_next_step_handler(msg, add_email)

@bot.callback_query_handler(lambda query: "nope" in query.data)
def return_to_menu(query):
    user = retrieve_user(query.from_user.id)
    if user['action'] == 'capeesh':
        user['action'] = 'help'
        help(query)
    else:
        pilot_selection(query)

@bot.callback_query_handler(lambda query: "restart" in query.data)
def restart_experience(query):
    help(query)

@bot.callback_query_handler(lambda query: "location" in query.data)
def location(query):
    geolocalisation(query)

@bot.callback_query_handler(lambda query: query.data in SERVICES[retrieve_user(query.from_user.id)['selected_pilot']])
def call_service_api(query):
    user = retrieve_user(query.from_user.id)
    user['selected_service'] = query.data

    if user['action'] == 'capeesh':
        language_course(query)
        return

    pathway_text = pathway_retrieve(user['selected_pilot'], user['selected_service'], user['selected_language'])

    if not pathway_text:
        files = {'data': (None, '{"pilot":"' + user['selected_pilot'] +'","service":"' + user['selected_service'] + '"}'),}

        url = 'http://easyrights.linksfoundation.com/v0.3/generate'
        try:
            response = requests.post(url, files=files)

            pathway = json.loads(response.text)

            pathway_text = ''
            block_message = ''
    
            for step in pathway:
                step_trs = translate(user['selected_language'], step)
                pathway_text = pathway_text + '<b>'+step_trs+'</b>' + '\n'

                for block in pathway[step]['labels']:
                    if not block.endswith('-'):
                        block_split = re.split(':|-', block)
                        if '_' in block_split[1]:
                            block_split[1] = re.sub('_', ' ', block_split[1])

                        block_message = translate(user['selected_language'], block_split[0].strip()) + ' - ' + translate(user['selected_language'], block_split[1].strip()) + ': ' + translate(user['selected_language'], ':'.join(block_split[2:]).strip()) +'\n'
                
                    pathway_text = pathway_text + block_message
                    block_message = ''

        except Exception as e:
            print(e)
            bot.send_message(chat_id=query.from_user.id, text=i18n.t('messages.error', locale=user['selected_language']))

        if user['selected_pilot'] not in pathways.keys():
            pathways[user['selected_pilot']] = {}
        if user['selected_service'] not in pathways[user['selected_pilot']].keys():
            pathways[user['selected_pilot']][user['selected_service']] = {}
        if user['selected_language'] not in pathways[user['selected_pilot']][user['selected_service']].keys():
            pathways[user['selected_pilot']][user['selected_service']][user['selected_language']] = {}

        pathways[user['selected_pilot']][user['selected_service']][user['selected_language']] = pathway_text
        pathways_file = open('./data/pathways.json', 'w')
        json.dump(pathways, pathways_file, indent=4)
        pathways_file.close()
        
    bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=pathway_text, parse_mode='HTML')

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language'])+' \U0001F44D', callback_data='Useful'))
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.no', locale=user['selected_language'])+' \U0001F44E', callback_data='Not Useful'))
    bot.send_message(chat_id=query.from_user.id, text=i18n.t('messages.rating', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

###########################
######## FUNCTIONS ########
###########################

def restart(message):
    user = retrieve_user(message.from_user.id)
    markup = menu_creation(buttons=['restart'], language=user['selected_language'])

    return markup

def change_lang(message):
    user = retrieve_user(message.from_user.id)
    user['action'] = 'help'

    language_selection(message)

def ask_for_position(message):
    user = retrieve_user(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language'])+' \U0001F44D', callback_data='location'))
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.no', locale=user['selected_language'])+' \U0001F44E', callback_data='nope'))
    bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message.id, text=i18n.t('messages.location_permission', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def auto_localisation(message):
    user = retrieve_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()
    for service in SERVICES[user['selected_pilot'].lower()]:
       markup.add(types.InlineKeyboardButton(text=service, callback_data=service)) 

    bot.send_message(chat_id=message.chat.id, text=i18n.t('messages.service_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def geolocalisation(message):
    user = retrieve_user(message.from_user.id)
    # Create a button that ask the user for the location 
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_geo = types.KeyboardButton(text=translate(user['selected_language'], "Share your location!"), request_location=True)
    keyboard.add(button_geo)

    user['action'] = 'localisation'
    # WARNING: IS THIS WORKING ALSO ON TELEGRAM WEB AND DESKTOP????
    bot.delete_message(chat_id=message.from_user.id, message_id=message.message.id)
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.location', locale=user['selected_language']), reply_markup=keyboard, parse_mode='HTML')

def language_selection(message):
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=LANGUAGES)    

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.lang_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def pilot_selection(message):
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=PILOTS, language=user['selected_language'])

    try:
        bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message.id, text=i18n.t('messages.pilot_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')
    except AttributeError:
        bot.send_message(chat_id=message.chat.id, text=i18n.t('messages.pilot_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def service_selection(message):
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=SERVICES[user['selected_pilot']], language=user['selected_language'])

    try:
        bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message.id, text=i18n.t('messages.service_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')
    except AttributeError:
        bot.send_message(chat_id=message.chat.id, text=i18n.t('messages.service_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def language_course(message):
    user = retrieve_user(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language']) + ' \U0001F44D', callback_data='course'))
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.no', locale=user['selected_language']) + ' \U0001F44E', callback_data='nope'))
    bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message.id, text=i18n.t('messages.capeesh', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def translate(language, text):
    try:
        return translations[language][text]
    except KeyError:
        print('The translation or the language is not present. Adding...')
        if language not in translations.keys():
            translations[language] = {}
        src_lang = translator.detect(text).lang
        if src_lang == language:
            return text
        new_translation = translator.translate(text, src=src_lang, dest=language).text
        translations[language][text] = new_translation
    
        translations_file = open('./data/message_translation.json', 'w')
        json.dump(translations, translations_file, indent=4)
        translations_file.close()
        return new_translation

def pathway_retrieve(pilot, service, language):
    try:
        return pathways[pilot][service][language]
    except KeyError:
        return None

def add_email(message):
    user = retrieve_user(message.from_user.id)    
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email = message.text

    if not re.match(regex, email):
        msg = bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.capeesh_mail_error', locale=user['selected_language']), parse_mode='html')
        bot.register_next_step_handler(msg, add_email)
        return

    api_key = config['CAPEESH_API_TOKEN']
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

    return_markup = restart(message)
    bot.send_message(chat_id=message.from_user.id, text=translate(user['selected_language'], text), reply_markup=return_markup, parse_mode='html')

def retrieve_user(user_id):
    try:
        user_id = str(user_id)
        return users[user_id]
    except KeyError:
        users[user_id] = {
            "selected_language" : 'en',
            "selected_pilot" : '',
            "selected_service" : '',
            "action" : 'localisation'
        }
        users_file = open('./data/users.json', 'w')
        json.dump(users, users_file, indent=4)
        users_file.close()
        return users[user_id]

def menu_creation(buttons, language='en'):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for button in buttons:
        action = 'commands.' + button
        markup.add(types.InlineKeyboardButton(text=i18n.t(action, locale=language), callback_data=button))

    return markup

#########################
######## POLLING ########
#########################

bot.polling()