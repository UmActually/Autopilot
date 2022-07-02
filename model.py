from __future__ import annotations
from typing import Any, Optional, Union, Tuple, List
import datetime

import utils


class Config:
    """Config class that wraps the userconfig JSON."""
    def __init__(self):
        self.path = 'Resources/userconfig.json'
        self.dict = utils.open_file(self.path)

    def save(self):
        utils.open_file(self.path, self.dict)

    def __getattr__(self, item: str) -> Any:
        return self.dict[item]

    def __setattr__(self, key: str, value: Any):
        if key in ['path', 'dict']:
            object.__setattr__(self, key, value)
            return
        self.dict[key] = value
        self.save()


class Time:
    """A very barebones time class to store and parse meeting times."""
    def __init__(self, hour: int, minute: int):
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError
        self.hour = hour
        self.minute = minute

    def as_dt_time(self, full=False) -> Union[datetime.time, datetime.datetime]:
        resp = datetime.time(self.hour, self.minute)
        if full:
            resp = datetime.datetime.combine(datetime.date.today(), resp)
        return resp

    def as_12_hour(self) -> Tuple[int, int, bool]:
        is_pm = self.hour > 11
        hour = (self.hour - 1) % 12 + 1
        return hour, self.minute, is_pm

    def subtracting_minute(self) -> Time:
        if self.minute == 0:
            if self.hour == 0:
                return self.__class__(23, 59)
            return self.__class__(self.hour - 1, 59)
        return self.__class__(self.hour, self.minute - 1)

    def sorting_key(self) -> float:
        """Assigns a "non-discrete" value for the time
        to help sort the schedule."""
        return self.hour + self.minute / 60

    @classmethod
    def now(cls) -> Time:
        now = utils.time().time()
        return cls(now.hour, now.minute)

    @classmethod
    def from_string(cls, time='auto', ask=False) -> Optional[Time]:
        if ask:
            time = input('Meeting time? (HH:MM) ')
        if time == 'auto':
            return
        split = time.split(':')
        if len(split) != 2:
            raise ValueError
        return cls(int(split[0]), int(split[1]))

    def __repr__(self):
        return f'{self.hour}:{"0" * (self.minute < 10)}{self.minute}'


class Meeting:
    """This class represents a meeting. It also has functions to translate to and from dicts
    for storing in schedule.json, and to find the next meeting in the user's schedule."""
    schedule = None

    def __init__(self, time: Optional[Time] = None, zoom: Optional[int] = None,
                 name: Optional[str] = None, days: Optional[List[int]] = None):
        self.time = time
        self.zoom = zoom
        self.name = name
        self.days = days
        self.wake = None
        self.is_right_now = False

    def as_dict(self) -> dict:
        return {
            'name': self.name,
            'days': self.days,
            'time': [self.time.hour, self.time.minute],
            'zoom': self.zoom
        }

    def infer_wake(self):
        """When meeting is given as an input rather than using the schedule,
        wake date is inferred to be the current or next day, depending on the
        meeting time."""
        date = utils.time()
        dx = datetime.timedelta(days=1)
        time = self.time.as_dt_time()
        if time <= date.time():
            date += dx
        self.wake = f'{date.month}/{date.day}/{date.year} ' \
                    f'{self.time}:00'

    def fmt_weekdays(self) -> str:
        names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        return ', '.join([names[d] for d in self.days])

    @staticmethod
    def parse_id(zoom='auto', ask=False) -> Optional[int]:
        if ask:
            zoom = input('Meeting ID? (Number or link) ')
        if zoom == 'auto':
            return
        return utils.parse_id(zoom)

    @classmethod
    def from_dict(cls, meeting: dict) -> Meeting:
        return cls(Time(*meeting['time']),
                   meeting['zoom'],
                   meeting['name'],
                   meeting['days'])

    @classmethod
    def schedule_of_day(cls, day: int, reverse=False) -> List[Meeting]:
        if cls.schedule is None:
            cls.schedule = list(map(
                cls.from_dict, utils.open_file('Resources/schedule.json')))
        day_schedule = []
        for meeting in cls.schedule:
            if day in meeting.days:
                day_schedule.append(meeting)
        day_schedule.sort(key=lambda m: m.time.sorting_key(), reverse=reverse)
        return day_schedule

    @classmethod
    def next(cls) -> Optional[Meeting]:
        """Get the next meeting in the user's schedule."""
        result = None
        date = utils.time()
        time = date.time()
        weekday = date.weekday() + 1
        dx = datetime.timedelta(days=1)
        k = 0
        while result is None:
            schedule = cls.schedule_of_day(weekday)
            for meeting in schedule:
                if meeting.time.as_dt_time() > time:
                    result = meeting
                    break
            else:
                date += dx
                weekday = (weekday % 7) + 1
                time = datetime.time()
            k += 1
            if k > 6:
                return
        result.wake = f'{date.month}/{date.day}/{date.year} ' \
                      f'{result.time}:00'
        return result

    @classmethod
    def last(cls) -> Optional[Meeting]:
        result = None
        date = utils.time()
        time = date.time().replace(second=0, microsecond=0)
        weekday = date.weekday() + 1
        schedule = cls.schedule_of_day(weekday, reverse=True)
        for meeting in schedule:
            if meeting.time.as_dt_time() <= time:
                result = meeting
                result.is_right_now = True
                break
        return result

    def __repr__(self):
        return self.name
