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


MAP_SOURCE_STATE = { # TODO complete
    'canceled': 'cancel',
    'Authorised': 'to_capture',
    'consumed': 'succeeded',
    'Refused': 'failed',
    'pending': 'pending',
    '[capture-received]': 'succeeded'}

 # zero decimal currency https://stripe.com/docs/currencies#zero-decimal
ZERO_DECIMAL_CURRENCIES = [
    u'BIF', u'CLP', u'DJF', u'GNF', u'JPY', u'KMF', u'KRW', u'MGA',
    u'PYG', u'RWF', u'VND', u'VUV', u'XAF', u'XOF', u'XPF',
]


class PaymentService(Component):
    _inherit = 'payment.service'
    _name = 'payment.service.adyen'
    _usage = 'adyen'
    _allowed_capture_method = ['immediately']

    def _get_formatted_amount(self): # TODO useful?
        amount = self.collection._get_amount_to_capture()
        if self.collection.currency_id.name in ZERO_DECIMAL_CURRENCIES:
            return int(amount)
        else:
            return int(float_round(amount*100, 0))

    # Code for generating the transaction on stripe and the transaction on odoo

    def _get_error_message(self, code): # TODO
        return {
            'invalid_number':
                _("The card number is not a valid credit card number."),
            'invalid_expiry_month':
                _("The card's expiration month is invalid."),
            'invalid_expiry_year':
                _("The card's expiration year is invalid."),
            'invalid_cvc':
                _("The card's security code is invalid."),
            'invalid_swipe_data':
                _("The card's swipe data is invalid."),
            'incorrect_number':
                _("The card number is incorrect."),
            'expired_card':
                _("The card has expired."),
            'incorrect_cvc':
                _("The card's security code is incorrect."),
            'incorrect_zip':
                _("The card's zip code failed validation."),
            'card_declined':
                _("The card was declined."),
            'missing':
                _("There is no card on a customer that is being charged."),
            'processing_error':
                _("An error occurred while processing the card."),
        }[code]

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

        # TODO card + encrypt
        # see https://docs.adyen.com/developers/api-reference/payments-api#card
        # https://docs.adyen.com/developers/ecommerce-integration/cse-integration-ecommerce
        # TODO use source somewhere?
        return {
                   'amount':  {"value": self._get_formatted_amount(),
                               "currency": transaction.currency_id.name},
                   'card': kwargs['card'],
                   'reference': description,
               }

    def _need_three_d_secure(self, source_data): # TODO
        return source_data['card']['three_d_secure'] != 'not_supported'

    def _prepare_source(self, source=None, return_url=None, **kwargs): # TODO
        return {
            'type': 'three_d_secure',
            'amount': self._get_formatted_amount(),
            'currency': self.collection.currency_id.name,
            'three_d_secure': {'card': source},
            'redirect': {'return_url': return_url},
            'api_key': self._api_key,
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
#        source_data = stripe.Source.retrieve(source, api_key=self._api_key)
#        three_d_secure = self._need_three_d_secure(source_data)
        three_d_secure = False
        try:
#        if True: # TODO
            if three_d_secure:
                res = stripe.Source.create(
                    **self._prepare_source(source=source, **kwargs))
                if res['status'] == 'chargeable':
                    # 3D secure have been not activated or not ready
                    # for this customer
                    three_d_secure = False
                else:
                    return res
            if not three_d_secure:
                return self._get_adyen_client().authorise(
                     request=self._prepare_charge(source=source, **kwargs))
        except ValueError as e: # TODO catch orther errors
            raise UserError(e)

    def _parse_creation_result(self, transaction, **kwargs):
        # TODO does it make sense to call super with the specific AdyenResult
        # object?
        res = super(PaymentService, self).\
            _parse_creation_result(transaction, **kwargs)
        transaction = transaction.message
        res.update({
            'amount': self.collection._get_amount_to_capture(), # transaction['amount']/100., TODO unlike Stripe, we don't have the amount in the result with Adyen
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
#            'amount': charge['amount']/100., TODO not such info with Adyen
            'external_id': charge['pspReference'],
            'state': MAP_SOURCE_STATE[str(charge['response'])],
#            'risk_level': charge.get('outcome', {}).get('risk_level'), # TODO
            'data': json.dumps(charge),
        }

    def _prepare_capture_payload(self):
        transaction = self.collection
        return {
            'originalReference': transaction.external_id,
            'modificationAmount': {'currency': transaction.currency_id.name, 'value': transaction.amount}
            }

    def capture(self):
        if self.collection.external_id.isdigit():
            payload = self._prepare_capture_payload()
            charge = self._get_adyen_client().capture(request=payload)
            vals = self._parse_capture_result(charge.message)
            self.collection.write(vals)
