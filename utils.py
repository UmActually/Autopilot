from typing import Any, Union, Optional, NoReturn, Tuple, List
from time import sleep
import sys
import subprocess
import datetime
import json
import re
import getpass

import pyautogui as pag


sources_path = f'/Users/{getpass.getuser()}/Library/com.UmActually.Autopilot/'
factor = 2


# GENERAL FUNCS


def run(executable: str, *args: str):
    """Run a command."""
    subprocess.run([executable, *args], text=True, stderr=subprocess.DEVNULL)


def sudo(executable: str, *args: str, password: str):
    """Run a command with sudo."""
    subprocess.run(['sudo', '-S', executable, *args], input=password, text=True, stderr=subprocess.DEVNULL)


def time() -> datetime.datetime:
    """Current date & time as datetime object."""
    return datetime.datetime.now()


def time_string() -> str:
    """Current time in string form."""
    return time().time().strftime("%H:%M:%S")


def open_file(path: str, write: Optional[Union[str, list, dict]] = None) -> Optional[Union[str, list, dict]]:
    """Read and write in file. If file is JSON, parse with the json module."""
    if not path.startswith('/'):
        path = sources_path + path
    is_json = path.endswith('.json')

    if write is not None:
        with open(path, 'w') as f:
            if is_json:
                json.dump(write, f)
            else:
                f.write(write)
        return

    with open(path) as f:
        if is_json:
            content = json.load(f)
        else:
            content = f.read()
    return content


def parse_id(zoom: str) -> int:
    """Parse meeting IDs, remove the link part."""
    zoom = zoom.strip(' \n').replace(' ', '')
    if zoom.startswith('https://') or 'zoom.us' in zoom:
        re_match = re.search(r'\d{5,}', zoom)
        if re_match is None:
            raise ValueError
        span = re_match.span()
        zoom = zoom[span[0]:span[1]]
    return int(zoom)


def raise_val_err(case: int) -> NoReturn:
    """When parsing input, raise a value error with some description."""
    if case == 0:
        err_msg = 'Error while parsing meeting time. Please check that it\'s correct.\n'
    elif case == 1:
        err_msg = 'Error while parsing meeting ID. Please check that it\'s correct.\n'
    else:
        err_msg = 'Error while parsing meeting time and/or ID. Please check that they\'re correct.\n'
    sys.stderr.write(err_msg)
    exit(1)


def distribute_list(any_list: list, n=3) -> List[list]:
    """Convert a list into a list of lists with n elements each."""
    resp = []
    acum = []
    k = 0
    for item in any_list:
        k += 1
        acum.append(item)
        if k == n:
            resp.append(acum)
            acum = []
            k = 0
    return resp


# PYAUTOGUI/AUTOMATION FUNCS


def open_app(name: str):
    """Open an app."""
    if '.app' in name:
        run('open', name)
        return
    run('open', f'/Applications/{name}.app')


def get_pos():
    """Print the mouse pos every two seconds."""
    while True:
        pos = pag.position()
        print(f'(x={pos[0]}, y={pos[1]})')
        sleep(2)


def get_rgb():
    """Print the mouse pos and underlying color every two seconds."""
    while True:
        pos = pag.position()
        print(pos + pag.pixel(pos[0] * factor, pos[1] * factor))
        sleep(2)


def color_match(x: int, y: int, r: int, g: int, b: int, tolerance=5) -> bool:
    """Check if pixel (x, y) currently has color values (r, g, b)."""
    return pag.pixelMatchesColor(x * factor, y * factor, (r, g, b), tolerance=tolerance)


def wait_until_color(
        x: int, y: int, r: int, g: int, b: int, interval=1, tolerance=5, timeout=0) -> bool:
    """Wait until the color match satisfies."""
    k = 0
    while not color_match(x, y, r, g, b, tolerance):
        k += 1
        sleep(interval)
        if timeout and k >= timeout:
            return False
    return True


def hotkey(*keys: str, wait=0.3):
    """Input a key combination in the keyboard."""
    for key in keys[:-1]:
        pag.keyDown(key)
    pag.press(keys[-1])
    for key in keys[1::-1]:
        pag.keyUp(key)
    sleep(wait)


def type_password(password: str):
    """Typing the password when waking the mac requires shift to be pressed
    whenever a character needs it. The shift-modified character cannot simply be passed
    to the PyAutoGUI typewrite function."""
    old_pause = pag.PAUSE
    pag.PAUSE = 0.5
    split_pass = []
    acum = ''
    caps = password[0].isupper()
    for char in password:
        if char.isupper() and not caps or char.islower() and caps:
            caps = not caps
            split_pass.append(acum)
            acum = char
        else:
            acum += char
    split_pass.append(acum)

    for part in split_pass:
        if part[0].isupper():
            pag.keyDown('shift')
            pag.typewrite(part.lower())
            pag.keyUp('shift')
        else:
            pag.typewrite(part.lower())
    pag.press('enter')
    pag.PAUSE = old_pause


def change_wake_time(new_time):
    """If the user disabled the ask password option, this is the
    alternative way to schedule a display wake (in System Preferences)."""
    open_app('/System/Applications/System Preferences.app')
    sleep(2)
    hotkey('command', 'f', wait=0.3)
    pag.typewrite('schedule st')
    sleep(0.5)
    pag.press('enter')
    sleep(1)
    pag.press('tab')
    sleep(1)
    pag.press('tab')
    hour, minute, pm = new_time.as_12_hour()
    pag.typewrite(str(hour))
    pag.press('tab')
    pag.typewrite(str(minute))
    pag.press('tab')
    pag.press('p' if pm else 'a')
    pag.press('enter')
    sleep(1)
    hotkey('command', 'q', wait=0.5)


# CONFIG TOOL FUNCS


def clear_term():
    """Clear terminal in a fancy way."""
    print('\033c', end='')


def pseudo_markdown(text: str) -> str:
    """Replace "markdown" chars in the program's text files."""
    return text.replace('<b>', '\033[1m').replace('</b>', '\033[0m')


def never_trust_user_input(
        text: str, limits: Tuple[int, int], *special: str, end='\n\n') -> Union[int, str]:
    """Ask for a choice out of a list of ints or "special" strs. Whenever an invalid input
    is given, the terminal is cleared and input is prompted again."""
    if limits[0] == limits[1]:
        prompt = f'Choice? ({limits[0]}'
    else:
        prompt = f'Choice? ({limits[0]}-{limits[1]}'
    if special:
        prompt += f' or {", ".join(special)}'
    prompt += ') '
    while True:
        clear_term()
        print(text, end=end)
        choice = input(prompt)
        if choice in special:
            return choice
        try:
            choice = int(choice)
            if limits[0] <= choice <= limits[1]:
                return choice
        except ValueError:
            pass


def sometimes_trust_user_input(
        text: str, prompt: str, cls: type, limits: Optional[Tuple[int, int]] = None,
        return_with_enter=False, count=0, end='\n\n') -> Any:
    """Ask for a value of a given type with given bounds/limits. Whenever an invalid
    input is given, the terminal is cleared and input is prompted again."""
    while True:
        clear_term()
        print(text, end=end)
        value = input(prompt + ' ')
        if return_with_enter and value == '':
            return

        # Strings are straightforward
        if cls is str:
            if value:
                return value
            continue

        # Parse input for bool type
        if cls is bool:
            value = value.lower()
            if value in ['on', 'true']:
                return True
            if value in ['off', 'false']:
                return False
            continue

        # Parse input for int type
        if cls is int:
            try:
                value = int(value)
            except ValueError:
                try:
                    value = parse_id(value)
                except ValueError:
                    continue
            if limits and (limits[0] <= value <= limits[1]) or not limits:
                return value
            continue

        # Parse input for list type (of ints)
        if cls is list:
            success = False
            for sep in [', ', ' ,', ',', ' ']:
                new = value.split(sep)
                try:
                    new = list(map(int, new))
                except ValueError:
                    continue
                if count and len(new) == count or not count:
                    success = True
                    break
            if not success:
                continue
            try:
                new = list(map(int, new))
            except ValueError:
                continue
            if limits and all([(limits[0] <= x <= limits[1]) for x in new]) or not limits:
                return new
            continue

        # Parse input for Time type
        try:
            value = cls.from_string(value)
            if value is not None:
                return value
        except ValueError:
            pass
