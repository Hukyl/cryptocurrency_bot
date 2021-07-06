import os
import sqlite3
import unittest
import time
import datetime as dt

import models
import configs
import utils


class BasicTestCase(unittest.TestCase):
    def setUp(self):
        self.db = models.db.DBHandler(configs.settings.DB_NAME)
        self.session_db = models.db.SessionDBHandler(configs.settings.DB_NAME)

    def tearDown(self):
        os.remove(configs.settings.DB_NAME)


class DBTestCase(BasicTestCase):
    def test_access_execute_method(self):
        with self.assertRaises(TypeError):
            self.db.execute("SELECT * FROM users")

    def test_add_user(self):
        self.assertFalse(self.db.check_user_exists(0))
        self.db.add_user(0)
        self.assertTrue(self.db.check_user_exists(0))
        with self.assertRaises(sqlite3.IntegrityError):
            # timezone not in range(-11, 13)
            self.db.add_user(-1, timezone=20)
        with self.assertRaises(sqlite3.IntegrityError):
            # timezone not in range(-11, 13)
            self.db.add_user(-1, timezone=-14)
        with self.assertRaises(sqlite3.IntegrityError):
            # should be 'en', 'ru', 'ua' etc.
            self.db.add_user(-1, language='English')  
        user_data = self.db.get_user(0)
        self.assertEqual(user_data['id'], 0)
        self.assertEqual(user_data['is_pro'], 0)
        self.assertEqual(user_data['is_active'], 1)
        self.assertEqual(user_data['is_staff'], 0)
        self.assertEqual(user_data['timezone'], 0)
        self.assertEqual(user_data['language'], 'en')

    def test_change_user(self):
        self.db.add_user(1)
        user_data = self.db.get_user(1)
        self.assertEqual(user_data['is_active'], 1)
        self.assertEqual(user_data['language'], 'en')
        self.db.change_user(1, language='ru', is_active=False)
        user_data = self.db.get_user(1)
        self.assertEqual(user_data['is_active'], 0)
        self.assertEqual(user_data['language'], 'ru')
        with self.assertRaises(KeyError):
            self.db.change_user(1, ababagalamaga='1212302')

    def test_add_user_rate(self):
        self.db.add_user(2)
        self.db.add_user_rate(2, 'BRENT', 55.0)
        rates = self.db.get_user_rates(2)
        self.assertEqual(len(rates), 1)
        self.assertEqual(len(rates[0]), 4)
        rate = rates[0]
        self.assertEqual(rate['iso'], 'BRENT')
        self.assertEqual(rate['value'], 55.0)
        self.assertEqual(rate['percent_delta'], 0.01)
        self.assertEqual(
            rate['check_times'], configs.settings.DEFAULT_CHECK_TIMES
        )

    def test_change_user_rate(self):
        self.db.add_user(0)
        self.db.add_user_rate(0, 'BRENT', 55.0)
        self.db.change_user_rate(0, 'BRENT', value=52, percent_delta=0.08)
        rate = self.db.get_user_rates(0)[0]
        self.assertEqual(rate['value'], 52.0)
        self.assertEqual(rate['percent_delta'], 0.08)
        with self.assertRaises(KeyError):
            self.db.change_user_rate(0, 'BRENT', asdfasdf='RUB')
        with self.assertRaises(AssertionError):
            self.db.change_user_rate(0, 'BRENT', value=-5)
        with self.assertRaises(models.exceptions.UserDoesNotExistError):
            self.db.change_user_rate(-1, 'BRENT', value=35.0)
        # not user is found, so returns None

    def test_delete_user_rate(self):
        self.db.add_user(0)
        self.db.add_user_rate(0, 'BRENT', 55.0)
        self.assertTrue(self.db.delete_user_rate(0, 'BRENT'))  
        # deletion succeeded, so returns True
        rates = self.db.get_user_rates(0)
        self.assertEqual(rates, [])

    def test_add_user_prediction(self):
        self.db.add_user(0)
        user_data = self.db.get_user(0)
        self.assertFalse(self.db.check_prediction_exists(1))
        self.assertTrue(
            self.db.add_prediction(
                user_data['id'], 'BRENT', 'USD', 
                55, utils.dt.get_now().replace(year=2120)
            )
        )
        self.assertTrue(self.db.check_prediction_exists(1))
        with self.assertRaises(models.exceptions.UserDoesNotExistError):
            self.db.add_prediction(
                -1, 'BRENT', 'USD', 55, utils.dt.get_now().replace(year=2120)
            )
        with self.assertRaises(AssertionError):
            self.db.add_prediction(
                user_data['id'], 'BRENT', 
                'USD', -55, 
                utils.dt.get_now().replace(year=2120)
            )
        with self.assertRaises(AssertionError):
            self.db.add_prediction(
                user_data['id'], 'BRENT', 
                'USD', 55, 
                utils.dt.get_now().replace(year=2020)
            )
        pred_data = self.db.get_prediction(1)
        self.assertEqual(pred_data['id'], 1)
        self.assertEqual(pred_data['user_id'], user_data['id'])
        self.assertEqual(pred_data['iso_from'], 'BRENT')
        self.assertEqual(pred_data['iso_to'], 'USD')
        self.assertEqual(pred_data['value'], 55.0)
        self.assertTrue(
            utils.dt.check_datetime_in_future(pred_data['up_to_date'])
        )
        self.assertIsNone(pred_data['real_value'])

    def test_change_user_prediction(self):
        self.db.add_user(0)
        self.db.add_prediction(
            0, 'BRENT', 'USD', 55, 
            utils.dt.get_now().replace(year=2120)
        )
        pred_data = self.db.get_prediction(1)
        self.assertEqual(pred_data['value'], 55.0)
        self.assertFalse(pred_data['is_by_experts'])
        self.db.change_prediction(
            pred_data['id'], value=59.5, is_by_experts=True
        )
        pred_data = self.db.get_prediction(1)
        self.assertEqual(pred_data['value'], 59.5)
        self.assertTrue(pred_data['is_by_experts'])
        with self.assertRaises(AssertionError):
            self.db.change_prediction(pred_data['id'], user_id=-1)
        with self.assertRaises(AssertionError):
            self.db.change_prediction(pred_data['id'], value=-55)
        with self.assertRaises(AssertionError):
            self.db.change_prediction(
                pred_data['id'], 
                up_to_date=utils.dt.get_now().replace(year=2000)
            )

    def test_get_actual_predictions(self):
        self.db.add_user(0)
        d = utils.dt.get_now() + dt.timedelta(0, 2)  # add 2 second
        self.db.add_prediction(0, 'RUB', 'USD', 0.007, d)
        self.assertEqual(len(self.db.get_actual_predictions()), 1)
        time.sleep(3)
        self.assertEqual(len(self.db.get_actual_predictions()), 0)

    def test_get_unverified_predictions(self):
        self.db.add_user(0)
        d = utils.dt.get_now() + dt.timedelta(0, 2)  # add 2 second
        self.db.add_prediction(0, 'RUB', 'USD', 0.007, d)
        self.assertEqual(len(self.db.get_unverified_predictions()), 0)
        time.sleep(3)
        self.assertEqual(len(self.db.get_unverified_predictions()), 1)        

    def test_get_experts_predictions(self):
        self.db.add_user(0)
        self.db.add_prediction(
            0, 'RUB', 'USD', 0.007, utils.dt.get_now().replace(year=2120)
        )
        self.db.change_prediction(1, is_by_experts=True)
        self.assertEqual(len(self.db.get_experts_predictions()), 1)
        self.db.change_prediction(1, is_by_experts=False)
        self.assertEqual(len(self.db.get_experts_predictions()), 0)

    def test_get_prediction_neighbours(self):
        user_id = 0
        prev_pred = None
        curr_pred = 1
        next_pred = None
        self.db.add_user(0)
        self.db.add_prediction(
            0, 'RUB', 'USD', 0.007, utils.dt.get_now().replace(year=2120)
        )
        self.assertDictEqual(
            self.db.get_closest_prediction_neighbours(curr_pred), 
            {'previous': prev_pred, 'current': curr_pred, 'next': next_pred}
        )
        self.db.add_prediction(
            user_id, 'UAH', 'USD', 0.036, utils.dt.get_now().replace(year=2120)
        )
        self.db.add_prediction(
            user_id, 'BRENT', 'USD', 
            0.007, utils.dt.get_now().replace(year=2120)
        )
        prev_pred, curr_pred, next_pred = 1, 2, 3
        self.assertDictEqual(
            self.db.get_closest_prediction_neighbours(curr_pred), 
            {'previous': prev_pred, 'current': curr_pred, 'next': next_pred}
        )

    def test_get_random_prediction(self):
        self.db.add_user(0)
        self.db.add_prediction(
            0, 'RUB', 'USD', 0.007, utils.dt.get_now().replace(year=2120)
        )
        self.assertEqual(self.db.get_random_prediction()['id'], 1)

    def test_delete_user_prediction(self):
        self.db.add_user(0)
        self.assertFalse(self.db.check_prediction_exists(1))
        self.db.add_prediction(
            0, 'RUB', 'USD', 0.007, utils.dt.get_now().replace(year=2120)
        )
        self.assertTrue(self.db.check_prediction_exists(1))
        self.db.delete_prediction(1)
        self.assertFalse(self.db.check_prediction_exists(1))

    def test_get_users_by_check_time(self):
        self.db.add_user(0)  # user's timezone is UTC
        self.db.add_user_rate(
            0, 'BRENT', 55.0, check_times=['00:01', '15:10', '18:05']
        )
        self.assertEqual(len(self.db.get_users_by_check_time('15:10')), 1)
        self.assertEqual(len(self.db.get_users_by_check_time('13:10')), 0)

    def test_predictions_reactions(self):
        self.db.add_user(0)
        self.db.add_prediction(
            0, 'BRENT', 'USD', 55, utils.dt.get_now().replace(year=2120)
        )
        user1 = 0
        pred1 = 1
        self.assertEqual(self.db.get_prediction_likes(pred1), 0)
        self.assertEqual(self.db.get_prediction_dislikes(pred1), 0)
        self.db.toggle_prediction_reaction(pred1, user1, reaction=True)
        self.assertEqual(self.db.get_prediction_likes(pred1), 1)
        self.assertEqual(self.db.get_prediction_dislikes(pred1), 0)
        self.db.toggle_prediction_reaction(pred1, user1, reaction=False)
        self.assertEqual(self.db.get_prediction_likes(pred1), 0)
        self.assertEqual(self.db.get_prediction_dislikes(pred1), 1)
        self.db.add_prediction(
            0, 'RUB', 'USD', 0.007, utils.dt.get_now().replace(year=2120)
        )
        pred2 = 2
        self.db.toggle_prediction_reaction(pred2, user1, reaction=True)
        self.assertEqual(
            [x['id'] for x in self.db.get_max_liked_predictions()], [2, 1]
        )

    def test_get_all_users(self):
        self.assertEqual(len(self.db.get_all_users()), 0)
        self.db.add_user(0)
        self.assertEqual(len(self.db.get_all_users()), 1)
        self.db.add_user(1)
        self.assertEqual(len(self.db.get_all_users()), 2)
        self.tearDown()
        self.setUp()
        self.assertEqual(len(self.db.get_all_users()), 0)

    def test_get_pro_users(self):
        self.assertEqual(len(self.db.get_pro_users()), 0)
        self.db.add_user(0)
        self.assertEqual(len(self.db.get_pro_users()), 0)
        self.db.change_user(0, is_pro=utils.dt.get_now().replace(year=2120))
        self.assertEqual(len(self.db.get_pro_users()), 1)
        self.db.add_user(1, is_pro=True)
        self.assertEqual(len(self.db.get_pro_users()), 2)
        self.assertEqual(len(self.db.get_pro_users(only_temp=True)), 1)
        self.db.change_user(0, is_pro=0)   
        self.assertEqual(len(self.db.get_pro_users()), 1)

    def test_get_staff_users(self):
        self.assertEqual(len(self.db.get_staff_users()), 0)
        self.db.add_user(0)
        self.assertEqual(len(self.db.get_staff_users()), 0)
        self.db.change_user(0, is_staff=1)
        self.assertEqual(len(self.db.get_staff_users()), 1)
        self.db.add_user(1, is_staff=1)
        self.assertEqual(len(self.db.get_staff_users()), 2)
        self.db.change_user(0, is_staff=0)   
        self.assertEqual(len(self.db.get_staff_users()), 1)



class UserModelTestCase(BasicTestCase):
    def test_add_user(self):
        self.db.add_user(0, timezone=+2, language='ru', is_staff=True)
        self.db.add_user_rate(
            0, 'BRENT', value=56.3, percent_delta=0.2, 
            check_times=['09:00', '18:00', '11:12']
        ) 
        self.db.add_user_rate(
            0, 'BTC', value=31_000, percent_delta=0.01, 
            check_times=['07:00', '09:00', '10:30']
        ) 
        user = models.user.User.from_dict(self.db.get_user(0))
        self.assertDictEqual(
            user.rates, 
            {
                'BRENT': {
                    'check_times': ['09:00', '18:00', '11:12'], 
                    'percent_delta': 0.2,
                    'value': 56.3
                },
                'BTC': {
                    'check_times': ['07:00', '09:00', '10:30'], 
                    'percent_delta': 0.01,
                    'value': 31000 
                }
            }
        )
        self.assertListEqual(
            [x for x in list(user) if not isinstance(x, dict)], 
            [0, 1, 0, 1, 1, 2, 'ru']
        )

    def test_add_dbuser(self):
        user = models.user.User(0)
        self.assertTrue(
            all([
                {k: {
                    'check_times': configs.settings.DEFAULT_CHECK_TIMES, 
                    'percent_delta': 0.01, 
                    'value': utils.get_default_rates(k, to_print=False).get(k)
                }} == {k: v}
                for k, v in user.rates.items()
            ])
        )
        self.assertListEqual(
            [x for x in list(user) if not isinstance(x, dict)], 
            [0, 1, 0, 0, 1, 0, 'en']
        )

    def test_change_dbuser(self):
        user = models.user.User(2)
        self.assertEqual(self.db.get_user(2)['timezone'], 0)  # timezone
        self.assertEqual(user.timezone, 0)
        user.update(timezone=+2)
        self.assertEqual(self.db.get_user(2)['timezone'], 2)  # timezone
        self.assertEqual(user.timezone, 2)
        with self.assertRaises(KeyError):
            user.update(ababgalgamaga=123)
        with self.assertRaises(ValueError):
            user.update(timezone=+20)

    def test_change_dbuser_rates(self):
        user = models.user.User(3)
        self.assertListEqual(
            user.rates.get('BRENT').get('check_times'), 
            configs.settings.DEFAULT_CHECK_TIMES
        )
        user.update_rates('BRENT', check_times=['09:00', '10:00', '11:00'])
        self.assertListEqual(
            user.rates.get('BRENT').get('check_times'), 
            ['09:00', '10:00', '11:00']
        )
        self.assertEqual(user.rates.get('BRENT').get('value'), 55)
        user.update_rates('BRENT', value=58.2)
        self.assertEqual(user.rates.get('BRENT').get('value'), 58.2)
        self.assertEqual(user.rates.get('BRENT').get('percent_delta'), 0.01)
        user.update_rates('BRENT', percent_delta=0.2)
        self.assertEqual(user.rates.get('BRENT').get('percent_delta'), 0.2)
        with self.assertRaises(KeyError):
            user.update_rates('BRENT', ababgalamaga=123123123)
        with self.assertRaises(TypeError):
            user.update_rates('BRENT', value='abcdef')

    def test_premium_dbuser(self):
        user = models.user.User(4)
        d1 = utils.dt.get_now().replace(year=2120)
        self.assertEqual(user.is_pro, 0)
        self.assertEqual(user.is_staff, 0)
        for k, v in user.rates.items():
            self.assertEqual(
                v.get('check_times'), 
                configs.settings.DEFAULT_CHECK_TIMES
            )
        user.init_premium(d1)
        self.assertEqual(user.is_pro, d1)
        self.assertEqual(user.is_staff, 0)
        for k, v in user.rates.items():
            self.assertEqual(
                v.get('check_times'), configs.settings.CHECK_TIMES
            )
        user.delete_premium()
        self.assertEqual(user.is_pro, 0)
        self.assertEqual(user.is_staff, 0)
        for k, v in user.rates.items():
            self.assertEqual(
                v.get('check_times'), configs.settings.DEFAULT_CHECK_TIMES
            )

    def test_staff_dbuser(self):
        user = models.user.User(5)
        d_test = utils.dt.get_now()
        self.assertEqual(user.is_pro, 0)
        self.assertEqual(user.is_staff, 0)
        for k, v in user.rates.items():
            self.assertEqual(
                v.get('check_times'), configs.settings.DEFAULT_CHECK_TIMES
            )
        user.init_staff()
        self.assertGreater(user.is_pro, d_test.replace(year=d_test.year + 2))
        self.assertEqual(user.is_staff, 1)
        for k, v in user.rates.items():
            self.assertEqual(
                v.get('check_times'), configs.settings.CHECK_TIMES
            )
        user.delete_staff()
        self.assertEqual(user.is_pro, 0)
        self.assertEqual(user.is_staff, 0)
        for k, v in user.rates.items():
            self.assertEqual(
                v.get('check_times'), configs.settings.DEFAULT_CHECK_TIMES
            )

    def test_add_dbuser_rates(self):
        user = models.user.User(6)
        self.assertEqual(len(user.rates), len(configs.settings.CURRENCIES))
        user.add_rate(
            'UAH', check_times=['09:00', '10:00', '12:00'], 
            value=0.03, percent_delta=0.05
        )
        self.assertEqual(len(user.rates), len(configs.settings.CURRENCIES) + 1)
        self.assertDictEqual(
            user.rates.get('UAH'), 
            dict(
                check_times=['09:00', '10:00', '12:00'], 
                value=0.03, percent_delta=0.05
            )
        )

    def test_delete_dbuser_rates(self):
        user = models.user.User(7)
        self.assertEqual(len(user.rates), len(configs.settings.CURRENCIES))
        user.add_rate("UAH")
        self.assertEqual(len(user.rates), len(configs.settings.CURRENCIES) + 1)
        with self.assertRaises(ValueError):
            user.delete_rate(configs.settings.CURRENCIES[0])
        with self.assertRaises(KeyError):
            user.delete_rate("ababagalamaga")
        user.delete_rate("UAH")
        self.assertEqual(len(user.rates), len(configs.settings.CURRENCIES))

    def test_get_currencies_by_check_time_dbuser(self):
        user = models.user.User(8)
        user.update_rates('BRENT', check_times=['09:00', '10:00', '11:00'])
        user.update_rates('RTS', check_times=['11:00', '12:00', '13:00'])
        user.update_rates('BTC', check_times=['13:00', '14:00', '15:00'])
        user.add_rate('UAH', check_times=['16:00', '17:00', '18:00'])
        self.assertDictEqual(
            user.get_currencies_by_check_time('11:00'),
            dict(BRENT=user.rates.get('BRENT'), RTS=user.rates.get("RTS"))
        )
        self.assertDictEqual(
            user.get_currencies_by_check_time('13:00'),
            dict(RTS=user.rates.get('RTS'), BTC=user.rates.get("BTC"))
        )
        self.assertDictEqual(
            user.get_currencies_by_check_time('18:00'),
            dict(UAH=user.rates.get('UAH'))
        )
        self.assertDictEqual(
            user.get_currencies_by_check_time('20:00'),
            dict()
        )

    def test_get_pro_users(self):
        user = models.user.User(9)
        self.assertEqual(len(list(models.user.User.get_pro_users())), 0)
        user.init_premium(utils.dt.get_now().replace(year=2120))
        self.assertEqual(len(list(models.user.User.get_pro_users())), 1)
        user.delete_premium()
        self.assertEqual(len(list(models.user.User.get_pro_users())), 0)

    def test_get_staff_users(self):
        user = models.user.User(10)
        self.assertEqual(len(list(models.user.User.get_pro_users())), 0)
        self.assertEqual(len(list(models.user.User.get_staff_users())), 0)
        user.init_staff()
        self.assertEqual(len(list(models.user.User.get_pro_users())), 1)
        self.assertEqual(len(list(models.user.User.get_staff_users())), 1)
        user.delete_staff()
        self.assertEqual(len(list(models.user.User.get_pro_users())), 0)
        self.assertEqual(len(list(models.user.User.get_staff_users())), 0)

    def test_get_all_users(self):
        self.assertEqual(len(list(models.user.User.get_all_users())), 0)
        models.user.User(11)
        self.assertEqual(len(list(models.user.User.get_all_users())), 1)
        self.tearDown()
        self.setUp()
        self.assertEqual(len(list(models.user.User.get_all_users())), 0)



class PredictionModelTestCase(BasicTestCase):
    def test_add_dbprediction(self):
        user = models.user.User(0)
        d1 = utils.dt.get_now().replace(year=2120)
        self.assertEqual(len(user.predictions), 0)
        user.create_prediction('BRENT', 'USD', value=55, up_to_date=d1)
        self.assertEqual(len(user.predictions), 1)
        pred = user.predictions[0]
        self.assertEqual(pred.iso_from, 'BRENT')
        self.assertEqual(pred.iso_to, 'USD')
        self.assertEqual(pred.value, 55)
        self.assertEqual(pred.up_to_date, d1)
        self.assertEqual(pred.real_value, None)
        with self.assertRaises(AssertionError):
            user.create_prediction(
                'BRENT', 'USD', value=55, up_to_date=d1.replace(year=1990)
            )
        with self.assertRaises(AssertionError):
            user.create_prediction('BRENT', 'USD', value=-55, up_to_date=d1)

    def test_change_future_dbprediction(self):
        user = models.user.User(0)
        d1 = utils.dt.get_now().replace(year=2120)
        user.create_prediction('BRENT', 'USD', value=55, up_to_date=d1)
        pred = user.predictions[0]
        self.assertEqual(pred.value, 55)
        pred.update(value=58)
        self.assertEqual(pred.value, 58)
        self.assertEqual(pred.is_by_experts, False)
        pred.update(is_by_experts=True)
        self.assertEqual(pred.is_by_experts, True)
        with self.assertRaises(AssertionError):
            pred.update(iso_from='RTS')
        with self.assertRaises(AssertionError):
            pred.update(iso_to='UAH')
        with self.assertRaises(AssertionError):
            pred.update(value=-10)
        with self.assertRaises(AssertionError):
            pred.update(real_value=-20)

    def test_toggle_like_dbprediction(self):
        u1 = models.user.User(0)
        u2 = models.user.User(1)
        u1.create_prediction(
            'BRENT', 'USD', value=55, 
            up_to_date=utils.dt.get_now().replace(year=2120)
        )
        pred = u1.predictions[0]
        self.assertEqual(pred.likes, 0)
        self.assertEqual(pred.dislikes, 0)
        pred.toggle_like(u1.id, True)
        self.assertEqual(pred.likes, 1)
        self.assertEqual(pred.dislikes, 0)
        pred.toggle_like(u2.id, False)
        self.assertEqual(pred.likes, 1)
        self.assertEqual(pred.dislikes, 1)
        pred.toggle_like(u2.id, True)
        self.assertEqual(pred.likes, 2)
        self.assertEqual(pred.dislikes, 0)

    def test_delete_dbprediction(self):
        user = models.user.User(0)
        user.create_prediction(
            'BRENT', 'USD', 
            value=55, up_to_date=utils.dt.get_now() + dt.timedelta(0, 2)
        )
        self.assertEqual(len(user.predictions), 1)
        p = user.predictions[0]
        p.delete()
        self.assertEqual(len(user.predictions), 0)
        user.create_prediction(
            'BRENT', 'USD', 
            value=55, up_to_date=utils.dt.get_now()
        )
        time.sleep(1)
        self.assertEqual(len(list(user.get_predictions(only_actual=False))), 1)
        with self.assertRaises(AssertionError):
            list(user.get_predictions(only_actual=False))[0].delete()
        self.assertEqual(len(list(user.get_predictions(only_actual=False))), 1)
        list(user.get_predictions(only_actual=False))[0].delete(force=True)
        self.assertEqual(len(list(user.get_predictions(only_actual=False))), 0)



class UtilsTestCase(unittest.TestCase):
    def test_merge_dicts(self):
        self.assertDictEqual(
            utils.merge_dicts({'one':1, 'two':2}), 
            {'one':1, 'two': 2}
        )
        self.assertDictEqual(
            utils.merge_dicts({'one': 1, 'two': 3}, {'two': 2}),
            {'one':1, 'two': 2}
        )
        with self.assertRaises(AssertionError):
            utils.merge_dicts()

    def test_prettify_utcoffset(self):
        self.assertEqual(utils.prettify_utcoffset(0), 'UTC')
        self.assertEqual(utils.prettify_utcoffset(2), 'UTC+02:00')
        self.assertEqual(utils.prettify_utcoffset(-5), 'UTC-05:00')
        self.assertEqual(utils.prettify_utcoffset(11), 'UTC+11:00')
        self.assertEqual(utils.prettify_utcoffset(-10), 'UTC-10:00')
        with self.assertRaises(AssertionError):
            utils.prettify_utcoffset(15)
        with self.assertRaises(AssertionError):
            utils.prettify_utcoffset(-18)

    def test_check_datetime_in_future(self):
        d = utils.dt.get_now().replace(year=2120)
        self.assertTrue(utils.dt.check_datetime_in_future(d))
        d = d.replace(year=2000)
        self.assertFalse(utils.dt.check_datetime_in_future(d))
        with self.assertRaises(AssertionError):
            utils.dt.check_datetime_in_future(
                dt.datetime.now().replace(
                    year=2120, tzinfo=dt.tzinfo(0, dt.timedelta(0, 3*3600))
                )
            )
        with self.assertRaises(AssertionError):
            utils.dt.check_datetime_in_future(
                dt.datetime.now().replace(
                    year=2000, tzinfo=dt.tzinfo(0, dt.timedelta(0, 3*3600))
                )
            )

    def test_adapt_datetime(self):
        start_dt = utils.dt.get_now().replace(hour=15)
        with self.assertRaises(AssertionError):
            utils.dt.adapt_datetime(start_dt, utcoffset=15)
        with self.assertRaises(AssertionError):
            utils.dt.adapt_datetime(start_dt, utcoffset=-12)
        result_dt = utils.dt.adapt_datetime(start_dt, utcoffset=3)
        self.assertIsNotNone(result_dt.tzinfo)
        self.assertEqual(result_dt.hour, 18)

    def test_convert_datetime(self):
        start_dt = utils.dt.get_now().replace(hour=15)
        with self.assertRaises(AssertionError):
            utils.dt.convert_datetime(start_dt, utcoffset=15)
        with self.assertRaises(AssertionError):
            utils.dt.convert_datetime(start_dt, utcoffset=-12)
        result_dt = utils.dt.convert_datetime(start_dt, 5)
        self.assertEqual(result_dt.hour, 10)

    def test_convert_check_times(self):
        start_check_times = ['09:00', '15:00', '21:00']
        with self.assertRaises(AssertionError):
            utils.dt.convert_check_times(start_check_times, utcoffset=15)
        with self.assertRaises(AssertionError):
            utils.dt.convert_check_times(start_check_times, utcoffset=-12)
        result_check_times = utils.dt.convert_check_times(
            start_check_times, utcoffset=3
        )
        self.assertListEqual(
            result_check_times, ['06:00', '12:00', '18:00']
        )

    def test_adapt_check_times(self):
        start_check_times = ['09:00', '15:00', '21:00']
        with self.assertRaises(AssertionError):
            utils.dt.adapt_check_times(start_check_times, utcoffset=15)
        with self.assertRaises(AssertionError):
            utils.dt.adapt_check_times(start_check_times, utcoffset=-12)
        result_check_times = utils.dt.adapt_check_times(
            start_check_times, utcoffset=1
        )
        self.assertListEqual(
            result_check_times, ['10:00', '16:00', '22:00']
        )



class SessionModelTestCase(BasicTestCase):
    def test_add_session(self):
        self.assertEqual(len(self.db.get_all_users()), 0)
        self.assertEqual(len(self.session_db.get_all_sessions()), 0)
        models.user.User(0)
        self.session_db.add_session(0)
        self.assertEqual(len(self.db.get_all_users()), 1)
        self.assertEqual(len(self.session_db.get_all_sessions()), 1)        

    def test_session_data(self):
        models.user.User(123)
        with self.assertRaises(models.exceptions.SessionDoesNotExistError):
            self.session_db.get_session(123)
        self.session_db.add_session(123)
        session = self.session_db.get_session(123)
        self.assertEqual(session['user_id'], 123)
        self.assertEqual(
            session['free_notifications_count'], 
            configs.settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER
        )
        self.session_db.delete_session(123)
        with self.assertRaises(models.exceptions.SessionDoesNotExistError):
            self.session_db.get_session(123)

    def test_session_fetch_count(self):
        models.user.User(123)
        self.session_db.add_session(123)
        self.assertEqual(
            self.session_db.fetch_count(123), 
            configs.settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER
        )
        self.assertEqual(
            self.session_db.fetch_count(123, with_decrease=True), 
            configs.settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER
        )
        self.assertEqual(
            self.session_db.fetch_count(123), 
            configs.settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER-1
        )
        session = self.session_db.get_session(123)
        self.assertEqual(
            session['free_notifications_count'], 
            configs.settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER-1
        )
        with self.assertRaises(models.exceptions.SessionDoesNotExistError):
            self.session_db.fetch_count(0)
        with self.assertRaises(models.exceptions.SessionDoesNotExistError):
            self.session_db.fetch_count(0, with_decrease=True)
        user = models.user.User(0)
        self.session_db.add_session(0)
        self.assertEqual(
            self.session_db.fetch_count(0), 
            configs.settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER
        )
        user.update(is_pro=utils.dt.get_now() + dt.timedelta(0, 24*60*60))
        self.assertEqual(self.session_db.fetch_count(0), 1)       
        user.update(is_pro=False) 
        self.assertEqual(
            self.session_db.fetch_count(0), 
            configs.settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER
        )

    def test_session_decrease_count(self):
        models.user.User(123)
        self.session_db.add_session(123)
        self.assertEqual(
            self.session_db.fetch_count(123), 
            configs.settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER
        )
        self.session_db.decrease_count(123)
        self.assertEqual(
            self.session_db.fetch_count(123), 
            configs.settings.DEFAULT_EXPERT_PREDICTIONS_NOTIFICATIONS_NUMBER-1
        )



if __name__ == '__main__':
    unittest.main()
