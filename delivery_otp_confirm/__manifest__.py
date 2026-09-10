{
    'name': 'Delivery OTP Confirmation',
    'version': '18.0.1.2.0',
    'category': 'Warehouse',
    'summary': 'Require OTP from customer to validate delivery orders',
    'author': 'Tag Technology by Omar Kraim & Owis',
    'depends': ['stock', 'sale', 'TAG_whats_18'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/delivery_otp_views.xml',
        'views/stock_picking_views.xml',
        'wizards/otp_verify_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'delivery_otp_confirm/static/src/js/otp_countdown_widget.js',
            'delivery_otp_confirm/static/src/xml/otp_countdown_widget.xml',
            'delivery_otp_confirm/static/src/scss/otp_countdown_widget.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}