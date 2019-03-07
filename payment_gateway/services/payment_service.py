# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import AbstractComponent
from odoo.exceptions import UserError
from odoo import _
from odoo.osv import expression
import logging
_logger = logging.getLogger(__name__)

try:
    from cerberus import Validator
except ImportError:
    _logger.debug('Can not import cerberus')


class PaymentService(AbstractComponent):
    _name = 'payment.service'
    _description = 'Payment Service'
    _collection = 'gateway.transaction'
    _usage = 'gateway.provider'
    _allowed_capture_method = None
    _webhook_method = []

    @property
    def _provider_name(self):
        return self._name.replace('payment.service.', '')

    # TODO this code is inspired from base_rest
    # maybe we should found a way to mutualise it
    def _get_schema_for_method(self, method_name):
        validator_method = '_validator_%s' % method_name
        if not hasattr(self, validator_method):
            raise NotImplementedError(validator_method)
        return getattr(self, validator_method)()

    def _secure_params(self, method, params):
        """
        This internal method is used to validate and sanitize the parameters
        expected by the given method.  These parameters are validated and
        sanitized according to a schema provided by a method  following the
        naming convention: '_validator_{method_name}'.
        :param method:
        :param params:
        :return:
        """
        method_name = method.__name__
        schema = self._get_schema_for_method(method_name)
        v = Validator(schema, purge_unknown=True)
        if v.validate(params):
            return v.document
        _logger.error("BadRequest %s", v.errors)
        raise UserError(_('Invalid Form'))

    def dispatch(self, method_name, params):
        if method_name not in self._webhook_method:
            raise UserError(_('Method not allowed for service %s'), self._name)

        func = getattr(self, method_name, None)
        if not func:
            raise UserError(_('Method %s not found in service %s'),
                            method_name, self._name)
        secure_params = self._secure_params(func, params)
        return func(**secure_params)

    def _get_account(self):
        gateway = self.collection
        domain = []
        provider_account = gateway.payment_mode_id.provider_account
        if provider_account:
            domain = expression.AND(
                [domain, [('id', '=', provider_account.id)]])
        keychain = self.env['keychain.account']
        namespace = (self._name).replace('payment.service.', '')
        domain = expression.AND([domain, [('namespace', '=', namespace)]])
        return keychain.sudo().retrieve(domain)[0]

    def _create_transaction(self, **kwargs):
        """Create the transaction on the backend of the service provider
        and return a json of the result of the creation"""
        raise NotImplemented

    def _transaction_need_3d_secure(self):
        """You can inherit this method to define if we should or not apply
        the 3d secure on the transaction. Each gateway implementation must
        depend of this method"""
        return True

    def _parse_creation_result(self, transaction, **kwargs):
        raise NotImplemented

    def generate(self, **kwargs):
        """Generate the transaction in the provider backend
        and update the odoo gateway.transaction"""
        transaction = self._create_transaction(**kwargs)
        vals = self._parse_creation_result(transaction, **kwargs)
        return self.collection.write(vals)

    def get_state(self):
        raise NotImplemented

    def capture(self, amount):
        raise NotImplemented
