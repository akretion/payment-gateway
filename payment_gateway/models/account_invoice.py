# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = [
        'account.invoice',
        'transaction.mixin',
    ]
    _name = 'account.invoice'

    @api.multi
    def _get_transaction_to_capture_amount(self):
        """
        Get the amount to capture of the transaction
        :return: float
        """
        self.ensure_one()
        return self.residual

    def _get_transaction_name_based_on_origin(self):
        transaction_name = self.number
        if not transaction_name:
            transaction_name = super(
                AccountInvoice, self)._get_transaction_name_based_on_origin()
        return transaction_name
