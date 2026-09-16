# 18.0.19.1 - Odoo 18 user API compatibility fix

- Replaced `useService("user")` in `OpsCenter` with the Odoo 18 exported `user` object from `@web/core/user`.
- Manager-group detection continues to use `await user.hasGroup("car_wash_dashboard.group_car_wash_manager")`.
- No Python model, controller, security, RPC contract, menu structure, template, or business logic changes.
