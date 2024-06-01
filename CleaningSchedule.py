from collections import deque
import json

from Utils import log, log_error


class CleaningSchedule:
    def __init__(self, filename="cleaning_schedule.json"):
        self.filename = filename
        self.names = self.load_names_from_schedule()
        self.weekday = self.load_detail_from_schedule('weekday')
        self.interval = self.load_detail_from_schedule('interval')
        self.hour = self.load_detail_from_schedule('hour')
        self.minute = self.load_detail_from_schedule('minute')


    def load_names_from_schedule(self):
        try:
            with open(self.filename, "r") as file:
                schedule = json.load(file)
                return deque(schedule["names"])
        except FileNotFoundError:
            return deque([])

    def load_detail_from_schedule(self, parameter_name):
        try:
            with open(self.filename, "r") as file:
                schedule = json.load(file)
                return schedule[parameter_name]
        except FileNotFoundError:
            return None

    def save_schedule(self, names=None, weekday=None, interval=None, hour=None, minute=None):
        if names:
            if isinstance(names, list):
                self.names.extend(names)
            else:
                self.names.append(names)
        if weekday:
            self.weekday = weekday
        if interval:
            self.interval = interval
        if hour:
            self.hour = hour
        if minute:
            self.minute = minute
        schedule = {
            "names": list(self.names),
            "weekday": self.weekday,
            "interval": self.interval,
            "hour": self.hour,
            "minute": self.minute
        }
        with open(self.filename, "w") as file:
            json.dump(schedule, file)

    def update_names(self, names):
        for name in names:
            try:
                self.names.remove(name)
                log(f"Removed {name} from the schedule.")
            except ValueError:
                log_error(f"{name} is not in the schedule.")

        with open(self.filename, "w") as file:
            json.dump(list(self.names), file)

    def get_next_person(self):
        next_person = self.names[0]
        self.names.rotate(-1)
        self.save_schedule()
        return next_person





