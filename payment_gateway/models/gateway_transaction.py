# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError
from openerp.tools.translate import _


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
        ('draft', 'Draft (Not requested to the bank)'),
        ('pending', 'Pending (Waiting Feedback from bank)'),
        ('to_capture', 'To Capture'),
        ('cancel', 'Cancel'),
        ('failed', 'Failed'),
        ('succeeded', 'Succeeded'),
        ], help=(
            "State of the transaction :\n"
            "- Draft: the transaction only exist in odoo and"
            " not have been send to the provider\n"
            "- Pending: Waiting feedback from the provider\n"
            "- To capture: the transaction is ready, capture it"
            " to get your money\n"
            "- Cancel: You have decided to cancel this transaction\n"
            "- Failed: The Transaction failed, no money was captured\n"
            "- Succeeded: The money is here, life is beautiful\n")
        )
    data = fields.Text()
    error = fields.Text()

    def _get_amount_to_capture(self):
        if self.invoice_id:
            # TODO
            pass
        elif self.sale_id:
            return self.sale_id.residual

    @api.multi
    def capture(self, raise_error=True):
        """Capture one transaction in the backend"""
        self.ensure_one()
        if self.state == 'succeeded':
            pass
        else:
            amount = self._get_amount_to_capture()
            provider = self.env[self.payment_method_id.provider]
            try:
                provider._capture(self, amount)
                self.state = 'succeeded'
                return True
            except Exception, e:
                if raise_error:
                    raise UserError(
                        _('Fail to capture the transaction: %s'),
                        e)
                else:
                    self.write({
                        'state': 'failed',
                        'error': str(e),
                        })
                return False
