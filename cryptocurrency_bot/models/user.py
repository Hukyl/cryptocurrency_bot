from datetime import datetime, timedelta

from .db import DBHandler, SessionDBHandler
from configs import settings
from utils import get_json_config, prettify_percent, get_default_rates, prettify_float
from utils.dt import (
    convert_to_country_format,
    convert_from_country_format,
    check_datetime_in_future,
    get_current_datetime,
    check_check_time_in_rate
)
from utils.translator import translate as _



class User(object):
    """
    User base class

    user_id:int: - user's id in Telegram
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

    def __init__(
            self, user_id:int, is_active:bool, is_pro, is_staff:bool, 
            rates:list, timezone:int, language:str
        ):
        self.user_id = user_id
        self.is_active = is_active
        self.is_pro = is_pro
        self.is_staff = is_staff
        self.rates = self.normalize_rates(rates)
        self.timezone = timezone
        self.language = language

    @staticmethod
    def normalize_rates(rates:list):
        return {
            rate[0]: {  # iso code
                'check_times': rate[-1],  # check_times
                'percent_delta': rate[2],  # percent_delta
                'start_value': rate[1]  # start_value
            }
            for rate in rates
        }

    @staticmethod
    def prettify_rates(rates:list):
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
                self.user_id, self.is_active, self.is_pro, 
                self.is_staff, self.rates, self.timezone, self.language
            ]:
            yield i



class DBUser(User):
    db = DBHandler(settings.DB_NAME)

    def __init__(self, user_id):
        self.init_user(user_id)
        data = self.db.get_user(user_id)
        super().__init__(*data)

    def update(self, **kwargs):
        self.db.change_user(self.user_id, **kwargs)
        for k, v in kwargs.items():
            if k in self.__dict__:
                self.__dict__[k] = v

    def get_currencies_by_check_time(self, check_time:str):
        return {
            k: v 
            for k, v in self.rates.items() 
            if check_check_time_in_rate(v.get('check_times'), check_time, self.timezone)
        }

    @property
    def predictions(self):
        return list(self.get_predictions())

    def get_predictions(self, only_actual:bool=True):
        for pred_data in self.db.get_user_predictions(self.user_id, only_actual):
            yield DBPrediction(pred_data[0])

    def update_rates(self, iso, **kwargs):
        self.db.change_user_rate(self.user_id, iso, **kwargs)
        self.rates = self.normalize_rates(self.db.get_user_rates(self.user_id))

    def create_prediction(self, iso_from:str, iso_to:str, value:float, up_to_date:datetime):
        assert check_datetime_in_future(up_to_date)
        self.db.add_prediction(
            self.user_id, iso_from, iso_to, 
            value, up_to_date, is_by_experts=self.is_staff
        )

    def add_rate(self, iso, **kwargs):
        self.db.add_user_rate(self.user_id, iso, **kwargs)
        self.rates = self.normalize_rates(self.db.get_user_rates(self.user_id))
        return True

    def delete_rate(self, iso):
        assert iso not in settings.CURRENCIES, f"can't delete {iso}, since it is in default currencies"
        assert iso in self.rates, f"can't delete non-present currency {iso}"
        self.db.delete_user_rate(self.user_id, iso)
        del self.rates[iso]
        return True

    @classmethod
    def init_user(cls, user_id):
        if not cls.db.check_user_exists(user_id):
            # if user not exists, create user and all his rates
            cls.db.add_user(user_id)
            defaults = get_default_rates(*settings.CURRENCIES, to_print=False)
            for currency in settings.CURRENCIES:
                cls.db.add_user_rate(user_id, currency, start_value=defaults.get(currency)) 

    @classmethod
    def get_pro_users(cls):
        for user_data in cls.db.get_pro_users():
            yield cls(user_data[0])

    @classmethod
    def get_all_users(cls):
        for user_data in cls.db.get_all_users():
            yield cls(user_data[0])

    @classmethod
    def get_staff_users(cls):
        for user_data in cls.db.get_staff_users():
            yield cls(user_data[0])

    @classmethod
    def get_users_by_check_time(cls, check_time):
        for user_data in cls.db.get_users_by_check_time(check_time):
            yield cls(user_data[0])

    def init_premium(self, up_to_datetime:datetime):
        self.update(is_pro=up_to_datetime)
        self.db.change_user(self.user_id, is_pro=up_to_datetime)
        for k, v in self.rates.items():
            self.update_rates(k, check_times=settings.CHECK_TIMES)

    def delete_premium(self):
        self.update(is_pro=0)
        for k, v in self.rates.items():
            if k not in settings.CURRENCIES:
                self.delete_rate(k)
            else:
                self.update_rates(k, check_times=settings.DEFAULT_CHECK_TIMES)

    def init_staff(self):
        until_datetime = get_current_datetime(utcoffset=self.timezone) + timedelta(days=100*365)
        self.init_premium(until_datetime)
        self.update(is_staff=1)
        for prediction in self.get_predictions(True):
            prediction.update(is_by_experts=1)

    def delete_staff(self):
        self.delete_premium()
        self.update(is_staff=0)
        for prediction in self.get_predictions(True):
            prediction.update(is_by_experts=0)



class DBPrediction(object):
    db = DBHandler(settings.DB_NAME)

    def __init__(self, pred_id):
        (
            self.id, self.user_id, self.iso_from, self.iso_to, self.value, 
            self.up_to_date, self.is_by_experts, self.real_value
        ) = self.db.get_prediction(pred_id)

    def toggle_like(self, user_id, if_like=True):
        """
        if_like:
            True - like prediction
            False - dislike prediction
            None - delete any reaction
        """
        self.db.toggle_prediction_reaction(self.id, user_id, if_like)

    def delete(self, force:bool=False):
        if not force:
            assert self.is_actual, "can't delete a past prediction"
        self.db.delete_prediction(self.id)

    def update(self, **kwargs):
        self.db.change_prediction(self.id, **kwargs)
        for k, v in kwargs.items():
            if k in self.__dict__:
                self.__dict__[k] = v

    def get_closest_neighbours(self):
        res = self.db.get_closest_neighbours_of_prediction(self.id)
        prev_id, next_id = res['previous'], res['next']
        return {
            'previous': DBPrediction(prev_id) if prev_id else None,
            'next': DBPrediction(next_id) if next_id else None
        }

    @property
    def is_actual(self):
        return check_datetime_in_future(self.up_to_date)

    @property
    def likes(self):
        return self.db.get_number_likes(self.id)

    @property
    def dislikes(self):
        return self.db.get_number_dislikes(self.id)

    @classmethod
    def get_experts_predictions(cls, only_actual:bool=False):
        for pred_data in cls.db.get_experts_predictions(only_actual):
            yield cls(pred_data[0]) # id

    @classmethod
    def get_most_liked_predictions(cls):
        for pred_data in cls.db.get_max_liked_predictions():
            yield cls(pred_data[0])

    @classmethod
    def get_unverified_predictions(cls):
        """
        Get predictions which `up_to_date` is expired and `real_value` is still None
        """
        for pred_data in cls.db.get_unverified_predictions():
            yield cls(pred_data[0]) # id

    @classmethod
    def get_random_prediction(cls):
        pred_data = cls.db.get_random_prediction()
        return cls(pred_data[0]) if (
            isinstance(pred_data, list) or isinstance(pred_data, tuple)
        ) else None

    def __repr__(self):
        return f"{self.iso_from}-{self.iso_to}, {self.up_to_date}"

    def __str__(self):
        return '\n'.join(
            [
                "Prediction", f"Currencies: {self.iso_from}-{self.iso_to}", 
                f"Up to: {self.up_to_date}", f"Exchange Rate: {prettify_float(self.value)}"
            ] +
            ([f"Likes: {self.likes}", f"Dislikes: {self.dislikes}"] if not self.is_by_experts else [])
        )



class DBSession(object):
    db = SessionDBHandler(settings.DB_NAME)

    def __init__(self, user_id):
        self.user = DBUser(user_id)
        self.db.add_session(user_id)

    @property
    def free_notifications_count(self):
        return self.db.fetch_count(self.user.user_id)

    def decrease_count(self):
        self.db.decrease_count(self.user.user_id)



if __name__ == '__main__':
    pass
