import os
from datetime import datetime as dt

from termcolor import cprint


ERROR = FATAL = 'error'
INFO = 'info'
DEBUG = 'debug'
WARNING = WARN = 'warning'



class Logger(object):
    MAX_SIZE = 100 * 1024  # bytes
    LOG_LEVELS = {
        'error': {'color': 'red', 'level': 40},
        'warning': {'color': 'yellow', 'level': 30},
        'info': {'color': 'cyan', 'level': 20},
        'debug': {'color': 'green', 'level': 10}
    }

    def __init__(self, *, using_files:bool=True):
        self.log_count = 0
        self.base_path = os.path.join(
            'logs', dt.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
        )
        self.log_level = 'info'
        os.makedirs(self.base_path, exist_ok=False)
        self.file = self.create_logfile()

    def create_logfile(self):
        """
        Create a log file, increase `log_count` and return it

        Return:
            file(_io.TextIOWrapper): open(
                base_path + 'log' + count, mode='w', encoding='utf-8'
            )
        
        """
        self.log_count += 1
        return open(
            os.path.join(self.base_path, f"log{self.log_count}.txt"), 
            'w', encoding="utf-8"
        )

    @property
    def logfile_size_ok(self) -> bool:
        return os.path.getsize(self.file.name) < self.MAX_SIZE

    def log(self, message:str, /, *, kind:str) -> None:
        """
        Log message to console and to file

        Positional parameters:
            message(str): what message will be logged
        Keyword parameters:
            kind(str): what type of log will be used
        Raises:
            AssertionError: if `kind` not in Logger.LOG_LEVELS
        Return: None
        """
        assert (
            info := self.LOG_LEVELS.get(kind.lower())
        ) is not None, "unsupported message kind"
        if self.LOG_LEVELS[self.log_level]['level'] <= info['level']:
            message = (
                f"[{dt.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"[{kind.upper()}] {message}"
            )
            self.file.write(message + "\n")
            self.file.flush()
            cprint(message, info['color'])
            if not self.logfile_size_ok:
                self.file = self.create_logfile()

    def error(self, message:str, /) -> None:
        return self.log(message, kind="error")

    def warning(self, message:str, /) -> None:
        return self.log(message, kind="warning")

    def info(self, message:str, /) -> None:
        return self.log(message, kind="info")

    def debug(self, message:str, /) -> None:
        return self.log(message, kind="debug")

    def set_level(self, level:str, /) -> None:
        """
        Set some min level of logs
        Any lower-level logs will be discarded
        (e.g. if level == 'info', 'debug' will not be shown)

        Positional parameters:
            level(str): level of logging
        Raises:
            AssertionError: if level not in Logger.LOG_LEVELS
        """
        assert level in self.LOG_LEVELS, 'unsupported logging level'
        self.log_level = level

    def catch_error(self, f):
        """
        Log errors if function raises any
        type: instancemethod, decorator
        """
        def inner(*args, **kwargs):
            try:
                res = f(*args, **kwargs)
            except Exception as e:
                self.error(
                    f"Function {f.__name__} raised {e.__class__.__name__}:{e}"
                )
            else:
                return res
        return inner

    def __del__(self):
        self.file.close()
