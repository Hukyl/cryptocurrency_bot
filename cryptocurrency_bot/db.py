import sqlite3
import json
from collections import namedtuple


User = namedtuple(
    'User',
    ['id', 'user_id', 'is_pro', 'is_active', 'check_times', 'initial_value', 'percent_delta', 'language']
)


class TelegramUserDBHandler(object):
    def __init__(self, db_name:str=None):
        self.db_name = db_name or 'db.sqlite3'
        self.setup_db()

    def setup_db(self):
        config_json = json.load(open("config.json"))
        self.execute_and_commit(
            '''CREATE TABLE IF NOT EXISTS users( 
                    id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    user_id INTEGER NOT NULL,
                    is_pro DATETIME DEFAULT NULL, 
                    is_active BOOLEAN DEFAULT FALSE, 
                    check_times TEXT,
                    initial_value DOUBLE DEFAULT %s,
                    percent_delta REAL DEFAULT %s,   
                    language TEXT DEFAULT "en",       
                    UNIQUE(user_id) ON CONFLICT REPLACE
                )
            ''' % (config_json.get('initialValue'), config_json.get('percentDelta'))
        )

    def execute_and_commit(self, sql, params=tuple()):
        with sqlite3.connect(self.db_name) as conn:
            cur = conn.cursor()
            res = cur.execute(sql, params).fetchall()
            conn.commit()
            return res

    def add_user(self, user_id, is_active=False, check_times='9:00,14:00,19:00', percent_delta=None, language:str='en'):
        config_json = json.load(open("config.json"))
        check_times = check_times
        percent_delta = percent_delta or float(config_json.get('percentDelta'))
        self.execute_and_commit(
            "INSERT INTO users(user_id, is_active, check_times, percent_delta, language) \
            VALUES (?, ?, ?, ?, ?)", 
            (user_id, is_active, check_times, percent_delta, language)
        )

    def check_user(self, user_id):
        res = self.execute_and_commit('SELECT user_id FROM users WHERE user_id = ?', (user_id, ))
        return len(res) > 0

    def get_users_by_check_time(self, check_time):
        return self.execute_and_commit(
            R"SELECT * FROM users WHERE is_active = TRUE AND check_times LIKE ?",
            ('%' + check_time + '%' ,)
        )

    def get_user(self, user_id):
        if self.check_user(user_id):
            return self.execute_and_commit('SELECT * FROM users WHERE user_id = ?', (user_id, ))[0]
        return []

    def get_active_users(self):
        res = self.execute_and_commit('SELECT * FROM users WHERE is_active = TRUE')
        return res

    def get_pro_users(self):
        return self.execute_and_commit('SELECT * FROM users WHERE is_pro = TRUE AND is_active = TRUE')

    def change_user(self, user_id, **kwargs):
        if self.check_user(user_id):
            for k, v in kwargs.items():
                try:
                    self.execute_and_commit('UPDATE users SET %s = ? WHERE user_id = ?' % k, (v, user_id))
                except sqlite3.OperationalError:
                    raise ValueError(f'invalid argument {k} or value {v}')



def get_user(*data):
    if len(data) == len(User._fields):
        return User(*data)
    return None


def get_user_db(db, user_id):
    res = list(db.get_user(user_id))
    if res:
        res[4] = res[4].split(',') # check_times          
        user = User(*res)
        return user
    return None



if __name__ == '__main__':
    db = TelegramUserDBHandler()
