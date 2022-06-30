import json
import os
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np

def is_json(myjson):
  try:
    json.loads(myjson)
  except ValueError as e:
    return False
  return True

with open("telegram_bot_log.out", "r") as log_file:
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

with open("telegram_bot_log_copy.out", "r") as log_file:
    logs = log_file.readlines()

# COUNT THE NUMBER OF USERS
users = []
count_users = 0
for log in logs:
    log = json.loads(log)
    if log["user_id"] not in users:
        users.append(log["user_id"])
        count_users += 1
print("Total number of users: ", count_users)
n_users = pd.DataFrame([count_users])
n_users.to_csv("./analysis/tables/n_users.csv")


# COUNT NUMBER OF TIMES A FEATURE HAS BEEN SELCTED
actions = pd.DataFrame(index = ["n"])
for log in logs:
    log = json.loads(log)
    if str(log["action"]) not in actions.columns:
        if str(log["action"]) == "localisation" or str(log["action"]) == "rating":
            actions[str(log["action"])] = [1]
    else:
        if str(log["action"]) == "localisation" or str(log["action"]) == "rating":
            actions[str(log["action"])][0] += 1
print("\nNumber of times a a feature was selected: ")
print(actions)
actions.to_csv("./analysis/tables/n_times_feature.csv")

plt.figure()
plt.bar(actions.columns, actions.iloc[0], width=0.5, color="lightcoral")
plt.title("Number of times a feature was selected")
plt.grid()
plt.savefig("./analysis/figures/n_times_feature.png")
plt.show()


# COUNT NUMBER OF TIMES A TOOL HAS BEEN SELCTED
actions = {}
for log in logs:
    log = json.loads(log)
    if str(log["action"]) not in actions:
        if str(log["action"]) != "localisation" and str(log["action"]) != "rating":
            actions[str(log["action"])] = [1]
    else:
        if str(log["action"]) != "localisation" and str(log["action"]) != "rating":
            actions[str(log["action"])][0] += 1
print("\nNumber of times a a tool was selected: ")
actions_df = pd.DataFrame(actions, index = ["n"])
actions_df.to_csv("./analysis/tables/n_times_tool.csv")
print(actions_df)
plt.figure()
plt.bar(actions_df.columns, actions_df.iloc[0], width=0.5)
plt.title("Number of times a tool was selected")
plt.grid()
plt.savefig("./analysis/figures/n_times_tool.png")
plt.show()

# COUNT NUMBER OF TIMES A PILOT HAS BEEN SELECTED
pilots = {}
for log in logs:
    log = json.loads(log)
    if str(log["action"]) == "capeesh" or str(log["action"]) == "pathway":
        if str(log["selected_pilot"]) not in pilots:
            pilots[str(log["selected_pilot"])] = [1]
        else:
            pilots[str(log["selected_pilot"])][0] += 1
print("\nNumber of times a pilot was selected:")
pilots = pd.DataFrame(pilots, index = ["n"])
pilots.to_csv("./analysis/tables/n_times_pilot.csv")
print(pilots)

plt.figure()
plt.bar(pilots.columns, pilots.iloc[0], width=0.5, color="darkorange")
plt.title("Number of times a pilot was selected")
plt.grid()
plt.savefig("./analysis/figures/n_times_pilots.png")
plt.show()

# COUNT NUMBER OF USERS PER PILOT
pilots = {
    "malaga": [],
    "larissa": [],
    "birmingham": [],
    "palermo": []
}
for log in logs:
    log = json.loads(log)
    if str(log["action"]) == "capeesh" or str(log["action"]) == "pathway":
        if str(log["user_id"]) not in pilots[str(log["selected_pilot"])]:
            pilots[str(log["selected_pilot"])].append(str(log["user_id"]))
for pilot in pilots:
    pilots[pilot] = [len(pilots[pilot])]
print("\nNumber of users per pilots: ")
pilots = pd.DataFrame(pilots, index = ["n"])
pilots.to_csv("./analysis/tables/n_users_pilot.csv")
print(pilots)

plt.figure()
plt.bar(pilots.columns, pilots.iloc[0], width=0.5, color="deepskyblue")
plt.title("Number of users per pilot")
plt.grid()
plt.savefig("./analysis/figures/n_users_pilots.png")
plt.show()

# COUNT NUMBER OF USERS PER TOOL
actions = {
    "capeesh": [],
    "calst": [],
    "pathway": [],
}
for log in logs:
    log = json.loads(log)
    if str(log["action"]) != "localisation" and str(log["action"]) != "rating":
        if str(log["user_id"]) not in actions[str(log["action"])]:
            actions[str(log["action"])].append(str(log["user_id"]))
for action in actions:
    actions[action] = len(actions[action])
print("Number of users per action:")
actions = pd.DataFrame(actions, index = ["n"])
actions.to_csv("./analysis/tables/n_users_tool.csv")
print(actions)

plt.figure()
plt.bar(actions.columns, actions.iloc[0], width=0.5, color="forestgreen")
plt.title("Number of users per tool")
plt.grid()
plt.savefig("./analysis/figures/n_users_tool.png")
plt.show()

# NUMBER OF USERS PER feature
features =  {
    "rating": [],
    "localisation": []
}

for log in logs:
    log = json.loads(log)
    if str(log["action"]) == "localisation" or str(log["action"]) == "rating":
        if str(log["user_id"]) not in features[str(log["action"])]:
            features[str(log["action"])].append(str(log["user_id"]))
for feature in features:
    features[feature] = len(features[feature])
print("Number of users per action:")
features = pd.DataFrame(features, index = ["n"])
features.to_csv("./analysis/tables/n_users_feature.csv")
print(features)

plt.figure()
plt.bar(features.columns, features.iloc[0], width=0.5, color="forestgreen")
plt.title("Number of users per tool")
plt.grid()
plt.savefig("./analysis/figures/n_users_feature.png")
plt.show()

# NUMBER OF USERS PER LANGUAGE
languages = {
    "ar": [],
    "el": [],
    "en": [],
    "es": [],
    "fr": [],
    "it": []
}
for log in logs:
    log = json.loads(log)
    if str(log["user_id"]) not in languages[str(log["selected_language"])]:
        languages[str(log["selected_language"])].append(str(log["user_id"]))
for language in languages:
    languages[language] = [len(languages[language])]
print("Number of users per language:")
languages = pd.DataFrame(languages, index = ["n"])
languages.to_csv("./analysis/tables/n_users_language.csv")
print(languages)

plt.figure()
plt.bar(languages.columns, languages.iloc[0], width=0.5, color="sandybrown")
plt.title("Number of users per language")
plt.grid()
plt.savefig("./analysis/figures/n_users_language.png")
plt.show()

# NUMBER OF USERS PER PILOTS IN EACH LANGUAGE
languages = {
    "ar": {
        "malaga": [],
        "larissa": [],
        "birmingham": [],
        "palermo": []
        },
    "el": {
        "malaga": [],
        "larissa": [],
        "birmingham": [],
        "palermo": []
        },
    "en": {
        "malaga": [],
        "larissa": [],
        "birmingham": [],
        "palermo": []
        },
    "es": {
        "malaga": [],
        "larissa": [],
        "birmingham": [],
        "palermo": []
    },
    "fr": {
        "malaga": [],
        "larissa": [],
        "birmingham": [],
        "palermo": []
        },
    "it": {
        "malaga": [],
        "larissa": [],
        "birmingham": [],
        "palermo": []
        }
}

for language in languages:
    for log in logs:
        log = json.loads(log)
        if log["selected_language"] == language:
            if str(log["action"]) == "capeesh" or str(log["action"]) == "pathway":
                if str(log["user_id"]) not in languages[language][str(log["selected_pilot"])]:
                    languages[language][str(log["selected_pilot"])].append(str(log["user_id"]))

for language in languages:
    for pilot in languages[language]:
        languages[language][pilot] = len(languages[language][pilot])

print("\nNumber of users per pilot in each language:")
languages = pd.DataFrame(languages, columns = ["it", "fr", "es", "en", "el", "ar"], index = ["malaga", "larissa", "birmingham", "palermo"])
languages.to_csv("./analysis/tables/n_users_pilot_language.csv")
print(languages)

plt.figure()
N = len(languages.columns)
ind = np.arange(N)
width = 0.2
x = -0.5
for i in range(len(languages.index)):
    bar = plt.bar(ind + x*width, languages.iloc[i], width=width)
    x += 1

plt.xticks(ind+width,languages.columns)
plt.title("Number of users per pilot in each language:")
plt.grid()
plt.legend(languages.index)
plt.savefig("./analysis/figures/n_users_pilot_language.png")
plt.show()



# # GIVEN A PILOT WHICH ARE THE SELECTED LANGUAGES?
# pilots = {
#     "larissa": {"ar": [],
#     "el": [],
#     "en": [],
#     "es": [],
#     "fr": [],
#     "it": []},
#     "malaga": [],
#     "birmingham": [],
#     "palermo": []
# }

# for log in logs:
#         log = json.loads(log)
#         if str(log["action"]) == "capeesh" or str(log["action"]) == "pathway":
#             if log["selected_pilot"] == "larissa":
#                 if str(log["user_id"]) not in pilots["larissa"][str(log["selected_language"])]:
#                     pilots["larissa"][str(log["selected_language"])].append(str(log["user_id"]))

# for language in list(pilots["larissa"].keys()):
#     pilots["larissa"][language] = len(pilots["larissa"][language])

# print(pilots)
# Same as previous dataframe


# NUMBER OF USERS PER PILOT PER SERVICE
pilots = {
    "malaga": {},
    "larissa": {},
    "birmingham": {},
    "palermo": {}
}

services = { "Asylum Request":{"malaga": []},
            "Work Permission":{"malaga": []},
            "Birth Certification":{"larissa":[]},
            "Certification of Nationality":{"larissa":[]},
            "baes esol":{"birmingham":[]},
            "Clean Air Zone":{"birmingham":[]},
            "Registration at Registry Office":{"palermo":[]}}


for service in services:
    for log in logs:
        log = json.loads(log)
        if str(log["action"]) == "capeesh" or str(log["action"]) == "pathway":
            if log["selected_service"] == service:
                if str(log["user_id"]) not in services[service][log["selected_pilot"]]:
                    services[service][log["selected_pilot"]].append(log["user_id"])

for service in services:
    services[service][list(services[service].keys())[0]] = [len(services[service][list(services[service].keys())[0]])]
    services[service] = pd.DataFrame(services[service], dtype=int)

print("\nNumber of users per pilot per service:")
services_concat = pd.concat(services)
services_concat.to_csv("./analysis/tables/n_users_pilot_services.csv")
print(services_concat)

plt.figure(figsize=(8,8))
x = list(services.keys())
# services_concat.plot.bar()
for pilot in pilots:
    y = list(map(int, services_concat[pilot].values[np.logical_not(np.isnan(services_concat[pilot].values))]))
    y = services_concat[pilot].values
    plt.bar(x, y)

plt.legend(list(pilots.keys()))
plt.xticks(list(services.keys()),  rotation=20)
plt.title("Number of users per pilot per service:")
plt.grid()
plt.savefig("./analysis/figures/n_users_pilot_service.png")
plt.show()


# NUMBER OF USERS OER PILOT PER TOOL PER SERVIZIO
pilots = {
    "malaga": {},
    "larissa": {},
    "birmingham": {},
    "palermo": {}
}

services = { "malaga": {"Asylum Request":                 {"capeesh": [], "pathway": []},
                        "Work Permission":                {"capeesh": [], "pathway": []}},
            "larissa": {"Birth Certification":            {"capeesh": [], "pathway": []},
                        "Certification of Nationality":   {"capeesh": [], "pathway": []}},
            "birmingham": {"baes esol":                   {"capeesh": [], "pathway": []},
                           "Clean Air Zone":              {"capeesh": [], "pathway": []}},
            "palermo": {"Registration at Registry Office":{"capeesh": [], "pathway": []}}}

for pilot in pilots:
    for service in services[pilot]:
        for log in logs:
            log = json.loads(log)
            if str(log["action"]) == "capeesh" or str(log["action"]) == "pathway":
                if log["selected_service"] == service:
                    if str(log["user_id"]) not in services[pilot][service][log["action"]]:
                        services[pilot][service][log["action"]].append(log["user_id"])
for pilot in pilots:
    for service in services[pilot]:
        for action in list(services[pilot][service].keys()):
            services[pilot][service][action] = [len(services[pilot][service][action])]
        services[pilot][service] = pd.DataFrame(services[pilot][service], dtype=int)
    services[pilot] = pd.concat(services[pilot])

print("\nNumber of users per pilot per service per tool:")
services_concat = pd.concat(services)
services_concat.to_csv("./analysis/tables/n_users_services_tool.csv")
print(services_concat)

fig = plt.figure(figsize=(8,8))
x_tot = [] # lista di servizi sull'asse delle x
# y1 = []
# y2 = []
# x = []
for pilot in pilots:
    for (service, tmp) in services[pilot].index:
        x_tot.append(service)
#         x.append(service)
#         y1.append(int(services_concat["capeesh"].loc[(pilot, service, 0)]))
#         y2.append(int(services_concat["pathway"].loc[(pilot, service, 0)]))
plt.bar(np.arange(len(x_tot)) - 0.2, services_concat["capeesh"].values, width = 0.4)
plt.bar(np.arange(len(x_tot)) + 0.2, services_concat["pathway"].values, width = 0.4)
plt.xticks(np.arange(len(x_tot)),x_tot,  rotation=20)
plt.legend(["capeesh", "pathway"])
plt.title("Number of users per service per tool:")
plt.grid()
plt.savefig("./analysis/figures/n_users_service_tool.png")
plt.show()



# NUMBER OF USERS PER PILOT PER TOOL

pilots = {
    "malaga": {"capeesh": [], "pathway": []},
    "larissa": {"capeesh": [], "pathway": []},
    "birmingham": {"capeesh": [], "pathway": []},
    "palermo": {"capeesh": [], "pathway": []}
}


for log in logs:
    log = json.loads(log)
    if str(log["action"]) == "capeesh" or str(log["action"]) == "pathway":
        if str(log["user_id"]) not in pilots[str(log["selected_pilot"])][log["action"]]:
            pilots[str(log["selected_pilot"])][log["action"]].append(log["user_id"])

for pilot in pilots:
    for tool in pilots[pilot]:
        pilots[pilot][tool] = [len(pilots[pilot][tool])]
    pilots[pilot] = pd.DataFrame(pilots[pilot], dtype=int)
pilots_concat = pd.concat(pilots)
pilots_concat.to_csv("./analysis/tables/n_users_pilot_tool.csv")
print("\nNumber of users per pilot per tool:")
print(pilots_concat)

plt.figure()
plt.bar(np.arange(len(list(pilots.keys()))) - 0.2, pilots_concat["capeesh"].values, width = 0.4)
plt.bar(np.arange(len(list(pilots.keys()))) + 0.2, pilots_concat["pathway"].values, width = 0.4)
plt.xticks(np.arange(len(list(pilots.keys()))), list(pilots.keys()),  rotation=20)
plt.legend(["capeesh", "pathway"])
plt.title("Number of users per pilot per tool:")
plt.grid()
plt.savefig("./analysis/figures/n_users_pilot_tool.png")
plt.show()



# AVERAGE/MAX NUMBER OF RATINGS PER USER
# tot number of pos/neg ratings
# avg number of pos/neg ratings per user

users_pos = {}
users_neg = {}
tot_pos = 0
tot_neg = 0

for log in logs:
    log = json.loads(log)
    if log["action"] == "rating":
        if log["score"] == "Not Useful":
            tot_neg += 1
            if log["user_id"] not in users_neg:
                users_neg[log["user_id"]] = [1]
            else:
                users_neg[log["user_id"]][0] += 1
        elif log["score"] == "Useful":
            tot_pos += 1
            if log["user_id"] not in users_pos:
                users_pos[log["user_id"]] = [1]
            else:
                users_pos[log["user_id"]][0] += 1

print("\nTotal number of positive ratings: ", tot_pos)
print("\nTotal number of negative ratings: ", tot_neg)
pos_ratings = [item for sublist in list(users_pos.values()) for item in sublist]
print("\nAverage number of positive ratings per user: ",np.mean(pos_ratings))
neg_ratings = [item for sublist in list(users_neg.values()) for item in sublist]
print("\nAverage number of negative ratings per user: ",np.mean(neg_ratings))


# # RATINGS PER TOOL
# tools = {"capeesh": 0,
#         "pathway": 0,
#         "calst": 0}


