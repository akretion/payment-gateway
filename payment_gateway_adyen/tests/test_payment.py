# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com).
# @author Raphael Valyi <raphael.valyi@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# pylint: disable=missing-manifest-dependency
# disable warning on 'vcr' missing in manifest: this is only a dependency for
# dev/tests

import os
import unittest
import Adyen
import json
import requests
import logging
from vcr import VCR
from os.path import join, dirname

from odoo.exceptions import Warning as UserError
from odoo.tests.common import TransactionCase
from odoo.addons.component.tests.common import SavepointComponentCase

logging.getLogger("vcr").setLevel(logging.WARNING)

recorder = VCR(
    record_mode=os.environ.get('VCR_MODE', 'once'),
    cassette_library_dir=join(dirname(__file__), 'fixtures/cassettes'),
    path_transformer=VCR.ensure_suffix('.yaml'),
    filter_headers=['Authorization'],
)


class AdyenCommonCase(SavepointComponentCase):

    def setUp(self, *args, **kwargs):
        super(AdyenCommonCase, self).setUp(*args, **kwargs)
        self.adyen_api = os.environ.get('ADYEN_API')
        self.env['keychain.account'].create({
            'namespace': 'adyen',
            'name': 'Adyen',
            'clear_password': self.adyen_api,
            'technical_name': 'adyen',
            'data': """{
                "merchant_account": "AkretionCOM",
                "username": "ws@Company.Akretion",
                "platform": "test",
                "app_name": "shopinvader"
            }"""})
        self.sale = self.env.ref('sale.sale_order_2')
        self.account_payment_mode = self.env.ref(
            'payment_gateway_adyen.account_payment_mode_adyen')
        self.sale.write({'payment_mode_id': self.account_payment_mode.id})

    def _get_card(self, card):
        if isinstance(card, dict):
            return card
        else:
            return {
                   "number": card,
                   "expiryMonth": 10,
                   "expiryYear": 2020,
                   "cvc": '737',
                   "holderName": 'John Doe',
                   }

#    def _fill_3d_secure(self, source, success=True):
#        res = requests.get(source['redirect']['url'])
#        url = res._content.split('method="POST" action="')[1].split('">')[0]
#        requests.post(url, {'PaRes': 'success' if success else 'failure'})


class AdyenScenario(object):

#    @recorder.use_cassette
#    def test_create_transaction_3d_required_failed(self):
#        self._test_3d('4000000000003063', success=False)

#    @recorder.use_cassette
#    def test_create_transaction_3d_required_success(self):
#        self._test_3d('4000000000003063', success=True)

#    @recorder.use_cassette
#    def test_create_transaction_3d_optional_failed(self):
#        self._test_3d('4000000000003055', success=False)

#    @recorder.use_cassette
#    def test_create_transaction_3d_optional_success(self):
#        self._test_3d('4000000000003055', success=True)

#    @recorder.use_cassette
#    def test_create_transaction_3d_not_supported(self):
#        transaction, source = self._create_transaction('378282246310005')
#        self.assertEqual(transaction.state, 'succeeded')

    @recorder.use_cassette
    def test_create_transaction_visa(self):
        self._test_card('5136333333333335')

    @recorder.use_cassette
    def test_create_transaction_us(self):
        self._test_card('4400000000000008')
#                        expected_state='failed')

    @recorder.use_cassette
    def test_create_transaction_france(self):
        self._test_card('4977949494949497')

#    @recorder.use_cassette
#    def test_create_transaction_france(self):
#        self._test_card('4000002500000003')

#    @recorder.use_cassette
#    def test_create_transaction_risk_highest(self):
#        with self.assertRaises(UserError):
#            self._test_card(
#                '4100000000000019',
#                expected_state='failed',
#                expected_risk_level='unknown')

#    @recorder.use_cassette
#    def test_create_transaction_risk_elevated(self):
#        self._test_card(
#            '4000000000009235',
#            expected_risk_level='elevated')

    @recorder.use_cassette
    def test_create_transaction_wrong_cvc(self):
        with self.assertRaises(UserError):
            self._test_card(
                   {
                   "number": '4977949494949497',
                   "expiryMonth": 10,
                   "expiryYear": 2020,
                   "cvc": 'wrong',
                   "holderName": 'John Doe',
                   },
                expected_state='failed')


class AdyenCase(AdyenCommonCase, AdyenScenario):

    def _create_transaction(self, card):
        card = self._get_card(card)
        transaction = self.env['gateway.transaction'].generate(
            'adyen',
            self.sale,
            card=card,
            return_url='https://IwillBeBack.vd')
        return transaction, json.loads(transaction.data)

    def _check_captured(self, transaction, expected_state='succeeded',
                        expected_risk_level='normal'):
        self.assertEqual(transaction.state, expected_state)
        self.assertEqual(self.sale.amount_total, transaction.amount)
#        self.assertEqual(transaction.risk_level, expected_risk_level)

#    def _test_3d(self, card, success=True):
#        transaction, source = self._create_transaction(card)
#        self.assertEqual(transaction.state, 'pending')
#        self._fill_3d_secure(source, success=success)
#        transaction.check_state()
#        if success:
#            self._check_captured(transaction)
#        else:
#            self.assertEqual(transaction.state, 'failed')

    def _test_card(self, card, **kwargs):
        transaction, source = self._create_transaction(card)
        self._check_captured(transaction, **kwargs)
