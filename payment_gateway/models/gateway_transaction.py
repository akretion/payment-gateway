# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models
import openerp.addons.decimal_precision as dp


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
    amount = fields.Float(dp=dp.get_precision('Account'))
    currency_id = fields.Many2one(
        'res.currency',
        'Currency')
    sale_id = fields.Many2one(
        'sale.order',
        'Sale')
    invoice_id = fields.Many2one(
        'account.invoice',
        'Invoice')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_capture', 'To Capture'),
        ('cancel', 'Cancel'),
        ('failed', 'Failed'),
        ('succeeded', 'Succeeded'),
        ],
        )
    data = fields.Text()

    @api.multi
    def capture(self):
        for record in self:
            if record.state != 'to_capture':
                provider = self.env[record.payment_method_id.provider]
                provider.capture(record)
