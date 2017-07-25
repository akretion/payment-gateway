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

    provider = fields.Selection(selection="_selection_provider")
    capture_payment = fields.Selection(selection='_selection_capture_payment')

    def _selection_capture_payment(self):
        return [
            ('immediately', _('Immediately')),
            # TODO implement me
            # ('order_confirm', _('At Order Confirmation')),
            # ('picking_confirm', _('At Picking Confirmation')),
            ]

    def _selection_provider(self):
        return [(p, p.replace('payment.service.', '').capitalize())
                for p in self.env['payment.service']._get_all_provider()]

    @api.onchange('provider')
    def onchange_provider(self):
        self.capture_payment = \
            self.env[self.provider]._allowed_capture_method[0]

    # TODO we should be able to apply domain on selection field
    @api.onchange('capture_payment')
    def onchange_capture(self):
        if self.provider:
            provider = self.env[self.provider]
            if self.capture_payment not in provider._allowed_capture_method:
                self.capture_payment = provider._allowed_capture_method[0]
                return {'warning': {
                    'title': _('Incorrect Value'),
                    'message': _('This method is not compatible with '
                                 'the provider selected'),
                    }}
