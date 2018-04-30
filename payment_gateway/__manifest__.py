# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Payment Gateway",
    "summary": "Payment Gateway alternative for odoo",
    "version": "10.0.1.0.0",
    "category": "Payment",
    "website": "www.akretion.com",
    "author": " Akretion",
    "license": "AGPL-3",
    "application": False,
    'installable': True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "queue_job",
        "account_payment_sale",
        "keychain",
        "base_suspend_security",
    ],
    "data": [
        "views/account_payment_mode_view.xml",
        "views/gateway_transaction_view.xml",
        "security/ir.model.access.csv",
    ],
    "demo": [
    ],
    "qweb": [
    ]
}
