# -*- coding: utf-8 -*-
# copyright 2017 akretion (http://www.akretion.com).
# @author sébastien beau <sebastien.beau@akretion.com>
# license agpl-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMode(models.Model):
    _inherit = 'account.payment.mode'

    provider = fields.Selection(selection_add=[('stripe', 'Stripe')])
