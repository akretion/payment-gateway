import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo10-addons-akretion-payment-gateway",
    description="Meta package for akretion-payment-gateway Odoo addons",
    version=version,
    install_requires=[
        'odoo10-addon-payment_gateway',
        'odoo10-addon-payment_gateway_adyen',
        'odoo10-addon-payment_gateway_move_completion',
        'odoo10-addon-payment_gateway_paypal',
        'odoo10-addon-payment_gateway_stripe',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 10.0',
    ]
)
