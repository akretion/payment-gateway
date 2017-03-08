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
        return keychain.suspend_security().retrieve([
            ('namespace', '=', namespace)
            ])[0]

    def _prepare_provider_transaction(self, record, **kwargs):
        raise NotImplemented

    def _create_provider_transaction(self, record, **kwargs):
        raise NotImplemented

    def _prepare_odoo_transaction(self, record, transaction):
        method = record.payment_method_id
        res = {'payment_method_id': method.id}
        if record._name == 'sale.order':
            res.update({
                'sale_id': record.id,
                'currency_id': record.currency_id.id,
                'name': record.name,
                'capture_payment': method.capture_payment,
	})
        elif record._name == 'account.invoice':
            res['invoice_id'] = record.id
        return res

    def _get_amount_to_capture(self, transaction):
        if transaction.invoice_id:
            # TODO
            pass
        elif transaction.sale_id:
            return transaction.sale_id.residual

    @api.model
    def generate(self, record, **kwargs):
        """Generate the transaction in the provider backend
        and create the transaction in odoo"""
        data = self._prepare_provider_transaction(record, **kwargs)
        transaction = self._create_provider_transaction(data)
        vals = self._prepare_odoo_transaction(record, transaction)
        return self.env['gateway.transaction'].create(vals)

    @api.model
    def capture(self, transaction, **kwargs):
        """Capture the transaction in the backend"""
        amount = self._get_amount_to_capture(transaction)
        return self._capture(transaction, amount, **kwargs)
