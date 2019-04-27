# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from contextlib import contextmanager
from datetime import datetime
from odoo import _, api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.addons.component.core import WorkContext
from odoo.addons.queue_job.job import job
from odoo.exceptions import UserError


class GatewayTransaction(models.Model):
    _name = 'gateway.transaction'
    _description = 'Gateway Transaction'
    _order = 'create_date desc'

    @contextmanager
    @api.multi
    def _get_provider(self, provider_name=None):
        provider_name = provider_name or self.payment_mode_id.provider
        if not provider_name:
            raise UserError(_('Provider name is missing'))
        work = WorkContext(model_name=self._name, collection=self)
        yield work.component_by_name('payment.service.%s' % provider_name)

    @api.model
    def _get_all_provider(self):
        work = WorkContext(model_name=self._name, collection=self)
        return [provider for provider in work.many_components(
                usage='gateway.provider')]

    @api.model
    def _selection_capture_payment(self):
        return self.env['account.payment.mode']._selection_capture_payment()

    name = fields.Char()
    payment_mode_id = fields.Many2one(
        'account.payment.mode',
        'Gateway')
    external_id = fields.Char(index=True)
    capture_payment = fields.Selection(
        selection="_selection_capture_payment",
        required=True)
    url = fields.Char()
    meta = fields.Serialized()
    amount = fields.Float(dp=dp.get_precision('Account'))
    currency_id = fields.Many2one(
        'res.currency',
        'Currency')
    origin_id = fields.Reference(
        selection=[
            ('sale.order', 'Sale Order'),
            ('account.invoice', 'Account Invoice'),
            ])
    res_model = fields.Char(compute='_compute_origin', store=True)
    res_id = fields.Integer(compute='_compute_origin', store=True)
    partner_id = fields.Many2one(
        'res.partner',
        'Partner')
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
    used_3d_secure = fields.Boolean(
        help="Tic if this transaction have used 3d secure")

    @api.multi
    @api.depends('origin_id')
    def _compute_origin(self):
        for record in self:
            record.res_id = record.origin_id.id
            record.res_model = record.origin_id._name

    @api.multi
    def _get_amount_to_capture(self):
        """
        Return the amount to capture depending on the target model
        :return: float
        """
        self.ensure_one()
        return self.origin_id._get_transaction_to_capture_amount()

    @api.multi
    def cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def set_back_to_capture(self):
        return self.write({'state': 'to_capture'})

    @api.multi
    def write(self, vals):
        result = super(GatewayTransaction, self).write(vals)
        if vals.get('state') == 'to_capture':
            immediate_records = self.filtered(
                lambda r: r.capture_payment == 'immediately')
            for record in immediate_records:
                record.capture()
        return result

    def _prepare_transaction(self, origin, **kwargs):
        mode = origin.payment_mode_id
        return {
            'name': origin._get_transaction_name_based_on_origin(),
            'payment_mode_id': mode.id,
            'capture_payment': mode.capture_payment,
            'redirect_cancel_url': kwargs.get('redirect_cancel_url'),
            'redirect_success_url': kwargs.get('redirect_success_url'),
            'currency_id': origin.currency_id.id,
            'origin_id': '%s,%s' % (origin._name, origin.id),
            'partner_id': origin.partner_id.id,
            }

    @api.model
    def generate(self, provider_name, origin, **kwargs):
        """
        Generate the transaction in the provider backend
        and create the transaction in odoo
        :param provider_name: str
        :param origin: target recordset
        :param kwargs: dict
        :return: self recordset
        """
        vals = self._prepare_transaction(origin, **kwargs)
        transaction = self.create(vals)
        with transaction._get_provider(provider_name) as provider:
            provider.generate(**kwargs)
        return transaction

    @api.multi
    def capture(self):
        """
        Capture one transaction in the backend
        Only one transaction can be captured to avoid rollback issue
        :return: bool
        """
        # TODO we should review the way to do the try/except
        # the main point to review is that we write here in the transaction
        # and also in the service. Having two write is useless and complexe
        self.ensure_one()
        vals = {}
        if self.state == 'succeeded':
            pass
        else:
            try:
                with self._get_provider() as provider:
                    provider.capture()
                vals = {'date_processing': datetime.now()}
            except Exception, e:
                vals = {
                    'state': 'failed',
                    'error': str(e),
                    'date_processing': datetime.now(),
                }
            self.write(vals)
        return vals.get('state') == 'succeeded'

    @api.multi
    def check_state(self):
        for record in self:
            if record.state == 'pending':
                with record._get_provider() as provider:
                    record.write({'state': provider.get_state()})

    @job(default_channel='root.gateway.webhook')
    def process_webhook(self, provider_name, method_name, params):
        with self._get_provider(provider_name) as provider:
            return provider.dispatch(method_name, params)
