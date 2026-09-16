{
    "name": "Crystal Clean Station Dashboard",
    "version": "18.0.1.0.0",
    "summary": "Interactive light dashboard for Crystal Clean car wash stations",
    "description": "A 16:9 RTL live station dashboard for Crystal Clean - Benghazi.",
    "author": "Takaddum",
    "category": "Operations/Manufacturing",
    "license": "LGPL-3",
    "depends": [
        "web",
        "car_wash_dashboard"
    ],
    "data": [
        "views/dashboard_actions.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "crystal_clean_station_dashboard/static/src/css/dashboard.css",
            "crystal_clean_station_dashboard/static/src/js/dashboard.js",
            "crystal_clean_station_dashboard/static/src/xml/dashboard.xml"
        ]
    },
    "application": False,
    "installable": True,
    "auto_install": False
}
