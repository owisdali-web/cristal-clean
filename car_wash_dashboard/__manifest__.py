{
    'name': 'Crystal Clean Car Wash Dashboard',
    'version': '18.0.3.1',
    'category': 'Operations/Car Wash',
    'summary': 'Visual operations dashboard for Crystal Clean car-wash sales, stations, inventory and finance',
    'author': 'Crystal Clean',
    'depends': ['web', 'sale', 'sale_mrp', 'mrp', 'mrp_workorder', 'stock', 'account'],
    'data': ['security/ir.model.access.csv', 'views/menu_views.xml', 'views/sale_order_views.xml'],
    'assets': {'web.assets_backend': ['car_wash_dashboard/static/src/scss/dashboard.scss', 'car_wash_dashboard/static/src/scss/dashboard_additions.scss', 'car_wash_dashboard/static/src/scss/dashboard_v2.scss', 'car_wash_dashboard/static/src/scss/dashboard_v3.scss', 'car_wash_dashboard/static/src/css/dashboard_motion.css', 'car_wash_dashboard/static/src/js/libs/chart.umd.min.js', 'car_wash_dashboard/static/src/js/dashboard.js', 'car_wash_dashboard/static/src/xml/dashboard.xml']},
    'installable': True,
    'application': True}
