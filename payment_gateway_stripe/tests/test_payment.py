# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import os
import unittest
import stripe
import json
import requests

from odoo.exceptions import Warning as UserError
from odoo.tests.common import TransactionCase
from odoo.addons.component.tests.common import SavepointComponentCase

from vcr import VCR

logging.getLogger("vcr").setLevel(logging.WARNING)

recorder = VCR(
    record_mode='once',
    cassette_library_dir=join(dirname(__file__), 'fixtures/cassettes'),
    path_transformer=VCR.ensure_suffix('.yaml'),
    filter_headers=['Authorization'],
)


@unittest.skipUnless(
    os.environ.get('STRIPE_API'),
    "Missing stripe connection environment variables")
class StripeCommonCase(SavepointComponentCase):

    def setUp(self, *args, **kwargs):
        super(StripeCommonCase, self).setUp(*args, **kwargs)
        self.stripe_api = os.environ.get('STRIPE_API')
        self.env['keychain.account'].create({
            'namespace': 'stripe',
            'name': 'Stripe',
            'clear_password': self.stripe_api,
            'technical_name': 'stripe',
            'data': "{}"})
        self.sale = self.env.ref('sale.sale_order_2')
        self.account_payment_mode = self.env.ref(
            'payment_gateway_stripe.account_payment_mode_stripe')
        self.sale.write({'payment_mode_id': self.account_payment_mode.id})

    def _get_source(self, card):
        return stripe.Source.create(
            type='card',
            card={
                "number": card,
                "exp_month": 12,
                "exp_year": 2040,
                "cvc": '123'
            }, api_key=self.stripe_api)

    def _fill_3d_secure(self, source, success=True):
        res = requests.get(source['redirect']['url'])
        url = res._content.split('method="POST" action="')[1].split('">')[0]
        requests.post(url, {'PaRes': 'success' if success else 'failure'})


class StripeScenario(object):

    @recorder.use_cassette
    def test_create_transaction_3d_required_failed(self):
        self._test_3d('4000000000003063', success=False)

    @recorder.use_cassette
    def test_create_transaction_3d_required_success(self):
        self._test_3d('4000000000003063', success=True)

    @recorder.use_cassette
    def test_create_transaction_3d_optional_failed(self):
        self._test_3d('4000000000003055', success=False)

    @recorder.use_cassette
    def test_create_transaction_3d_optional_success(self):
        self._test_3d('4000000000003055', success=True)

    @recorder.use_cassette
    def test_create_transaction_3d_not_supported(self):
        transaction, source = self._create_transaction('378282246310005')
        self.assertEqual(transaction.state, 'succeeded')

    @recorder.use_cassette
    def test_create_transaction_visa(self):
        self._test_card('4242424242424242')

    @recorder.use_cassette
    def test_create_transaction_brazil(self):
        self._test_card('4000000760000002')

    @recorder.use_cassette
    def test_create_transaction_france(self):
        self._test_card('4000002500000003')

    @recorder.use_cassette
    def test_create_transaction_france(self):
        self._test_card('4000002500000003')

    @recorder.use_cassette
    def test_create_transaction_risk_highest(self):
        with self.assertRaises(UserError):
            self._test_card(
                '4100000000000019',
                expected_state='failed',
                expected_risk_level='unknown')

    @recorder.use_cassette
    def test_create_transaction_risk_elevated(self):
        self._test_card(
            '4000000000009235',
            expected_risk_level='elevated')

    @recorder.use_cassette
    def test_create_transaction_expired_card(self):
        with self.assertRaises(UserError):
            self._test_card(
                '4000000000000069',
                expected_state='failed',
                expected_risk_level='unknown')


class StripeCase(StripeCommonCase, StripeScenario):

    def _create_transaction(self, card):
        source = self._get_source(card)
        transaction = self.env['gateway.transaction'].generate(
            'stripe',
            self.sale,
            source=source['id'],
            return_url='https://IwillBeBack.vd')
        return transaction, json.loads(transaction.data)

    def _check_captured(self, transaction, expected_state='succeeded',
                        expected_risk_level='normal'):
        self.assertEqual(transaction.state, expected_state)
        charge = json.loads(transaction.data)
        self.assertEqual(self.sale.amount_total, transaction.amount)
        self.assertEqual(charge['amount'], int(transaction.amount*100))
        self.assertEqual(transaction.risk_level, expected_risk_level)

    def _test_3d(self, card, success=True):
        transaction, source = self._create_transaction(card)
        self.assertEqual(transaction.state, 'pending')
        self._fill_3d_secure(source, success=success)
        transaction.check_state()
        if success:
            self._check_captured(transaction)
        else:
            self.assertEqual(transaction.state, 'failed')

    def _test_card(self, card, **kwargs):
        transaction, source = self._create_transaction(card)
        self._check_captured(transaction, **kwargs)
