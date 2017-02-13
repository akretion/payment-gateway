# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models


class GatewayTransaction(models.Model):
    _name = 'gateway.transaction'
    _description = 'Gateway Transaction'

    @api.model
    def _selection_capture_payment(self):
        return self.env['payment.method']._selection_capture_payment()

    name = fields.Char()
    payment_method_id = fields.Many2one(
        'payment.method',
        'Gateway')
    external_id = fields.Char()
    capture_payment = fields.Selection(
        selection="_selection_capture_payment",
        required=True)
    url = fields.Char()
    sale_id = fields.Many2one(
        'sale.order',
        'Sale')
    invoice_id = fields.Many2one(
        'account.invoice',
        'Invoice')
