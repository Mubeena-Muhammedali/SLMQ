# Vendor Registration (`od_vendor_registration`)

Odoo 19 module that lets a buyer/purchasing team share a public, unique link
with an external vendor so the vendor can self-register their own company
details (like a lightweight `res.partner` master), attach documents, and go
through a **Register → Review → Approve** workflow.

## Technical model

| | |
|---|---|
| Model | `od.vendor.registration` |
| Menu | Vendor Registration → Registrations |
| Public URL | `<base_url>/vendor/register/<record_id>/<access_token>` |

Field names follow Odoo 19 naming conventions used in this project (custom
models are prefixed `od.`).

### Fields

| Field | Type | Notes |
|---|---|---|
| `name` | Char | Vendor / company name |
| `contact_person` | Char | |
| `phone` | Char | |
| `email` | Char | |
| `street`, `street2`, `city`, `state_id`, `zip`, `country_id` | Address fields, same shape as `res.partner` |
| `document_ids` | Many2many → `ir.attachment` | Documentation uploaded by the vendor |
| `documentation_notes` | Text | Free-text notes about the documents |
| `state` | Selection | `register` / `review` / `approve` |
| `access_token` | Char | Random UUID, generated on create, used to secure the public URL |
| `registration_url` | Char (computed) | Full shareable link, shown on the form with a copy-to-clipboard widget |
| `partner_id` | Many2one → `res.partner` | Auto-created/linked when approved |

## Workflow

1. **Register** – An internal user clicks **New** on the *Vendor
   Registrations* menu (same as any other Odoo model) and saves the record.
   The form shows a **Registration URL** field (with a "copy" button) — this
   is the link to send to the vendor by email/chat.
2. The vendor opens the link (no login required — it's a public,
   token-protected website page) and fills in Name, Phone, Contact Person,
   Email, Address, and uploads supporting documents.
   * This page is only *editable* while the record's `state = register`.
     Once submitted it flips to `review` and the public page becomes
     read-only for that vendor.
3. **Review** – An internal user (Purchasing/Vendor Officer) checks the
   submitted data and documents on the backend form.
   * `Reopen for Vendor` sends it back to `register` if corrections are
     needed (the same public link becomes editable again).
4. **Approve** – Internal user clicks **Approve**. This:
   * Creates (or updates) a `res.partner` record with `supplier_rank = 1`
     and copies the address fields across.
   * Creates a child contact for the `contact_person`, if provided.
   * Copies the uploaded documents onto the new partner record.
   * Locks the registration (state = `approve`); the public link becomes
     permanently read-only.

## Security

* Backend model access: any internal user (`base.group_user`) can create,
  read, update, delete registration records — restrict further with a
  dedicated group/record rule if you need role-based approval.
* Public/portal users never get direct ORM access to the model. The
  controller uses `sudo()` internally (the same pattern Odoo's own
  "Contact Us" website form uses) and explicitly checks `state == 'register'`
  before allowing any write, so a vendor can never edit a record that has
  moved to Review/Approve — even by replaying the old URL.
* The `write()` override on the model is a second line of defense: any
  non-internal-group write to a non-`register` record raises a `UserError`.

## Files

```
od_vendor_registration/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py                     # public /vendor/register/... routes
├── models/
│   ├── __init__.py
│   └── od_vendor_registration.py   # model + workflow actions
├── security/
│   └── ir.model.access.csv
└── views/
    ├── od_vendor_registration_views.xml   # backend form/list/search/menu
    └── public_templates.xml               # public form + thank-you page
```

> This module does **not** depend on the `website` app. The public pages
> are plain `auth='public'` HTTP routes rendering self-contained QWeb
> templates (own `<html>`/inline CSS), so it installs cleanly even on
> databases where the Website app isn't installed or would pull in
> unrelated broken modules.

## Installation

1. Copy the `od_vendor_registration` folder into your Odoo 19 `addons`
   path.
2. Update the apps list, then install **Vendor Registration**.
3. Go to **Vendor Registration → Registrations → New**, save, and share the
   generated **Registration URL** with your vendor.

## Possible extensions

* Add a security group (e.g. *Vendor Registration / Officer*) and a record
  rule so only that group can `Approve`.
* Add automated emails (e.g. `mail.template`) triggered on state changes —
  "link created", "submitted for review", "approved" — using
  `message_post` hooks already present in the model.
* Add a scheduled action to expire/delete stale `register`-state links after
  N days for extra security.
