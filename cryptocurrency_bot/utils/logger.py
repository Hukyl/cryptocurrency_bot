import os
from datetime import datetime as dt

from termcolor import cprint


class Logger(object):
    MAX_SIZE = 100 * 1024  # bytes

    def __init__(self, *, using_files:bool=True):
        self.matching_colors = {
            'error': 'red', 'debug': 'green',
            'warning': 'yellow', 'info': 'cyan'
        }
        self.log_count = 0
        self.base_path = os.path.join('logs', dt.utcnow().strftime('%Y-%m-%d_%H-%M-%S'))
        os.makedirs(self.base_path, exist_ok=False)
        self.file = self.create_logfile()

    def create_logfile(self):
        self.log_count += 1
        return open(
            os.path.join(self.base_path, f"log{self.log_count}.txt"), 
            'w', encoding="utf-8"
        )

    @property
    def logfile_size_ok(self) -> bool:
        return os.path.getsize(self.file.name) < self.MAX_SIZE

    def log(self, message:str, /, *, kind:str) -> None:
        assert (color := self.matching_colors.get(kind.lower())) is not None, "unsupported message kind"
        message = f"[{dt.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] [{kind.upper()}] {message}"
        self.file.write(message + "\n")
        self.file.flush()
        cprint(message, color)
        if not self.logfile_size_ok:
            self.file = self.create_logfile()

    def catch_error(self, func):
        def inner(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
            except Exception as e:
                self.log(
                    f"Function {func.__name__} raised {e.__class__.__name__}:{str(e)}", 
                    kind='error'
                )
            else:
                return res
        return inner

    def __del__(self):
        self.file.close()
