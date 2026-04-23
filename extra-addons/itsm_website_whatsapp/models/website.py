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

from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    wa_enabled = fields.Boolean(string="Enable WhatsApp Button", default=False)
    wa_phone = fields.Char(
        string="WhatsApp Number",
        help="Phone number with country code, e.g. +261340000000",
    )
    wa_default_message = fields.Char(
        string="Default Message",
        default="Hello! I have a question.",
        help="Pre-filled message when the visitor opens WhatsApp.",
    )
    wa_tooltip = fields.Char(
        string="Tooltip Text",
        default="Chat with us on WhatsApp",
    )
    wa_position = fields.Selection(
        [
            ("bottom-right", "Bottom Right"),
            ("bottom-left", "Bottom Left"),
            ("bottom-center", "Bottom Center"),
            ("mid-right", "Middle Right"),
            ("mid-left", "Middle Left"),
        ],
        string="Button Position",
        default="bottom-right",
    )
    wa_size = fields.Selection(
        [
            ("small", "Small"),
            ("medium", "Medium"),
            ("large", "Large"),
        ],
        string="Button Size",
        default="medium",
    )
    wa_color = fields.Char(
        string="Button Color",
        default="#25D366",
        help="Hex color code for the button background.",
    )
    wa_pulse = fields.Boolean(
        string="Pulse Animation",
        default=True,
        help="Show a pulse animation to attract visitor attention.",
    )
    wa_business_hours = fields.Boolean(
        string="Business Hours Only",
        default=False,
        help="Show the button only during business hours.",
    )
    wa_hour_from = fields.Float(
        string="From (Hour)",
        default=8.0,
        help="Start hour in 24h format (e.g. 8.0 for 8:00 AM).",
    )
    wa_hour_to = fields.Float(
        string="To (Hour)",
        default=18.0,
        help="End hour in 24h format (e.g. 18.0 for 6:00 PM).",
    )
    wa_days = fields.Char(
        string="Business Days",
        default="1,2,3,4,5",
        help="Comma-separated day numbers (1=Monday, 7=Sunday). Default: Mon-Fri.",
    )
