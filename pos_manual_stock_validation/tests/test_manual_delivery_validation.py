from odoo import Command
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPosManualDeliveryValidation(TestPointOfSaleCommon):

    def test_paid_pos_order_keeps_delivery_pending(self):
        self.pos_config.open_ui()
        session = self.pos_config.current_session_id

        product = self.env["product.product"].create({
            "name": "Manual POS Delivery Product",
            "available_in_pos": True,
            "is_storable": True,
            "list_price": 10.0,
        })
        stock_location = self.company_data["default_warehouse"].lot_stock_id
        self.env["stock.quant"]._update_available_quantity(
            product, stock_location, 5.0
        )

        order = self.PosOrder.create({
            "company_id": self.env.company.id,
            "session_id": session.id,
            "partner_id": self.partner1.id,
            "pricelist_id": self.partner1.property_product_pricelist.id,
            "lines": [Command.create({
                "name": product.display_name,
                "product_id": product.id,
                "price_unit": 10.0,
                "qty": 1.0,
                "tax_ids": [Command.clear()],
                "price_subtotal": 10.0,
                "price_subtotal_incl": 10.0,
            })],
            "amount_tax": 0.0,
            "amount_total": 10.0,
            "amount_paid": 0.0,
            "amount_return": 0.0,
            "last_order_preparation_change": "{}",
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        payment = self.PosMakePayment.with_context(**payment_context).create({
            "amount": 10.0,
            "payment_method_id": self.cash_payment_method.id,
        })
        payment.with_context(**payment_context).check()

        self.assertEqual(order.state, "paid")
        self.assertEqual(len(order.picking_ids), 1)
        picking = order.picking_ids
        self.assertNotEqual(picking.state, "done")
        self.assertNotIn("done", picking.move_ids.mapped("state"))
        self.assertFalse(any(picking.move_ids.mapped("picked")))
        self.assertIn(
            picking.state,
            ("assigned", "confirmed", "partially_available", "waiting"),
        )
