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

    def _create_transaction(self, **kwargs):
        """Create the transaction on the backend of the service provider
        and return a json of the result of the creation"""
        raise NotImplemented

    def _parse_creation_result(self, transaction, **kwargs):
        return {}

    def generate(self, **kwargs):
        """Generate the transaction in the provider backend
        and update the odoo gateway.transaction"""
        transaction = self._create_transaction(**kwargs)
        vals = self._parse_creation_result(transaction, **kwargs)
        return self.collection.write(vals)

    def get_state(self):
        raise NotImplemented

    def capture(self, amount):
        raise NotImplemented
