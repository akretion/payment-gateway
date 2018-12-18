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
    HttpComponentCase)
import paypalrestsdk
from odoo.exceptions import  UserError


class PaypalCommonCase(HttpComponentCase):

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


class PaypalScenario(object):

    def _create_transaction(self):
        # Should be implemented on your test case
        # This method should create and return a transsaction
        raise NotImplemented

    def _simultate_return(self):
        # Should be implemented on your real test case
        # this method should simulate the return from the paypal
        # website on your website and so the processing of the
        # transaction
        raise NotImplemented

    def _expected_cancel_url(self):
        return REDIRECT_URL['redirect_cancel_url']

    def _expected_return_url(self):
        return REDIRECT_URL['return_url']

    def _check_payment_create_sale_order(self, transaction):
        paypalrestsdk.Payment.assert_called_with({
            'redirect_urls': {
                'cancel_url': self._expected_cancel_url(),
                'return_url': self._expected_return_url(),
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
        self.assertEqual(transaction.origin_id, self.sale)
        self.assertEqual(transaction.state, 'pending')

    def _check_successfull_return(self, transaction, result):
        self.assertEqual(transaction.state, 'succeeded')

    def _check_failing_return(self, transaction, result):
        self.assertEqual(transaction.state, 'failed')

    def test_create_transaction(self):
        with paypal_mock(PaypalPaymentSuccess):
            transaction = self._create_transaction(**REDIRECT_URL)
            self._check_payment_create_sale_order(transaction)

    def test_execute_transaction(self):
        with paypal_mock(PaypalPaymentSuccess):
            transaction = self._create_transaction(**REDIRECT_URL)
            result = self._simulate_return(transaction.external_id)
            self._check_successfull_return(transaction, result)

    def test_failing_execute_transaction(self):
        with paypal_mock(PaypalPaymentPending):
            transaction = self._create_transaction(**REDIRECT_URL)
            result = self._simulate_return(transaction.external_id)
            self._check_failing_return(transaction, result)
            self.assertEqual(transaction.state, 'failed')
            self.assertNotEqual(transaction.error, '')

    def test_wrong_transaction(self):
        with paypal_mock(PaypalPaymentSuccess):
            transaction = self._create_transaction(**REDIRECT_URL)
            with self.assertRaises(UserError):
                self._simulate_return('wrong_transaction_id')


class PaypalCase(PaypalCommonCase, PaypalScenario):

    def _create_transaction(self, **REDIRECT_URL):
        self.env['gateway.transaction'].generate(
            'paypal', self.sale, **REDIRECT_URL)
        transaction = self.sale.transaction_ids
        self.assertEqual(len(transaction), 1)
        return transaction

    def _simulate_return(self, transaction_id):
        with self.env['gateway.transaction']._get_provider('paypal')\
                as provider:
            return provider.process_return(paymentId=transaction_id)
