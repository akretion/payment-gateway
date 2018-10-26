# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from os.path import dirname
from .paypal_mock import (
    paypal_mock,
    PaypalPaymentSuccess,
    PaypalPaymentPending,
    REDIRECT_URL)
from odoo.addons.payment_gateway.tests.common import (
    PaymentScenarioType,
    HttpSavepointComponentCase)
import paypalrestsdk


class PaypalCommonCase(HttpSavepointComponentCase):

    def setUp(self, *args, **kwargs):
        super(PaypalCommonCase, self).setUp(*args, **kwargs)
        self.env['keychain.account'].create({
            'namespace': 'paypal',
            'name': 'Paypal',
            'clear_password': 'test',
            'technical_name': 'paypal',
            'data': """{
                "client_id": "ycezvezv3448cdyvuvkrzoz98765gcxzgc",
                "experience_profile_id": "LX-39DK-DI4IH-EOD3-KDO0"
            }""",
            })
        self.sale = self.env.ref('sale.sale_order_2')
        self.account_payment_mode = self.env.ref(
            'payment_gateway_paypal.account_payment_mode_paypal')
        self.sale.write({'payment_mode_id': self.account_payment_mode.id})

    def _check_payment_create_sale_order(self, redirect_url):
        transaction = self.sale.transaction_ids
        self.assertEqual(len(transaction), 1)
        paypalrestsdk.Payment.assert_called_with({
            'redirect_urls': {
                'cancel_url': REDIRECT_URL['redirect_cancel_url'],
                'return_url': REDIRECT_URL['return_url']
            },
            'experience_profile_id': u"LX-39DK-DI4IH-EOD3-KDO0",
            'intent': 'sale',
            'payer': {
                'payment_method': 'paypal',
                },
            'transactions': [{
                'amount': {
                    'currency': u'USD',
                    'total': "2947.50",
                    },
                'description':
                    u'SO002|deltapc@yourcompany.example.com|%s' %
                    transaction.id},
            ]}, api="123")

        self.assertEqual(transaction.name, self.sale.name)
        self.assertEqual(
            transaction.payment_mode_id, self.account_payment_mode)
        self.assertEqual(
            transaction.external_id,
            paypalrestsdk.Payment.transaction['id'])
        self.assertEqual(transaction.capture_payment, 'immediately')
        self.assertEqual(transaction.amount, self.sale.amount_total)
#        self.assertEqual(transaction.sale_id, self.sale)  TODO
        self.assertEqual(transaction.state, 'pending')


class PaypalCase(PaypalCommonCase):
    __metaclass__ = PaymentScenarioType
    _test_path = dirname(__file__)

    def test_create_transaction(self):
        with paypal_mock(PaypalPaymentSuccess):
            self.env['gateway.transaction'].generate(
                'paypal', self.sale, **REDIRECT_URL)
            self._check_payment_create_sale_order(REDIRECT_URL)

    def test_execute_transaction(self):
        with paypal_mock(PaypalPaymentSuccess):
            transaction = self.env['gateway.transaction'].generate(
                'paypal', self.sale, **REDIRECT_URL)
            transaction.capture()

    def test_failing_execute_transaction(self):
        with paypal_mock(PaypalPaymentPending):
            transaction = self.env['gateway.transaction'].generate(
                'paypal', self.sale, **REDIRECT_URL)
            transaction.capture()
            self.assertEqual(transaction.state, 'failed')
            self.assertNotEqual(transaction.error, '')
