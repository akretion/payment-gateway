# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com).
# @author Raphael Valyi <raphael.valyi@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import Warning as UserError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.addons.component.core import Component
import json
import logging
_logger = logging.getLogger(__name__)

try:
    import Adyen
except ImportError:
    _logger.debug('Cannot import Adyen')


MAP_SOURCE_STATE = {  # TODO check if complete
    '[cancel-received]': 'cancel',
    'Authorised': 'to_capture',
    'consumed': 'succeeded',
    'Refused': 'failed',
    'RedirectShopper': 'pending',
    '[capture-received]': 'succeeded'}

# decimal points of currencies https://docs.adyen.com/developers/currency-codes
ZERO_DECIMAL_CURRENCIES = [
    u'CVE', u'DJF', u'GNF', u'IDR', u'JPY', u'KMF', u'KRW', u'PYG',
    u'RWF', u'UGX', u'VND', u'VUV', u'XAF', u'XOF', u'XPF',
],

THREE_DECIMAL_CURRENCIES = [
    u'BHD', u'JOD', u'KWD', u'LYD', u'OMR', u'TND'
]


class PaymentService(Component):
    _inherit = 'payment.service'
    _name = 'payment.service.adyen'
    _usage = 'adyen'
    _allowed_capture_method = ['immediately']
    _webhook_method = ['process_event']

    def process_return(self, **params):
        payload = {}
        payload["browserInfo"] = {
            "userAgent": "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9) Gecko/2008052912 Firefox/3.0",
            "acceptHeader": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        payload["md"] = params['MD']
        payload["paResponse"] = params['PaRes']
        transaction = None
        try:
            result = self._get_adyen_client().authorise3d(request=payload)
            vals = {
                'state': MAP_SOURCE_STATE[result.message['resultCode']],
                'data': json.dumps(result.message),
            }

            transaction = self.env['gateway.transaction'].search([
                ('external_id', '=', result.message['pspReference']),
                ('payment_mode_id.provider', '=', 'adyen'),
                ])
        except ValueError as e:
            # NOTE catch orther errors?
            # do we want to cancel the transaction? Can we do it?
            raise UserError(e.message)

        if transaction:
            transaction.write(vals)
        else:
            raise UserError(
                _('The transaction %s do not exist in Odoo') % result.message[
                    'pspReference'])

    def _validator_process_event(self):
        return {
            'data': {
                'type': 'dict',
                'schema': {
                    'object': {
                        'type': 'dict',
                        'schema': {
                            'MD': {'type': 'string'},
                            'PaRes': {'type': 'string'},
                        }
                    }
                }
            }
        }

    def _get_formatted_amount(self, amount=None):
        if amount is None:
            amount = self.collection._get_amount_to_capture()
        if self.collection.currency_id.name in ZERO_DECIMAL_CURRENCIES:
            return int(amount)
        elif self.collection.currency_id.name in THREE_DECIMAL_CURRENCIES:
            return int(float_round(amount * 1000, 0))
        else:
            return int(float_round(amount * 100, 0))

    def _prepare_charge(self, source=None, **kwargs):
        transaction = self.collection
        description = "|".join([
            transaction.name,
            transaction.partner_id.email,
            str(transaction.id)])
        # For now capture is always true as only the policy 'immedialtely' is
        # available in the configuration but it will be easier to implement
        # the logic of defeared capture
        capture = transaction.capture_payment == 'immediately'
        return {
                   'amount':  {"value": self._get_formatted_amount(),
                               "currency": transaction.currency_id.name},
                   'card': kwargs['card'],
                   'reference': description,
                   'additionalData': {"executeThreeD": "true"}  # TODO add CSE
               }

    def _get_adyen_client(self):
        account = self._get_account()
        data = account.get_data()
        ady = Adyen.Adyen()
        ady.payment.client.username = data['username']
        ady.payment.client.platform = str(data['platform'])
        ady.payment.client.merchant_account = data['merchant_account']
        ady.payment.client.password = account._get_password()
        ady.payment.client.app_name = data['app_name']
        return ady.payment

    def _create_transaction(self, source=None, **kwargs):
        try:
            return self._get_adyen_client().authorise(
                request=self._prepare_charge(source=source, **kwargs))
        except ValueError as e:  # TODO catch orther errors?
            raise UserError(e.message)

    def _parse_creation_result(self, transaction, **kwargs):
        # TODO does it make sense to call super with the specific AdyenResult
        # object?
        res = super(PaymentService, self).\
            _parse_creation_result(transaction, **kwargs)
        transaction = transaction.message
        res.update({
            'amount': self.collection._get_amount_to_capture(),
            'external_id': transaction['pspReference'],
            'state': MAP_SOURCE_STATE[transaction['resultCode']],
            'data': json.dumps(transaction),
        })
        if transaction.get('redirect', {}).get('url'): # TODO
            res['url'] = transaction['redirect']['url']
        risk_level = transaction.get('outcome', {}).get('risk_level')
        if risk_level: # TODO
            res['risk_level'] = risk_level
        return res

    # code for getting the state of the current transaction

    def get_state(self):
        source = stripe.Source.retrieve(
            self.collection.external_id, api_key=self._api_key)
        return MAP_SOURCE_STATE[source['status']]

    # Code for capturing the transaction

    def _parse_capture_result(self, charge):
        return {
            'external_id': charge['pspReference'],
            'state': MAP_SOURCE_STATE[str(charge['response'])],
#            'risk_level': charge.get('outcome', {}).get('risk_level'), # TODO
            'data': json.dumps(charge),
        }

    def _prepare_capture_payload(self):
        transaction = self.collection
        return {
            'originalReference': transaction.external_id,
            'modificationAmount': {'currency': transaction.currency_id.name,
                                   'value': self._get_formatted_amount(
                                       transaction.amount)}
            }

    def capture(self):
        if self.collection.external_id.isdigit():
            payload = self._prepare_capture_payload()
            charge = self._get_adyen_client().capture(request=payload)
            vals = self._parse_capture_result(charge.message)
            self.collection.write(vals)
