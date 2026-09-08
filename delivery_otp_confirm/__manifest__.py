{
    'name': 'Delivery OTP Confirmation',
    'version': '18.0.1.0.0',
    'category': 'Warehouse',
    'summary': 'Require OTP from customer to validate delivery orders',
    'author': 'Tag Technology',
    'depends': ['stock', 'sale'],  # optional: reuse token retrieval
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/delivery_otp_views.xml',
        'views/stock_picking_views.xml',
        'wizards/otp_verify_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
