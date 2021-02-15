import sqlite3
from datetime import datetime
import threading

from configs import settings

from utils.dt import check_datetime_in_future, check_check_time_in_rate
from utils.decorators import private, rangetest



@private(['get', 'set'], 'execute_and_commit')
class DBHandler(object):
    """
    DB Format:

    users:
        id: Just incrementing id
        user_id: user's id in Telegram
        is_pro: is user subscribed
        is_staff: is user staff
        timezone: offset from UTC (+3, -2)
        language: language

    user_rates: notifing user if currency rate changed by some percent
        user_id: user's id in Telegram
        iso: currency's isocode
        start_value: A value from which to calculate difference
        percent_delta: A percent delta at which to notify
        check_times: Times at which to check (in user's time zone)
        !!! Checking of rate is by `iso`-USD rate !!!

    currency_predictions: predict rate at some date
        id: just an id
        user_id: user's id in Telegram who made the prediction
        iso_from: currency's iso for convertation
        iso_to: currency's iso for convartation
        value: convertation rate (1 `iso_from` - `value` `iso_to`)
        up_to_date: datetime, at which predict the exchange rate
        is_by_experts: is user, who made the prediction, has `is_staff` status
        real_value: value, which really was on `up_to_date`

    predictions_reactions:
        pred_id: id of prediction
        user_id: user's Telegram ID, who made reaction
        reaction: like/dislike (1/0 respectively)
    """
    def __init__(self, db_name:str=None):
        self.DB_NAME = db_name or settings.DB_NAME
        self.setup_db()

    def setup_db(self):
        self.execute_and_commit(
            '''CREATE TABLE IF NOT EXISTS users( 
                    user_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 0,
                    is_pro DATETIME DEFAULT FALSE, 
                    is_staff BOOLEAN DEFAULT 0,
                    timezone TINYINT DEFAULT 0 CHECK (
                        timezone in (
                            -11, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 
                            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
                        )
                    ),
                    language VARCHAR(2) DEFAULT "en" CHECK (LENGTH(language) IN (2, 3)), 
                    UNIQUE(user_id) ON CONFLICT REPLACE
                )
            '''
        )
        self.execute_and_commit(
            '''CREATE TABLE IF NOT EXISTS users_rates( 
                    user_id INTEGER NOT NULL,
                    iso VARCHAR(5),
                    start_value DOUBLE DEFAULT 0,
                    percent_delta REAL DEFAULT 1,
                    check_times VARCHAR,
                    UNIQUE(user_id, iso) ON CONFLICT REPLACE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            '''
        )
        self.execute_and_commit(
            '''CREATE TABLE IF NOT EXISTS currency_predictions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    user_id INTEGER,
                    iso_from VARCHAR(5),
                    iso_to VARCHAR(5),
                    value DOUBLE,
                    up_to_date DATETIME,
                    is_by_experts BOOLEAN DEFAULT FALSE,
                    real_value DOUBLE DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            '''
        )
        self.execute_and_commit(
            '''CREATE TABLE IF NOT EXISTS predictions_reactions(
                pred_id INTEGER,
                user_id INTEGER,
                reaction BOOLEAN,
                FOREIGN KEY (pred_id) REFERENCES currency_predictions(pred_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            '''
        )

    def execute_and_commit(self, sql, params=tuple()):
        with threading.Lock():
            with sqlite3.connect(self.DB_NAME) as conn:
                cur = conn.cursor()
                res = cur.execute(sql, params).fetchall()
                conn.commit()
                return res

    def add_user(
            self, user_id:int, is_active:bool=True, is_pro=False, 
            is_staff:bool=False, timezone:int=0, language:str='en'
        ):
        self.execute_and_commit(
            "INSERT INTO users\
            (user_id, is_active, is_pro, is_staff, timezone, language) \
            VALUES (?, ?, ?, ?, ?, ?)", 
            (
                user_id, is_active, 
                is_pro.strftime('%Y-%m-%d %H:%M:%S') if isinstance(is_pro, datetime) else is_pro, 
                is_staff, timezone, language
            )
        )
        return True

    @rangetest(start_value=(0, float('inf')))
    def add_user_rate(
            self, user_id, iso, start_value=1, 
            percent_delta=0.01, check_times:list=settings.DEFAULT_CHECK_TIMES
        ):
        check_times = ','.join(check_times)
        self.execute_and_commit(
            "INSERT INTO users_rates \
            VALUES (?, ?, ?, ?, ?)", 
            (user_id, iso, start_value, percent_delta, check_times)
        )
        return True

    @rangetest(value=(0, float("inf")))
    def add_prediction(
            self, user_id, iso_from:str, iso_to:str, 
            value:float, up_to_date:datetime, is_by_experts=False
        ):
        """
        Add a prediction if user with `user_id` exists
        Returns True if succeded else None
        """
        if self.check_user_exists(user_id):
            assert check_datetime_in_future(
                up_to_date
            ), 'can\'t create prediction with past `up_to_date`'
            self.execute_and_commit(
                "INSERT INTO currency_predictions\
                (user_id, iso_from, iso_to, value, up_to_date, is_by_experts) \
                VALUES (?, ?, ?, ?, ?, ?)", 
                (user_id, iso_from, iso_to, value, str(up_to_date), is_by_experts)
            )
            return True

    def check_user_exists(self, user_id:int):
        res = self.execute_and_commit('SELECT user_id FROM users WHERE user_id = ?', (user_id, ))
        return len(res) > 0

    def check_prediction_exists(self, pred_id:int):
        res = self.execute_and_commit(
            'SELECT id FROM currency_predictions WHERE id = ?',
            (pred_id, )
        )
        return len(res) > 0

    def get_users_by_check_time(self, check_time:str):
        """
        Get all users, which checktimes, converted from their timezone to UTC,
        equals to `check_time` (which is in UTC)
        """
        users_lst = list()
        for user_id in self.execute_and_commit('SELECT DISTINCT user_id FROM users'):
            user = self.get_user(user_id[0])
            if any(check_check_time_in_rate(rate[-1], check_time, user[-2]) for rate in user[-3]):
                users_lst.append(user)
        return users_lst

    def get_user(self, user_id:int):
        """
        Get all user data (except the predictions) by its id
        Returns None if user with this id does not exists
        otherwise returns list(user_id, is_active, is_pro, is_staff, rates, timezone, language)
        """
        if self.check_user_exists(user_id):
            user_id, is_active, is_pro, is_staff, timezone, language = list(
                self.execute_and_commit('SELECT * FROM users WHERE user_id = ?', (user_id, ))[0]
            )
            rates = self.get_user_rates(user_id)
            is_pro = datetime.strptime(
                is_pro, '%Y-%m-%d %H:%M:%S'
            ) if isinstance(is_pro, str) else is_pro
            return [user_id, is_active, is_pro, is_staff, rates, timezone, language]
        return None

    def get_all_users(self):
        return [
            self.get_user(user_data[0])
            for user_data in self.execute_and_commit('SELECT user_id FROM users')
        ]

    def get_staff_users(self):
        """
        Get all users with is_staff status
        """
        return [
            self.get_user(user_data[0])
            for user_data in self.execute_and_commit(
                'SELECT user_id FROM users WHERE is_staff = 1'
            )
        ]

    def get_active_users(self):
        """
        Get all active users
        """
        return [
            self.get_user(user_data[0])
            for user_data in self.execute_and_commit(
                'SELECT user_id FROM users WHERE is_active = TRUE'
            )
        ]

    def get_pro_users(self):
        """
        Get all users who are pro and active
        """
        return [
            self.get_user(user_id[0])
            for user_id in self.execute_and_commit(
                'SELECT user_id \
                FROM users \
                WHERE is_active = TRUE and is_pro != FALSE'
            )
        ]

    def get_user_rates(self, user_id):
        """
        Get users rates
        Returns list of tuples (iso, start_value, percent_delta, check_times) 
        If no rates found, returns empty list
        """
        return [
            tuple(list(rate[:-1]) + [rate[-1].split(',')])
            for rate in self.execute_and_commit(
                'SELECT \
                u_r.iso, u_r.start_value, u_r.percent_delta, u_r.check_times \
                FROM users JOIN users_rates u_r \
                ON users.user_id = u_r.user_id AND users.user_id = ?',
                (user_id, )
            )
        ]

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
            *other_data, up_to_date, is_by_experts, real_value = self.execute_and_commit(
                    'SELECT \
                    id, user_id, iso_from, iso_to, value, up_to_date, is_by_experts, real_value \
                    FROM currency_predictions WHERE id = ?', 
                    (pred_id, )
                )[0]
            return [
                *other_data, datetime.strptime(up_to_date, '%Y-%m-%d %H:%M:%S%z'), 
                is_by_experts, real_value
            ]

    def get_actual_predictions(self):
        return [
            self.get_prediction(data[0])
            for data in self.execute_and_commit(
                'SELECT \
                id \
                FROM currency_predictions \
                WHERE datetime() < datetime(up_to_date) \
                ORDER BY up_to_date ASC'
            )
        ]

    def get_user_predictions(self, user_id, only_actual:bool=False):
        check_datetime_str = 'datetime() < datetime(up_to_date) and ' if only_actual else ''
        return [
            self.get_prediction(data[0])
            for data in self.execute_and_commit(
                'SELECT \
                id \
                FROM currency_predictions \
                WHERE %s user_id = ? \
                ORDER BY up_to_date ASC' % check_datetime_str,
                (user_id, )
            )
        ]

    def get_random_prediction(self):
        res = [
            self.get_prediction(data[0])
            for data in self.execute_and_commit(
                'SELECT \
                id \
                FROM currency_predictions WHERE is_by_experts = FALSE ORDER BY RANDOM() LIMIT 1;'
            )
        ]
        return res[0] if res else -1

    def get_closest_neighbours_of_prediction(self, pred_id):
        """
        Returns previous and next prediction of prediction by `pred_id`
        :return: dict(previous=X, current=pred_id, next=Y)
        """
        def get_next():
            res = [
                self.get_prediction(data[0])
                for data in self.execute_and_commit(
                    # used `LIMIT` and `id > ?` because selection by certain id can cause errors
                    "SELECT \
                    id \
                    FROM currency_predictions \
                    WHERE id > ? AND is_by_experts = FALSE and datetime(up_to_date) > datetime() \
                    ORDER BY id ASC LIMIT 1",
                    (pred_id,)
                )
            ]
            return res[0] if res else None

        def get_previous():
            res = [
                self.get_prediction(data[0])
                for data in self.execute_and_commit(
                    # used `LIMIT` and `id < ?` because selection by certain id can cause errors
                    "SELECT \
                    id \
                    FROM currency_predictions \
                    WHERE id < ? AND is_by_experts = FALSE and datetime(up_to_date) > datetime() \
                    ORDER BY id DESC LIMIT 1",
                    (pred_id,)
                )
            ]
            return res[0] if res else None

        prev = get_previous() 
        next = get_next()
        return {
            'previous': prev[0] if prev else None,  # prev_id
            'current': pred_id,
            'next': next[0] if next else None  # next_id
        }

    def get_experts_predictions(self, only_actual:bool=False):
        check_datetime_str = 'datetime() < datetime(up_to_date) and ' if only_actual else ''
        return [
            self.get_prediction(data[0])
            for data in self.execute_and_commit(
                'SELECT \
                id \
                FROM currency_predictions \
                WHERE %s is_by_experts = TRUE \
                ORDER BY up_to_date DESC' % check_datetime_str
            )
        ]

    def get_unverified_predictions(self):
        return [
            self.get_prediction(data[0])
            for data in self.execute_and_commit(
                'SELECT \
                id \
                FROM currency_predictions \
                WHERE datetime() > datetime(up_to_date) AND real_value is NULL'
            )
        ]

    def change_user(self, user_id, **kwargs):
        if self.check_user_exists(user_id):
            try:
                for k, v in kwargs.items():
                    if isinstance(v, datetime):
                        v = v.strftime('%Y-%m-%d %H:%M:%S')
                    self.execute_and_commit(
                        'UPDATE users SET %s = ? WHERE user_id = ?' % k, 
                        (v, user_id)
                    )
            except sqlite3.OperationalError:
                raise ValueError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            else:
                return True

    @rangetest(start_value=(0, float("inf")))
    def change_user_rate(self, user_id, iso, **kwargs):
        if self.check_user_exists(user_id):
            for k, v in kwargs.items():
                if k == 'check_times' and (isinstance(v, list) or isinstance(v, tuple)):
                    v = ','.join(v)
                try:
                    self.execute_and_commit(
                        'UPDATE users_rates SET %s = ? WHERE user_id = ? and iso = ?' % k,
                        (v, user_id, iso)
                    )
                except sqlite3.OperationalError:
                    raise ValueError(f'invalid argument {repr(k)}') from None
                except sqlite3.IntegrityError:
                    raise ValueError(f"invalid value {repr(v)}") from None
            return True

    def delete_user_rate(self, user_id, iso):
        self.execute_and_commit(
            'DELETE FROM users_rates WHERE user_id = ? AND iso = ?',
            (user_id, iso)
        )
        return True

    @rangetest(value=(0, float("inf")), real_value=(0, float("inf")), )
    def change_prediction(self, id, **kwargs):
        if self.check_prediction_exists(id):
            # validation of parameters
            assert (
                kwargs.get('iso_from') or kwargs.get('iso_to')
            ) is None, "can't change isos of prediction"
            assert 'user_id' not in kwargs, 'cant\'t change `user_id` of prediction'
            up_to_date = kwargs.get('up_to_date', None)
            if up_to_date is not None and isinstance(up_to_date, datetime):
                assert check_datetime_in_future(
                    up_to_date
                ), 'can\'t change `up_to_date` to past datetime'
                kwargs['up_to_date'] = str(up_to_date)
            del up_to_date
            # end of validation
            try:
                for k, v in kwargs.items():
                    self.execute_and_commit(
                        'UPDATE currency_predictions SET %s = ? WHERE id = ? ' % k,
                        (v, id,)
                    )
            except sqlite3.OperationalError:
                raise ValueError(f'invalid argument {repr(k)}') from None
            except sqlite3.IntegrityError:
                raise ValueError(f"invalid value {repr(v)}") from None
            return True

    def delete_prediction(self, pred_id):
        self.execute_and_commit(
            'DELETE FROM currency_predictions WHERE id = ?',
            (pred_id, )
        )
        return True

    def toggle_prediction_reaction(self, pred_id, user_id, if_like=True):
        """
        if_like:
            True - like prediction
            False - dislike prediction
            None - delete any reaction
        """
        if self.check_prediction_exists(pred_id) and self.check_user_exists(user_id):
            self.execute_and_commit(
                'DELETE FROM predictions_reactions WHERE pred_id = ? and user_id = ?',
                (pred_id, user_id)
            )
            if if_like is not None:
                self.execute_and_commit(
                    'INSERT INTO predictions_reactions VALUES (?, ?, ?)',
                    (pred_id, user_id, if_like)
                )
            return True
        return None

    def get_number_likes(self, pred_id):
        if self.check_prediction_exists(pred_id):
            return self.execute_and_commit(''' 
                    SELECT COUNT(reaction) 
                    FROM predictions_reactions 
                    where pred_id = ? AND reaction = 1
                    ''',
                    (pred_id, )
                )[0][0]

    def get_number_dislikes(self, pred_id):
        if self.check_prediction_exists(pred_id):
            return self.execute_and_commit(''' 
                    SELECT COUNT(reaction) 
                    FROM predictions_reactions 
                    where pred_id = ? AND reaction = 0
                    ''',
                    (pred_id, )
                )[0][0]

    def get_max_liked_predictions(self):
        return [
            self.get_prediction(pred_data[0])
            for pred_data in self.execute_and_commit('''
                SELECT
                p.id, CAST(TOTAL(r.reaction) AS INT) likes_diff
                FROM currency_predictions p LEFT OUTER JOIN predictions_reactions r
                ON p.id = r.pred_id
                WHERE datetime(p.up_to_date) > datetime()
                GROUP BY p.id
                ORDER BY likes_diff DESC;
            ''')
        ] # only actual predictions



if __name__ == '__main__':
    db = DBHandler()
