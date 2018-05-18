# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http


class PaymentGatewayWebhook(http.Controller):

    @http.route(
        '/payment-gateway-http-webhook/'
        '<string:service_name>/<string:method_name>',
        type='http',
        auth='none',
        csrf=False,
        methods=['POST'])
    def payment_gateway_http_hook(
            self, service_name=None, method_name=None, **params):
        http.request.env['gateway.transaction'].sudo().with_delay()\
            .process_webhook(service_name, method_name, params)
        return ''

    @http.route(
        '/payment-gateway-json-webhook/'
        '<string:service_name>/<string:method_name>',
        type='json',
        auth='none',
        csrf=False,
        methods=['POST'])
    def payment_gateway_json_hook(self, service_name=None, method_name=None):
        params = http.request.jsonrequest
        http.request.env['gateway.transaction'].sudo().with_delay()\
            .process_webhook(service_name, method_name, params)
        return True
