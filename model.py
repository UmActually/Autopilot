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
    _schedule = None

    def __init__(self, time: Optional[Time] = None, zoom: Optional[int] = None,
                 name: Optional[str] = None, days: Optional[List[int]] = None, on_sched=False):
        self.time = time
        self.zoom = zoom
        self.name = name
        self.days = days
        self.wake = None
        self.is_right_now = time is None
        self.is_on_sched = on_sched

    def infer_wake(self):
        """When meeting is given as an input rather than using the schedule, wake date is inferred to be
        the current or next day, depending on the meeting time. Otherwise, if a meeting is remembered using
        --recent flag, get the appropiate date as well."""
        if self.is_right_now:
            return
        date = utils.time()
        dx = datetime.timedelta(days=1)
        if self.is_on_sched:
            # Look for the next meeting with the same ID and assign its wake date.
            self.__class__.schedule_lookup(self)
        else:
            time = self.time.as_dt_time()
            if time <= date.time():
                date += dx
            self.wake = f'{date.month}/{date.day}/{date.year} ' \
                        f'{self.time}:00'

    def fmt_weekdays(self) -> str:
        names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        return ', '.join([names[d] for d in self.days])

    def as_dict(self) -> dict:
        time = None if self.time is None else [self.time.hour, self.time.minute]
        return dict(time=time, zoom=self.zoom, name=self.name, days=self.days, on_sched=self.is_on_sched)

    @classmethod
    def from_dict(cls, meeting: dict) -> Meeting:
        time = None if meeting['time'] is None else Time(*meeting['time'])
        return cls(time, meeting['zoom'], meeting['name'], meeting['days'], meeting['on_sched'])

    @classmethod
    def schedule(cls):
        if cls._schedule is None:
            cls._schedule = list(map(
                cls.from_dict, utils.open_file('Resources/schedule.json')))
        return cls._schedule

    @classmethod
    def schedule_of_day(cls, day: int, reverse=False) -> List[Meeting]:
        day_schedule = []
        for meeting in cls.schedule():
            if day in meeting.days:
                day_schedule.append(meeting)
        day_schedule.sort(key=lambda m: m.time.sorting_key(), reverse=reverse)
        return day_schedule

    @classmethod
    def schedule_lookup(
            cls, target_meet: Optional[Meeting] = None, reverse=False) -> Optional[Meeting]:
        """Skim through the schedule in order, starting from the present, until desired target(s) satisfied.
        If the target meeting is None, return whichever meeting is found first. If a target meeting is passed,
        the returned meeting must have the same zoom ID.

        When reverse is False, go forward in time. Only look for meetings with a time greater than the target time
        (future), in case of the starting day. After looking up in the current weekday, set the target time to zero
        to accept any meeting from the days after. The algorithm gives up once the seven weekdays are exhausted.

        When reverse is True, go backward in time. Only look for meetings of the same day with a time lower than the
        target time (past)."""
        look_for_meet = target_meet is not None
        date = utils.time()
        target_time = date.time()
        weekday = date.weekday() + 1

        for _ in range(7):
            day_sched = cls.schedule_of_day(weekday, reverse=reverse)

            for meeting in day_sched:
                # IF the meeting has a GREATER TIME (or rather LESSER if in reverse), AND
                # in case there is a MEETING target, ALSO MAKE SURE it is satisfied.
                if (meeting.time.as_dt_time() > target_time) != reverse and \
                        (meeting == target_meet or not look_for_meet):
                    if look_for_meet:
                        meeting = target_meet
                    if reverse:
                        meeting.is_right_now = True
                    else:
                        meeting.wake = f'{date.month}/{date.day}/{date.year} {meeting.time}:00'
                    return meeting

            if reverse:
                return  # Give up
            target_time = datetime.time()
            date += datetime.timedelta(days=1)
            weekday = (weekday % 7) + 1

    @classmethod
    def next(cls) -> Optional[Meeting]:
        return cls.schedule_lookup()

    @classmethod
    def last(cls) -> Optional[Meeting]:
        return cls.schedule_lookup(reverse=True)

    @staticmethod
    def parse_id(zoom='auto', ask=False) -> Optional[int]:
        if ask:
            zoom = input('Meeting ID? (Number or link) ')
        if zoom == 'auto':
            return
        return utils.parse_id(zoom)

    def __eq__(self, other):
        try:
            return self.zoom == other.zoom
        except AttributeError:
            return False

    def __repr__(self):
        return self.name
