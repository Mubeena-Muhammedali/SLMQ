/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";
import { xml } from "@odoo/owl";

export class OdVendorRegistrationListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    async onClickRegistrationLink() {
        const action = await this.orm.call(
            "od.vendor.registration",
            "action_show_self_service_link",
            []
        );
        this.actionService.doAction(action);
    }
}

// Defined inline (instead of a separate static/src/xml file) so the template
// registers as soon as this JS module loads, independent of the XML-assets
// bundling pipeline.
const buttonsTemplate = xml`
    <t t-inherit="web.ListView.Buttons" t-inherit-mode="extension">
        <xpath expr="//button[hasclass('o_list_button_add')]" position="after">
            <button type="button"
                    class="btn btn-secondary o_vendor_registration_link_btn"
                    t-on-click="onClickRegistrationLink">
                Registration Link
            </button>
        </xpath>
    </t>
`;

export const OdVendorRegistrationListView = {
    ...listView,
    Controller: OdVendorRegistrationListController,
    buttonTemplate: buttonsTemplate,
};

registry.category("views").add("od_vendor_registration_list", OdVendorRegistrationListView);
