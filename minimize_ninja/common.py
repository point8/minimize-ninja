import logging
import time
from rich.logging import RichHandler
from rich.console import Console


def configure_logger(verbosity, log_file=None):
    formatter = logging.Formatter('%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console = RichHandler(rich_tracebacks=True)
    console.setFormatter(formatter)
    if verbosity >= 1:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    logger = logging.getLogger('MinimizeNinjaLogger')
    logger.addHandler(console)
    if log_file is not None:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        if verbosity >= 1:
            fh.setLevel(logging.DEBUG)
        else:
            fh.setLevel(logging.INFO)
        logger.addHandler(fh)
    # logger.propagate = False
    if verbosity >= 1:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


def get_logger():
    logger_exists = 'MinimizeNinjaLogger' in logging.root.manager.loggerDict
    if not logger_exists:
        configure_logger(0)
    logger = logging.getLogger('MinimizeNinjaLogger')
    return logger


class Stopwatch(object):
    def __init__(self):
        self._time = time.time()
        self._lap = time.time()

    def reset(self):
        self._time = time.time()
        self._lap = time.time()

    def lap(self, message=None):
        elapsed = (time.time() - self._lap) * 1000.0
        if message is not None:
            print(f'Elapsed: {elapsed:.4f} ms [{message}]')
        else:
            print(f'Elapsed: {elapsed:.4f} ms')
        self._lap = time.time()


def read_config():
    logger = get_logger()

    # rcfile = os.path.expanduser('~/.misstiffyrc.yaml')
    resources = {}

    # if os.path.isfile(rcfile):
    #     with open(rcfile) as file:
    #         resources = yaml.safe_load(file)
    # else:
    #     logger.error('Cannot load settings from ~/.misstiffyrc.yaml. '
    #                  'Exiting.')
    #     raise FileNotFoundError('Cannot load settings from '
    #                             '~/.misstiffyrc.yaml. Exiting.')

    console = Console(record=True)
    resources['logger'] = logger
    resources['console'] = console

    return resources
