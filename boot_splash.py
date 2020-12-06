from pyfiglet import figlet_format
from termcolor import cprint 


def print_title(text):
    cprint(figlet_format(text, font='starwars'), 
        'blue', 'on_white', attrs=['bold'])


def print_subtitle(text):
    print(figlet_format(text, font='digital'))


def print_logo(text):
    cprint(figlet_format('', font='starwars'),
        'yellow', 'on_red', attrs=['bold'])
