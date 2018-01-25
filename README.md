[![Build Status](https://travis-ci.org/akretion/payment-gateway.svg?branch=10.0)](https://travis-ci.org/akretion/payment-gateway)
[![codecov](https://codecov.io/gh/akretion/payment-gateway/branch/10.0/graph/badge.svg)](https://codecov.io/gh/akretion/payment-gateway/branch/10.0)
[![Code Climate](https://codeclimate.com/github/akretion/payment-gateway/badges/gpa.svg)](https://codeclimate.com/github/akretion/payment-gateway)


# Payment Gateway

Alternative implementation of payment gateway for odoo
Note : this module are still moving a lot


## Why?
Because I need something that work well for Shopinvader project and I think we should use existing python library instead of redevelopping the code inside Odoo (less maintenance and more feature)

- Stripe gateway depend on the official Stripe lib : https://github.com/stripe/stripe-python
- Paypal gateway depend on the official Paypal lib : https://github.com/paypal/PayPal-Python-SDK

## Roadmap
- Refactor service class to use component : https://github.com/OCA/connector/tree/10.0/component
- Adding the possibility to paid and refund from the odoo backoffice (from a sale or from an invoice)
- Add documentation
- Maybe one day be able to be merge with Odoo gateway...

## Integration with Odoo website
- We do not plan to work on the integration with Odoo Website as we developpe a better alternative ;) Shopinvader
