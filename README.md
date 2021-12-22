# easyRights ChatBot
A simple Python Telegram bot for the easyRights interface.

### Setup virtual environment

In order to install and use the external libraries used in this repository, we recommend the use of a virtual environment.
It can be created using the following command:

```bash
python3 -m venv env
```

You can now activate the virtual environment using the command:

```bash
source env/bin/activate
```

And use ```deactivate``` to disable it.

Once your virtual is activated, you can install the external libraries:

```python
pip3 install -r requirements.txt
```

### Chatbot start

To activate the bot and enable its functionalities, just use the following command after activating the virtual environment (it works with Python 3+):
```bash
python bot.py
```
You can now find the Bot in Telegram by searching for the @easyrights_bot handle.

### Functionalities

The first choice proposed to user once the **start** button is clicked is on which language he wants to read the information provided by the chatbot.
This information is stored and remembered during all the functionalities provided and can be changed anytime.

#### Pathway experience
This experience has the purpose of guiding the user towards the pathway, that is a set of simple istructions useful for accessing a specific service.
To do this, first of all the user is asked if he wants to share his positions: in this way, if he is in one of the municipalities supported by the easyRights project, 
he will be directly redirected to the choice among the available services in that municipality.

Otherwise, he will be offered a choice from the available cities.

Once this information has been collected, the chatbot will send an API request to the Pathway Generator which will respond with a json containing the pathway
which will be displayed in the bot after some formatting. Finally, it will be asked to the user wether the information were useful or not, storing the response.

![alt text](https://github.com/D2KLab/easyRights_bot/blob/main/imgs/pathway.png)

#### Language course experience
This experience will guide the user to the access to the Capeesh application, which provides some tailored language courses for the migrants.
Just like it was for the pathway, the process starts with some questions in order to collect the information about the service and the municipality
the user is asking for help.

Then, the bot will ask for an email, which will be sent to Capeesh for the registration of the user. Once done, istructions for downloading and installing the Capeesh application will be displayed in the bot, along with the istructions on how to access it.


![alt text](https://github.com/D2KLab/easyRights_bot/blob/main/imgs/capeesh.png)

#### Pronunciation exercises experience
In this experience, the user will be redirected to the CALST platform where he can access in order to start the pronunciation exercises.

![alt text](https://github.com/D2KLab/easyRights_bot/blob/main/imgs/calst.png)