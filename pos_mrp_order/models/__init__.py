# -*- coding: utf-8 -*-
# Based on "Make MRP Orders from POS" by Cybrosys Technologies (AGPL-3).
# Reworked to create Delivery + MO through procurement rules, exactly like Sales.
from . import procurement_group
from . import mrp_production
from . import pos_order
from . import pos_order_line
from . import stock_picking
from . import product_template
