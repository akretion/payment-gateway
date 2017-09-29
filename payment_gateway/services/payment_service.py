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

    def _get_all_provider(self):
        provider = []
        for model in self.env.registry.keys():
            if 'payment.service' in model and 'payment.service' != model:
                provider.append(model)
        return provider

    def _get_account(self):
        keychain = self.env['keychain.account']
        namespace = (self._name).replace('payment.service.', '')
        return keychain.sudo().retrieve([
            ('namespace', '=', namespace)
            ])[0]

    def create_provider_transaction(self, record, **kwargs):
        raise NotImplemented

    def _prepare_odoo_transaction(self, record, transaction, **kwargs):
        mode = record.payment_mode_id
        res = {
            'payment_mode_id': mode.id,
            'redirect_cancel_url': kwargs.get('redirect_cancel_url'),
            'redirect_success_url': kwargs.get('redirect_success_url'),
            }
        if record._name == 'sale.order':
            res.update({
                'sale_id': record.id,
                'currency_id': record.currency_id.id,
                'name': record.name,
                'capture_payment': mode.capture_payment,
            })
        elif record._name == 'account.invoice':
            res['invoice_id'] = record.id
        return res

    @api.model
    def generate(self, record, **kwargs):
        """Generate the transaction in the provider backend
        and create the transaction in odoo"""
        transaction = self.create_provider_transaction(record, **kwargs)
        vals = self._prepare_odoo_transaction(record, transaction, **kwargs)
        return self.env['gateway.transaction'].create(vals)

    @api.model
    def get_transaction_state(self, transaction):
        raise NotImplemented

    @api.model
    def capture(self, transaction, amount):
        raise NotImplemented
