import json
import os

def is_json(myjson):
  try:
    json.loads(myjson)
  except ValueError as e:
    return False
  return True

with open("telegram_bot_log_copy.out", "r") as log_file:
    logs = log_file.readlines()

developers_id = ["858840591","1971283519","153798713"]

if os.stat("telegram_bot_log_copy.out").st_size > 0: 
    with open("telegram_bot_log_copy.out", "w") as log_file:
      for log in logs:
          if is_json(log):
              log = json.loads(log)
              if str(log["user_id"]) not in developers_id:
                  log_file.writelines(json.dumps(log)+"\n")
else:
    print("Empty log file")

