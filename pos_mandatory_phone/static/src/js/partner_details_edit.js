/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_details_edit/partner_details_edit";

const PARTNER_FIELDS = [
    "name", "phone", "mobile", "email", "street", "street2",
    "city", "zip", "country_id", "state_id", "vat", "barcode",
    "property_product_pricelist",
];

patch(PartnerDetailsEdit.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    /**
     * Intercept Save: if the phone already belongs to another contact,
     * ask the cashier whether to reuse it instead of creating a new one.
     */
    async saveChanges() {
        const phone = this.state.partner.phone;
        const currentId = this.props.partner && this.props.partner.id;

        if (phone) {
            let existing = false;
            try {
                existing = await this.orm.call(
                    "res.partner",
                    "find_partner_by_phone",
                    [phone]
                );
            } catch (e) {
                existing = false;
            }

            if (existing && existing.id !== currentId) {
                return new Promise((resolve) => {
                    this.dialog.add(ConfirmationDialog, {
                        title: _t("Phone number already in use"),
                        body: _t(
                            "The phone number '%s' is already linked to the contact '%s'.\n\n" +
                            "Do you want to use that existing contact for this order?",
                            phone,
                            existing.name
                        ),
                        confirmLabel: _t("Use existing contact"),
                        cancelLabel: _t("Cancel"),
                        confirm: async () => {
                            await this._useExistingPartner(existing.id);
                            resolve();
                        },
                        cancel: () => resolve(),
                    });
                });
            }
        }
        return super.saveChanges(...arguments);
    },

    /**
     * Dedicated button: "Use Existing Contact".
     */
    async onUseExistingContact() {
        const phone = this.state.partner.phone;
        if (!phone) {
            this.notification.add(
                _t("Please enter a phone number first."),
                { type: "warning" }
            );
            return;
        }

        let existing = false;
        try {
            existing = await this.orm.call(
                "res.partner",
                "find_partner_by_phone",
                [phone]
            );
        } catch (e) {
            existing = false;
        }

        if (!existing) {
            this.notification.add(
                _t("No existing contact found with the phone number %s.", phone),
                { type: "warning" }
            );
            return;
        }

        await this._useExistingPartner(existing.id);
    },

    /**
     * Attach the existing partner to the current order and close the form.
     */
    async _useExistingPartner(partnerId) {
        const pos = this.env.services.pos;
        const order = pos.get_order();

        let partner = pos.db.get_partner_by_id(partnerId);
        if (!partner) {
            const [record] = await this.orm.read(
                "res.partner",
                [partnerId],
                PARTNER_FIELDS
            );
            partner = record;
            pos.db.addPartner(partner);
        }

        await order.set_partner(partner);

        // Close the edit form without saving
        if (this.props.cancel) {
            this.props.cancel();
        }

        this.notification.add(
            _t("Existing contact '%s' set on the order.", partner.name),
            { type: "success" }
        );
    },
});