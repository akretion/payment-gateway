# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from .paypal_mock import (
    paypal_mock,
    PaypalPaymentSuccess,
    PaypalPaymentPending,
    REDIRECT_URL)
from openerp.tests.common import TransactionCase
from openerp.exceptions import Warning as UserError
import paypalrestsdk


class PaypalCommonCase(TransactionCase):

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
        self.payment_method = self.env.ref(
            'payment_gateway_paypal.payment_method_paypal')
        self.sale.write({'payment_method_id': self.payment_method.id})

    def _check_payment_create_sale_order(self):
        paypalrestsdk.Payment.assert_called_with({
            'redirect_urls': REDIRECT_URL,
            'experience_profile_id': "LX-39DK-DI4IH-EOD3-KDO0",
            'intent': 'sale',
            'payer': {
                'payment_method': 'paypal',
                },
            'transactions': [{
                'amount': {
                    'currency': u'EUR',
                    'total': 2947.5,
                    },
                'description':
                    u'SO002|wealthyandsons@yourcompany.example.com'},
            ]}, api="123")

        transaction = self.sale.transaction_ids
        self.assertEqual(len(transaction), 1)
        self.assertEqual(transaction.name, self.sale.name)
        self.assertEqual(
            transaction.payment_method_id, self.payment_method)
        self.assertEqual(
            transaction.external_id,
            paypalrestsdk.Payment.transaction['id'])
        self.assertEqual(transaction.capture_payment, 'immediately')
        self.assertEqual(transaction.amount, self.sale.amount_total)
        self.assertEqual(transaction.sale_id, self.sale)
        self.assertEqual(transaction.state, 'pending')


class PaypalCase(PaypalCommonCase):

    def test_create_transaction(self):
        with paypal_mock(PaypalPaymentSuccess):
            self.env['payment.service.paypal'].generate(
                self.sale, **REDIRECT_URL)
            self._check_payment_create_sale_order()

    def test_execute_transaction(self):
        with paypal_mock(PaypalPaymentSuccess):
            self.env['payment.service.paypal'].generate(
                self.sale, **REDIRECT_URL)
            transaction = self.sale.transaction_ids
            transaction.capture()

    def test_failing_execute_transaction_no_raise(self):
        with paypal_mock(PaypalPaymentPending):
            self.env['payment.service.paypal'].generate(
                self.sale, **REDIRECT_URL)
            transaction = self.sale.transaction_ids
            transaction.capture(raise_error=False)
            self.assertEqual(transaction.state, 'failed')
            self.assertNotEqual(transaction.error, '')

    def test_failing_execute_transaction(self):
        with paypal_mock(PaypalPaymentPending):
            self.env['payment.service.paypal'].generate(
                self.sale, **REDIRECT_URL)
            transaction = self.sale.transaction_ids
            with self.assertRaises(UserError):
                transaction.capture()
