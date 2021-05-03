import abc
import sqlite3
from datetime import datetime
import threading

from configs import settings

from utils.dt import check_datetime_in_future
from utils.decorators import private, rangetest
from . import exceptions


LOCK = threading.Lock()


sqlite3.register_adapter(datetime, lambda x: x.strftime('%Y-%m-%d %H:%M:%S').encode('ascii'))
sqlite3.register_converter(
    "datetime", 
    lambda x: datetime.strptime(x.decode("ascii"), '%Y-%m-%d %H:%M:%S') if x.decode("ascii") != '0' else False
)
sqlite3.register_adapter(list, lambda x: ','.join(x).encode('ascii'))
sqlite3.register_converter("list", lambda x: [el.decode('ascii') for el in x.split(b",")])


class DBHandlerBase(abc.ABC):
    def __init__(self, db_name:str=None):
        self.DB_NAME = db_name or settings.DB_NAME
        self.setup_db()

    @staticmethod
    def dict_factory(cursor, row):
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    @abc.abstractmethod
    def setup_db(self):
        pass

    def execute(self, sql, params=tuple()):
        with LOCK:
            with sqlite3.connect(self.DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                conn.row_factory = self.dict_factory
                return conn.execute(sql, params).fetchall()


@private(['get', 'set'], 'execute')
class DBHandler(DBHandlerBase):
    """
    DB Format:

    users:
        id: user's id in Telegram
        is_pro: is user subscribed
        is_staff: is user staff
        timezone: offset from UTC (+3, -2)
        language: language

    user_rates: notifying user if currency rate changed by some percent
        user_id: user's id in Telegram
        iso: currency's iso-code
        start_value: A value from which to calculate difference
        percent_delta: A percent delta at which to notify
        check_times: Times at which to check (in user's time zone)
        !!! Checking of rate is by `iso`-USD rate !!!

    currency_predictions: predict rate at some date
        id: just an id
        user_id: user's id in Telegram who made the prediction
        iso_from: currency's iso for convertation
        iso_to: currency's iso for convertation
        value: convertation rate (1 `iso_from` - `value` `iso_to`)
        up_to_date: datetime, at which predict the exchange rate
        is_by_experts: is user, who made the prediction, has `is_staff` status
        real_value: value, which really was on `up_to_date`

    predictions_reactions:
        pred_id: id of prediction
        user_id: user's Telegram ID, who made reaction
        reaction: like/dislike (1/0 respectively)
    """

    def setup_db(self):
        self.execute(
            '''CREATE TABLE IF NOT EXISTS users( 
                    id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 0,
                    is_pro DATETIME DEFAULT FALSE, 
                    is_staff BOOLEAN DEFAULT 0,
                    to_notify_by_experts BOOLEAN DEFAULT 1,
                    timezone TINYINT DEFAULT 0 CHECK (
                        timezone in (
                            -11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 
                            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
                        )
                    ),
                    language VARCHAR(2) DEFAULT "en" CHECK (LENGTH(language) IN (2, 3)), 
                    UNIQUE(id) ON CONFLICT REPLACE
                )
            '''
        )
        self.execute(
            '''CREATE TABLE IF NOT EXISTS users_rates( 
                    user_id INTEGER NOT NULL,
                    iso VARCHAR(5),
                    start_value DOUBLE DEFAULT 0,
                    percent_delta REAL DEFAULT 1,
                    check_times LIST,
                    UNIQUE(user_id, iso) ON CONFLICT REPLACE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            '''
        )
        self.execute(
            '''CREATE TABLE IF NOT EXISTS currency_predictions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    user_id INTEGER,
                    iso_from VARCHAR(5),
                    iso_to VARCHAR(5),
                    value DOUBLE,
                    up_to_date DATETIME,
                    is_by_experts BOOLEAN DEFAULT FALSE,
                    real_value DOUBLE DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
            )
            '''
        )
        self.execute(
            '''CREATE TABLE IF NOT EXISTS predictions_reactions(
                pred_id INTEGER,
                user_id INTEGER,
                reaction BOOLEAN,
                FOREIGN KEY (pred_id) REFERENCES currency_predictions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )

    def add_user(
            self, user_id:int, is_active: bool=True, is_pro=False,
            is_staff:bool=False, to_notify_by_experts:bool=True, timezone:int=0, language:str='en'
    ):
        self.execute(
            "INSERT INTO users\
            (id, is_active, is_pro, is_staff, to_notify_by_experts, timezone, language) \
            VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, is_active, is_pro, is_staff, to_notify_by_experts, timezone, language)
        )
        return True

    @rangetest(start_value=(0, float('inf')))
    def add_user_rate(
            self, user_id:int, iso:str, start_value:float=1,
            percent_delta:float=0.01, check_times:list=settings.DEFAULT_CHECK_TIMES
    ):
        if self.check_user_exists(user_id):
            self.execute(
                "INSERT INTO users_rates VALUES (?, ?, ?, ?, ?)",
                (user_id, iso, start_value, percent_delta, check_times)
            )
            return True
        raise exceptions.UserDoesNotExistError(f"user id {user_id} does not exist", cause='id')

    @rangetest(value=(0, float("inf")))
    def add_prediction(
            self, user_id:int, iso_from:str, iso_to:str,
            value:float, up_to_date:datetime, is_by_experts:bool=False
    ):
        """
        Add a prediction if user with `user_id` exists
        Returns True if succeeded else None
        """
        if self.check_user_exists(user_id):
            assert check_datetime_in_future(
                up_to_date
            ), 'can\'t create prediction with past `up_to_date`'
            self.execute(
                "INSERT INTO currency_predictions \
                (user_id, iso_from, iso_to, value, up_to_date, is_by_experts) \
                VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, iso_from, iso_to, value, up_to_date, is_by_experts)
            )
            return True
        raise exceptions.UserDoesNotExistError(f"user id {user_id} does not exist", cause='id')

    def check_user_exists(self, user_id: int):
        return len(self.execute('SELECT id FROM users WHERE id = ?', (user_id,))) > 0

    def check_prediction_exists(self, pred_id: int):
        return len(self.execute(
            'SELECT id FROM currency_predictions WHERE id = ?', (pred_id,)
        )) > 0

    def get_users_by_check_time(self, check_time:str):
        """
        Get all users, which check times, converted from their timezone to UTC,
        equals to `check_time` (which is in UTC)
        """
        return [
            self.get_user(user_id['id'])
            for user_id in self.execute('SELECT DISTINCT id FROM users WHERE is_active = 1')
            if any(check_time in rate['check_times'] for rate in self.get_user_rates(user_id['id']))
        ]

    def get_user(self, user_id:int):
        """
        Get all user data (except the predictions) by its id
        Returns None if user with this id does not exist
        otherwise returns list(user_id, is_active, is_pro, is_staff, rates, timezone, language)
        """
        if self.check_user_exists(user_id):
            return {
                **self.execute('SELECT * FROM users WHERE id = ?', (user_id,))[0],
                **{'rates': self.get_user_rates(user_id)}
            }
        raise exceptions.UserDoesNotExistError(f"user id {user_id} does not exist", cause='id')

    def get_all_users(self, *, if_all:bool=True):
        filter_sql = 'WHERE is_staff != 1' if not if_all else ''
        return [
            self.get_user(user_data['id'])
            for user_data in self.execute('SELECT id FROM users %s' % filter_sql)
        ]

    def get_staff_users(self):
        """
        Get all users with is_staff status
        """
        return [
            self.get_user(user_data['id'])
            for user_data in self.execute(
                'SELECT id FROM users WHERE is_staff = 1'
            )
        ]

    def get_active_users(self):
        """
        Get all active users
        """
        return [
            self.get_user(user_data['id'])
            for user_data in self.execute(
                'SELECT id FROM users WHERE is_active = TRUE'
            )
        ]

    def get_pro_users(self):
        """
        Get all users who are pro and active
        """
        return [
            self.get_user(user_data['id'])
            for user_data in self.execute(
                'SELECT id FROM users WHERE is_active = TRUE and is_pro != FALSE'
            )
        ]

    def get_user_rates(self, user_id:int):
        """
        Get users rates
        Returns list of tuples (iso, start_value, percent_delta, check_times) 
        If no rates found, returns empty list
        """
        if self.check_user_exists(user_id):
            return self.execute(
                'SELECT \
                u_r.iso, u_r.start_value, u_r.percent_delta, u_r.check_times \
                FROM users u JOIN users_rates u_r \
                ON u.id = u_r.user_id AND u.id = ?',
                (user_id,)
            )
        raise exceptions.UserDoesNotExistError(f"user id {user_id} does not exist", cause='id')

    def get_prediction(self, pred_id:int):
        """
        Get prediction by its id
        Returns None if prediction with this id does not exist
        otherwise returns list(
            id, user_id, iso_from, iso_to, 
            value, up_to_date, is_by_experts, real_value
        )
        """
        if self.check_prediction_exists(pred_id):
            return self.execute(
                'SELECT id, user_id, iso_from, iso_to, value, up_to_date, is_by_experts, real_value \
                FROM currency_predictions WHERE id = ?',
                (pred_id,)
            )[0]
        raise exceptions.PredictionDoesNotExistError(f"prediction id {pred_id} does not exist", cause='id')

    def get_actual_predictions(self):
        return self.execute(
            'SELECT * FROM currency_predictions \
            WHERE datetime() < datetime(up_to_date) \
            ORDER BY up_to_date ASC'
        )

    def get_user_predictions(self, user_id:int, *, only_actual:bool=False):
        check_datetime_str = 'datetime() < datetime(up_to_date) and ' if only_actual else ''
        return self.execute(
            'SELECT * FROM currency_predictions \
            WHERE %s user_id = ? ORDER BY up_to_date ASC' % check_datetime_str,
            (user_id,)
        )

    def get_random_prediction(self):
        res = self.execute(
            'SELECT * FROM currency_predictions \
            WHERE is_by_experts = FALSE ORDER BY RANDOM() LIMIT 1'
        )
        return res[0] if res else -1

    def get_closest_prediction_neighbours(self, pred_id:int):
        """
        Returns previous and next prediction of prediction by `pred_id`
        :return: dict(previous=X, current=pred_id, next=Y)
        """

        def get_next():
            res = self.execute(
                # used `LIMIT` and `id > ?` because selection by certain id can cause errors
                "SELECT id FROM currency_predictions \
                WHERE id > ? AND is_by_experts = FALSE and datetime(up_to_date) > datetime() \
                ORDER BY id ASC LIMIT 1",
                (pred_id,)
            )
            return res[0] if res else None

        def get_previous():
            res = self.execute(
                # used `LIMIT` and `id < ?` because selection by certain id can cause errors
                "SELECT * FROM currency_predictions \
                WHERE id < ? AND is_by_experts = FALSE and datetime(up_to_date) > datetime() \
                ORDER BY id DESC LIMIT 1",
                (pred_id,)
            )
            return res[0] if res else None

        if self.check_prediction_exists(pred_id):
            return {
                'previous': prev['id'] if (prev := get_previous()) else None,
                'current': pred_id,
                'next': next['id'] if (next := get_next()) else None
            }
        raise exceptions.PredictionDoesNotExistError(f"prediction id {pred_id} does not exist", cause='id')

    def get_experts_predictions(self, only_actual: bool = False):
        check_datetime_str = 'datetime() < datetime(up_to_date) and ' if only_actual else ''
        return self.execute(
            'SELECT * FROM currency_predictions \
            WHERE %s is_by_experts = TRUE \
            ORDER BY up_to_date DESC' % check_datetime_str
        )

    def get_unverified_predictions(self):
        return self.execute(
            'SELECT * FROM currency_predictions \
            WHERE datetime() > datetime(up_to_date) AND real_value is NULL'
        )

    def change_user(self, user_id:int, **kwargs):
        if self.check_user_exists(user_id):
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE users SET %s = ? WHERE id = ?' % k,
                        (v, user_id)
                    )
            except sqlite3.OperationalError:
                raise ValueError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True
        raise exceptions.UserDoesNotExistError(f"user id {user_id} does not exist", cause='id')

    @rangetest(start_value=(0, float("inf")))
    def change_user_rate(self, user_id:int, iso:str, **kwargs):
        if self.check_user_exists(user_id):
            for k, v in kwargs.items():
                try:
                    self.execute(
                        'UPDATE users_rates SET %s = ? WHERE user_id = ? and iso = ?' % k,
                        (v, user_id, iso)
                    )
                except sqlite3.OperationalError:
                    raise ValueError(f'invalid argument {repr(k)}') from None
                except sqlite3.IntegrityError:
                    raise ValueError(f"invalid value {repr(v)}") from None
            return True
        raise exceptions.UserDoesNotExistError(f"user id {user_id} does not exist", cause='id')

    def delete_user_rate(self, user_id:int, iso:str):
        self.execute(
            'DELETE FROM users_rates WHERE user_id = ? AND iso = ?',
            (user_id, iso)
        )
        return True

    @rangetest(value=(0, float("inf")), real_value=(0, float("inf")))
    def change_prediction(self, pred_id:int, **kwargs):
        if self.check_prediction_exists(pred_id):
            # validation of parameters
            assert all(
                [x not in kwargs for x in ['iso_to', 'iso_from', 'user_id', 'pred_id']]
            ), 'unsupported arguments'
            if kwargs.get('up_to_date') is not None:
                assert check_datetime_in_future(
                    kwargs['up_to_date']
                ), 'can\'t change `up_to_date` to past datetime'
            # end of validation
            try:
                for k, v in kwargs.items():
                    self.execute(
                        'UPDATE currency_predictions SET %s = ? WHERE id = ? ' % k,
                        (v, pred_id,)
                    )
            except sqlite3.OperationalError:
                raise ValueError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            return True
        raise exceptions.PredictionDoesNotExistError(f"prediction id {pred_id} does not exist", cause='id')

    def delete_prediction(self, pred_id:int):
        self.execute(
            'DELETE FROM currency_predictions WHERE id = ?',
            (pred_id,)
        )
        return True

    def toggle_prediction_reaction(self, pred_id:int, user_id:int, if_like:bool=True):
        """
        if_like:
            True - like prediction
            False - dislike prediction
            None - delete any reaction
        """
        if not self.check_prediction_exists(pred_id):
            raise exceptions.PredictionDoesNotExistError(f"prediction id {pred_id} does not exist", cause='id')
        if not self.check_user_exists(user_id):
            raise exceptions.UserDoesNotExistError(f"user id {user_id} does not exist", cause='id')
        self.execute(
            'DELETE FROM predictions_reactions WHERE pred_id = ? and user_id = ?',
            (pred_id, user_id)
        )
        if if_like is not None:
            self.execute(
                'INSERT INTO predictions_reactions VALUES (?, ?, ?)',
                (pred_id, user_id, if_like)
            )
        return True

    def get_prediction_likes(self, pred_id:int):
        if self.check_prediction_exists(pred_id):
            return self.execute(
                ''' 
                    SELECT COUNT(reaction) as num
                    FROM predictions_reactions 
                    where pred_id = ? AND reaction = 1
                ''',
                (pred_id,)
            )[0]['num']
        raise exceptions.PredictionDoesNotExistError(f"prediction id {pred_id} does not exist", cause='id')

    def get_prediction_dislikes(self, pred_id:int):
        if self.check_prediction_exists(pred_id):
            return self.execute(
                ''' 
                    SELECT COUNT(reaction) as num
                    FROM predictions_reactions 
                    where pred_id = ? AND reaction = 0
                ''',
                (pred_id,)
            )[0]['num']
        raise exceptions.PredictionDoesNotExistError(f"prediction id {pred_id} does not exist", cause='id')

    def get_max_liked_predictions(self):
        return [
            self.get_prediction(pred_data['id'])
            for pred_data in self.execute(
                '''
                    SELECT
                    p.id, CAST(TOTAL(r.reaction) AS INT) likes_diff
                    FROM currency_predictions p LEFT OUTER JOIN predictions_reactions r
                    ON p.id = r.pred_id
                    WHERE datetime(p.up_to_date) > datetime()
                    GROUP BY p.id
                    ORDER BY likes_diff DESC;
                '''
            )
        ]  # only actual predictions


@private(['get', 'set'], 'execute')
class SessionDBHandler(DBHandlerBase):
    def setup_db(self):
        self.execute(
            '''CREATE TABLE IF NOT EXISTS sessions(
                user_id INTEGER NOT NULL,
                free_notifications_count TINYINT DEFAULT %s,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id) ON CONFLICT REPLACE
            )''' % settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER
        )

    def check_session_exists(self, user_id:int):
        return len(self.execute('SELECT user_id FROM sessions WHERE user_id = ?', (user_id,))) > 0

    def add_session(self, user_id:int):
        self.execute('INSERT INTO sessions(user_id) VALUES (?)', (user_id,))
        return True

    def delete_session(self, user_id:int):
        self.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
        return True

    def get_session(self, user_id:int):
        if self.check_session_exists(user_id):
            return self.execute('SELECT * FROM sessions WHERE user_id = ?', (user_id,))[0]
        raise exceptions.SessionDoesNotExistError(f"session with user id {user_id} does not exist", cause='user_id')

    def get_all_sessions(self):
        return self.execute("SELECT * FROM sessions")

    def decrease_count(self, user_id:int):
        if self.check_session_exists(user_id):
            self.execute(
                'UPDATE sessions SET free_notifications_count = free_notifications_count - 1 WHERE user_id = ?',
                (user_id,)
            )
            return True
        raise exceptions.SessionDoesNotExistError(f"session with user id {user_id} does not exist", cause='user_id')

    def set_count(self, user_id:int, count:int):
        if self.check_session_exists(user_id):
            self.execute(
                'UPDATE sessions SET free_notifications_count = ? WHERE user_id = ?',
                (count, user_id,)
            )
            return True
        raise exceptions.SessionDoesNotExistError(f"session with user id {user_id} does not exist", cause='user_id')

    def fetch_count(self, user_id:int, *, with_decrease:bool=False):
        if self.check_session_exists(user_id):
            is_user_pro = self.execute(
                'SELECT is_pro FROM users WHERE id = ?',
                (user_id,)
            )
            if len(is_user_pro) > 0 and is_user_pro[0]['is_pro'] != 0:
                return 1
            count = self.execute(
                'SELECT free_notifications_count FROM sessions WHERE user_id = ?',
                (user_id,)
            )[0]['free_notifications_count']
            if with_decrease:
                self.decrease_count(user_id)
            return count
        raise exceptions.SessionDoesNotExistError(f"session with user id {user_id} does not exist", cause='user_id')
