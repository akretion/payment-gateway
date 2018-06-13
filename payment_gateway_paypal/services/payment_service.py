# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import Warning as UserError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.addons.component.core import Component

import json
import logging
_logger = logging.getLogger(__name__)

try:
    import paypalrestsdk
except ImportError:
    _logger.debug('Can not `import paypalrestsdk` library')


# TODO FIXME
def create_profile(paypal):
    web_profile = paypalrestsdk.WebProfile({
        "name": 'Adaptoo 2',
        "presentation": {
            "brand_name": "Adaptoo Paypal",
            "logo_image": ("http://www.adaptoo.com/skin/frontend/"
                           "adaptoo/default/images/logo.gif"),
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
        _logger.info("Web Profile[%s] created successfully", web_profile.id)
    else:
        _logger.error('%s', web_profile.error)


class PaymentService(Component):
    _inherit = 'payment.service'
    _name = 'payment.service.paypal'
    _usage = 'gateway.provider'
    _allowed_capture_method = ['immediately']

    def _get_connection(self):
        account = self._get_account()
        params = account.get_data()
        experience_profile = params.pop("experience_profile_id", None)
        params['client_secret'] = account._get_password()
        # create_profile(paypal)
        return paypalrestsdk.Api(params), experience_profile

    def _prepare_transaction(
            self, return_url=None, cancel_url=None, **kwargs):
        transaction = self.collection
        description = "|".join([
            transaction.name,
            transaction.partner_id.email])
#            str(transaction.id)])   TODO add it? then how to fix tests?
        return {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url,
                },
            "transactions": [{
                "amount": {
                    "total": transaction._get_amount_to_capture(),
                    "currency": transaction.currency_id.name,
                    },
                "description": description,
                }],
            }

    def _create_transaction(self, **kwargs):
        data = self._prepare_transaction(**kwargs)
        # TODO paypal lib is not perfect, we should wrap it in a class
        paypal, experience_profile = self._get_connection()
        data["experience_profile_id"] = experience_profile
        payment = paypalrestsdk.Payment(data, api=paypal)
        if not payment.create():
            # TODO improve manage error
            raise UserError(payment.error)
        return payment.to_dict()

    def get_transaction_state(self, transaction):
        if transaction.state == 'pending':
            paypal, experience_profile = self._get_connection()
            payment = paypalrestsdk.Payment.find(
                transaction.external_id, api=paypal)
            if payment.to_dict()['payer'].get('payer_info'):
                return 'to_capture'
        return transaction.state

    def _parse_creation_result(self, transaction, **kwargs):
        res = super(PaymentService, self)._parse_creation_result(
            transaction, **kwargs)
        url = [l for l in transaction['links'] if l['method'] == 'REDIRECT'][0]
        res.update({
            'amount': transaction['transactions'][0]['amount']['total'],
            'external_id': transaction['id'],
            'data': json.dumps(transaction),
            'url': url['href'],
            'state': 'pending',
        })
        return res

    def capture(self, transaction, amount):
        paypal, experience_profile = self._get_connection()
        payment = paypalrestsdk.Payment.find(
            transaction.external_id, api=paypal)
        payer_id = payment.to_dict()['payer']\
            .get('payer_info', {}).get('payer_id')
        if payer_id:
            if payment.execute({'payer_id': payer_id}):
                transaction.write({'state': 'succeeded'})
            else:
                transaction.write({
                    'state': 'failed',
                    'error': payment.error,
                    })
        else:
            transaction.write({'state': 'abandonned'})
