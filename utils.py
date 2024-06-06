import logging
import re
from typing import Text
from datetime import datetime, timedelta


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

    level=logging.INFO
)
logger = logging.getLogger(__name__)

def log(message: Text):
    logger.log(20, message)

def log_error(message: Text):
    logger.log(40, message)

# Helper functions
def parse_names(text: Text):
    return [name for name in text.split(", ") if name]

def convert_timer_settings(info) -> int:
    day = weekday_to_int(info[0].lower())
    interval, hour, minute = [extract_and_convert_to_int(info[i]) for i in range(1, 4)]
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

def validate_input(text: str):
    pattern = re.compile(
        r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*[0-9],\s*(0?[0-9]|1[0-9]|2[0-3]),\s*(0?[0-9]|[1-5][0-9])$', re.IGNORECASE)
    if pattern.match(text):
        return True
    return False

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


