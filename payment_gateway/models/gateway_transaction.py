# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from contextlib import contextmanager
from datetime import datetime
from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.addons.component.core import WorkContext


class GatewayTransaction(models.Model):
    _name = 'gateway.transaction'
    _description = 'Gateway Transaction'
    _order = 'create_date desc'

    @contextmanager
    @api.multi
    def _get_provider(self, usage=None):
        if not usage:
            if self:
                usage = self.payment_mode_id.provider
            else:
                raise UserError('Usage is missing')
        work = WorkContext(model_name=self._name, collection=self)
        yield work.component(usage=usage)

    @api.model
    def _selection_capture_payment(self):
        return self.env['account.payment.mode']._selection_capture_payment()

    name = fields.Char()
    payment_mode_id = fields.Many2one(
        'account.payment.mode',
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
        ('abandoned', 'Abandoned'),
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
            "- Abandoned: The Customer didn't fill the payment information\n"
            "- Succeeded: The money is here, life is beautiful\n")
        )
    data = fields.Text()
    error = fields.Text()
    date_processing = fields.Datetime('Processing Date')
    risk_level = fields.Selection([
        ('unknown', 'Unknown'),
        ('normal', 'Normal'),
        ('elevated', 'Elevated'),
        ('highest', 'Highest'),
        ], default='unknown')
    redirect_cancel_url = fields.Char()
    redirect_success_url = fields.Char()

    def _get_amount_to_capture(self):
        if self.invoice_id:
            # TODO
            pass
        elif self.sale_id:
            # TODO - the field "residual" missed in object "sale.order". On 8.0
            # version it was create on module payment_sale_method
            # https://github.com/OCA/sale-workflow/blob/8.0/sale_payment_method/
            # sale.py#L53 there is PR on migration to 9.0 where the field was
            # create in module sale_payment
            # https://github.com/OCA/sale-workflow/pull/403/
            # files#diff-c002243b01cfec667dfb7e6dac0c77d4R34
            return self.sale_id.amount_total

    @api.multi
    def cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def set_back_to_capture(self):
        return self.write({'state': 'to_capture'})

    @api.multi
    def write(self, vals):
        super(GatewayTransaction, self).write(vals)
        if vals['state'] == 'to_capture':
            for record in self:
                if record.capture_payment == 'immediately':
                    record.capture()
        return True

    @api.model
    def create(self, vals):
        transaction = super(GatewayTransaction, self).create(vals)
        if vals['state'] == 'to_capture':
            if transaction.capture_payment == 'immediately':
                transaction.capture()
        return transaction

    @api.model
    def generate(self, usage, record, **kwargs):
        """Generate the transaction in the provider backend
        and create the transaction in odoo"""
        with self._get_provider(usage) as provider:
            transaction = provider.create_provider_transaction(record, **kwargs)
            vals = provider._prepare_odoo_transaction(record, transaction, **kwargs)
        return self.create(vals)

    @api.multi
    def capture(self):
        """Capture one transaction in the backend
        Only one transaction can be captured to avoid rollback issue"""
        self.ensure_one()
        if self.state == 'succeeded':
            pass
        else:
            amount = self._get_amount_to_capture()
            vals = {}
            try:
                with self._get_provider() as provider:
                    provider.capture(amount)
                vals = {
                    'state': 'succeeded',
                    'date_processing': datetime.now(),
                    }
            except Exception, e:
                vals = {
                    'state': 'failed',
                    'error': str(e),
                    'date_processing': datetime.now(),
                    }
            self.write(vals)
        return vals['state'] == 'succeeded'

    @api.multi
    def check_state(self):
        for record in self:
            if record.state == 'pending':
                with record._get_provider() as provider:
                    record.write({'state': provider.get_transaction_state()})
