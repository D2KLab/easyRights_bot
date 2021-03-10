#!/bin/bash 

python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt

nohup python3 bot.py > telegram_bot_log.out &