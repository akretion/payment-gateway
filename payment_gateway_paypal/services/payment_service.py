# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models
import paypalrestsdk
import json


def create_profile(paypal):
    web_profile = paypalrestsdk.WebProfile({
        "name": 'Adaptoo 2',
        "presentation": {
            "brand_name": "Adaptoo Paypal",
            "logo_image": "http://www.adaptoo.com/skin/frontend/adaptoo/default/images/logo.gif",
            "locale_code": "FR"
        },
        "input_fields": {
            "no_shipping": 1,
            "address_override": 1
        },
        "flow_config": {
            "user_action": "commit"
        }
    }, api=paypal)
    if web_profile.create():
        print "Web Profile[%s] created successfully" % (web_profile.id)
    else:
        print web_profile.error


class PaymentService(models.Model):
    _inherit = 'payment.service'
    _name = 'payment.service.paypal'

    def _get_connection(self):
        account = self._get_account()
        params = account.get_data()
        params['client_secret'] = account.get_password()
        return paypalrestsdk.Api(params)

    def _prepare_provider_transaction(self, record):
        description = "%s|%s" % (
            record.name,
            record.partner_id.email)
        capture = record.payment_method_id.capture_payment == 'immediately'
        address = record.partner_shipping_id
        return {
            "experience_profile_id": "XP-X46Z-A86H-DRY2-H8EN",
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls" : {
                "return_url": "https://todo",
                "cancel_url": "https://cancel",
                },
            "transactions": [{
            	"amount": {
                    "total": record.residual,
                    "currency": record.currency_id.name,
                     },
                "description": description,
            }],
	 }

    def _create_provider_transaction(self, data):
        paypal = self._get_connection()
        #create_profile(paypal)
        payment = paypalrestsdk.Payment(data, api=paypal)
        if not payment.create():
            # TODO improve manage error
            raise UserError(payment.error)
        return payment.to_dict()

    def _prepare_odoo_transaction(self, cart, transaction):
        res = super(PaymentService, self).\
            _prepare_odoo_transaction(cart, transaction)
        url = [l for l  in transaction['links'] if l['method']=='REDIRECT'][0]
        res.update({
            'amount': transaction['transactions'][0]['amount']['total'],
            'external_id': transaction['id'],
            'data': json.dumps(transaction),
            'url': url['href'],
        })
        return res

    def capture(self, transaction, amount):
        pass
