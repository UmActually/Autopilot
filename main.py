if __name__ != '__main__':
    exit(1)

from time import sleep
import os
import getpass

import pyautogui as pag

from model import Config
import parsing
import utils


pag.PAUSE = 0.5
args = parsing.args
config = Config()


def _print(value):
    if not args.quiet:
        print(value)


if args.config:
    import configtool
    configtool.launch(config)
    exit()


meeting = parsing.figure_out_meeting_info(config)
test_mode = args.test or (meeting.name == 'Autopilot Test')


def wait_for_meeting():
    """Wait until the meeting time, and wake the computer.
    The display can be either asleep or awake during this function.
    This step is omitted if Autopilot is invoked in "right now" mode."""
    if config.ask_pass:
        utils.sudo('pmset', 'schedule', 'wake', meeting.wake, password=user_pass)
    else:
        utils.change_wake_time(meeting.time)
    _print((f'"{meeting.name}" found in schedule. ' * (meeting.name is not None))
           + f'Wake time: {meeting.wake}')

    _print(f'Autopilot ready. You can now put your mac to sleep. To cancel, use ctrl+C.')

    sooner = meeting.time.subtracting_minute()
    is_awake = True

    _print('Waiting for meeting...')

    while utils.time().hour != sooner.hour:
        sleep(config.interval)
    while utils.time().minute != sooner.minute:
        if utils.time().minute == meeting.time.minute:
            is_awake = False
            break
        sleep(config.interval)

    if is_awake:
        _print('One minute left...')
        utils.run('osascript', '-e',
                  'display notification "Zoom meeting is about to start." with title "Autopilot"')
        dx = meeting.time.as_dt_time(full=True) - utils.time()
        sleep(dx.seconds - 2)
        if config.ask_pass:
            utils.hotkey('command', 'ctrlleft', 'q')
        sleep(1)

    _print(f'Waking computer: {utils.time_string()}')
    utils.run('caffeinate', '-u', '-t', '1')
    if config.ask_pass:
        utils.run('osascript', '-e', 'tell application "System Events" to key code 124')
        utils.type_password(user_pass)
    sleep(2)


def enter_meeting():
    """Once everything's ready, open Zoom, enter the meeting.
    With the default config, join audio and go fullscreen."""
    utils.open_file('Resources/recent.json', meeting.as_dict())
    if meeting.is_right_now and meeting.name is not None:
        _print(f'Joining "{meeting.name}": {utils.time_string()}')
    else:
        _print(f'Opening zoom: {utils.time_string()}')

    utils.open_app('zoom.us')
    utils.wait_until_color(122, 276, 239, 124, 65, timeout=8)
    utils.hotkey('command', 'j', wait=0.5)
    pag.typewrite(str(meeting.zoom))
    sleep(0.3)

    if test_mode:
        _print('Program was run in test mode. Exiting...')
        exit()
    pag.press('enter')

    if config.video:
        while not (utils.color_match(1372, 872, 169, 53, 47) or utils.color_match(1421, 784, 169, 53, 47)):
            found = utils.wait_until_color(904, 671, 50, 112, 229, timeout=5)
            if found:
                pag.click(x=800, y=670)
                break

    sleep(3)

    is_fullscreen = utils.color_match(1372, 872, 169, 53, 47)
    if config.close_menu:
        utils.hotkey('command', '`')
        utils.hotkey('command', 'w')
        if is_fullscreen:
            utils.hotkey('command', '`')
    if config.fullscreen and not is_fullscreen:
        utils.hotkey('command', 'shift', 'f')


def notify_by_email():
    """This is not implemented yet."""
    import yagmail
    # noinspection PyUnboundLocalVariable
    with yagmail.SMTP(email, email_pass) as yag:
        # noinspection PyUnboundLocalVariable
        yag.send(dest, 'Ha Iniciado El Zoom', 'Atte. Autopilot')


try:
    dest, email, email_pass, user_pass = \
        utils.open_file(f'/Users/{getpass.getuser()}/.SuperSecretTokens/autopilot.txt').split('\n')
    authentic = True
except FileNotFoundError:
    if config.ask_pass and not meeting.is_right_now:
        user_pass = getpass.getpass()
    authentic = False


# Function execution


if not meeting.is_right_now:
    wait_for_meeting()

enter_meeting()

if authentic:
    notify_by_email()

if config.remove_ss:
    for file in os.listdir():
        if 'screenshot' in file:
            os.remove(file)


_print(f'Done! {utils.time_string()}\n')
