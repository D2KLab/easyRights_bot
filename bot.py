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

service_mapping = {
    "registry_office": "Registration at Registry Office",
    "job_seeking": "Job Seeking",
    "caz": "Clean Air Zone",
    "asylum_request": "Asylum Request",
    "nationality": "Certification of Nationality",
    "baes_esol": "baes esol",
    "birth_certificate": "Birth Certification",
    "work_permission": "Work Permission"
}

##################################
######## MESSAGE HANDLERS ########
##################################

@bot.message_handler(commands=['pathway'])
def pathway(message):
    """
    Start of the pathway experience. We set this as action of the user and we proceed to ask for the position.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)
    user['action'] = 'pathway'

    ask_for_position(message)

@bot.message_handler(commands=['capeesh'])
def capeesh(message):
    """
    Start of the language course experience. We set this as action of the user and we proceed to ask for the municipality.
    :message: the Telegram message.
    """
    users[str(message.from_user.id)]['action'] = 'capeesh'

    pilot_selection(message)

@bot.message_handler(commands=['wiki'])
def wiki(message):
    """
    Start of the wiki experience. We set this as action of the user and we proceed to ask for the municipality.
    :message: the Telegram message.
    """
    users[str(message.from_user.id)]['action'] = 'wiki'

    pilot_selection(message)

@bot.message_handler(commands=['calst'])
def calst(message):
    """
    Start of the pronunciation exercises experience. We set this as action of the user and we proceed to send a message with the link of CALST platform.
    :message: the Telegram message.
    #TODO: possible further integration for selecting source and target language for the platform.
    """
    user = retrieve_user(message.from_user.id)
    user['action'] = 'calst'

    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S,%f")

    log = {
        "datetime"            :  dt_string,
        "user_id"             :  message.from_user.id,
        "username"            :  message.from_user.username,
        "query_id"            :  message.id,
        #"chat_instance"       :  message.chat_instance,
        "action"              :  user["action"],
        "selected_language"   :  user['selected_language']
    }
    print(json.dumps(log))
    
    return_markup = restart(message)

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.calst', locale=user['selected_language']), reply_markup=return_markup, parse_mode='HTML')

@bot.message_handler(commands=['start'])
def start(message):
    """
    This is what happens when, in the first contact with the chatbot, the user click on "start". We set "help" as action and proceed to ask what language has to be set for the experience.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)
    user['action'] = 'help'
    language_selection(message)

@bot.message_handler(content_types=['location'])
def location_handler(message):
    """
    This function is not linked with a real command. The content_types parameter allow to catch the TYPE of message and not the content.
    The rationale is that if the user send a position, this function catch it and, using the Google geocoders, extract the city.
    The other information about the position is not used, since we check only if the city is one of the municipalities supported.
    If this is the case, we set the user['selected_pilot'] and proceed to ask for the services supported by that city.
    In all the other cases, we continue the experience by explicitly asking for the pilot selection.
    :message: the Telegram message.
    """
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
            bot.send_message(chat_id=message.from_user.id, text='There are no services available in your city.', parse_mode='HTML')
            pilot_selection(message)
    except KeyError:
        pilot_selection(message)

"""still need to understand wether this could be a possible solution for pathway visualization. otherwise, this code is useless
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
@bot.message_handler(commands=['change_lang'])
def change_lang(message):
    """
    This function is meant to add the command for changing the language. 
    This is because if the user choose a language he does not know by accident, it is difficult to change it from the buttons displayed in help message.
    This command will be also displayed in the bottom left menu on telegram mobile devices.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)
    user['action'] = 'help'

    language_selection(message)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def help(message):
    """
    This is the main message that is displayed to the user.
    The button menu displays all the possible commands that can be chose by the user.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=COMMANDS, language=user['selected_language'], skip_restart=True)
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.help', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

################################
######## QUERY HANDLERS ########
################################

@bot.callback_query_handler(lambda query: query.data in COMMANDS)
def command_handler(query):
    """
    This function explicitly call one of the commands that is selected by pressing one of the buttons displayed in help message.
    :query: the Telegram query packet created when a callback_data is pressed.
    """
    globals()[query.data](query)

@bot.callback_query_handler(lambda query: query.data in LANGUAGES)
def language_handler(query):
    """
    This function catch the user choice of the language.
    Based on the action that has been set for the user, we choose the proper function to call.
    :query: the Telegram query packet created when a callback_data is pressed.
    """
    user = retrieve_user(query.from_user.id)
    user['selected_language'] = query.data
    
    if user['action'] == 'capeesh':
        pilot_selection(query)
    elif user['action'] == 'pathway':
        pilot_selection(query)
    elif user['action'] == 'wiki':
        pilot_selection(query)
    elif user['action'] == 'localisation':
        geolocalisation(query)
    elif user['action'] == 'help':
        help(query)

@bot.callback_query_handler(lambda query: query.data in PILOTS)
def pilot_handler(query):
    """
    This function catch the selection of the pilot. We save this information in the user in his information and we call the function that displays the 
    menu of the available services in that pilot.
    :query: the Telegram query packet created when a callback_data is pressed.
    """
    user = retrieve_user(query.from_user.id)
    user['selected_pilot'] = query.data

    service_selection(query)

@bot.callback_query_handler(lambda query: "Useful" in query.data)
def store_rating(query):
    """
    This function catch the selection of the rating asked to the user for the quality of the pathway information. 
    We store these information in the ratings.csv file.
    The information saved are: the user, the timestamp, the pilot, the service, the language and finally the choice.
    :query: the Telegram query packet created when a callback_data is pressed.
    """
    user = retrieve_user(query.from_user.id)
    rating_file = open('./data/ratings.csv', 'a')

    # store also the handle of the user
    handle_user = query.from_user.username
    user_id = query.from_user.id
    date_msg = datetime.fromtimestamp(query.message.date)

    try:
        string_to_store = str(user_id) + ',' + handle_user + ',' + str(date_msg) + ',' + user['selected_pilot'] + ',' + user['selected_service'] + ',' + user['selected_language'] + ','
        if query.data == 'Useful':
            score = True
        elif query.data == 'Not Useful':
            score = False
        string_to_store = string_to_store + str(score) + '\n'
    except Exception as e:
        print(e)
        string_to_store = ''

    rating_file.write(string_to_store)
    rating_file.close()

    # LOG CREATION
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S,%f")
    log = {
        "datetime"            :  dt_string,
        "user_id"             :  user_id,
        "username"            :  handle_user,
        "query_id"            :  query.id,
        "chat_instance"       :  query.chat_instance,
        "action"              :  "rating",
        "selected_pilot"      :  user['selected_pilot'],
        "selected_service"    :  user['selected_service'],
        "selected_language"   :  user['selected_language'],
        "score"               :  query.data
    }
    print(json.dumps(log))
    return_markup = restart(query)
    bot.send_message(chat_id=query.from_user.id, text=i18n.t('messages.rating_submission', locale=user['selected_language']), reply_markup=return_markup)

@bot.callback_query_handler(lambda query: "course" in query.data)
def sign_up_to_capeesh(query):
    """
    This function catch the choice of the user for the language course. If the user press yes, we proceed to ask the email for accessing Capeesh.
    :query: the Telegram query packet created when a callback_data is pressed.
    """
    user = retrieve_user(query.from_user.id)
    # markup = restart(query)
    msg = bot.send_message(chat_id=query.from_user.id, text=i18n.t('messages.capeesh_mail_insertion', locale=user['selected_language']))
    bot.register_next_step_handler(msg, add_email)

@bot.callback_query_handler(lambda query: "nope" in query.data)
def return_to_menu(query):
    """
    This function catch when the user press a negative button. If this answer is on the capeesh experience, we return to the help message.
    If this answer is on the pathway experience (no location sharing), we proceed to the selection of the pilots.
    :query: the Telegram query packet created when a callback_data is pressed.
    """
    user = retrieve_user(query.from_user.id)
    if user['action'] == 'capeesh':
        user['action'] = 'help'
        help(query)
    else:
        pilot_selection(query)

@bot.callback_query_handler(lambda query: "restart" in query.data)
def restart_experience(query):
    """
    This function catch the choice of the user to resetart the experience. We redirect the user to the help message with the commands available.
    :query: the Telegram query packet created when a callback_data is pressed.
    """
    help(query)

@bot.callback_query_handler(lambda query: "location" in query.data)
def location(query):
    """
    This function catch the choice to share the position. We then proceed to display the proper button to do so. 
    :query: the Telegram query packet created when a callback_data is pressed.
    """
    geolocalisation(query)

@bot.callback_query_handler(lambda query: query.data in SERVICES[str.lower(retrieve_user(query.from_user.id)['selected_pilot'])])
def call_service_api(query):
    """
    This function catch the choice of the user about the service. If the action is capeesh, we redirect the information to the language_course function.
    Otherwise, we call the Pathway Generator API with the information about the pilot and the service.
    If the translation of the pathway is already present, we already store the information and we just display the text.
    Otherwise, we call the API, load the result and translate the text with Google Translator. We then display the message and proceed to update the translations
    file.
    The loop has the purpose to read the response from the json format of the pathway.
    :query: the Telegram query packet created when a callback_data is pressed.
    """


    user = retrieve_user(query.from_user.id)
    # service_key = user['selected_service'] 
    user['selected_service'] = service_mapping[query.data]

    # LOG CREATION FOR PATHWAY AND CAPEESH
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S,%f")
    log = {
        "datetime"            :  dt_string,
        "user_id"             :  query.from_user.id,
        "username"            :  query.from_user.username,
        "query_id"            :  query.id,
        "chat_instance"       :  query.chat_instance,
        "action"              :  user["action"],
        "selected_pilot"      :  user['selected_pilot'],
        "selected_service"    :  user['selected_service'],
        "selected_language"   :  user['selected_language']
    }
    print(json.dumps(log))

    #print ( user['selected_service'])

    if user['action'] == 'capeesh':
        language_course(query)
        return
    elif user['action'] == 'wiki':
        wiki_payoff(query)
        return

    translation_key = 'pathways.' + user['selected_pilot'] + '.' + query.data
    pathway_text = i18n.t(translation_key, locale=user['selected_language'])
    language = user['selected_language']

    if pathway_text == translation_key:
        files = {'data': (None, '{"pilot":"' + user['selected_pilot'] +'","service":"' + user['selected_service'] + '"}'),}

        url = 'https://easyrights.linksfoundation.com/v0.3/generate'
        try:
            response = requests.post(url, files=files)

            pathway = json.loads(response.text)  
            
            pathway_text = ''
            block_message = ''
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
            path = './locale/' + user['selected_language'] + '/pathways.' + user['selected_language'] + '.yml'
            file_input = open(path, 'r')
            pathways_dict = yaml.safe_load(file_input)
            os.remove(path)
            if pathways_dict[user['selected_language']][user['selected_pilot']]:
                pathways_dict[user['selected_language']][user['selected_pilot']].update({query.data: pathway_text})
            else:
                pathways_dict[user['selected_language']][user['selected_pilot']] = {}
                pathways_dict[user['selected_language']][user['selected_pilot']].update({query.data: pathway_text})
            yaml.safe_dump(pathways_dict, open(path, 'w'), encoding='utf-8', allow_unicode=True)

        except Exception as e:
            print(e)
            bot.send_message(chat_id=query.from_user.id, text=i18n.t('messages.error', locale=user['selected_language']))

    elif pathway_text[:9] == '<b>Step 1' and language != 'en':
        # print("here")
        translator = Translator()
        pathway_text = translator.translate(pathway_text, dest=language).text

        path = './locale/' + user['selected_language'] + '/pathways.' + user['selected_language'] + '.yml'
        file_input = open(path, 'r')
        pathways_dict = yaml.safe_load(file_input)
        os.remove(path)
        if pathways_dict[user['selected_language']][user['selected_pilot']]:
            pathways_dict[user['selected_language']][user['selected_pilot']].update({query.data: pathway_text})
        else:
            pathways_dict[user['selected_language']][user['selected_pilot']] = {}
            pathways_dict[user['selected_language']][user['selected_pilot']].update({query.data: pathway_text})
        yaml.safe_dump(pathways_dict, open(path, 'w'), encoding='utf-8', allow_unicode=True)
    
    # introductory message that explains what is a pathway
    pathway_introduction = i18n.t('messages.pathway_intro', locale=user['selected_language']) #+ i18n.t('services.'+user['selected_service'], locale=user['selected_language'])
    if user['selected_pilot'] == "palermo" and query.data == "job_seeking":
        pass
    else:
        bot.send_message(chat_id=query.from_user.id, text=pathway_introduction, parse_mode='HTML')

    bot.send_message(chat_id=query.from_user.id, text=pathway_text, parse_mode='HTML') #parse_mode='HTML'

    # Further info and services
    if user['selected_pilot'] == 'malaga':
        pass
        # extra_service = i18n.t('messages.malaga_payoff', locale=user['selected_language'])
        # bot.send_message(chat_id=query.from_user.id, text=extra_service, parse_mode='HTML')
    elif user['selected_pilot'] == "palermo" and query.data == "job_seeking":
        pass
    else:
        # print('messages.'+user['selected_pilot']+'_'+query.data+'_payoff')
        extra_service = i18n.t('messages.'+user['selected_pilot']+'_'+query.data+'_payoff', locale=user['selected_language'])
        bot.send_message(chat_id=query.from_user.id, text=extra_service, parse_mode='HTML')
    
    rating_submission(query)

###########################
######## FUNCTIONS ########
###########################

def restart(message):
    """
    Show the "restart" button. The list of buttons is empty because in menu_creation it is an option already considered to be added to other list of buttons.
    This function is called when the user reach the end of one of the three experiences offered (pathway, language course and pronunciation exercises).
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)
    markup = menu_creation(buttons=[], language=user['selected_language'])

    return markup

def rating_submission(message):
    """
    We ask if the information displayed in the pathway is useful or not.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()
    # markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language'])+' \U0001F44D', callback_data='Useful'))
    # markup.add(types.InlineKeyboardButton(text=i18n.t('messages.no', locale=user['selected_language'])+' \U0001F44E', callback_data='Not Useful'))
    markup.add(types.InlineKeyboardButton(text=' \U0001F44D', callback_data='Useful'), 
            types.InlineKeyboardButton(text=' \U0001F44E', callback_data='Not Useful'))
    # markup.add(types.InlineKeyboardButton(text=' \U0001F44E', callback_data='Not Useful'))
    markup.add(types.InlineKeyboardButton(text=i18n.t('commands.restart', locale=user['selected_language']), callback_data='restart'))
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.rating', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def ask_for_position(message):
    """
    Ask the user wether he wants to share his location.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    # markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language'])+' \U0001F44D', callback_data='location'))
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language']), callback_data='location'), 
            types.InlineKeyboardButton(text=i18n.t('messages.no', locale=user['selected_language']), callback_data='nope'))
    markup.add(types.InlineKeyboardButton(text=i18n.t("commands.restart", locale=user['selected_language']), callback_data='restart'))

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.location_permission', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def auto_localisation(message):
    """
    If the location of the user correspond to one of the available municipalities, we show the services supported.
    :message: the Telegram message.
    TODO: align with the menu_creation function
    """
    user = retrieve_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()
    for service in SERVICES[user['selected_pilot'].lower()]:
        if service == "job_seeking" and user['action'] == "pathway":
            pass
        elif service == "registry_office" and user['action'] == "wiki":
            pass
        else:
            markup.add(types.InlineKeyboardButton(text=service, callback_data=service)) 


    bot.send_message(chat_id=message.chat.id, text=i18n.t('messages.service_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def geolocalisation(message):
    """
    Print a button for the location request. The key parameter is the request_location in the button features.
    :message: the Telegram message.
    NB: the localisation feature is not supported by Telegram Desktop, but it is by Telegram Web (only Google Chrome) and Telegram Messenger.
    """
    user = retrieve_user(message.from_user.id)

    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button_geo = types.KeyboardButton(text=i18n.t('messages.share', locale=user['selected_language']), request_location=True)
    keyboard.add(button_geo)

    user['action'] = 'localisation'
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.location', locale=user['selected_language']), reply_markup=keyboard, parse_mode='HTML')

def language_selection(message):
    """
    Creation of the menu buttons with the supported languages from the bot.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=LANGUAGES, skip_restart=True)    

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.lang_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def pilot_selection(message):
    """
    Creation of the menu buttons with the list of the available municipalities.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)

    markup = menu_creation(buttons=PILOTS, language=user['selected_language'])

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.pilot_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def service_selection(message):
    """
    Creation of the menu buttons with the services supported in the pilot selected by the user.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)

    # we need to distinguish the service choice for palermo
    service_buttons = []
    for service in SERVICES[user['selected_pilot']]:
        if service == "job_seeking" and user['action'] == "pathway":
            pass
        elif service == "registry_office" and user['action'] == "wiki":
            pass
        else:
            service_buttons.append(service)

    markup = menu_creation(buttons=service_buttons, language=user['selected_language'], type='services.'+user['selected_pilot'])

    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.service_selection', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def language_course(message):
    """
    Capeesh integration. We ask the user wether he wants to access a language course.
    :message: the Telegram message.
    """
    user = retrieve_user(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    # markup.add(types.InlineKeyboardButton(text=i18n.t('messages.yes', locale=user['selected_language']) + ' \U0001F44D', callback_data='course'))
    markup.add(types.InlineKeyboardButton(text=i18n.t('messages.next', locale=user['selected_language']), callback_data='course'),
                types.InlineKeyboardButton(text=i18n.t('messages.back', locale=user['selected_language']), callback_data='nope'))
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('messages.capeesh', locale=user['selected_language']), reply_markup=markup, parse_mode='HTML')

def wiki_payoff(message):
    user = retrieve_user(message.from_user.id)
    return_markup = restart(message)
    bot.send_message(chat_id=message.from_user.id, text=i18n.t('wiki.'+user['selected_pilot']+"."+message.data, locale=user['selected_language']),reply_markup=return_markup)

def add_email(message):
    """
    Capeesh integration. Here, we check if the input mail or username is correct and then we make an API request to Capeesh to insert the email into their databases.
    :message: the Telegram message.
    TODO: escape char or sequence if the user does not want to insert an email.
    """
    user = retrieve_user(message.from_user.id)    
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    regex2 = r'[A-Za-z0-9._-]'
    email = message.text

    # if email == "@escape":
    #     user['action'] = 'help'                     
    #     help(query)

    if re.match(regex2, email) and not re.match(regex, email):
        email = email + "@easyrights.eu"

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
    """
    Retrieves the user from the users global variable. If not found, update the user file with the addition of the new one.
    :user_id: the user id that has to be find. 
    """
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

def menu_creation(buttons, language='en', type='commands', skip_restart=False):
    """
    Function for the creation of buttons menu.
    :buttons: list of the buttons. The values of this list will define the data of the callback.
    :langague: the language. The default is english.
    :type: specifies the type of button. Useful for building the python i18n translation key.
    :skip_restat: if set to True, the restart button will not appear. 
    """

    markup = types.InlineKeyboardMarkup(row_width=1)
    for button in buttons:
        action = type + '.' + button
        markup.add(types.InlineKeyboardButton(text=i18n.t(action, locale=language), callback_data=button))

    if not skip_restart:
        markup.add(types.InlineKeyboardButton(text=i18n.t("commands.restart", locale=language), callback_data='restart'))
    return markup
    
##########################
######## POLLING #########
##########################

while True:
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S,%f")
    print(dt_string + " Restart ")
    try:
        # bot.infinity_polling(timeout=10, long_polling_timeout = 5)
        # bot.polling(True)
        bot.polling()
    except Exception as e:
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S,%f")
        print("Exception occurred: ", dt_string)
        print(e)
    