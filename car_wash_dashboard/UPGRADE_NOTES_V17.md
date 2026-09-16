# Crystal Clean V17 - Customer Display Backend Contract

- Adds a dedicated `Car Wash Customer Display` security group.
- The group intentionally does not imply Internal User, MRP, POS, Stock or Accounting access.
- Adds `get_customer_display_data()` and `/car_wash/customer_display/data`.
- Adds an authenticated, permission-gated company logo endpoint.
- Customer-facing payload excludes customer identity, phone, monetary/payment/accounting data and operator identity.
- Progress is computed read-only from Work Order completion plus current-stage elapsed/expected duration.
- ETA is current-stage only and becomes unreliable if a station is closed, in maintenance, over capacity, or lacks expected duration.
- No Customer Display visual client/menu/action is added in V17; visual work remains intentionally deferred.
- No MRP/POS/Stock/Accounting business logic is changed.
