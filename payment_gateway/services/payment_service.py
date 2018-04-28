# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.addons.component.core import AbstractComponent

class PaymentService(AbstractComponent):
    _name = 'payment.service'
    _description = 'Payment Service'
    _collection = 'gateway.transaction'
    _allowed_capture_method = None

    def _get_account(self):
        keychain = self.env['keychain.account']
        namespace = (self._name).replace('payment.service.', '')
        return keychain.sudo().retrieve([
            ('namespace', '=', namespace)
            ])[0]

    def _create_provider_transaction(self, **kwargs):
        raise NotImplemented

    def _prepare_odoo_transaction(self, transaction, **kwargs):
        return {}

    def generate(self, **kwargs):
        """Generate the transaction in the provider backend
            and create the transaction in odoo"""
        transaction = self._create_provider_transaction(**kwargs)
        vals = self._prepare_odoo_transaction(transaction, **kwargs)
        return self.collection.write(vals)

    def get_transaction_state(self):
        raise NotImplemented

    def capture(self, amount):
        raise NotImplemented
