#!/usr/bin/env python3
import logging


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


FAIL = bcolors.FAIL + bcolors.BOLD
ERROR = bcolors.FAIL
WARNING = bcolors.WARNING
INFO = bcolors.OKGREEN
DEBUG = bcolors.OKBLUE


def log(lvl, msg):
    return f"{lvl}{msg}{bcolors.ENDC}"


def fail(msg):
    logging.fatal(log(FAIL, msg))


def error(msg):
    logging.error(log(ERROR, msg))


def warn(msg):
    logging.warning(log(WARNING, msg))


def info(msg):
    logging.info(log(INFO, msg))


def debug(msg):
    logging.debug(log(DEBUG, msg))
