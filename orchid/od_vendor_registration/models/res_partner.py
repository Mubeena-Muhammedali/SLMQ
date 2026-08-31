
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    od_cr_number = fields.Char(
        string='CR',
        copy=False,
    )
    od_category = fields.Selection([
        ('ksa_based_vendor', 'KSA-based Vendor'),
        ('onsite_work_vendor', 'On-site Work Vendor'),
        ('technical_engineering_vendor', 'Technical/Engineering Vendor'),
    ], string='Category', tracking=True)

    od_vendor_code = fields.Char(
        string='Vendor ID',
        copy=False,
        readonly=True,
        index=True,
    )
    od_vendor_document_count = fields.Integer(
        compute='_compute_od_vendor_document_count', string='Documents',
        help='Count of Vendor Registration documents linked to this Partner.')

    od_registration_url = fields.Char(string='Registration URL')


    def _compute_od_vendor_document_count(self):
        for rec in self:
            rec.od_vendor_document_count = self.env[
                'od.vendor.document'].sudo().search_count(
                [('partner_id', '=', rec.id)])

    def action_od_vendor_document_view(self):
        """Opens a view listing all Vendor Registration documents linked
        to this Partner."""
        self.ensure_one()
        return {
            'name': _('Documents'),
            'domain': [('partner_id', '=', self.id)],
            'res_model': 'od.vendor.document',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'context': "{'default_partner_id': %s}" % self.id,
        }

    def _get_expired_vendor_documents(self):
        """Return expired documents for the vendor."""
        self.ensure_one()

        today = fields.Date.today()

        return self.env['od.vendor.document'].sudo().search([
            ('partner_id', '=', self.id),
            ('has_expiry', '=', True),
            ('expiry_date', '<', today),
        ])

    def _check_vendor_document_expiry(self):
        """Block purchasing if any vendor document has expired."""
        for partner in self:
            expired_documents = partner._get_expired_vendor_documents()

            if expired_documents:
                document_names = '\n- '.join(
                    expired_documents.mapped('document_type_id.name')
                )

                raise UserError(_(
                    'Purchase Order cannot be created for this vendor.\n\n'
                    'The following vendor document(s) have expired:\n'
                    '- %s\n\n'
                    'Please renew the expired document(s) before creating '
                    'a Purchase Order.'
                ) % document_names)