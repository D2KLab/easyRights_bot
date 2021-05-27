import telebot
import requests
import logging
import json

from config import TOKEN, LANGUAGES, PILOTS, SERVICES, PROCEDURES, MESSAGES
from telebot import types
from googletrans import Translator

bot = telebot.TeleBot(TOKEN, parse_mode=None)

translator = Translator()

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)



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

    bot.send_message(chat_id=message.chat.id, text=msg)

@bot.message_handler(commands=['pathway'])
def pathway(message):
    markup = types.InlineKeyboardMarkup()

    for language in LANGUAGES.keys():
        markup.add(types.InlineKeyboardButton(text=language, callback_data=language))

    bot.send_message(chat_id=message.chat.id, text=MESSAGES['lang_selection'], reply_markup=markup, parse_mode='HTML')

@bot.message_handler(commands=['capeesh'])
def language_course(message):
    markup = types.InlineKeyboardMarkup()

    for language in LANGUAGES.keys():
        markup.add(types.InlineKeyboardButton(text=language, callback_data=language))

    bot.send_message(chat_id=message.chat.id, text=MESSAGES['lang_selection'], reply_markup=markup, parse_mode='HTML')

@bot.message_handler(commands=['calst'])
def pronunciation_exercise(message):
    msg = 'Hi! CALST is a platform designed to practice pronunciation in a foreign language, with exercises specifically designed based on the combination of your native language and the one you need to practice.\n\n You can access the tool using the following link https://www.ntnu.edu/isl/calst'

    bot.send_message(chat_id=message.chat.id, text=msg)

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

    #Offer language course
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=translator.translate('Yes', src='en', dest=user.selected_language).text + ' \U0001F44D', callback_data='capeesh'))
    markup.add(types.InlineKeyboardButton(text=translator.translate('No', src='en', dest=user.selected_language).text + ' \U0001F44E', callback_data='Not capeesh'))
    bot.send_message(chat_id=query.from_user.id, text=translator.translate(MESSAGES['capeesh'], src='en', dest=user.selected_language).text, reply_markup=markup, parse_mode='HTML')



@bot.callback_query_handler(lambda query: "capeesh" in query.data)
def sign_up_to_capeesh(query):
    bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=translator.translate(
        'please enter your email address', src='en',
        dest=user.selected_language).text)

@bot.message_handler(func=lambda query: '@' in query.text)
def add_email(query):

    email = query.text

    api_key = '874a8ce4fb964ae7af797849a64db9bf'
    api_key_get_headers = {
        "X-API-KEY": api_key
    }

    add_user_url = 'https://api.capeesh.com/api/easyrights/user/add/'
    user_data = {
        "Email": email,
        "Tag": user.selected_service.lower()
    }
    response = requests.post(add_user_url, headers=api_key_get_headers, json=user_data)
    if response.status_code == 200:
        pass
    text ="""
You have been invited by EasyRights to a specially tailored language course about %s in the Capeesh app. 

The Capeesh app contains language lessons, quizzes and challenges made just for you!

EasyRights is looking forward having you onboard with Capeesh, and we have created a simple four-step guide to make it as easy as possible for you to get started. 
How to get started now:

1	Download the capeesh app from the Apple App Store or Google Play Store. If it does not appear when you search for it, please contact support@capeesh.com for further assistance.
2	Open the app, select your native language and click continue
3	Then register your account by entering the email %s and clicking continue
4	Finally, choose your own password and click Create user
                          """%(user.selected_service, email)

    bot.send_message(chat_id=query.from_user.id,
                     text=text
                     )

    #Do you think the information was useful?
    # markup = types.InlineKeyboardMarkup()
    # markup.add(types.InlineKeyboardButton(
    #     text=translator.translate('Yes', src='en', dest=user.selected_language).text + ' \U0001F44D',
    #     callback_data='Useful'))
    # markup.add(types.InlineKeyboardButton(
    #     text=translator.translate('No', src='en', dest=user.selected_language).text + ' \U0001F44E',
    #     callback_data='Not Useful'))
    # bot.send_message(chat_id=query.from_user.id,
    #                  text=translator.translate(MESSAGES['rating'], src='en', dest=user.selected_language).text,
    #                  reply_markup=markup, parse_mode='HTML')



@bot.callback_query_handler(lambda query: "Useful" in query.data)
def store_rating(query):
    rating_file = open('./ratings.csv', 'a')

    string_to_store = user.selected_pilot + ',' + user.selected_service + ','
    if query.data == 'Useful':
        string_to_store = string_to_store + str(True) + '\n'
    else:
        string_to_store = string_to_store + str(False) + '\n'

    rating_file.write(string_to_store)
    rating_file.close()
    bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.id, text=translator.translate(MESSAGES['rating_submission'], src='en', dest=user.selected_language).text)

######## POLLING ########

bot.polling()

