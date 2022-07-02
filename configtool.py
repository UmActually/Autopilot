from typing import Optional, Any, Tuple
import shutil

from model import Meeting, Time, Config
import utils


# TODO: system_profiler SPDisplaysDataType | grep Resolution
# Many global vars are kept to avoid passing stuff around.
main_menu = utils.pseudo_markdown(utils.open_file('Resources/configmenu.txt'))
details = utils.distribute_list(
    utils.pseudo_markdown(utils.open_file('Resources/configdetails.txt')).split('\n'))
sched = utils.pseudo_markdown(utils.open_file('Resources/schedulemenu.txt'))
sched_dtl = utils.pseudo_markdown(utils.open_file('Resources/scheddetail.txt'))

opt_limits = [(0, 59), (1, 59), (100, 10000), (0, 10000)]
tuples = [('name', str, 'Name?', None),
          ('days', list, 'Weekdays? (1-7, 1 is Monday, separate by spaces or commas)', (1, 7)),
          ('time', Time, 'Meeting time? (HH:MM, 24-hour)', None),
          ('zoom', int, 'Meeting ID? (Number or link)', None)]

config: Optional[Config] = None
schedule: Optional[list] = None
refresh = False
size = shutil.get_terminal_size()


def save_schedule():
    """Saves schedule to JSON and ensures view is refreshed."""
    global refresh
    refresh = True
    utils.open_file('Resources/schedule.json', schedule)


def read_easily(value: Any) -> Any:
    """Prettify bools and lists."""
    if isinstance(value, bool):
        return 'ON' if value else 'OFF'
    if isinstance(value, list):
        return tuple(value)
    return value


def meeting_view(meeting: Meeting, show_opts=True) -> str:
    """Builds the detailed view of a particular meeting."""
    return '\n' * (size.lines // 4) + sched_dtl.format(
        'New Meeting' if meeting.name is None else meeting.name,
        '...' if meeting.days is None else meeting.fmt_weekdays(),
        '...' if meeting.time is None else str(meeting.time),
        '...' if meeting.zoom is None else meeting.zoom) + \
        '[\033[1m0\033[0m] Go back, [\033[1m1\033[0m] Edit, [\033[1m2\033[0m] Delete' * show_opts


def schedule_view() -> Tuple[str, int]:
    """Builds the view of the schedule (meeting list)."""
    global schedule
    schedule = utils.open_file('Resources/schedule.json')
    sched_menu = sched
    k = -1
    for k, meeting in enumerate(schedule):
        sched_menu += f'\n[\033[1m{k + 1}\033[0m] {meeting["name"]}'
    sched_menu += '\n\n[\033[1m+\033[0m] Add class/meeting' \
                  '\n[\033[1m0\033[0m] Go back'
    return sched_menu, (k + 1)


def add_or_edit_meeting(index: Optional[int] = None, meeting: Optional[Meeting] = None) -> Meeting:
    """Prompts the attributes of a new or existing meeting."""
    editing = index is not None

    def p(text: str) -> str:
        if editing:
            text = 'Leave blank to keep current value.\n' + text
        return text

    if not editing:
        meeting = Meeting()

    for attr, cls, prompt, limits in tuples:
        value = utils.sometimes_trust_user_input(
            meeting_view(meeting, show_opts=False), p(prompt), cls, limits, return_with_enter=editing)
        if value is not None:
            setattr(meeting, attr, value)

    if editing:
        schedule[index] = meeting.as_dict()
    else:
        schedule.append(meeting.as_dict())

    save_schedule()
    return meeting


def edit_schedule():
    """Show the schedule list and prompt for an option."""
    sched_menu, count = schedule_view()
    global refresh
    refresh = False

    # Select a meeting
    while True:
        if refresh:
            refresh = False
            sched_menu, count = schedule_view()
        index = utils.never_trust_user_input(sched_menu, (0, count), '+')
        if index == 0:
            return
        if index == '+':
            index = len(schedule)
            meeting = add_or_edit_meeting()
        else:
            index -= 1
            meeting = Meeting.from_dict(schedule[index])
        view = meeting_view(meeting)

        # Edit/delete meeting
        while True:
            choice = utils.never_trust_user_input(view, (0, 2))
            if choice == 0:
                break
            if choice == 1:
                meeting = add_or_edit_meeting(index, meeting)
                view = meeting_view(meeting)
                continue
            if choice == 2:
                del schedule[index]
                save_schedule()
                break


def detail_view(index: int, limits: Optional[Tuple[int, int]] = None):
    """Show the details of an option and prompt to change its value."""
    option, value = list(config.dict.items())[index]
    title, desc, prompt = details[index]
    title = title.format(read_easily(value))

    new_value = utils.sometimes_trust_user_input(
        '\n' * (size.lines // 4) + '\n\n' + title + '\n\n' + desc,
        prompt, type(value), limits, True, 2)

    if new_value is not None:
        setattr(config, option, new_value)


def launch(_config: Config):
    """Show the option list and prompt for an option.
    This is the starting point of the config tool interface."""
    global config
    config = _config

    while True:
        values = map(read_easily, [v for v in config.dict.values()])
        fmt_menu = main_menu.format(*values)

        choice = utils.never_trust_user_input(fmt_menu, (0, 10))

        # Save and close
        if choice == 0:
            break

        # Edit schedule
        if choice == 1:
            edit_schedule()
            continue

        # Every other case
        limits = None
        if choice in [2, 3]:
            limits = opt_limits[choice - 2]
        if choice in [9, 10]:
            limits = opt_limits[choice - 7]
        detail_view(choice - 2, limits)
