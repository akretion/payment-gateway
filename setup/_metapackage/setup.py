import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo8-addons-akretion-payment-gateway",
    description="Meta package for akretion-payment-gateway Odoo addons",
    version=version,
    install_requires=[
        'odoo8-addon-payment_gateway',
        'odoo8-addon-payment_gateway_move_completion',
        'odoo8-addon-payment_gateway_paypal',
        'odoo8-addon-payment_gateway_stripe',
        'odoo8-addon-sale_quick_payment_gateway',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 8.0',
    ]
)
