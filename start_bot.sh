#!/bin/bash 

# Activate the environment
python3 -m venv env
source env/bin/activate

# Install the requirements
pip3 install -r requirements.txt

# Start the bot
nohup python3 -u bot.py >> telegram_bot_log.out 2>&1 &