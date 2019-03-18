.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================
Payment Gateway Adyen
======================

This module add adyen payment support for odoo

Installation
============

Just install the module

Configuration
=============

TODO

Usage
=====

TODO

Runing Test
===========
Test are recorded with VCR, so on travis test are running offline without real
account. If you want to run the test without VCR mock you need to configure the
following enviroment variable
ADYEN_API=
ADYEN_ACCOUNT=
ADYEN_USER=
VCR_MODE=all

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/akretion/payment_gateway/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Sébastien BEAU <sebastien.beau@akretion.com>

Funders
-------

The development of this module has been financially supported by:

* Adaptoo (www.adaptoo.com)
* Akretion R&D
