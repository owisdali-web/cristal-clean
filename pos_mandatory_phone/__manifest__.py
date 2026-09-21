{
    'name': 'Mandatory & Unique Contact Phone',
    'version': '18.0.1.1.0',
    'summary': 'Makes phone number mandatory and ensures uniqueness with links to existing contacts.',
    'category': 'Sales/Point of Sale',
    'author': 'Tag by Omar Kraim',
    'depends': ['base', 'point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_mandatory_phone/static/src/js/partner_details_edit.js',
            'pos_mandatory_phone/static/src/xml/partner_details_edit.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}