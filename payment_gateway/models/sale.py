# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = [
        'sale.order',
        'transaction.mixin',
    ]
    _name = 'sale.order'

    @api.multi
    def _get_transaction_to_capture_amount(self):
        """
        Get the amount to capture of the transaction
        :return: float
        """
        self.ensure_one()
        return self.amount_total
