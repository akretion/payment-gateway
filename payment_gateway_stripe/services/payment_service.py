# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import Warning as UserError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.addons.component.core import Component
import json
import logging
_logger = logging.getLogger(__name__)

try:
    import stripe
except ImportError:
    _logger.debug('Cannot import stripe')


MAP_SOURCE_STATE = {
    'canceled': 'cancel',
    'chargeable': 'to_capture',
    'consumed': 'succeeded',
    'failed': 'failed',
    'pending': 'pending',
    'succeeded': 'succeeded'}

# zero decimal currency https://stripe.com/docs/currencies#zero-decimal
ZERO_DECIMAL_CURRENCIES = [
    u'BIF', u'CLP', u'DJF', u'GNF', u'JPY', u'KMF', u'KRW', u'MGA',
    u'PYG', u'RWF', u'VND', u'VUV', u'XAF', u'XOF', u'XPF',
]


class PaymentService(Component):
    _inherit = 'payment.service'
    _name = 'payment.service.stripe'
    _usage = 'stripe'
    _allowed_capture_method = ['immediately']
    _webhook_method = ['process_event']

    def process_event(self, **params):
        transaction_id = params['data']['object']['id']
        # For now we only implement a basic webhook for simple transaction
        # Receving the webhook will force to update the related transaction
        transaction = self.env['gateway.transaction'].search([
            ('external_id', '=', transaction_id),
            ('payment_mode_id.provider', '=', 'stripe'),
            ])
        if transaction:
            transaction.check_state()
        else:
            raise UserError(
                _('The transaction %s do not exist') % transaction_id)

    def _validator_process_event(self):
        return {
            'data': {
                'type': 'dict',
                'schema': {
                    'object': {
                        'type': 'dict',
                        'schema': {
                            'id': {'type': 'string'},
                        }
                    }
                }
            }
        }

    @property
    def _api_key(self):
        account = self._get_account()
        return account._get_password()

    def _get_formatted_amount(self):
        amount = self.collection._get_amount_to_capture()
        if self.collection.currency_id.name in ZERO_DECIMAL_CURRENCIES:
            return int(amount)
        else:
            return int(float_round(amount*100, 0))

    # Code for generating the transaction on stripe and the transaction on odoo

    def _get_error_message(self, code):
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
        # the logic of deferred capture
        capture = transaction.capture_payment == 'immediately'
        return {
            'currency': transaction.currency_id.name,
            'source': source,
            'description': description,
            'capture': capture,
            'amount': self._get_formatted_amount(),
            'api_key': self._api_key,
            }

    def _need_three_d_secure(self, source_data):
        return source_data['card']['three_d_secure'] != 'not_supported'

    def _prepare_source(self, source=None, return_url=None, **kwargs):
        return {
            'type': 'three_d_secure',
            'amount': self._get_formatted_amount(),
            'currency': self.collection.currency_id.name,
            'three_d_secure': {'card': source},
            'redirect': {'return_url': return_url},
            'api_key': self._api_key,
        }

    def _create_transaction(self, source=None, **kwargs):
        source_data = stripe.Source.retrieve(source, api_key=self._api_key)
        three_d_secure = self._need_three_d_secure(source_data)
        try:
            if three_d_secure:
                res = stripe.Source.create(
                    **self._prepare_source(source=source, **kwargs))
                if res['status'] == 'chargeable':
                    # 3D secure has not been activated or is not ready
                    # for this customer
                    three_d_secure = False
                else:
                    return res
            if not three_d_secure:
                return stripe.Charge.create(
                    **self._prepare_charge(source=source, **kwargs))
        except stripe.error.CardError as e:
            raise UserError(self._get_error_message(e.code))

    def _parse_creation_result(self, transaction, **kwargs):
        res = super(PaymentService, self).\
            _parse_creation_result(transaction, **kwargs)
        res.update({
            'amount': transaction['amount']/100.,
            'external_id': transaction['id'],
            'state': MAP_SOURCE_STATE[transaction['status']],
            'data': json.dumps(transaction),
        })
        if transaction.get('redirect', {}).get('url'):
            res['url'] = transaction['redirect']['url']
        risk_level = transaction.get('outcome', {}).get('risk_level')
        if risk_level:
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
            'amount': charge['amount']/100.,
            'external_id': charge['id'],
            'state': MAP_SOURCE_STATE[charge['status']],
            'risk_level': charge.get('outcome', {}).get('risk_level'),
            'data': json.dumps(charge),
        }

    def _prepare_capture_payload(self):
        transaction = self.collection
        return {
            'currency': transaction.currency_id.name,
            'source': transaction.external_id,
            'description': transaction.name,
            'capture': True,
            'amount': self._get_formatted_amount(),
            'api_key': self._api_key,
            }

    def capture(self):
        if self.collection.external_id.startswith('src_'):
            # Transaction is a source convert it to a charge
            payload = self._prepare_capture_payload()
            charge = stripe.Charge.create(**payload)
            vals = self._parse_capture_result(charge)
            self.collection.write(vals)
