# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models


class PaySaleOrder(models.TransientModel):
    _inherit = 'pay.sale.order'

    journal_id = fields.Many2one(related='payment_method_id.journal_id')
    payment_method_id = fields.Many2one(
        'payment.method',
        'Payment Method')

    @api.multi
    def _pay_with_provider(self):
        order = self.env['sale.order'].browse(self.env.context['active_id'])
        order.payment_method_id = self.payment_method_id
        provider = self.env[self.payment_method_id.provider]
        provider.generate(order)

    @api.multi
    def pay_sale_order(self):
        self.ensure_one()
        if self.payment_method_id.provider:
            return self._pay_with_provider()
        else:
            return super(PaySaleOrder, self).pay_sale_order()
