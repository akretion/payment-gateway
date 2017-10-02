# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    transaction_ids = fields.One2many(
        'gateway.transaction',
        'sale_id',
        'Transaction')
    current_transaction_id = fields.Many2one(
        'gateway.transaction',
        'Current Transaction',
        compute='_compute_current_transaction')

    @api.multi
    def capture_transaction(self):
        for sale in self:
            for transaction in sale.transaction_ids:
                if transaction.state == 'to_capture':
                    transaction.capture(sale.residual)

    @api.multi
    def _compute_current_transaction(self):
        for record in self:
            if record.transaction_ids:
                record.current_transaction_id = record.transaction_ids[-1]
            else:
                record.current_transaction_id = None
