from datetime import datetime, timedelta

from .db import DBHandler, SessionDBHandler
from configs import settings
from utils import prettify_percent, get_default_rates, prettify_float
from utils.dt import (
    check_datetime_in_future, get_now, 
    adapt_datetime, convert_to_country_format
)
from . import exceptions




class UserBase(object):
    """
    User base class

    id:int: - user's id in Telegram
    is_pro:None or datetime.datetime: - has user bought the subscription
    is_active:bool: - if to send the notifications
    is_staff:bool: - is user staff
    rates:dict:
        iso_code:str: - currnies str:
            'check_times': list of times (IN USER'S UTCOFFSET)
            'percent_delta':float: not in percent format (not 23%, 0.23)
            'start_value':float: just normal
    timezone:int: - utcoffset ( in range (-11, 13) )
    language:str: - user's language
    """

    def __init__(self, user_data:dict):
        supported_fields = [
            'id', 'is_active', 'is_pro', 'is_staff',
            'to_notify_by_experts', 'rates', 'timezone', 'language'
        ]
        for k, v in user_data.items():
            if k in supported_fields:
                self.__dict__[k] = v
        if 'rates' in user_data:
            self.rates = self.normalize_rates(self.rates)

    @staticmethod
    def normalize_rates(rates:list):
        return {
            rate['iso']: { 
                'check_times': rate['check_times'],
                'percent_delta': rate['percent_delta'],
                'start_value': rate['start_value']
            }
            for rate in rates
        }

    @staticmethod
    def prettify_rates(rates: list):
        total_str = ''
        for idx, (k, v) in enumerate(rates.items(), start=1):
            total_str += "\t{}. {}:;\t\t▫ Процент - {};\t\t▫ Время проверки - {};".format(
                    idx, 
                    k, 
                    prettify_percent(v.get('percent_delta')), 
                    ', '.join(v.get('check_times'))
                ).replace(
                    '\t', 
                    '    '
                )
        return total_str

    def __iter__(self):
        # also implements list(User), because __iter__ is used by list()
        for i in [
                self.id, self.is_active, self.is_pro, self.is_staff,
                self.to_notify_by_experts, self.rates, self.timezone, self.language
                ]:
            yield i



class User(UserBase):
    db = DBHandler(settings.DB_NAME)

    def __init__(self, user_id:int):
        self.init_user(user_id)
        data = self.db.get_user(user_id)
        super().__init__(data)

    def update(self, **kwargs):
        self.db.change_user(self.id, **kwargs)
        for k, v in kwargs.items():
            if k in self.__dict__:
                self.__dict__[k] = v

    @classmethod
    def from_dict(cls, data:dict):
        bare_user = cls.__new__(cls)
        super(cls, bare_user).__init__(data)
        return bare_user

    def get_currencies_by_check_time(self, check_time:str):
        return {
            k: v for k, v in self.rates.items()
            if check_time in v.get('check_times')
        }

    @property
    def predictions(self):
        return list(self.get_predictions())

    def get_predictions(self, only_actual:bool=True):
        for pred_data in self.db.get_user_predictions(self.id, only_actual=only_actual):
            yield Prediction.from_dict(pred_data)

    def update_rates(self, iso, **kwargs):
        self.db.change_user_rate(self.id, iso, **kwargs)
        self.rates = self.normalize_rates(self.db.get_user_rates(self.id))

    def create_prediction(self, iso_from:str, iso_to:str, value:float, up_to_date:datetime):
        assert check_datetime_in_future(up_to_date)
        self.db.add_prediction(
            self.id, iso_from, iso_to, 
            value, up_to_date, is_by_experts=self.is_staff
        )

    def add_rate(self, iso: str, **kwargs):
        self.db.add_user_rate(self.id, iso, **kwargs)
        self.rates = self.normalize_rates(self.db.get_user_rates(self.id))
        return True

    def delete_rate(self, iso: str):
        assert iso not in settings.CURRENCIES, f"can't delete {iso}, since it is in default currencies"
        assert iso in self.rates, f"can't delete non-present currency {iso}"
        self.db.delete_user_rate(self.id, iso)
        del self.rates[iso]
        return True

    @classmethod
    def init_user(cls, user_id: int):
        if not cls.db.check_user_exists(user_id):
            # if user not exists, create user and all his rates
            cls.db.add_user(user_id)
            defaults = get_default_rates(*settings.CURRENCIES, to_print=False)
            for currency in settings.CURRENCIES:
                cls.db.add_user_rate(user_id, currency, start_value=defaults.get(currency)) 

    @classmethod
    def get_pro_users(cls, *args, **kwargs):
        for user_data in cls.db.get_pro_users(*args, **kwargs):
            yield cls.from_dict(user_data)

    @classmethod
    def get_all_users(cls, *args, **kwargs):
        for user_data in cls.db.get_all_users(*args, **kwargs):
            yield cls.from_dict(user_data)

    @classmethod
    def get_staff_users(cls, *args, **kwargs):
        for user_data in cls.db.get_staff_users(*args, **kwargs):
            yield cls.from_dict(user_data)

    @classmethod
    def get_users_by_check_time(cls, check_time):
        for user_data in cls.db.get_users_by_check_time(check_time):
            yield cls.from_dict(user_data)

    def init_premium(self, up_to_datetime:datetime):
        self.update(is_pro=up_to_datetime)
        for k, v in self.rates.items():
            self.update_rates(k, check_times=settings.CHECK_TIMES)

    def delete_premium(self):
        self.update(is_pro=0)
        try:
            Session.db.set_count(self.id, settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER)
        except exceptions.SessionDoesNotExistError:
            pass
        for k, v in self.rates.items():
            if k not in settings.CURRENCIES:
                self.delete_rate(k)
            else:
                self.update_rates(k, check_times=settings.DEFAULT_CHECK_TIMES)

    def init_staff(self):
        until_datetime = get_now() + timedelta(days=100*365)
        self.init_premium(until_datetime)
        self.update(is_staff=1)
        for prediction in self.get_predictions(True):
            prediction.update(is_by_experts=1)

    def delete_staff(self):
        self.delete_premium()
        self.update(is_staff=0)
        for prediction in self.get_predictions(True):
            prediction.update(is_by_experts=0)



class Prediction(object):
    db = DBHandler(settings.DB_NAME)

    def __init__(self, pred_id:int):
        for k, v in self.db.get_prediction(pred_id).items():
            self.__dict__[k] = v

    @classmethod
    def from_dict(cls, pred_data:dict):
        bare_pred = cls.__new__(cls)
        for k, v in pred_data.items():
            bare_pred.__dict__[k] = v
        return bare_pred

    def toggle_like(self, user_id:int, if_like:bool=True):
        """
        if_like:
            True - like prediction
            False - dislike prediction
            None - delete any reaction
        """
        self.db.toggle_prediction_reaction(self.id, user_id, if_like)

    def delete(self, *, force:bool=False):
        if not force:
            assert self.is_actual, "can't delete a past prediction"
        self.db.delete_prediction(self.id)

    def update(self, **kwargs):
        self.db.change_prediction(self.id, **kwargs)
        for k, v in kwargs.items():
            if k in self.__dict__:
                self.__dict__[k] = v

    def get_closest_neighbours(self):
        res = self.db.get_closest_prediction_neighbours(self.id)
        prev_id, next_id = res['previous'], res['next']
        return {
            'previous': Prediction(prev_id) if prev_id else None,
            'next': Prediction(next_id) if next_id else None
        }

    @property
    def is_actual(self):
        return check_datetime_in_future(self.up_to_date)

    @property
    def likes(self):
        return self.db.get_prediction_likes(self.id)

    @property
    def dislikes(self):
        return self.db.get_prediction_dislikes(self.id)

    @classmethod
    def get_experts_predictions(cls, *, only_actual:bool=False):
        for pred_data in cls.db.get_experts_predictions(only_actual=only_actual):
            yield cls.from_dict(pred_data)

    @classmethod
    def get_most_liked_predictions(cls, *args, **kwargs):
        for pred_data in cls.db.get_max_liked_predictions(*args, **kwargs):
            yield cls(pred_data[0])

    @classmethod
    def get_unverified_predictions(cls, *args, **kwargs):
        """
        Get predictions which `up_to_date` is expired and `real_value` is still None
        """
        for pred_data in cls.db.get_unverified_predictions(*args, **kwargs):
            yield cls.from_dict(pred_data)

    @classmethod
    def get_random_prediction(cls):
        pred_data = cls.db.get_random_prediction()
        return cls.from_dict(pred_data) if pred_data else None

    def repr(self, user:User):
        return f"{self.iso_from}-{self.iso_to}, {convert_to_country_format(adapt_datetime(self.up_to_date), user.language)}"

    def str(self, user:User):
        return '\n'.join(
            [
                "Prediction", f"Currencies: {self.iso_from}-{self.iso_to}", 
                f"Up to: {convert_to_country_format(adapt_datetime(self.up_to_date), user.language)}",
                f"Exchange Rate: {prettify_float(self.value)}"
            ] +
            ([f"Likes: {self.likes}", f"Dislikes: {self.dislikes}"] if not self.is_by_experts else [])
        )



class Session(object):
    db = SessionDBHandler(settings.DB_NAME)

    def __init__(self, user_id: int):
        self.user = User(user_id)
        self.db.add_session(user_id)

    @property
    def free_notifications_count(self):
        return self.db.fetch_count(self.user.user_id)

    def decrease_count(self):
        self.db.decrease_count(self.user.user_id)

    def set_count(self, count: int):
        self.db.set_count(self.user.user_id, count)
