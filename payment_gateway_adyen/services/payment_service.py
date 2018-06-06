# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com).
# @author Raphael Valyi <raphael.valyi@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import Warning as UserError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.addons.component.core import Component
import re
import json
import logging
_logger = logging.getLogger(__name__)

try:
    import Adyen
    from Adyen.exceptions import (AdyenAPIValidationError,
                                  AdyenAPIResponseError,
                                  AdyenAPIAuthenticationError,
                                  AdyenAPIInvalidPermission,
                                  AdyenAPICommunicationError,
                                  AdyenAPIInvalidAmount,
                                  AdyenAPIInvalidFormat)

except ImportError:
    _logger.debug('Cannot import Adyen')


MAP_SOURCE_STATE = {  # TODO check if complete
    '[cancel-received]': 'cancel',
    'Authorised': 'to_capture',
    'consumed': 'succeeded',
    'Refused': 'failed',
    'RedirectShopper': 'pending',
    '[capture-received]': 'succeeded'}

# decimal points of currencies https://docs.adyen.com/developers/currency-codes
ZERO_DECIMAL_CURRENCIES = [
    u'CVE', u'DJF', u'GNF', u'IDR', u'JPY', u'KMF', u'KRW', u'PYG',
    u'RWF', u'UGX', u'VND', u'VUV', u'XAF', u'XOF', u'XPF',
],

THREE_DECIMAL_CURRENCIES = [
    u'BHD', u'JOD', u'KWD', u'LYD', u'OMR', u'TND'
]


class PaymentService(Component):
    _inherit = 'payment.service'
    _name = 'payment.service.adyen'
    _usage = 'gateway.provider'
    _allowed_capture_method = ['immediately']

    def _raise_error_message(self, code):
        errors = {
            # admin errors (can be detailed):
            'authentication_failed':
                _("Unable to authenticate with Adyen's Servers."
                  " Please verify the credentials set with the Adyen base"
                  " class. Please reach out to your Adyen Admin"
                  " if the problem persists"),
            'invalid_permission':
                _("You provided the merchant account:'%s' that"
                  " doesn't exist or you don't have access to it.\n"
                  "Please verify the merchant account provided. \n"
                  "Reach out to support@adyen.com"
                  " if the issue persists"),

            # user friendly errors for the shopper:
            'communication_error':
                _("Transaction failed."
                  "Unexpected error while communicating with Adyen"),
            'validation':
                _("Transaction failed due to invalid values."),
            'invalid_amount':
                _("Transaction failed due to an invalid amount:"
                  "Amount may be improperly formatted, too small or too big."),
            '101': _("The card number is not a valid credit card number!"),
            '105': _("The 3D Secure validation failed."),
            '129': _("The expiration date is invalid."),
            '140': _("The expiration date is invalid."),
            '141': _("The expiration date is invalid."),
            '103': _("The card's security code does not have"
                     " the right length"),
            '153': _("The card's security code is invalid.")
            }
        raise UserError(errors.get(code, ("Transaction failed. "
                                          "Some unknown error happened"
                                          "with the Adyen payment gateway.")))

    def _http_adyen_request(self, service, payload):
        "re-catches Adyen errors to be more user friendly"
        if service not in ('authorise', 'authorise3d'):
            raise UserError(_('Invalid API service!'))
        try:
            return getattr(self._get_adyen_client(), service)(request=payload)
        except AdyenAPIAuthenticationError as e:
            self._raise_error_message('authentication_failed')
        except AdyenAPIInvalidPermission as e:
            self._raise_error_message('invalid_permission')
        except AdyenAPICommunicationError as e:
            self._raise_error_message('communication_error')
        except AdyenAPIInvalidAmount as e:
            self._raise_error_message('invalid_amount')
        except AdyenAPIInvalidFormat as e:
            self._raise_error_message('validation')
        except (AdyenAPIResponseError, AdyenAPIValidationError) as e:
            if e.error_code:
                code = e.error_code
            else:
                match = re.search('errorCode: ([0-9][0-9][0-9][0-9]?)',
                                  e.message)
                if match:
                    code = match.group(1).strip()
                else:
                    code = 'undef'
            self._raise_error_message(code)
        except Exception as e:
            self._raise_error_message('undef')

    def process_return(self, **params):
        payload = {}
        payload["browserInfo"] = params.get('browserInfo', {
            "userAgent":
                ("Mozilla/5.0 (X11; U; Linux i686; en-US; rv:\
                1.9) Gecko/2008052912 Firefox/3.0"),
            "acceptHeader":
                ("text/html,application/xhtml+xml,\
                application/xml;q=0.9,*/*;q=0.8")
        })
        payload["md"] = params['MD']
        payload["paResponse"] = params['PaRes']
        result = self._http_adyen_request('authorise3d', payload)
        vals = {
            'state': MAP_SOURCE_STATE[result.message['resultCode']],
            'data': json.dumps(result.message),
            }
        transaction = self.env['gateway.transaction'].search([
            ('external_id', '=', result.message['pspReference']),
            ('payment_mode_id.provider', '=', 'adyen'),
            ])
        if transaction:
            transaction.write(vals)
        else:
            raise UserError(
                _('The transaction %s do not exist in Odoo') % result.message[
                    'pspReference'])

    def _get_formatted_amount(self, amount=None):
        if amount is None:
            amount = self.collection._get_amount_to_capture()
        if self.collection.currency_id.name in ZERO_DECIMAL_CURRENCIES:
            return int(amount)
        elif self.collection.currency_id.name in THREE_DECIMAL_CURRENCIES:
            return int(float_round(amount * 1000, 0))
        else:
            return int(float_round(amount * 100, 0))

    def _prepare_charge(self, source=None, **kwargs):
        transaction = self.collection
        description = "|".join([
            transaction.name,
            transaction.partner_id.email,
            str(transaction.id)])
        # TODO FIX ME we need to pass th browser info here and not in 3D
        vals = {
            'amount': {
                "value": self._get_formatted_amount(),
                "currency": transaction.currency_id.name},
            'reference': description,
            'browserInfo': kwargs.get('browserInfo'),
            'additionalData': {"executeThreeD": "true"}  # optional may be?
            }
        if kwargs.get('encrypted_card'):
            vals['additionalData'] = {
                'card.encrypted.json': kwargs['encrypted_card'],
                'executeThreeD': 'true'
                }
        else:
            raise UserError(_('Error: encrypted_card information missing!'))
        return vals

    def _get_adyen_client(self):
        account = self._get_account()
        data = account.get_data()
        ady = Adyen.Adyen()
        ady.payment.client.username = data['username']
        ady.payment.client.platform = str(data['platform'])
        ady.payment.client.merchant_account = data['merchant_account']
        ady.payment.client.password = account._get_password()
        ady.payment.client.app_name = data['app_name']
        return ady.payment

    def _create_transaction(self, source=None, **kwargs):
        payload = self._prepare_charge(source=source, **kwargs)
        return self._http_adyen_request('authorise', payload)

    def _parse_creation_result(self, transaction, **kwargs):
        # TODO does it make sense to call super with the specific AdyenResult
        # object?
        res = super(PaymentService, self).\
            _parse_creation_result(transaction, **kwargs)
        transaction = transaction.message
        res.update({
            'amount': self.collection._get_amount_to_capture(),
            'external_id': transaction['pspReference'],
            'state': MAP_SOURCE_STATE[transaction['resultCode']],
            'data': json.dumps(transaction),
            })
        if transaction.get('resultCode') == 'RedirectShopper':
            res.update({
                'url': transaction['issuerUrl'],
                'meta': {
                    'paRequest': transaction['paRequest'],
                    'MD': transaction['md'],
                    'termUrl': transaction.get('issuerUrl'),
                    }
                })
        return res

    # Code for capturing the transaction

    def _parse_capture_result(self, charge):
        return {
            'external_id': charge['pspReference'],
            'state': MAP_SOURCE_STATE[str(charge['response'])],
            'data': json.dumps(charge),
            }

    def _prepare_capture_payload(self):
        transaction = self.collection
        return {
            'originalReference': transaction.external_id,
            'modificationAmount': {
                'currency': transaction.currency_id.name,
                'value': self._get_formatted_amount(transaction.amount)
                }
            }

    def capture(self):
        if self.collection.external_id.isdigit():
            payload = self._prepare_capture_payload()
            charge = self._get_adyen_client().capture(request=payload)
            vals = self._parse_capture_result(charge.message)
            self.collection.write(vals)
