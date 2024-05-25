from collections import deque
import json


class CleaningSchedule:
    def __init__(self, filename="cleaning_schedule.json"):
        self.filename = filename
        self.schedule = self.load_schedule()


    def load_schedule(self):
        try:
            with open(self.filename, "r") as file:
                schedule = json.load(file)
                return deque(schedule)
        except FileNotFoundError:
            return deque([])

    def save_schedule(self, names=None):
        if names:
            self.schedule.append(names)
        with open(self.filename, "w") as file:
            json.dump(list(self.schedule), file)

    def get_next_person(self):
        next_person = self.schedule[0]
        self.schedule.rotate(-1)
        self.save_schedule()
        return next_person





