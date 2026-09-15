# Crystal Clean Dashboard V10.3

## What changed
- Sidebar simplified: kept only Home, Appointments, Stations, Customers & HR, Materials & Accounts, POS, and Customer Screen.
- Removed sidebar entries for Vehicles, Reports, Maintenance, and Settings.
- Removed chat and bell icons from the top bar.
- Top bar user block now reads the current Odoo user instead of fixed mock text.
- Added a combined **Customers & Human Resources** page with customer KPIs, user/employee table, shifts, attendance, and quick actions.
- Rebuilt the **Materials & Accounts** page in a layout closer to the approved reference: financial KPIs, weekly sales chart, expense distribution, materials band, recent accounting moves, low stock alerts, and quick actions.
- Improved the **Customer Screen** to look more realistic and suitable for a display in the waiting lounge.

## Notes
- HR/user metrics are defensive and work even if some HR apps are not installed.
- Existing hidden pages were not fully deleted from code to avoid breaking internal shortcuts, but they are removed from the sidebar.
