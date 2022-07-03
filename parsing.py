from typing import Callable
import sys
import argparse

from model import Meeting, Time, Config
import utils


readme = 'https://github.com/UmActually/Autopilot#autopilot'


parser = argparse.ArgumentParser(prog='autopilot')

parser.add_argument('time', nargs='?', default='auto',
                    help='the time of the meeting, H:MM or HH:MM format, defaults to your next class')

parser.add_argument('zoom', nargs='?', default='auto',
                    help='the ID or link of the meeting, defaults to your next class')

parser.add_argument('-c', '--config', '-s', '--settings', action='store_true',
                    help='change your autopilot settings or classes schedule')

parser.add_argument('-l', '--late', action='store_true',
                    help='join the closest present/past class of your schedule')

parser.add_argument('-r', '--recent', action='store_true',
                    help='join the most recent autpilot-launched meeting')

parser.add_argument('-t', '--test', action='store_true',
                    help='for testing, stops right before entering meeting')

parser.add_argument('-i', '--input', action='store_true',
                    help='ask for time and ID, rather than using arguments or next class')

parser.add_argument('-q', '--quiet', action='store_true',
                    help='print nothing to the console')

parser.add_argument('--version', action='version', version='%(prog)s 0.6.1')

args = parser.parse_args(sys.argv[1:])


def tries_twice(func: Callable) -> Callable:
    """If the positional arg parsing (time and meeting ID) doesn't work,
    try passing the arguments the other way around."""
    def wrapper(config: Config) -> Meeting:
        try:
            resp = func(args.time, args.zoom, config)
        except ValueError:
            try:
                resp = func(args.zoom, args.time, config)
            except ValueError:
                utils.raise_val_err(2)
        # noinspection PyUnboundLocalVariable
        return resp
    return wrapper


@tries_twice
def figure_out_meeting_info(raw_time: str, raw_zoom: str, config: Config) -> Meeting:
    """Get the meeting time and ID with whatever information is available."""
    if args.recent:
        try:
            meeting = Meeting.from_dict(utils.open_file('Resources/recent.json'))
            meeting.infer_wake()
            return meeting
        except KeyError:
            print('No recent meeting info was found.')
            exit()

    if args.input:
        time = Time.from_string(ask=True)
        zoom = Meeting.parse_id(ask=True)
        meeting = Meeting(time, zoom)
        meeting.infer_wake()
        return meeting

    if raw_time == 'auto' and raw_zoom == 'auto':
        meeting = Meeting.next()
        last = Meeting.last()

        if last is not None:
            dx = (utils.time() - last.time.as_dt_time(full=True)).seconds // 60
            if args.late or dx < config.threshold:
                return last
        elif args.late:
            if not args.quiet:
                print('According to the schedule, no classes have passed today.')
            exit()

        if meeting is not None:
            return meeting
        else:
            if not args.quiet:
                print('Your schedule is empty. Run "autopilot -c" to open settings '
                      'and edit your schedule. You can also pass meeting time & ID '
                      f'as arguments. Check the README for a full guide: {readme}')
            exit()

    if raw_time != 'auto' and raw_zoom != 'auto':
        time = Time.from_string(raw_time)
        zoom = Meeting.parse_id(raw_zoom)
        meeting = Meeting(time, zoom)
    else:
        time = Time.from_string(raw_time)
        zoom = Meeting.parse_id(raw_zoom)
        # if time is None:
        #     time = Time.from_string(ask=True)
        if zoom is None:
            zoom = Meeting.parse_id(ask=True)
        meeting = Meeting(time, zoom)

    meeting.infer_wake()
    return meeting
