{
    'name': 'Car Wash Management',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'Manage car wash orders with location capacity and flow.',
    'description': """
        Complete car wash management:
        - Dynamic pricing per car type & service.
        - Configurable location flows (step-by-step).
        - Capacity management with waiting zone.
        - Manual progression and override.
        - Real-time Kanban dashboard.
    """,
    'author': 'Tag by Omar Kraim & Owis',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/demo_data.xml',
        'views/car_wash_order_views.xml',
        'views/car_wash_location_views.xml',
        'views/car_wash_service_views.xml',
        'views/car_wash_type_views.xml',
        'views/car_wash_pricelist_views.xml',
        'views/dashboard_kanban.xml',
        'wizard/manual_override_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}