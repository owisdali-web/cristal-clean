{
    'name': 'Crystal Clean Car Wash Dashboard',
    'version': '18.0.5.2',
    'category': 'Operations/Car Wash',
    'summary': 'Crystal Clean concept-replica dashboard with live Odoo operations data',
    'author': 'Crystal Clean',
    'depends': ['web', 'sale', 'sale_mrp', 'mrp', 'mrp_workorder', 'stock', 'account'],
    'data': ['security/ir.model.access.csv', 'views/menu_views.xml', 'views/sale_order_views.xml'],
    'assets': {'web.assets_backend': ['car_wash_dashboard/static/src/css/dashboard_concept_replica.css', 'car_wash_dashboard/static/src/js/dashboard.js', 'car_wash_dashboard/static/src/xml/dashboard.xml']},
    'installable': True,
    'application': True,
}
