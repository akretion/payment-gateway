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
    'requires_payment_method': 'pending',
    'requires_confirmation': 'pending',
    'requires_action': 'pending',
    'processing': 'pending',
    'requires_capture': 'to_capture',
    'succeeded': 'succeeded',
    }


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

    def create_provider_transaction(self, record, source=None, **kwargs):
        description = "%s|%s" % (
            record.name,
            record.partner_id.email)
        return stripe.PaymentIntent.create(
            payment_method=source,
            amount=int(record.residual * 100),
            currency=record.currency_id.name,
            confirmation_method="manual",
            confirm=True,
            description=description,
            api_key=self._api_key,
        )

    def _prepare_odoo_transaction(self, cart, transaction, **kwargs):
        res = super(PaymentService, self).\
            _prepare_odoo_transaction(cart, transaction, **kwargs)
        res.update({
            'amount': transaction['amount']/100.,
            'external_id': transaction['id'],
            'state': MAP_SOURCE_STATE[transaction['status']],
            'data': json.dumps(transaction),
        })
        return res

    def get_transaction_state(self, transaction):
        source = stripe.Payment.retrieve(
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
        if transaction.external_id.startswith('pi_'):
            self.check_state()
            if transaction.status == 'processing':
                intent = stripe.PaymentIntent.confirm(
                    stripe_payment_intent_id,
                    api_key=self._api_key)
                self.check_state()
