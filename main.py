import logging
import re
from collections import deque

from dotenv import load_dotenv
import os
from typing import Final, Text
from tzlocal import get_localzone
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, \
    ConversationHandler
from datetime import datetime, timedelta
from apscheduler.triggers.interval import IntervalTrigger

from CleaningSchedule import CleaningSchedule

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('I will help you remember your cleaning schedule. Type / to see all possible commands')

async def delete_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_jobs = context.job_queue.jobs()
    if len(current_jobs) == 0:
        await update.message.reply_text("There is currently no reminder. Type /set_reminder.")
        return
    for job in current_jobs:
        job.schedule_removal()
    await update.message.reply_text("Your reminder is deleted!")

async def show_mitbewohnys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = cleaning_schedule.schedule
    text = f"The list is empty, start adding mitbewohnys by typing /add_mitbewohny" if not names else ", ".join(names)
    await update.message.reply_text(text)



# Conversations
ADDING = range(1)
REMOVING = range(1)
SETTING_REMINDER = range(1)
async def add_mitbewohny_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Type the names of the mitbewohnys that you want to add separated by comma: Mitbewohny1, Mitbewohny2, ...')
    return ADDING

async def remove_mitbewohny_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Type the names of the mitbewohnys that you want to remove separated by comma: Mitbewohny1, Mitbewohny2, ...')
    return REMOVING

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not cleaning_schedule.schedule:
        await update.message.reply_text("Please add at least one mitbewohny first. Type /add_mitbewohny.")
        return ConversationHandler.END
    await update.message.reply_text('Set up a reminder by specifying the weekday, interval, and time. Eg.: Sunday, 1, 12, 30. This will send out a reminder each week on sundays at 12:30.')
    return SETTING_REMINDER

async def done_adding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    names = parse_names(update.message.text)
    for name in names:
        cleaning_schedule.save_schedule(name)
    names_string = ", ".join(names)
    await update.message.reply_text(f"I added {names_string} to the list!")
    return ConversationHandler.END

async def done_removing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    names = parse_names(update.message.text)
    for name in names:
        cleaning_schedule.schedule.remove(name)
    names_string = ", ".join(names)
    await update.message.reply_text(f"I removed {names_string} from the list!")
    return ConversationHandler.END

async def done_setting_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    #TODO: clean up this integer string mess
    info = update.message.text.split(", ")
    day = info[0].lower()
    interval = info[1]
    day_as_int, interval_as_int, hour_as_int, minute_as_int = parse_timer_settings(update.message.text)
    chat_id = update.effective_message.chat_id
    # TODO: make timezone adjustable
    timezone = get_localzone()
    context.job_queue.run_custom(reminder, job_kwargs={"trigger": IntervalTrigger(seconds=interval_as_int,
        start_date=determine_start_date(day_as_int, hour_as_int, minute_as_int, timezone))
    }, chat_id=chat_id)

    text =f"Your reminder will be sent out on {day}s every week!" if interval == "1" \
        else f"Your reminder will be sent out on {day}s every {interval} weeks!"

    await update.message.reply_text(text)
    return ConversationHandler.END

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f"Okay, lets quit this.")
    return ConversationHandler.END

# Job callback function
async def reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    name = cleaning_schedule.get_next_person()
    await context.bot.send_message(context.job.chat_id, text=f"{name} has to clean the flat this week!")

# Helper functions
def parse_names(text: Text):
    return [name.lower() for name in text.split(", ") if name]

def parse_timer_settings(text: Text) -> int:
    info = text.split(", ")
    day = weekday_to_int(info[0].lower())
    interval = extract_and_convert_to_int(info[1])
    hour = extract_and_convert_to_int(info[2])
    minute = extract_and_convert_to_int(info[3])
    return day, interval, hour, minute

def extract_and_convert_to_int(string):
    match = re.search(r'\d+', string)
    if match:
        return int(match.group())
    else:
        raise ValueError("No number found in the string")

def weekday_to_int(weekday_name):
    weekday_name = weekday_name.lower()
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    if weekday_name in weekdays:
        return weekdays.index(weekday_name)
    else:
        raise ValueError(f"{weekday_name} is not a valid weekday name")


def determine_start_date(target_weekday, hour, minute, timezone):
    now = datetime.now()
    current_weekday = now.weekday()
    days_until_next = (target_weekday - current_weekday + 7) % 7
    start_date = now + timedelta(days=days_until_next)
    start_date = start_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    log(f"now: {now}\n"
        f"target weekday: {target_weekday}\n"
        f"current weekday: {current_weekday}\n"
        f"days until next: {days_until_next}\n"
        f"start date: {start_date}")
    return start_date



def log(message: Text):
    logger.log(20, message)


if __name__ == '__main__':
    load_dotenv()
    token = os.getenv('TOKEN')
    if not token:
        print("Bot token not found")

    log("Bot is running..")
    app = Application.builder().token(token).build()

    # Initialize schedule
    cleaning_schedule = CleaningSchedule()

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('delete_reminder', delete_reminder_command))
    app.add_handler(CommandHandler('show_mitbewohnys', show_mitbewohnys_command))

    # Conversations
    adding_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_mitbewohny", add_mitbewohny_command)],
        states={
            ADDING: [
                MessageHandler(filters.ALL, done_adding)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    removing_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("remove_mitbewohny", remove_mitbewohny_command)],
        states={
            REMOVING: [
                MessageHandler(filters.ALL, done_removing)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    setting_reminder_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set_reminder", set_reminder)],
        states={
            SETTING_REMINDER: [
                MessageHandler(filters.ALL, done_setting_reminder)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )


    app.add_handler(adding_conv_handler)
    app.add_handler(removing_conv_handler)
    app.add_handler(setting_reminder_conv_handler)

    #TODO: add error handlers


    # Run the bot
    log("Polling..")
    app.run_polling(poll_interval=3)

