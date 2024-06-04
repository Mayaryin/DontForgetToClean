import asyncio
import os
from dotenv import load_dotenv
from telegram.error import NetworkError
from tzlocal import get_localzone
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from apscheduler.triggers.interval import IntervalTrigger

from flask import Flask, request

from api.cleaning_schedule import CleaningSchedule, NameNotFoundError
from api.utils import *

app = Flask(__name__)

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

async def show_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    job = context.job_queue.get_jobs_by_name('onlyjob')
    if not job:
        text = "There is no reminder. Start the set up by typing /set_reminder."
    else:
        interval = cleaning_schedule.interval
        minute_string = str(cleaning_schedule.minute)
        if cleaning_schedule.minute < 10:
            minute_string = "0" + str(cleaning_schedule.minute)
        text = f"Your current reminder is sent out on {cleaning_schedule.weekday.capitallize()} every week" if interval == 1 \
        else f"Your current reminder is sent out on {cleaning_schedule.weekday.capitalize()} every {interval} weeks"
        text = text + f" at {cleaning_schedule.hour}:{minute_string}"
    await update.message.reply_text(text)

async def show_mitbewohnies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    names = cleaning_schedule.names
    text = f"The list is empty, start adding mitbewohnys by typing /add_mitbewohny" \
        if not names else ", ".join(names)
    await update.message.reply_text(text)

# Conversations
ADDING = range(1)
REMOVING = range(1)
SCHEDULING_JOB = range(1)
async def add_mitbewohny_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Type the names of the mitbewohnys that you want to add separated by comma: Mitbewohny1, Mitbewohny2, ...')
    return ADDING

async def remove_mitbewohny_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Type the names of the mitbewohnys that you want to remove separated by comma: Mitbewohny1, Mitbewohny2, ...')
    return REMOVING

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not cleaning_schedule.names:
        await update.message.reply_text("Please add at least one mitbewohny first. Type /add_mitbewohny.")
        return ConversationHandler.END
    await update.message.reply_text('Set up a reminder by specifying the weekday, interval, and time. \n'
                                    'Eg.: Sunday, 1, 12, 30. This will send out a reminder each week on Sunday at 12:30.\n'
                                    'Note: There is always only one job at a time. Any current job will be overwritten.')
    return SCHEDULING_JOB

async def done_adding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    names = parse_names(update.message.text)
    cleaning_schedule.save_schedule(names)
    names_string = ", ".join(names)
    await update.message.reply_text(f"I added {names_string} to the list!")
    return ConversationHandler.END

async def done_removing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    names = parse_names(update.message.text)
    try:
        cleaning_schedule.update_names(names)
        names_string = ", ".join(names)
        await update.message.reply_text(f"I removed {names_string} from the list!")
    except NameNotFoundError as e:
        await update.message.reply_text(f"There is no {e.name} in the list!")
    return ConversationHandler.END

async def schedule_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    incoming_message: str = update.message.text
    if not validate_input(incoming_message):
        await update.message.reply_text("Please stick to the format. Example: Sunday, 1, 12, 30")
    else:
        text = schedule(update, context, incoming_message)
        await update.message.reply_text(text)
        return ConversationHandler.END

def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, message):

    # delete current job
    for job in context.job_queue.jobs():
        job.schedule_removal()

    info = message.split(", ")
    log(f"info: {info}")
    day_as_int, interval_as_int, hour_as_int, minute_as_int = convert_timer_settings(info)
    timezone = get_localzone()
    day = info[0]
    interval = info[1]
    chat_id = update.effective_message.chat_id

    context.job_queue.run_custom(reminder, job_kwargs={
        "trigger": IntervalTrigger(weeks=interval_as_int,
                                  start_date=determine_start_date(day_as_int, hour_as_int,minute_as_int, timezone))
                                },
                                 name="onlyjob", chat_id=chat_id)

    cleaning_schedule.save_schedule(weekday=day, interval=interval_as_int, hour=hour_as_int, minute=minute_as_int)

    text = f"Your reminder will be sent out on {day.capitalize()} every week!" if interval == "1" \
        else f"Your reminder will be sent out on {day.capitalize()} every {interval} weeks!"

    return text


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f"Okay, lets quit this.")
    return ConversationHandler.END

# Job callback function
async def reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    name = cleaning_schedule.get_next_person()
    retries = 3
    delay = 60
    for attempt in range(retries):
        try:
            await context.bot.send_message(context.job.chat_id, text=f"🧼 {name} will clean the flat this week ✨ ")
            log(f"Message sent successfully on attempt {attempt + 1}")
            break
        except NetworkError as e:
            log_error(f"Failed to send message on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                log_error("All retry attempts failed.")

# Error
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_error(f'Update {update.update_id} caused error: {context.error}')


if __name__ == '__main__':

    load_dotenv()
    token = os.getenv('TOKEN')
    bot_username = os.getenv('BOT_USERNAME')
    if not token:
        log_error("Bot token not found")
    if not bot_username:
        log_error("Bot username not found")

    log("Bot is running..")
    telegram_app = Application.builder().token(token).build()

    @app.route('/webhook', methods=['POST'])
    async def webhook():
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        await telegram_app.process_update(update)
        return 'ok'

    # Initialize schedule
    cleaning_schedule = CleaningSchedule()

    # Commands
    telegram_app.add_handler(CommandHandler('start', start_command))
    telegram_app.add_handler(CommandHandler('delete_reminder', delete_reminder_command))
    telegram_app.add_handler(CommandHandler('show_mitbewohnies', show_mitbewohnies_command))
    telegram_app.add_handler(CommandHandler('show_reminder', show_reminder_command))

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
            SCHEDULING_JOB: [
                MessageHandler(filters.ALL, schedule_job)
            ],

        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
        per_chat=True, per_user=True,
    )


    telegram_app.add_handler(adding_conv_handler)
    telegram_app.add_handler(removing_conv_handler)
    telegram_app.add_handler(setting_reminder_conv_handler)

    # Errors
    telegram_app.add_error_handler(error)

    # Run the bot
    log("Polling..")
    #telegram_app.run_polling(3)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

