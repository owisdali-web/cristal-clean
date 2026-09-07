{
    'name': 'Car Wash Dashboard',
    'version': '18.0.1.0',
    'category': 'Manufacturing',
    'summary': 'Modern dashboard for car wash operations',
    'author': 'Your Company',
    'depends': ['sale', 'mrp', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'car_wash_dashboard/static/src/scss/dashboard.scss',
            'car_wash_dashboard/static/src/js/libs/chart.umd.min.js',
            'car_wash_dashboard/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
}