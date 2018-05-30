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

from odoo.exceptions import Warning as UserError
from odoo.addons.payment_gateway.tests.common import (
    RecordedScenario,
    HttpSavepointComponentCase)


class AdyenCommonCase(HttpSavepointComponentCase):

    def setUp(self, *args, **kwargs):
        super(AdyenCommonCase, self).setUp(*args, **kwargs)
        self.adyen_api = os.environ.get('ADYEN_API')
        encryption_key = """10001|ADCCEED8EC3760415BF83DAD23F41A33CE93B749EE984\
AE8A4B00572913728C7A8B5E8834D05E506DE378E89F58B80D609096E851B78492C55283F05B50A\
CCB3735A046FE6F9805F7DEB49DCD23E18F8466D3682511103F142063E314173CA961DABF2C57A9\
60DE8BD86A8AC25457FAFA2181321E84BE7A10F88692F97A1BA5253F247C9A18545FAF2AC37A69A\
5A1F5F974923FF43DBF9054008FAFC0F712CB4381608CF8C737A0AB5B6D906E1A503BE82EF652A8\
949B7B37D525EFEEFB6EFECBD2BCB1F807677F3BC73441028D64B7C36345BD9A39CCC43B738AF5A\
25E6950BA6EBFD1CF6A49FE6003056F9B8627D3EAC112ED77C04947EEC9B38AA9886EC1B"""
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
        self.cse = ClientSideEncrypter(encryption_key)

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

    def _fill_3d_secure(self, source, card_number, success=True):
        url = source['issuerUrl']
        webhook_url = 'http://yourserver.com/process_return'
        data = {
                   'PaReq': source['paRequest'],
                   'MD': source['md'],
                   'TermUrl': webhook_url,
               }
        result = requests.post(url, data)
        session_id = result.headers['Set-Cookie'].split(
            'JSESSIONID=')[1].split(';')[0]
        validate_url = "https://test.adyen.com/hpp/3d/authenticate.shtml;\
            jsessionid=%s" % (session_id,)
        validation = requests.post(validate_url, data={
            'PaReq': source['paRequest'],
            'MD': source['md'],
            'TermUrl': webhook_url,
            'username': 'user',
            'password': 'password',
            'cardNumber': card_number
        })
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(validation.content.decode('utf-8')), parser)
        e = tree.xpath("//input[@name='PaRes']")[0]
        pa_res = e.values()[2]
        return pa_res


class AdyenScenario(RecordedScenario):

    def test_create_transaction_3d_required_failed(self):
        self._test_3d('5212345678901234', success=False)

    def test_create_transaction_3d_required_success(self):
        self._test_3d('5212345678901234', success=True)

    def test_create_transaction_visa(self):
        self._test_card('5136333333333335')

    def test_create_transaction_us(self):
        self._test_card('4400000000000008')

    def test_create_transaction_france(self):
        self._test_card('4977949494949497')

#    def test_create_transaction_risk_elevated(self):
#        self._test_card(
#            '4000000000009235',
#            expected_risk_level='elevated')

    def test_create_transaction_wrong_cvc(self):
        with self.assertRaises(UserError):
            self._test_card({
                                "number": '4977949494949497',
                                "expiryMonth": 10,
                                "expiryYear": 2020,
                                "cvc": 'wrong',
                                "holderName": 'John Doe',
                            },
                            expected_state='failed')


class AdyenCase(AdyenCommonCase, AdyenScenario):

    def __init__(self, *args, **kwargs):
        super(AdyenCase, self).__init__(*args, **kwargs)
        self._decorate_test(dirname(__file__))

    def _create_transaction(self, card):
        card = self._get_card(card)
        encrypted_card = self.cse.generate_adyen_nonce(card['holderName'],
                                                       card['number'],
                                                       card['cvc'],
                                                       card['expiryMonth'],
                                                       card['expiryYear'])
        transaction = self.env['gateway.transaction'].generate(
            'adyen',
            self.sale,
            encrypted_card=encrypted_card,
            return_url='https://IwillBeBack.vd')
        return transaction, json.loads(transaction.data)

    def _check_captured(self, transaction, expected_state='succeeded',
                        expected_risk_level='normal'):
        self.assertEqual(transaction.state, expected_state)
        self.assertEqual(self.sale.amount_total, transaction.amount)
#        self.assertEqual(transaction.risk_level, expected_risk_level)

    def _test_3d(self, card, success=True):
        transaction, source = self._create_transaction(card)
        self.assertEqual(transaction.state, 'pending')
        pa_res = self._fill_3d_secure(source, card, success=success)
        params = {
            'MD': source['md'],
            'PaRes': pa_res
        }
        if success:
            with transaction._get_provider('adyen') as provider:
                provider.process_return(**params)
            self._check_captured(transaction)
        else:
            params['PaRes'] = 'failed validation'
            with self.assertRaises(UserError):
                with transaction._get_provider('adyen') as provider:
                    provider.process_return(**params)
            self.assertIn(transaction.state, ['pending', 'failed'])

    def _test_card(self, card, **kwargs):
        transaction, source = self._create_transaction(card)
        self._check_captured(transaction, **kwargs)
