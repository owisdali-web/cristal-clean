# -*- coding: utf-8 -*-
{
    "name": "Customer Required in POS",
    "author": "AskByte Technolab",
    "summary": """Customer Required in POS""",
    "description": """Customer Required in POS""",
    "category": "Point of Sale",
    "version": "18.0.1.0",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "abt_customer_required_in_pos/static/src/app/store/pos_store.js",
            "abt_customer_required_in_pos/static/src/app/screens/payment_screen/payment_screen.xml"
        ],
    }, 
    "images": ["static/description/thumbnail.png"],
    "license": "LGPL-3",
    "application": True,
    "auto_install": False,
}
