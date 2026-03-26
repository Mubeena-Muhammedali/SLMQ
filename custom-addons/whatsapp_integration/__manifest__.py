{
    'name': 'WhatsApp Integration',
    'version': '19.0.0.0',

    'summary': 'Send WhatsApp messages and PDF attachments using Twilio',

    'description': """
        WhatsApp Integration using Twilio

        This module provides a simple and reusable service to send WhatsApp messages
        directly from Odoo using Twilio APIs.

        Features:
        - Send plain text WhatsApp messages
        - Send PDF attachments via WhatsApp
        - Centralized Twilio configuration in Settings
        - Reusable service method callable from any custom module

        Configuration:
        - Twilio Account SID
        - Twilio Auth Token
        - Twilio WhatsApp-enabled number

        Usage:
        Developers can call the service from any model to send messages or documents.

        This module is designed to be lightweight, generic, and easy to integrate
        with other business workflows like invoices, sales, and notifications.
    """,

    'license': 'LGPL-3',
    'author': 'FSIB',

    'depends': ['base_setup'],

    'data': [
        'views/res_config_settings_view.xml',
    ],

    'installable': True,
    'application': False,
}