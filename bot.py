import telebot
import requests
import logging
import json
import re
import os
import i18n
import yaml

from datetime import datetime
from geopy.geocoders import Nominatim
from dotenv import dotenv_values
from data.static import LANGUAGES, PILOTS, SERVICES, COMMANDS
from telebot import types
from googletrans import Translator

for folder in os.listdir('./locale/'):
    i18n.load_path.append('./locale/' + folder)

config = dotenv_values(".env")

bot = telebot.TeleBot(config['TELEGRAM_API_TOKEN'], parse_mode=None)

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

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.calst', locale=user['selected_language']), reply_markup=return_markup, parse_mode='HTML')

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
    try:
        municipality = location.raw['address']['city']

        user = retrieve_user(message.from_user.id)

        if municipality.lower() in PILOTS:
            user['selected_pilot'] = municipality
            auto_localisation(message)
        else:
            # The country is not supported
            pilot_selection(message)
    except KeyError:
        pilot_selection(message)

"""still need to understand wether this could be a possible solution for pathway visualization
@bot.message_handler(commands=['test'])
def visualize_pathway(message):
    pathway = {'Step 1': 'This is the text related to step 1',
                'Step 2': 'This is the text related to step 2',
                'Step 3': 'This is the text related to step 3',
            }
    markup = types.InlineKeyboardMarkup(row_width=1)
    for step in pathway.keys():
        markup.add(types.InlineKeyboardButton(text=step, callback_data=step))

    bot.send_message(chat_id=message.from_user.id, text='test', reply_markup=markup, parse_mode='HTML')
    rating_submission(message)

@bot.callback_query_handler(lambda query: "Step" in query.data)
def visualize_step(query):
    pathway = {'Step 1': 'This is the text related to step 1',
                'Step 2': 'This is the text related to step 2',
                'Step 3': 'This is the text related to step 3',
            }

    bot.answer_callback_query(callback_query_id=query.id, show_alert=True, text=pathway[query.data])
"""
@bot.message_handler(func=lambda message: True, content_types=['text'])
def help(message):
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=COMMANDS, language=user['selected_language'], lang_selection=True)
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
    bot.send_message(chat_id=query.from_user.id, text=i18n.t('messages.rating_submission', locale=user['selected_language']), reply_markup=return_markup)

@bot.callback_query_handler(lambda query: "course" in query.data)
def sign_up_to_capeesh(query):
    user = retrieve_user(query.from_user.id)
    msg = bot.send_message(chat_id=query.from_user.id, text=i18n.t('messages.capeesh_mail_insertion', locale=user['selected_language']))
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
    tmp_mapping = {
        "registry_office": "Registration at Registry Office",
        "caz": "Clean Air Zone",
        "asylum_request": "Asylum Request",
        "nationality": "Certification of Nationality",
        "baes_esol": "baes esol",
        "birth_certificate": "Birth Certification",
        "work_permission": "Work Permission"
    }
    user = retrieve_user(query.from_user.id)
    user['selected_service'] = tmp_mapping[query.data]

    if user['action'] == 'capeesh':
        language_course(query)
        return

    translation_key = 'pathways.' + user['selected_pilot'] + '.' + query.data
    pathway_text = i18n.t(translation_key, locale=user['selected_language'])
    
    if pathway_text == translation_key:
        files = {'data': (None, '{"pilot":"' + user['selected_pilot'] +'","service":"' + user['selected_service'] + '"}'),}

        url = 'http://easyrights.linksfoundation.com/v0.3/generate'
        try:
            response = requests.post(url, files=files)

            pathway = json.loads(response.text)

            pathway_text = ''
            block_message = ''
            language = user['selected_language']
            translator = Translator()

            for step in pathway:
                step_trs = translator.translate(step, dest=language).text
                pathway_text = pathway_text + '<b>'+step_trs+'</b>' + '\n'

                for block in pathway[step]['labels']:
                    if not block.endswith('-'):
                        block_split = re.split(':|-', block)
                        if '_' in block_split[1]:
                            block_split[1] = re.sub('_', ' ', block_split[1])

                        block_message = translator.translate(block_split[0].strip(), dest=language).text + ' - ' + translator.translate(block_split[1].strip(), dest=language).text + ': ' + translator.translate(':'.join(block_split[2:]).strip(), dest=language).text +'\n'
                
                    pathway_text = pathway_text + block_message
                    block_message = ''

        except Exception as e:
            print(e)
            bot.send_message(chat_id=query.from_user.id, text=i18n.t('messages.error', locale=user['selected_language']))

        path = './locale/' + language + '/pathways.' + language + '.yml'
        file_input = open(path, 'r')
        pathways_dict = yaml.safe_load(file_input)
        os.remove(path)
        pathways_dict[language][user['selected_pilot']] = {}
        pathways_dict[language][user['selected_pilot']].update({query.data: pathway_text})
        yaml.safe_dump(pathways_dict, open(path, 'w'), encoding='utf-8', allow_unicode=True)
        
    bot.send_message(chat_id=query.from_user.id, text=pathway_text, parse_mode='HTML')

    rating_submission(query)

###########################
######## FUNCTIONS ########
###########################

def restart(message):
    user = retrieve_user(message.from_user.id)
    markup = menu_creation(buttons=[], language=user['selected_language'])

    return markup

def rating_submission(message):
    user = retrieve_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language'])+' \U0001F44D', callback_data='Useful'))
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.no', locale=user['selected_language'])+' \U0001F44E', callback_data='Not Useful'))
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.rating', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def change_lang(message):
    user = retrieve_user(message.from_user.id)
    user['action'] = 'help'

    language_selection(message)

def ask_for_position(message):
    user = retrieve_user(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language'])+' \U0001F44D', callback_data='location'))
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.no', locale=user['selected_language'])+' \U0001F44E', callback_data='nope'))
    markup.add(types.InlineKeyboardButton(text=i18n.t("commands.restart", locale=user['selected_language']), callback_data='restart'))

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.location_permission', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

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
    button_geo = types.KeyboardButton(text=i18n.t('messages.share', locale=user['selected_language']), request_location=True)
    keyboard.add(button_geo)

    user['action'] = 'localisation'
    # WARNING: IS THIS WORKING ALSO ON TELEGRAM WEB AND DESKTOP????
    bot.delete_message(chat_id=message.from_user.id, message_id=message.message.id)
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.location', locale=user['selected_language']), reply_markup=keyboard, parse_mode='HTML')

def language_selection(message):
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=LANGUAGES, lang_selection=True)    

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.lang_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def pilot_selection(message):
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=PILOTS, language=user['selected_language'])

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.pilot_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def service_selection(message):
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=SERVICES[user['selected_pilot']], language=user['selected_language'], type='services.'+user['selected_pilot'])

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.service_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def language_course(message):
    user = retrieve_user(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language']) + ' \U0001F44D', callback_data='course'))
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.no', locale=user['selected_language']) + ' \U0001F44E', callback_data='nope'))
    markup.add(types.InlineKeyboardButton(text=i18n.t("commands.restart", locale=user['selected_language']), callback_data='restart'))
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.capeesh', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

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

    return_markup = restart(message)
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.capeesh_course', locale=user['selected_language']), reply_markup=return_markup, parse_mode='html')

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

def menu_creation(buttons, language='en', type='commands', lang_selection=False):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for button in buttons:
        action = type + '.' + button
        markup.add(types.InlineKeyboardButton(text=i18n.t(action, locale=language), callback_data=button))

    if not lang_selection:
        markup.add(types.InlineKeyboardButton(text=i18n.t("commands.restart", locale=language), callback_data='restart'))
    return markup

#########################
######## POLLING ########
#########################

bot.polling()