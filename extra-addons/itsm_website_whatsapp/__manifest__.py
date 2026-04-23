# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2026 IT-Solutions.mg. All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    "name": "Website WhatsApp Chat Button",
    "version": "19.0.1.0.0",
    "category": "Website",
    "summary": "Add a floating WhatsApp chat button on your website",
    "description": """
        Add a customizable floating WhatsApp button to your website:
        - Configurable phone number and default message
        - Button position, size, and color customization
        - Pulse animation to attract attention
        - Business hours scheduling (show only during work hours)
        - Tooltip text customization
        - Mobile responsive
        - Enable/disable per website
    """,
    "author": "IT-Solutions.mg",
    "depends": ["website"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "itsm_website_whatsapp/static/src/scss/whatsapp_button.scss",
            "itsm_website_whatsapp/static/src/js/whatsapp_button.js",
        ],
    },
    'images': [
        'static/images/main_screenshot.png',
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "price": 0,
    "currency": "EUR",
}
