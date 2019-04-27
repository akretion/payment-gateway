# -*- coding: utf-8 -*-
# copyright 2017 akretion (http://www.akretion.com).
# @author sébastien beau <sebastien.beau@akretion.com>
# license agpl-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.translate import _


class AccountPaymentMode(models.Model):
    _inherit = 'account.payment.mode'

    provider = fields.Selection(selection='_selection_provider')
    provider_account = fields.Many2one(
        comodel_name='keychain.account',
        domain=[('namespace', '!=', False)]
    )
    capture_payment = fields.Selection(selection='_selection_capture_payment')

    def _selection_capture_payment(self):
        return [
            ('immediately', _('Immediately')),
            # TODO implement me
            # ('order_confirm', _('At Order Confirmation')),
            # ('picking_confirm', _('At Picking Confirmation')),
            ]

    def _selection_provider(self):
        if self._context.get('install_mode'):
            # load all component that should be installed
            builder = self.env['component.builder']
            components_registry = builder._init_global_registry()
            builder.build_registry(
                components_registry,
                states=('installed', 'to upgrade', 'to install'))
        return [
            (p._provider_name, p._provider_name.title())
            for p in self.env['gateway.transaction']._get_all_provider()]

    def _get_allowed_capture_method(self):
        transaction_obj = self.env['gateway.transaction']
        with transaction_obj._get_provider(self.provider) as provider:
            return provider._allowed_capture_method

    @api.onchange('provider')
    def onchange_provider(self):
        self.capture_method = self._get_allowed_capture_method()[0]

    # TODO we should be able to apply domain on selection field
    @api.onchange('capture_payment')
    def onchange_capture(self):
        if self.provider:
            capture_methods = self._get_allowed_capture_method()
            if self.capture_payment not in capture_methods:
                self.capture_payment = capture_methods[0]
                return {'warning': {
                    'title': _('Incorrect Value'),
                    'message': _('This method is not compatible with '
                                 'the provider selected'),
                    }}
