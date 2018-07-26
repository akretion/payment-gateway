# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os
import json
import requests
import stripe
from os.path import dirname

from odoo.exceptions import UserError
from odoo.addons.payment_gateway.tests.common import (
    RecordedScenario,
    HttpSavepointComponentCase,
    JSON_WEBHOOK_PATH)


class StripeCommonCase(HttpSavepointComponentCase):

    def setUp(self, *args, **kwargs):
        super(StripeCommonCase, self).setUp(*args, **kwargs)
        self.stripe_api = os.environ.get('STRIPE_API', 'offline')
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
        self.base_url = self.env['ir.config_parameter']\
            .get_param('web.base.url')

    def _get_source(self, card):
        return stripe.Source.create(
            type='card',
            card={
                "number": card,
                "exp_month": 12,
                "exp_year": 2040,
                "cvc": '123'
            }, api_key=self.stripe_api)

    def _fill_3d_secure(self, transaction, success=True):
        res = requests.get(transaction.url)
        url = res._content.split('method="POST" action="')[1].split('">')[0]
        requests.post(url, {'PaRes': 'success' if success else 'failure'})

    def _simulate_webhook(self, transaction):
        self._init_job_counter()
        # We only mock the data that we are interested in
        event = {'data': {'object': {'id': transaction.external_id}}}
        # Commit transaction (fake commit on test cursor)
        self.env.cr.commit()
        hook_url = self.base_url + JSON_WEBHOOK_PATH + '/stripe/process_event'
        r = requests.post(hook_url, json=event)
        self.assertEqual(r.status_code, 200)
        self._check_nbr_job_created(1)
        self._perform_created_job()

    def _check_captured(self, transaction, expected_state='succeeded',
                        expected_risk_level='normal'):
        self.assertEqual(transaction.state, expected_state)
        charge = json.loads(transaction.data)
        self.assertEqual(self.sale.amount_total, transaction.amount)
        self.assertEqual(charge['amount'], int(transaction.amount*100))
        self.assertEqual(transaction.risk_level, expected_risk_level)


class StripeScenario(RecordedScenario):

    def test_create_transaction_3d_required_failed(self):
        self._test_3d('4000000000003063', success=False)

    def test_create_transaction_3d_required_success(self):
        self._test_3d('4000000000003063', success=True)

    def test_create_transaction_3d_optional_failed(self):
        self._test_3d('4000000000003055', success=False)

    def test_create_transaction_3d_optional_success(self):
        self._test_3d('4000000000003055', success=True)

    def test_create_transaction_3d_required_failed_webhook(self):
        self._test_3d('4000000000003063', success=False, mode='webhook')

    def test_create_transaction_3d_required_success_webhook(self):
        self._test_3d('4000000000003063', success=True, mode='webhook')

    def test_create_transaction_3d_optional_failed_webhook(self):
        self._test_3d('4000000000003055', success=False, mode='webhook')

    def test_create_transaction_3d_optional_success_webhook(self):
        self._test_3d('4000000000003055', success=True, mode='webhook')

    def test_create_transaction_3d_not_supported(self):
        transaction, source = self._create_transaction('378282246310005')
        self.assertEqual(transaction.state, 'succeeded')

    def test_create_transaction_visa(self):
        self._test_card('4242424242424242')

    def test_create_transaction_brazil(self):
        self._test_card('4000000760000002')

    def test_create_transaction_france(self):
        self._test_card('4000002500000003')

    def test_create_transaction_france(self):
        self._test_card('4000002500000003')

    def test_create_transaction_risk_highest(self):
        with self.assertRaises(UserError):
            self._test_card(
                '4100000000000019',
                expected_state='failed',
                expected_risk_level='unknown')

    def test_create_transaction_risk_elevated(self):
        self._test_card(
            '4000000000009235',
            expected_risk_level='elevated')

    def test_create_transaction_expired_card(self):
        with self.assertRaises(UserError):
            self._test_card(
                '4000000000000069',
                expected_state='failed',
                expected_risk_level='unknown')


class StripeCase(StripeCommonCase, StripeScenario):

    def __init__(self, *args, **kwargs):
        super(StripeCase, self).__init__(*args, **kwargs)
        self._decorate_test(dirname(__file__))

    def _simulate_return(self, transaction):
        with transaction._get_provider('stripe') as provider:
            provider.process_return(source=transaction.external_id)

    def _test_3d(self, card, success=True, mode='return'):
        transaction, source = self._create_transaction(card)
        self.assertEqual(transaction.state, 'pending')
        self._fill_3d_secure(transaction, success=success)

        if mode == 'webhook':
            self._simulate_webhook(transaction)
        else:
            self._simulate_return(transaction)

        if success:
            self._check_captured(transaction)
        else:
            self.assertEqual(transaction.state, 'failed')
        self.assertEqual(transaction.used_3d_secure, True)

    def _create_transaction(self, card):
        source = self._get_source(card)
        transaction = self.env['gateway.transaction'].generate(
            'stripe',
            self.sale,
            token=source['id'],
            return_url='https://IwillBeBack.vd')
        return transaction, json.loads(transaction.data)

    def _test_card(self, card, **kwargs):
        transaction, source = self._create_transaction(card)
        self._check_captured(transaction, **kwargs)
        self.assertEqual(transaction.used_3d_secure, False)

    def test_config(self):
        self.assertEqual(
            self.account_payment_mode._get_allowed_capture_method(),
            ['immediately'])
