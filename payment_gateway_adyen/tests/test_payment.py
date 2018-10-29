# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com).
# @author Raphael Valyi <raphael.valyi@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# pylint: disable=missing-manifest-dependency
# disable warning on 'vcr' missing in manifest: this is only a dependency for
# dev/tests

import os
import requests
import json
from lxml import etree
from io import StringIO
from os.path import dirname
from adyen_cse_python.encrypter import ClientSideEncrypter

from odoo.exceptions import UserError
from odoo.addons.payment_gateway.tests.common import (
    PaymentScenarioType,
    HttpComponentCase)


FAKE_KEY = (
    "10001|A052F4CD5F64C8DA05F0A75B7F679DC3049E2F9390664F87E6A444D042A12217D"
    "F199B787761BFA1427F1B4046FFFC1D298F5A3061EAA7F8C914A657739BC997DA59F8E2"
    "0BBA17667848D194BA6DA399166F78EDA04BD90D6A1DB33E0ED275E427C691CC7860D90"
    "DF09B417904004A5F2804F6703A4AF56A2CB40101EBC9EC775E150FFCDC05D7DE6EEA03"
    "F335F4958B222619B3973DFD365BD6E904768BE5C4583CD8BB3C48DC031E0CC427D22D8"
    "158AC5C2A1CA3EF3A51003C2DF784ACB4C5857E904F7DA41D6907C80006C4268D8CA3C9"
    "750BF5BBCB978D834E2BAAD69B45734E8A5011E8D6CAF6D22C2859391DFC84419A40256"
    "DBEC9B8E52FE1E0221EC5"
)

SHOPPER_IP = '42.42.42.42'
ACCEPT_HEADER =\
    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
USER_AGENT = (
    'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9) '
    'Gecko/2008052912 Firefox/3.0')


class AdyenCommonCase(HttpComponentCase):

    def setUp(self, *args, **kwargs):
        super(AdyenCommonCase, self).setUp(*args, **kwargs)
        self.adyen_api = os.environ.get('ADYEN_API', 'offline')
        self.env['keychain.account'].create({
            'namespace': 'adyen',
            'name': 'Adyen',
            'clear_password': self.adyen_api,
            'technical_name': 'adyen',
            'data': """{
                "merchant_account": "%s",
                "username": "%s",
                "platform": "test",
                "app_name": "shopinvader"
            }""" % (
                os.environ.get('ADYEN_ACCOUNT', 'offline'),
                os.environ.get('ADYEN_USER', 'offline')
                )})
        self.sale = self.env.ref('sale.sale_order_2')
        self.account_payment_mode = self.env.ref(
            'payment_gateway_adyen.account_payment_mode_adyen')
        self.sale.write({'payment_mode_id': self.account_payment_mode.id})
        self.cse = ClientSideEncrypter(
            os.environ.get('ADYEN_CRYPT_KEY', FAKE_KEY))

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

    def _get_encrypted_card(self, card):
        card = self._get_card(card)
        return self.cse.generate_adyen_nonce(
            card['holderName'],
            card['number'],
            card['cvc'],
            card['expiryMonth'],
            card['expiryYear'])

    def _fill_3d_secure(self, transaction, card_number, success=True):
        if not success:
            return 'failed validation'
        else:
            data = {
                'PaReq': transaction.meta['paRequest'],
                'MD': transaction.meta['MD'],
                'TermUrl': transaction.meta['termUrl'],
                }
            result = requests.post(transaction.url, data)
            session_id = result.headers['Set-Cookie'].split(
                'JSESSIONID=')[1].split(';')[0]
            validate_url = "https://test.adyen.com/hpp/3d/authenticate.shtml;\
                jsessionid=%s" % (session_id,)
            validation = requests.post(validate_url, data={
                'PaReq': transaction.meta['paRequest'],
                'MD': transaction.meta['MD'],
                'TermUrl': transaction.meta['termUrl'],
                'username': 'user',
                'password': 'password',
                'cardNumber': card_number
            })
            parser = etree.HTMLParser()
            tree = etree.parse(StringIO(validation.content.decode('utf-8')),
                               parser)
            e = tree.xpath("//input[@name='PaRes']")[0]
            pa_res = e.values()[2]
            return pa_res


class AdyenScenario(object):

    def test_create_transaction_3d_required_failed(self):
        self._test_3d('5212345678901234', success=False)

    def test_create_transaction_3d_required_success(self):
        self._test_3d('5212345678901234', success=True)

    def test_create_transaction_mastecard(self):
        self._test_card('5136333333333335')

    def test_create_transaction_us(self):
        self._test_card('4400000000000008')

    def test_create_transaction_france(self):
        self._test_card('4977949494949497')

    def test_create_transaction_wrong_cvc(self):
        with self.assertRaises(UserError):
            self._test_card({
                "number": '4977949494949497',
                "expiryMonth": 10,
                "expiryYear": 2020,
                "cvc": 'wrong',
                "holderName": 'John Doe',
                }, expected_state='failed')

    def test_create_transaction_wrong_number(self):
        with self.assertRaises(UserError):
            self._test_card({
                "number": '497794fail',
                "expiryMonth": 10,
                "expiryYear": 2020,
                "cvc": '737',
                "holderName": 'John Doe',
                }, expected_state='failed')

    def test_create_transaction_wrong_expiry(self):
        # NOTE that here Adyen returns a 000 error code
        # which doesn't point to a wrong expiry as documented
        # the message is correct but we decided not forward Adyen
        # messages blindly, so the error is said to be unknown...
        with self.assertRaises(UserError):
            self._test_card({
                "number": '4977949494949497',
                "expiryMonth": 13,
                "expiryYear": 2020,
                "cvc": '737',
                "holderName": 'John Doe',
                }, expected_state='failed')

    def test_wrong_api_key(self):
        keychain = self.env['keychain.account']
        account = keychain.sudo().retrieve([
            ('namespace', '=', 'adyen')
            ])[0]
        account.write({'clear_password': 'wrong_api_key'})
        with self.assertRaises(UserError):
            self._test_card('5136333333333335')


class AdyenCase(AdyenCommonCase, AdyenScenario):
    __metaclass__ = PaymentScenarioType
    _test_path = dirname(__file__)

    def _create_transaction(self, card):
        token = self._get_encrypted_card(card)
        transaction = self.env['gateway.transaction'].generate(
            'adyen',
            self.sale,
            token=token,
            return_url='https://IwillBeBack.vd',
            accept_header=ACCEPT_HEADER,
            user_agent=USER_AGENT,
            shopper_ip=SHOPPER_IP)
        return transaction, json.loads(transaction.data)

    def _check_captured(self, transaction, expected_state='succeeded',
                        expected_risk_level='normal'):
        self.assertEqual(transaction.state, expected_state)
        self.assertEqual(self.sale.amount_total, transaction.amount)

    def _test_3d(self, card, success=True):
        transaction, source = self._create_transaction(card)
        self.assertEqual(transaction.state, 'pending')
        pa_res = self._fill_3d_secure(transaction, card, success=success)
        params = {
            'md': source['md'],
            'pares': pa_res,
            'accept_header': ACCEPT_HEADER,
            'user_agent': USER_AGENT,
            'shopper_ip': SHOPPER_IP,
        }
        if success:
            with transaction._get_provider('adyen') as provider:
                provider.process_return(**params)
            self._check_captured(transaction)
        else:
            with self.assertRaises(UserError):
                with transaction._get_provider('adyen') as provider:
                    provider.process_return(**params)
            self.assertIn(transaction.state, ['pending', 'failed'])

    def _test_card(self, card, **kwargs):
        transaction, source = self._create_transaction(card)
        self._check_captured(transaction, **kwargs)
