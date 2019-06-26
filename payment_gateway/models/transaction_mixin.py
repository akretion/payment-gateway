# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.fields import first


class TransactionMixin(models.AbstractModel):
    """
    Abstract model to use for models who use gateway transaction
    (sale.order for example).
    During the inheritance, you have to overwrite the
    _get_transaction_to_capture_amount function.
    """
    _name = 'transaction.mixin'
    _description = "Gateway transaction abstract model"

    transaction_ids = fields.One2many(
        'gateway.transaction',
        'res_id',
        'Transaction',
        domain=lambda self: [('res_model', '=', self._name)],
    )
    current_transaction_id = fields.Many2one(
        'gateway.transaction',
        'Current Transaction',
        compute='_compute_current_transaction',
        store=True,
    )

    @api.multi
    def _get_transaction_to_capture_amount(self):
        """
        Get the amount to capture of the transaction
        :return: float
        """
        return NotImplementedError

    @api.multi
    def capture_transaction(self):
        transactions = self.mapped("transaction_ids").filtered(
            lambda r: r.state == 'to_capture')
        for transaction in transactions:
            transaction.capture()

    @api.multi
    @api.depends('transaction_ids')
    def _compute_current_transaction(self):
        for record in self:
            # Load the more recent transaction
            record.current_transaction_id = first(
                record.transaction_ids.sorted('id', reverse=True))

    def _get_transaction_name_based_on_origin(self):
        return self.name or ('%s with id %s' % (self._name, self.id))
