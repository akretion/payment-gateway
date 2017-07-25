# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models
from openerp.exceptions import Warning as UserError
from openerp.tools.translate import _
import json
import logging
_logger = logging.getLogger(__name__)

try:
    import stripe
except ImportError:
    _logger.debug('Can not import stripe')

MAP_SOURCE_STATE = {
    'canceled': 'cancel',
    'chargeable': 'to_capture',
    'consumed': 'succeeded',
    'failed': 'failed',
    'pending': 'pending',
    'succeeded': 'succeeded'}


class PaymentService(models.Model):
    _inherit = 'payment.service'
    _name = 'payment.service.stripe'
    _allowed_capture_method = ['immediately']

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

    @property
    def _api_key(self):
        account = self._get_account()
        return account.get_password()

    def _prepare_provider_transaction(
            self, record, source=None, return_url=None, **kwargs):
        description = "%s|%s" % (
            record.name,
            record.partner_id.email)
        # For now capture is always true as only the policy 'immedialtely' is
        # available in the configuration but it will be easier to implement
        # the logic of defeared capture
        capture = record.payment_method_id.capture_payment == 'immediately'
        return {
            'currency': record.currency_id.name,
            'source': source,
            'return_url': return_url,
            'description': description,
            'capture': capture,
            'amount': int(record.residual * 100),
            }

    def _need_three_d_secure(self, data, source):
        return source['card']['three_d_secure'] != 'not_supported'

    def _prepare_source(self, data):
        return {
            'type': 'three_d_secure',
            'amount': data['amount'],
            'currency': data['currency'],
            'three_d_secure': {'card': data['source']},
            'redirect': {'return_url': data['return_url']},
        }

    def _create_provider_transaction(self, data):
        source = stripe.Source.retrieve(data['source'], api_key=self._api_key)
        try:
            if self._need_three_d_secure(data, source):
                return stripe.Source.create(
                    api_key=self._api_key,
                    **self._prepare_source(data))
            else:
                data.pop('return_url')
                return stripe.Charge.create(api_key=self._api_key, **data)
        except stripe.error.CardError as e:
            raise UserError(self._get_error_message(e.code))

    def _prepare_odoo_transaction(self, cart, transaction, **kwargs):
        res = super(PaymentService, self).\
            _prepare_odoo_transaction(cart, transaction, **kwargs)
        res.update({
            'amount': transaction['amount']/100.,
            'external_id': transaction['id'],
            'state': MAP_SOURCE_STATE[transaction['status']],
            'data': json.dumps(transaction),
        })
        if transaction.get('redirect', {}).get('url'):
            res['url'] = transaction['redirect']['url']
        return res

    def get_transaction_state(self, transaction):
        source = stripe.Source.retrieve(
            transaction.external_id, api_key=self._api_key)
        return MAP_SOURCE_STATE[source['status']]

    def _prepare_odoo_transaction_from_charge(self, charge):
        return {
            'amount': charge['amount']/100.,
            'external_id': charge['id'],
            'state': MAP_SOURCE_STATE[charge['status']],
            'risk_level': charge.get('outcome', {}).get('risk_level'),
            'data': json.dumps(charge),
        }

    def capture(self, transaction, amount):
        if transaction.external_id.startswith('src_'):
            # Transaction is a source convert it to a charge
            charge = stripe.Charge.create(
                currency=transaction.currency_id.name,
                source=transaction.external_id,
                description=transaction.name,
                capture=True,
                amount=int(amount * 100),
                api_key=self._api_key)
            vals = self._prepare_odoo_transaction_from_charge(charge)
            transaction.write(vals)
