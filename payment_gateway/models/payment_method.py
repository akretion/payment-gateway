# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models
from openerp.tools.translate import _


# Note on V9 and V10 the sale.payment.method is replaced by
# the account.payment.mode
# we will depend on the following OCA module
# oca/bank-payment/account_payment_sale


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    @api.model
    def _selection_capture_payment(self):
        return [
            ('immediately', _('Immediately')),
            ('order_confirm', _('At Order Confirmation')),
            ('picking_confirm', _('At Picking Confirmation')),
            ]

    provider = fields.Selection([])
    capture_payment = fields.Selection(selection='_selection_capture_payment')
