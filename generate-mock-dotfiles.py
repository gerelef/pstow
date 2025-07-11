#!/usr/bin/env python3
import os
import random
import string
from random import randint
from pathlib import Path

LOREM_IPSUM_TOKENS = [
    'pulvinar', 'a', 'eleifend', 'libero', 'elit', 'neque', 'ullamcorper', 'commodo', 'sodales', 'magna',
    'incididunt', 'at', 'risus', 'lectus', 'enim', 'ornare', 'eu', 'lorem', 'nec', 'tellus', 'mi', 'eiusmod',
    'nulla', 'maecenas', 'purus', 'congue', 'labore', 'pellentesque', 'aliqua', 'sollicitudin', 'ipsum', 'vel',
    'odio', 'tortor', 'malesuada', 'euismod', 'varius', 'leo', 'interdum', 'pharetra', 'urna', 'volutpat',
    'elementum', 'montes', 'cras', 'nullam', 'facilisi', 'platea', 'ultrices', 'auctor', 'augue', 'tempus',
    'posuere', 'eget', 'consectetur', 'convallis', 'tempor', 'magnis', 'venenatis', 'hac', 'pretium', 'feugiat',
    'proin', 'mattis', 'do', 'morbi', 'ac', 'netus', 'quam', 'nibh', 'non', 'porta', 'cursus', 'dolor', 'diam',
    'quisque', 'consequat', 'tincidunt', 'aliquam', 'nascetur', 'sit', 'dictumst', 'turpis', 'mollis', 'dolore',
    'fames', 'fermentum', 'parturient', 'viverra', 'in', 'phasellus', 'bibendum', 'etiam', 'rutrum', 'sagittis',
    'porttitor', 'id', 'nam', 'velit', 'dis', 'massa', 'sapien', 'egestas', 'sed', 'ligula', 'amet', 'habitasse',
    'scelerisque', 'aenean', 'nisl', 'quis', 'mauris', 'adipiscing', 'ut', 'nisi', 'accumsan', 'est', 'nunc',
    'semper', 'et', 'faucibus', 'orci', 'vitae', 'integer', 'condimentum'
]

UNIQUE_FILES = [
    ".has-run",
    "baraction.sh",
    "macho-gui.sh",
    "macho.sh",
    ".stowconfig",
    ".shell-requirements",
    ".gitconfig"
]

UNIQUE_SCRIPTS = [
    ".bashrc",
    ".vimrc",
    ".zshrc",
    ".nanorc",
    ".jwmrc",
]

COMMON_NAMES = [
    "README",
    "config",
]

COMMON_POSTFIXES = [
    "",
    ".sh",
    ".py",
    ".fish",
    ".yml",
    ".json",
    ".md",
    ".rc",
    ".conf",
    ".list",
    ".xml",
]

COMMON_CONFIG_DIRS = [
    "i3",
    "doom",
    "emacs",
    "bspwm",
    "berry",
    "awesome"
    "alacritty",
    "kitty",
    "modorganizer2",
    "pipewire",
    "lsd",
    "sublime-text",
    "vscode",
    "xmonad",
    "xmobar",
    "vifm",
    "tint2",
    "termite",
    "surf",
    "rofi",
    "qutebrowser",
    "qtile",
    "polybar",
    "picom",
    "openbox",
    "nvim",
    "nitrogen"
]


def generate_lorem_ipsum(count: int) -> str:
    txt = "Lorem"
    newline = False
    capitalize = False
    for i in range(count):
        next_token: str = " " + random.choice(LOREM_IPSUM_TOKENS)
        if capitalize:
            next_token = f".\n{random.choice(LOREM_IPSUM_TOKENS).title()}" if newline else f". {random.choice(LOREM_IPSUM_TOKENS).title()}"

        txt += next_token
        newline = bool(randint(1, 2) == 1)
        capitalize = bool(randint(1, 14) == 1)

    return txt + "."


def generate_random_name(name_pool: list[str] | None, postfix_pool: list[str] | None) -> str:
    name = "".join([c for c in random.choices(string.ascii_lowercase, k=randint(3, 7))])
    postfix = random.choice(postfix_pool) if postfix_pool else ""
    if name_pool and randint(1, 4) == 1:
        name = random.choice(name_pool)
    if randint(1, 3) == 1:
        postfix = ""
    return name + postfix


def generate_file_structure(parent: Path, num: int) -> None:
    if not parent.exists():
        parent.mkdir()

    for i in range(num):
        new_file = Path(str(parent.absolute()) + "/" + generate_random_name(COMMON_NAMES, COMMON_POSTFIXES))
        new_file.touch(exist_ok=True)
        with open(new_file, "w") as file:
            file.writelines(generate_lorem_ipsum(randint(30, 70)))
        print("Created " + str(new_file))


def generate_root(root: Path) -> None:
    if root.exists(follow_symlinks=False):
        print("Mock dotfiles exist, bailing for safety!")
        exit(0)
    root.mkdir(exist_ok=True)
    for unique_file in UNIQUE_FILES:
        file = Path(str(root.absolute()) + "/" + unique_file)
        file.touch(exist_ok=True)
        with open(file, "w") as f:
            f.writelines(generate_lorem_ipsum(randint(5, 150)))


def generate_dotconfig_dir(root: Path) -> Path:
    dotconfigs_dir = Path(str(root.absolute()) + "/.config")
    dotconfigs_dir.mkdir()
    for config_dir_name in COMMON_CONFIG_DIRS:
        common_config_dir = Path(str(dotconfigs_dir.absolute()) + "/" + config_dir_name)
        generate_file_structure(common_config_dir, randint(1, 4))

    return dotconfigs_dir


def generate_manpages_dir(root: Path) -> Path:
    dotmanpages_dir = Path(str(root.absolute()) + "/manpages")
    generate_file_structure(dotmanpages_dir, randint(1, 3))

    dotman1_dir = Path(str(dotmanpages_dir.absolute()) + "/man1")
    generate_file_structure(dotman1_dir, randint(15, 100))

    dotman7_dir = Path(str(dotmanpages_dir.absolute()) + "/man7")
    generate_file_structure(dotman7_dir, randint(30, 70))
    return dotmanpages_dir


def generate_dotgit_dir(root: Path) -> Path:
    dotgit_dir = Path(str(root.absolute()) + "/.git")
    generate_file_structure(dotgit_dir, randint(50, 200))
    for i in range(100):
        gen_dir = randint(1, 5) == 1
        if gen_dir:
            random_dotgit_subdir = Path(str(dotgit_dir.absolute()) + f"/{generate_random_name(None, None)}")
            generate_file_structure(random_dotgit_subdir, randint(40, 70))
    return dotgit_dir


def generate_scripts_dir(root: Path) -> Path:
    dotscripts_dir = Path(str(root.absolute()) + "/scripts")
    generate_file_structure(dotscripts_dir, randint(4, 34))
    for unique_file in UNIQUE_SCRIPTS:
        file = Path(str(dotscripts_dir.absolute()) + "/" + unique_file)
        file.touch(exist_ok=True)
    return dotscripts_dir


if __name__ == "__main__":
    root = Path(os.getcwd() + "/dotfiles")
    generate_root(root)
    generate_dotconfig_dir(root)
    generate_manpages_dir(root)
    generate_dotgit_dir(root)
    generate_scripts_dir(root)
