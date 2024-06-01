# DontForgetToClean

This is a simple telegram bot that sends out recurring reminders so that you and your flatmates keep track of your cleaning
schedule easily ✨

## Installation

To install the required packages, run the following command in your virtual environment:

```bash
pip install -r requirements.txt
```
Paste your bot's token in the .env file. If you don't have a token yet
create a new bot using Telegram's BotFather.
```
TOKEN = 'paste your bot\'s token here'
```
To run the project, use the following command:
```bash
python3 main.py
```

## Usage

✨ First, add a list of the people who will participate in the cleaning schedule by using <span style="color:blue">/add_mitbewohny</span>.

✨ Then, set a reminder (<span style="color:blue">/set_reminder</span>) by specifying the weekday, interval in weeks, hour and minute.<br>
Example:<br>
```
Sunday, 1, 12, 30
```
This will send out a weekly reminder every Sunday at 12:30.


