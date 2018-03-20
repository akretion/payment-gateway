# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from openerp.addons.account_move_base_import.models.account_move import \
    ErrorTooManyPartner


class AccountMoveCompletionRule(models.Model):
    _inherit = 'account.move.completion.rule'

    function_to_call = fields.Selection(
        selection_add=[
            ('get_from_transaction_id_and_gateway_transaction',
             'Match Transaction using transaction ID')
        ])

    def get_from_transaction_id_and_gateway_transaction(self, line):
        """
        Match the partner based on the transaction ID field of the
        Payment Gateway Transaction.
        Then, call the generic st_line method to complete other values.
        In that case, we always fullfill the reference of the line with the SO
        name.
        :param dict st_line: read of the concerned account.bank.statement.line
        :return:
            A dict of value that can be passed directly to the write method of
            the statement line or {}
           {'partner_id': value,
            'account_id' : value,
            ...}
            """
        res = {}
        transaction = self.env['gateway.transaction'].search([
            ('external_id', '=', line.transaction_ref)])
        if len(transaction) > 1:
            raise ErrorTooManyPartner(
                _('Transaction "%s" was matched by more than '
                  'one transaction.') % line.transaction_ref)
        if len(transaction) == 1:
            if transaction.sale_id:
                res['partner_id'] = transaction.sale_id.partner_id.id
            elif transaction.invoice_id:
                res['partner_id'] = transaction.invoice_id.partner_id.id
        return res
