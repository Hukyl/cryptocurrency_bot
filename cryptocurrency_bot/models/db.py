import json
import sqlite3
from datetime import datetime
import threading

from configs import _globals



class TelegramUserDBHandler(object):
    def __init__(self, db_name:str=None):
        self.db_name = db_name or 'db.sqlite3'
        self.setup_db()

    def setup_db(self):
        self.execute_and_commit(
            '''CREATE TABLE IF NOT EXISTS users( 
                    id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    user_id INTEGER NOT NULL,
                    is_pro DATETIME DEFAULT NULL, 
                    is_active BOOLEAN DEFAULT FALSE,
                    is_staff BOOLEAN DEFAULT FALSE,
                    language TEXT DEFAULT "en", 
                    UNIQUE(user_id) ON CONFLICT REPLACE
                )
            '''
        )
        self.execute_and_commit(
            '''CREATE TABLE IF NOT EXISTS users_rates( 
                    user_id INTEGER NOT NULL,
                    iso VARCHAR,
                    start_value DOUBLE DEFAULT 0,
                    percent_delta REAL DEFAULT 1,
                    check_times VARCHAR DEFAULT '10:00,15:00,19:00',
                    UNIQUE(user_id, iso) ON CONFLICT REPLACE
                )
            '''
        )
        self.execute_and_commit(
            '''CREATE TABLE IF NOT EXISTS currency_predictions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    user_id INTEGER NOT NULL,
                    iso_from VARCHAR,
                    iso_to VARCHAR,
                    value DOUBLE,
                    up_to_date DATETIME,
                    is_by_experts BOOLEAN DEFAULT FALSE,
                    real_value REAL DEFAULT NULL,
                    UNIQUE(user_id, iso_from, iso_to, up_to_date) ON CONFLICT REPLACE
            )
            '''
        )
        self.execute_and_commit(
            '''CREATE TABLE IF NOT EXISTS predictions_reactions(
                pred_id INTEGER,
                user_id INTEGER,
                reaction BOOLEAN
            )
            '''
        )

    def execute_and_commit(self, sql, params=tuple()):
        with threading.Lock():
            with sqlite3.connect(self.db_name) as conn:
                cur = conn.cursor()
                res = cur.execute(sql, params).fetchall()
                conn.commit()
                return res

    def add_user(self, user_id, is_active=False, is_pro:bool=False, is_staff:bool=False, language:str='en'):
        self.execute_and_commit(
            "INSERT INTO users(user_id, is_active, is_pro, is_staff, language) \
            VALUES (?, ?, ?, ?, ?)", 
            (user_id, is_active, is_pro, is_staff, language)
        )
        return True

    def add_user_rate(self, user_id, iso, start_value=1, percent_delta=1, check_times:list=_globals.DEFAULT_CHECK_TIMES):
        check_times = ','.join(check_times)
        self.execute_and_commit(
            "INSERT INTO users_rates \
            VALUES (?, ?, ?, ?, ?)", 
            (user_id, iso, start_value, percent_delta, check_times)
        )
        return True

    def add_user_prediction(self, user_id, iso_from, iso_to, value, up_to_date:datetime, is_by_experts=False):
        self.execute_and_commit(
            "INSERT INTO currency_predictions(user_id, iso_from, iso_to, value, up_to_date, is_by_experts) \
            VALUES (?, ?, ?, ?, ?, ?)", 
            (user_id, iso_from, iso_to, value, up_to_date, is_by_experts)
        )
        return True

    def check_user_exists(self, user_id):
        res = self.execute_and_commit('SELECT user_id FROM users WHERE user_id = ?', (user_id, ))
        return len(res) > 0

    def check_prediction_exists(self, pred_id):
        res = self.execute_and_commit('SELECT id FROM currency_predictions WHERE id = ?', (pred_id, ))
        return len(res) > 0

    def get_users_by_check_time(self, check_time):
        return [
            self.get_user(user_id[0])
            for user_id in self.execute_and_commit(
                'SELECT DISTINCT users.user_id\
                FROM users JOIN users_rates\
                WHERE users.user_id = users_rates.user_id AND users.is_active = TRUE AND users_rates.check_times LIKE ?',
                (f"%{check_time}%", )
            )
        ]

    def get_user(self, user_id):
        if self.check_user_exists(user_id):
            id, user_id, is_pro, is_active, is_staff, language = list(
                self.execute_and_commit('SELECT * FROM users WHERE user_id = ?', (user_id, ))[0]
            )
            rates = self.get_user_rates(user_id)
            return [id, user_id, is_pro, is_active, is_staff, rates, language]
        return []

    def get_all_users(self):
        return [
            list(user[:-1]) + 
            [self.get_user_rates(user[1])] + # get_user_rates(user_id)
            [user[-1]]
            for user in self.execute_and_commit('SELECT * FROM users')
        ]

    def get_staff_users(self):
        return self.execute_and_commit(
                'SELECT * FROM users WHERE is_staff = 1 AND is_active = 1'
            )

    def get_active_users(self):
        return [
            list(user[:-1]) + 
            [self.get_user_rates(user[1])] + # get_user_rates(user_id)
            [user[-1]]
            for user in self.execute_and_commit('SELECT * FROM users WHERE is_active = TRUE')
        ]

    def get_pro_users(self):
        return [
            list(user[:-1]) + 
            [self.get_user_rates(user[1])] + # get_user_rates(user_id)
            [user[-1]]
            for user in self.execute_and_commit('SELECT * FROM users WHERE is_active = TRUE and is_pro != NULL')
        ]

    def get_user_rates(self, user_id):
        return self.execute_and_commit(
            'SELECT \
            users_rates.iso, users_rates.start_value, users_rates.percent_delta, users_rates.check_times \
            FROM users JOIN users_rates WHERE users.user_id = users_rates.user_id AND users.user_id = ?',
            (user_id, )
        )

    def get_actual_predictions(self):
        return self.execute_and_commit(
            'SELECT * FROM currency_predictions \
            WHERE datetime() < up_to_date \
            ORDER BY up_to_date ASC'
        )

    def get_user_predictions(self, user_id, if_all:bool=False):
        check_datetime_str = 'datetime() < up_to_date and ' if not if_all else ''
        return self.execute_and_commit(
            'SELECT * FROM currency_predictions \
            WHERE ' + check_datetime_str + 'user_id = ? \
            ORDER BY up_to_date ASC',
            (user_id, )
        )

    def get_prediction(self, pred_id):
        if self.check_prediction_exists(pred_id):
            return self.execute_and_commit(
                    'SELECT * FROM currency_predictions WHERE id = ?', 
                    (pred_id, )
                )[0]

    def get_random_prediction(self):
        return self.execute_and_commit(
                'SELECT * FROM currency_predictions WHERE is_by_experts = FALSE ORDER BY RANDOM() LIMIT 1;'
            )[0]

    def get_closest_neighbours_of_prediction(self, pred_id):
        """
        Returns previous and next prediction of prediction by `pred_id`
        :return: dict(previous=X, current=pred_id, next=Y)
        """
        def get_next():
            res = self.execute_and_commit(
                    "SELECT * FROM currency_predictions WHERE id > ? AND is_by_experts = FALSE ORDER BY id ASC LIMIT 1",
                    (pred_id,)
                )
            if res:
                return res[0]

        def get_previous():
            res = self.execute_and_commit(
                    "SELECT * FROM currency_predictions WHERE id < ? AND is_by_experts = FALSE ORDER BY id DESC LIMIT 1",
                    (pred_id,)
                )
            if res:
                return res[0]

        prev = get_previous()
        next = get_next()
        return {
            'previous': prev[0] if prev else None,
            'current': pred_id,
            'next': next[0] if next else None
        }

    def get_experts_predictions(self, if_all:bool=False):
        check_datetime_str = 'datetime() < up_to_date and ' if not if_all else ''
        return self.execute_and_commit(
                'SELECT * FROM currency_predictions WHERE ' + (
                    check_datetime_str
                ) + 'is_by_experts = TRUE ORDER BY up_to_date DESC'
            )

    def get_unverified_predictions(self):
        return self.execute_and_commit(
                'SELECT * FROM currency_predictions WHERE datetime() > up_to_date AND real_value is NULL'
            )

    def change_user(self, user_id, **kwargs):
        if self.check_user_exists(user_id):
            for k, v in kwargs.items():
                if isinstance(v, datetime):
                    v = v.strftime('%Y-%m-%d %H:%M:%S')
                try:
                    self.execute_and_commit('UPDATE users SET %s = ? WHERE user_id = ?' % k, (v, user_id))
                except sqlite3.OperationalError:
                    raise ValueError(f'invalid argument {k} or value {v}')
            return True

    def change_user_rates(self, user_id, iso, **kwargs):
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
                    raise ValueError(f'invalid argument {k} or value {v}')
            return True

    def delete_user_rate(self, user_id, iso):
        if self.check_user_exists(user_id):
            try:
                self.execute_and_commit(
                        'DELETE FROM users_rates WHERE user_id = ? AND iso = ?',
                        (user_id, iso)
                    )
            except sqlite3.OperationalError:
                pass
            else:
                return True

    def change_user_prediction(self, pred_id, **kwargs):
        if self.check_prediction_exists(pred_id):
            for k, v in kwargs.items():
                try:
                    self.execute_and_commit(
                        'UPDATE currency_predictions SET %s = ? WHERE id = ? ' % k,
                        (v, pred_id,)
                    )
                except sqlite3.OperationalError:
                    raise ValueError(f'invalid argument `{k}` or value `{v}`')
            return True

    def delete_user_prediction(self, pred_id):
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
        if self.check_prediction_exists(pred_id):
            try:
                self.execute_and_commit(
                        'DELETE FROM predictions_reactions WHERE pred_id = ? and user_id = ?',
                        (pred_id, user_id)
                    )
            except sqlite3.OperationalError: # if no reaction were made by this user about this prediction 
                pass
            if if_like is not None:
                self.execute_and_commit(
                        'INSERT INTO predictions_reactions VALUES (?, ?, ?)',
                        (pred_id, user_id, if_like)
                    )
            return True

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

    def get_max_liked_predictions_ids(self):
        return self.execute_and_commit('''
                SELECT DISTINCT currency_predictions.id
                FROM currency_predictions JOIN predictions_reactions
                WHERE currency_predictions.id = predictions_reactions.pred_id AND currency_predictions.up_to_date > datetime()
                ORDER BY
                (
                    SELECT COUNT(reaction) 
                    FROM predictions_reactions 
                    where pred_id = currency_predictions.id AND reaction = 1
                ) - (
                    SELECT COUNT(reaction) 
                    FROM predictions_reactions 
                    where pred_id = currency_predictions.id AND reaction = 0
                ) DESC;
            ''')


if __name__ == '__main__':
    db = TelegramUserDBHandler()
