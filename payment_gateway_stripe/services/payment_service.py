# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models


class PaymentService(models.Model):
    _inherit = 'payment.service'
    _name = 'payment.service.stripe'

    def _get_connection(self):
        account = self._get_account()
        import stripe
        stripe.api_key = account.get_password()
        return stripe

    def _prepare_provider_transaction(self, record):
        description = "%s|%s" % (
            record.name,
            record.partner_id.email)
        capture = record.payment_method_id.capture_payment == 'immediately'
        return {
            'currency': record.currency_id.code,
            'source': record.stripe_token,
            'description': description,
            'capture': capture,
            }

    def _create_provider_transaction(self, data):
        stripe = self._get_connection()
        return stripe.Charge.create(data)

    def _prepare_odoo_transaction(self, cart, transaction):
        return {}

    def capture(self, transaction, amount):
        pass
