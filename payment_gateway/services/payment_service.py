# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, models


# It will be better to have a class that is more abstract than the AbtractModel
# Indeed I just use this here in order to use the inheritance feature
class PaymentService(models.AbstractModel):
    _name = 'payment.service'
    _description = 'Payment Service'

    def _get_account(self):
        keychain = self.env['keychain.account']
        return keychain.suspend_security().retrieve([
            ('namespace', '=', self._name)
            ])[0]

    def _prepare_provider_transaction(self, record, **kwargs):
        raise NotImplemented

    def _create_provider_transaction(self, record, **kwargs):
        raise NotImplemented

    def _create_odoo_transaction(self, record, **kwargs):
        raise NotImplemented

    @api.model
    def generate(self, record, **kwargs):
        """Generate the transaction in the provider backend
        and create the transaction in odoo"""
        data = self._prepare_provider_transaction(record, **kwargs)
        transaction = self._create_provider_transaction(data)
        vals = self._prepare_odoo_transaction(record, transaction)
        return self.env['gateway.transaction'].create(vals)

    @api.model
    def capture(self, transaction, amount):
        """Capture the transaction in the backend"""
        raise NotImplemented
