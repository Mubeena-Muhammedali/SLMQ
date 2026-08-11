{
    'name': 'Vendor Registration',
    'version': '19.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Self-service vendor registration via a shareable public form with a Register/Review/Approve workflow',
    'description': """
Vendor Registration
====================
This module lets an internal user create a Vendor Registration record from
Odoo (a normal "New" button, like any other model) and share a unique public
URL with an external vendor/supplier contact.

Workflow
--------
1. **Register**  - Internal user creates the record (or it is created empty).
   The chatter/form shows a unique, token-protected public URL. While the
   record is in this state, the *external* vendor can open that URL and
   fill in / edit their own data (Name, Phone, Contact Person, Email,
   Address, supporting documents). Submitting the public form moves the
   record to *Review*.
2. **Review** - Data is locked for the external user. An internal
   Purchase/Vendor officer reviews the submitted information and documents.
3. **Approve** - Internal user approves the registration. A matching
   `res.partner` (Vendor) record is created/linked automatically. The
   record is now fully locked for the external user - only the Register
   state allows the public form to be edited.

Key points
----------
* Model: ``od.vendor.registration`` (Odoo 19 custom models in this project
  are prefixed with ``od.``)
* Fields mirror the "partner master": Name, Phone, Contact Person, Email,
  Street/Street2/City/State/Zip/Country
* Supporting documents can be uploaded from the public form
* A unique, non-guessable ``access_token`` protects the public URL
* Only records in the *Register* state accept edits from the public form
* On approval, a ``res.partner`` supplier record is created and linked
""",
    'author': 'Your Company',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'data/sequence.xml',    
        'security/ir.model.access.csv',
        'wizard/vendor_registration_link_wizard_views.xml',
        'views/vendor_registration_views.xml',
        'views/vendor_registration_public_templates.xml',
        'views/res_partner_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'od_vendor_registration/static/src/js/vendor_registration_list_view.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
