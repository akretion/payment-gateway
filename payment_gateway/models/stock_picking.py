# -*- coding: utf-8 -*-
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from openerp import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # TODO capture if not captured

    def capture_transaction(self):
        # TODO
        pass

    def todo_set_done(self):
        # TODO
        pass
