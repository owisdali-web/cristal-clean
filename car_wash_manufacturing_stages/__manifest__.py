{
    "name": "Car Wash Manufacturing Stages",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Sequence manufacturing work orders by car-wash work center",
    "description": """
Adds a car-wash routing sequence to work centers.

For manufacturing orders with Car Wash Routing enabled:
- Work centers are ordered by Car Wash Sequence.
- Work orders on the same sequence can be ready together.
- Every work order on a later sequence waits for all work orders
  on the immediately preceding used sequence of the same MO.
- The routing is isolated per manufacturing order.
""",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["mrp"],
    "data": [
        "security/ir.model.access.csv",
        "views/mrp_workcenter_views.xml",
        "views/mrp_production_views.xml",
    ],
    "installable": True,
    "application": False,
}
