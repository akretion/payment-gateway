# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import fields, models


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    provider = fields.Selection(
        selection_add=[('payment.service.stripe', 'Stripe')])
