# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models
import json
try:
    import stripe
except ImportError:
    _logger.debug('Can not import stripe')


class PaymentService(models.Model):
    _inherit = 'payment.service'
    _name = 'payment.service.stripe'
    _allowed_capture_method = ['immediately']

    def _get_api_key(self):
        return account.get_password()

    def _prepare_provider_transaction(self, record, token=None):
        description = "%s|%s" % (
            record.name,
            record.partner_id.email)
        capture = record.payment_method_id.capture_payment == 'immediately'
        return {
            'currency': record.currency_id.name,
            'source': token,
            'description': description,
            'capture': capture,
            'amount': int(record.residual * 100),
            }

    def _create_provider_transaction(self, data):
        data['api_key'] = self._get_api_key()
        return stripe.Charge.create(**data)

    def _prepare_odoo_transaction(self, cart, transaction):
        res = super(PaymentService, self).\
            _prepare_odoo_transaction(cart, transaction)
        res.update({
            'amount': transaction['amount'],
            'external_id': transaction['id'],
            'data': json.dumps(transaction),
        })
        return res

    def _capture(self, transaction, amount):
        api = self._get_connection()
        charge = stripe.Charge.retrieve(
            transaction.external_id,
            api_key=self._get_api_key())
        result = charge.capture()
        # TODO process result
        return True
