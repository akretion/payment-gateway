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
    def get_transaction_state(self):
        raise NotImplemented

    @api.model
    def capture(self, amount):
        raise NotImplemented
