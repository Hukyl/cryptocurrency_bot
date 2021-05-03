class UserDoesNotExistError(Exception):
    def __init__(self, message:str, *, cause:str=None):
        super().__init__(message)
        self.cause = cause


class UserAlreadyExistsError(Exception):
    def __init__(self, message:str, *, cause:str=None):
        super().__init__(message)
        self.cause = cause


class PredictionDoesNotExistError(Exception):
    def __init__(self, message:str, *, cause:str=None):
        super().__init__(message)
        self.cause = cause


class RateDoesNotExistError(Exception):
    def __init__(self, message:str, *, cause:str=None):
        super().__init__(message)
        self.cause = cause


class SessionDoesNotExistError(Exception):
    def __init__(self, message:str, *, cause:str=None):
        super().__init__(message)
        self.cause = cause
