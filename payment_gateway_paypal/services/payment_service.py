# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _
from odoo.exceptions import Warning as UserError
from odoo.tools import float_round, float_repr
from odoo.addons.component.core import Component

import json
import logging
_logger = logging.getLogger(__name__)

try:
    import paypalrestsdk
except ImportError:
    _logger.debug('Can not `import paypalrestsdk` library')


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
        return paypalrestsdk.Api(params), experience_profile

    def _get_formatted_amount(self, amount):
        """paypal API is expecting at most two (2) decimal places with a
        period separator."""
        if amount is None:
            return 0
        return float_repr(float_round(amount, 2), 2)

    def _prepare_transaction(self, return_url, **kwargs):
        transaction = self.collection
        description = "|".join([
            transaction.name,
            transaction.partner_id.email,
            ('%s' % transaction.id)])
        amount = self._get_formatted_amount(
            transaction._get_amount_to_capture())
        return {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": transaction.redirect_cancel_url,
                },
            "transactions": [{
                "amount": {
                    "total": amount,
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

    def _parse_creation_result(self, transaction, **kwargs):
        url = [l for l in transaction['links'] if l['method'] == 'REDIRECT'][0]
        return {
            'amount': transaction['transactions'][0]['amount']['total'],
            'external_id': transaction['id'],
            'data': json.dumps(transaction),
            'url': url['href'],
            'state': 'pending',
        }

    def _process_return(self, **params):
        # For now we always capture immediatly the paypal transaction
        transaction = self.env['gateway.transaction'].search([
            ('external_id', '=', params['paymentId']),
            ('payment_mode_id.provider', '=', 'paypal'),
            ('state', '=', 'pending')])
        if transaction:
            transaction.capture()
            return transaction
        else:
            raise UserError(
                _('The transaction %s do not exist in Odoo')
                % params['paymentId'])

    def _capture(self):
        transaction = self.collection
        paypal, experience_profile = self._get_connection()
        payment = paypalrestsdk.Payment.find(
            transaction.external_id, api=paypal)
        payer_id = payment.to_dict()['payer']\
            .get('payer_info', {}).get('payer_id')
        if payer_id:
            if payment.execute({'payer_id': payer_id}):
                result = payment.to_dict()
                # Even if the execute have succeed, we need to check the state
                if result['state'] == 'approved':
                    vals = {
                        'state': 'succeeded',
                        'data': result,
                        }
                else:
                    vals = {
                        'state': 'failed',
                        'error': _('Wrong state in result'),
                        'data': result,
                        }
            else:
                vals = {
                    'state': 'failed',
                    'error': payment.error,
                    }
        else:
            vals = {'state': 'abandonned'}
        transaction.write(vals)
