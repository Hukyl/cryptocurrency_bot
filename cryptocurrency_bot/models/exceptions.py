class ExceptionWithCause(Exception):
    def __init__(self, message:str, *, cause:str=None):
        super().__init__(message)
        self.cause = cause    


class UserDoesNotExistError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class PredictionDoesNotExistError(Exception):
    pass


class RateDoesNotExistError(Exception):
    pass


class SessionDoesNotExistError(Exception):
    pass


class CurrencyDoesnotExistError(Exception):
    pass
