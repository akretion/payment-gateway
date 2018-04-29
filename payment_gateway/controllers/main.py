# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http


class PaymentGatewayWebhook(http.Controller):

    @http.route(
        'payment-gateway-webhook/<string:_service_name>/<string:method_name>',
        type='http',
        auth='public',
        methods=['POST'])
    def payment_gateway_hook(self, **kwargs):
        import pdb; pdb.set_trace()
        return "TODO"
