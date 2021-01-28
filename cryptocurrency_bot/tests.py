import os
import sys
import sqlite3
import unittest

import main_bot
import main
import models
import configs
import utils



class DBTestCase(unittest.TestCase):
    def setUp(self):
        self.db = models.db.TelegramUserDBHandler(configs.settings.DB_NAME)

    def tearDown(self):
        os.remove(configs.settings.DB_NAME)

    def test_add_user(self):
        self.assertFalse(self.db.check_user_exists(0))
        self.db.add_user(0)
        self.assertTrue(self.db.check_user_exists(0))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_user(-1, timezone=20) # timezone not in range(-11, 13)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_user(-1, timezone=-14)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.add_user(-1, language='English') # 'en', 'ru', 'ua' etc.
        id, user_id, is_pro, is_active, is_staff, rates, timezone, language = self.db.get_user(0)
        self.assertEqual(id, 1)
        self.assertEqual(user_id, 0)
        self.assertEqual(is_pro, 0)
        self.assertEqual(is_active, 1)
        self.assertEqual(is_staff, 0)
        self.assertEqual(timezone, 0)
        self.assertEqual(language, 'en')

    def test_change_user(self):
        self.db.add_user(1)
        id, user_id, is_pro, is_active, is_staff, rates, timezone, language = self.db.get_user(1)
        self.assertEqual(is_active, 1)
        self.assertEqual(language, 'en')
        self.db.change_user(1, language='ru', is_active=False)
        id, user_id, is_pro, is_active, is_staff, rates, timezone, language = self.db.get_user(1)
        self.assertEqual(is_active, 0)
        self.assertEqual(language, 'ru')
        with self.assertRaises(ValueError):
            self.db.change_user(1, ababagalamaga='1212302')

    def test_add_user_rate(self):
        self.db.add_user(2)
        self.db.add_user_rate(2, 'BRENT', 55.0)
        rates = self.db.get_user_rates(2)
        self.assertEqual(len(rates), 1)
        self.assertEqual(len(rates[0]), 4)
        iso, start_value, percent_delta, check_times = rates[0]
        self.assertEqual(iso, 'BRENT')
        self.assertEqual(start_value, 55.0)
        self.assertEqual(percent_delta, 0.01)
        self.assertEqual(check_times, configs.settings.DEFAULT_CHECK_TIMES)

    def test_change_user_rate(self):
        self.db.add_user(0)
        self.db.add_user_rate(0, 'BRENT', 55.0)
        self.db.change_user_rate(0, 'BRENT', start_value=52, percent_delta=0.08)
        iso, start_value, percent_delta, check_times = self.db.get_user_rates(0)[0]
        self.assertEqual(start_value, 52.0)
        self.assertEqual(percent_delta, 0.08)
        with self.assertRaises(ValueError):
            self.db.change_user_rate(0, 'BRENT', asdfasdf='RUB')
        self.assertIsNone(self.db.change_user_rate(-1, 'BRENT', start_value=35.0)) # not user is found, so returns None

    def test_delete_user_rate(self):
        self.db.add_user(0)
        self.db.add_user_rate(0, 'BRENT', 55.0)
        self.assertTrue(self.db.delete_user_rate(0, 'BRENT')) # deletion succeded, so returns True
        rates = self.db.get_user_rates(0)
        self.assertEqual(rates, [])

    def test_add_user_prediction(self):
        self.db.add_user(0)
        id, user_id, is_pro, is_active, is_staff, rates, timezone, language = self.db.get_user(0)
        self.assertFalse(self.db.check_prediction_exists(1))
        self.assertTrue(
            self.db.add_prediction(
                user_id, 
                'BRENT', 
                'USD', 
                55, 
                utils.dt.get_current_datetime(utcoffset=2).replace(year=2120)
            )
        )
        self.assertTrue(self.db.check_prediction_exists(1))
        self.assertIsNone(
            self.db.add_prediction(
                -1, 
                'BRENT', 
                'USD', 
                55, 
                utils.dt.get_current_datetime(utcoffset=2).replace(year=2120)
            )
        )
        with self.assertRaises(AssertionError):
            self.db.add_prediction(user_id, 'BRENT', 'USD', -55, utils.dt.get_current_datetime().replace(year=2120))
        with self.assertRaises(AssertionError):
            self.db.add_prediction(user_id, 'BRENT', 'USD', 55, utils.dt.get_current_datetime().replace(hour=0))
        pid, puser_id, piso_from, piso_to, pvalue, pup_to_date, pis_by_experts, preal_value = self.db.get_prediction(1)
        self.assertEqual(pid, 1)
        self.assertEqual(puser_id, user_id)
        self.assertEqual(piso_from, 'BRENT')
        self.assertEqual(piso_to, 'USD')
        self.assertEqual(pvalue, 55.0)
        self.assertTrue(utils.dt.check_datetime_in_future(pup_to_date, utcoffset=timezone))
        self.assertIsNone(preal_value)

    def test_change_user_prediction(self):
        self.db.add_user(0)
        self.db.add_prediction(0, 'BRENT', 'USD', 55, utils.dt.get_current_datetime(utcoffset=2).replace(year=2120))
        pid, puser_id, piso_from, piso_to, pvalue, pup_to_date, pis_by_experts, preal_value = self.db.get_prediction(1)
        self.assertEqual(pvalue, 55.0)
        self.assertFalse(pis_by_experts)
        self.db.change_prediction(pid, value=59.5, is_by_experts=True)
        pid, puser_id, piso_from, piso_to, pvalue, pup_to_date, pis_by_experts, preal_value = self.db.get_prediction(pid)
        self.assertEqual(pvalue, 59.5)
        self.assertTrue(pis_by_experts)
        with self.assertRaises(AssertionError):
            self.db.change_prediction(pid, user_id=-1)
        with self.assertRaises(AssertionError):
            self.db.change_prediction(pid, value=-55)
        with self.assertRaises(AssertionError):
            self.db.change_prediction(pid, up_to_date=utils.dt.get_current_datetime().replace(hour=0))

    def test_check_actual_predictions(self):
        self.db.add_user(0)
        self.db.add_prediction(0, 'RUB', 'USD', 0.007, utils.dt.get_current_datetime().replace(year=2120))
        self.assertEqual(len(self.db.get_actual_predictions()), 1)

    def test_check_experts_predictions(self):
        self.db.add_user(0)
        self.db.add_prediction(0, 'RUB', 'USD', 0.007, utils.dt.get_current_datetime().replace(year=2120))
        self.db.change_prediction(1, is_by_experts=True)
        self.assertEqual(len(self.db.get_experts_predictions()), 1)
        self.db.change_prediction(1, is_by_experts=False)
        self.assertEqual(len(self.db.get_experts_predictions()), 0)

    def test_check_prediction_neighbours(self):
        user_id = 0
        prev_pred = None
        curr_pred = 1
        next_pred = None
        self.db.add_user(0)
        self.db.add_prediction(0, 'RUB', 'USD', 0.007, utils.dt.get_current_datetime().replace(year=2120))
        self.assertDictEqual(
            self.db.get_closest_neighbours_of_prediction(curr_pred), 
            {'previous': prev_pred, 'current': curr_pred, 'next': next_pred}
        )
        self.db.add_prediction(user_id, 'UAH', 'USD', 0.036, utils.dt.get_current_datetime().replace(year=2120))
        self.db.add_prediction(user_id, 'BRENT', 'USD', 0.007, utils.dt.get_current_datetime().replace(year=2120))
        prev_pred, curr_pred, next_pred = 1, 2, 3
        self.assertDictEqual(
            self.db.get_closest_neighbours_of_prediction(curr_pred), 
            {'previous': prev_pred, 'current': curr_pred, 'next': next_pred}
        )

    def test_check_random_prediction(self):
        self.db.add_user(0)
        self.db.add_prediction(0, 'RUB', 'USD', 0.007, utils.dt.get_current_datetime().replace(year=2120))
        self.assertEqual(self.db.get_random_prediction()[0], 1)

    def test_delete_user_prediction(self):
        self.db.add_user(0)
        self.assertFalse(self.db.check_prediction_exists(1))
        self.db.add_prediction(0, 'RUB', 'USD', 0.007, utils.dt.get_current_datetime().replace(year=2120))
        self.assertTrue(self.db.check_prediction_exists(1))
        self.db.delete_prediction(1)
        self.assertFalse(self.db.check_prediction_exists(1))



if __name__ == '__main__':
    unittest.main()
