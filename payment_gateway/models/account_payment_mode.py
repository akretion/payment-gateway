# -*- coding: utf-8 -*-
# copyright 2017 akretion (http://www.akretion.com).
# @author sébastien beau <sebastien.beau@akretion.com>
# license agpl-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.translate import _


class AccountPaymentMode(models.Model):
    _inherit = 'account.payment.mode'

    provider = fields.Selection(selection=[])
    capture_payment = fields.Selection(selection='_selection_capture_payment')

    def _selection_capture_payment(self):
        return [
            ('immediately', _('Immediately')),
            # TODO implement me
            # ('order_confirm', _('At Order Confirmation')),
            # ('picking_confirm', _('At Picking Confirmation')),
            ]

   # @api.onchange('provider')
   # def onchange_provider(self):
   #     self.capture_payment = \
   #         self.env[self.provider]._allowed_capture_method[0]

   # # TODO we should be able to apply domain on selection field
   # @api.onchange('capture_payment')
   # def onchange_capture(self):
   #     if self.provider:
   #         provider = self.env[self.provider]
   #         if self.capture_payment not in provider._allowed_capture_method:
   #             self.capture_payment = provider._allowed_capture_method[0]
   #             return {'warning': {
   #                 'title': _('Incorrect Value'),
   #                 'message': _('This method is not compatible with '
   #                              'the provider selected'),
   #                 }}
