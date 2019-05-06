# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from mock import Mock
from contextlib import contextmanager
import paypalrestsdk
from datetime import datetime
import copy

REDIRECT_URL = {
    'redirect_cancel_url': 'https://IamGoingToKickYourAssIfYouDoNotPaid.com',
    'redirect_success_url': 'https://ThanksYou.com',
    'return_url': 'https://ThanksYou.com',
    }


class PaypalPaymentSuccess(Mock):

    def __call__(self, data, api=None):
        super(PaypalPaymentSuccess, self).__call__(data, api=api)
        self.data = data
        self.api = api
        return self

    def __getitem__(self, key):
        return self.transaction[key]

    # pylint: disable=W8106
    def create(self):
        self.transaction = copy.deepcopy(self.data)
        self.transaction.update({
            'links': [{
                'href': u'http://get',
                'method': u'GET',
                'rel': u'self',
            }, {
                'href': u'https://redirect',
                'method': u'REDIRECT',
                'rel': u'approval_url',
            }, {
                'href': u'https://post',
                'method': u'POST',
                'rel': u'execute',
            }],
            'state': u'created',
            'create_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'id': u'PAY-49DJDKZCIVJZVZALDEVVU334',
        })
        return True

    def to_dict(self):
        return self.transaction

    def find(self, transaction_id, api=None):
        self.transaction.update({
            'payer': {
                'payment_method': u'paypal',
                'status': u'VERIFIED',
                'payer_info': {
                    'first_name': u'Harry',
                    'last_name': u'BEAU',
                    'email': u'beau.harry@akretion.com',
                    'country_code': u'FR',
                    'payer_id': u'4FRJVJRVRNBRE',
                    }
                }
            })
        return self

    def execute(self, params):
        self.transaction.update({
            'state': 'approved',
            })
        return True


class PaypalPaymentNoPayer(PaypalPaymentSuccess):

    def find(self, transaction_id, api=None):
        return self


class PaypalPaymentWrongState(PaypalPaymentSuccess):

    def execute(self, params):
        return True


@contextmanager
def paypal_mock(payment_class):
    paypalrestsdk.Api = Mock(return_value='123')
    paypalrestsdk.Payment = payment_class()
    yield True
