# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Payment Gateway Move Completion",
    "summary": "Auto Complete move base on payment gateway transaction",
    "version": "8.0.1.0.0",
    "category": "Payment",
    "website": "www.akretion.com",
    "author": " Akretion",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "payment_gateway",
        "account_move_transactionid_import",
    ],
    "data": [
        "data/completion_rule_data.xml",
    ],
    "demo": [
    ],
    "qweb": [
    ]
}
