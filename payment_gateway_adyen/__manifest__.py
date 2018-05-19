# -*- coding: utf-8 -*-
# Copyright 2018 Akretion (http://www.akretion.com).
# @author Raphael Valyi <raphael.valyi@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Adyen Payment Gateway",
    "summary": "Adyen Payment Gateway alternative for odoo",
    "version": "10.0.1.0.0",
    "category": "Payment",
    "website": "www.akretion.com",
    "author": " Akretion",
    "license": "AGPL-3",
    "application": False,
    'installable': True,
    "external_dependencies": {
        "python": ['Adyen'],
        "bin": [],
    },
    "depends": [
        "payment_gateway",
    ],
    "data": [
        "data/account_payment_mode_data.xml",
    ],
    "demo": [
    ],
    "qweb": [
    ]
}
