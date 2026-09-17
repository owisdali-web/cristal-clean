# -*- coding: utf-8 -*-
# Based on "Make MRP Orders from POS" by Cybrosys Technologies (AGPL-3).
# Reworked to create MOs through procurement rules, exactly like Sales.
{
    'name': 'Make MRP Orders from POS',
    'version': '18.0.2.1.0',
    'category': 'Point of Sale',
    'summary': 'Create Manufacturing Orders from POS orders the same way Sales does.',
    'description': """Paid POS orders launch procurements on the Manufacture route,
so the Manufacturing Orders are created, merged and confirmed by the standard
stock rules, exactly like confirmed Sales Orders.""",
    'author': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['point_of_sale', 'mrp'],
    'data': [
        'views/product_template_views.xml',
        'views/pos_order_views.xml',
        'views/mrp_production_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'application': False,
}
