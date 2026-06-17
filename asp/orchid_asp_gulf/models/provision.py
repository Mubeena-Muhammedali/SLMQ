# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidProvisionForm(models.Model):
	_name = "od.asp.provision.form"
	_description = "Provision Form"
	_inherit = ['mail.thread']


	@api.depends('vm_ids')
	def compute_values(self):
		for record in self:
			total_compute=0
			total_ram=0
			total_disk=0
			for line in record.vm_ids:
				total_compute+=line.vcpu
				total_ram+=line.vram
				total_disk+=line.disk_qty
			record.total=total_compute
			record.total_ram=total_ram
			record.total_disk=total_disk

	name=fields.Char(string="Name", default="New", copy=False,)
	partner_id = fields.Many2one('res.partner', string="Partner", ondelete='restrict', tracking=True)
	tech_contact_id = fields.Many2one('res.partner', string="Technical Contact", ondelete='restrict', tracking=True, domain="[('parent_id','=',partner_id)]",)
	email =fields.Char(string="Email")
	phone =fields.Char(string="Phone")
	state = fields.Selection([('draft', 'Draft'), ('gm_review', 'Waiting for Approval'), ('dco_action', 'DOC operations'), ('operation', 'Operations'), ('completed', 'Completed'),('cancel','Cancelled')],string="Status", copy=False, default='draft', tracking=True)

	sam_id = fields.Many2one('res.users', string="SAM", ondelete='restrict', tracking=True)
	date = fields.Date(string="Date")
	date_handover = fields.Date(string="Date of Handover")

	# type_of_service_id = fields.Many2one('od.provision.service.type', string="Type of Service", ondelete='restrict', tracking=True)
	type_of_provision_id = fields.Selection([('azzurance','Azzurance'), ('mhs','MHS'), ('cls','CLS')],string="Type of Provision")
	# gm_comments_id = fields.Many2one('od.gm.comments', string="GM Comments", ondelete='restrict', tracking=True)
	gm_comments = fields.Char(string="GM Comments", tracking=True, copy=False)
	# finance_check_id = fields.Many2one('od.finance.check', string="Finance Check", ondelete='restrict', tracking=True)
	finance_check = fields.Boolean(string="Finance Check", tracking=True, copy=False)
	finance_check_remark = fields.Char(string="Remarks", tracking=True, copy=False)

	total = fields.Float(string="Total Compute", compute="compute_values")
	total_ram = fields.Float(string="Total RAM", compute="compute_values")
	total_disk = fields.Float(string="Total Disk in GB", compute="compute_values")
	no_of_public_ip = fields.Integer(string="No of Public IP")

	# DCO Actions
	provisioned_by_id = fields.Many2one('res.users', string="Provisioned BY")
	assurance_cluster_id = fields.Many2one('od.azzurance.cluster', string="Azzurance Cluster")
	public_ip_details = fields.Char(string="Public IP Details")
	backup_details = fields.Char(string="Backup Details")
	firewall_details = fields.Char(string="Firewall Details")
	provision_status = fields.Selection([('In Progress','In Progress'), ('Complete','Complete')],string="Provision Status", default='In Progress')
	handover_to_ops = fields.Selection([('In Progress','In Progress'), ('Complete','Complete')],string="Handover to OPS", default='In Progress')
	# Operations
	tam_id = fields.Many2one('res.users', string="TAM")
	application_installation = fields.Selection([('In Progress','In Progress'), ('Complete','Complete')],string="Application Installation", default='In Progress')
	license_check = fields.Selection([('In Progress','In Progress'), ('Complete','Complete')],string="License Check", default='In Progress')
	test_server = fields.Selection([('In Progress','In Progress'), ('Complete','Complete')],string="Test Server", default='In Progress')
	handover_to_client = fields.Selection([('In Progress','In Progress'), ('Complete','Complete')],string="Handover to client", default='In Progress')

	

	vm_ids =fields.One2many('od.provision.vm.line','provision_id', string="VM Lines", copy=True)
	mhs_ids =fields.One2many('od.provision.mhs','provision_id', string="MHS", copy=True)
	cls_ids =fields.One2many('od.provision.cls','provision_id', string="CLS", copy=True)


	current_revision_id = fields.Many2one('od.asp.provision.form','Current revision',readonly=True,copy=True)
	old_revision_ids = fields.One2many('od.asp.provision.form','current_revision_id','Old revisions',readonly=True,context={'active_test': False})
	revision_number = fields.Integer('Revision',copy=False)
	unrevisioned_name = fields.Char('Provision Reference',copy=False,readonly=True)
	active = fields.Boolean('Active',default=True,copy=True) 
	revised = fields.Boolean('Revised Provision')   



	def button_gmreview(self):
		self.state='gm_review'

	def button_dcoaction(self):
		self.state='dco_action'

	def button_operation(self):
		self.state='operation'

	def button_completed(self):
		self.state='completed'


	@api.model
	def create(self, vals):
		if 'unrevisioned_name' not in vals:
			if vals.get('name', 'New') == 'New':
				seq = self.env['ir.sequence']
				vals['name'] = seq.next_by_code('od.asp.provision.form') or '/'
			vals['unrevisioned_name'] = vals['name']
		return super(OrchidProvisionForm, self).create(vals)
	

	def button_revision(self):
		self.ensure_one()
		view_ref = self.env['ir.model.data'].get_object_reference('orchid_asp_gulf', 'od_asp_provision_form_view')
		view_id = view_ref and view_ref[1] or False,
		self.with_context(provision_revision_history=True).copy()
		self.write({'state': 'draft'})
		self.finance_check = False
		self.finance_check_remark = ""
		return {
			'type': 'ir.actions.act_window',
			'name': _('Provision Form'),
			'res_model': 'od.asp.provision.form',
			'res_id': self.id,
			'view_type': 'form',
			'view_mode': 'form',
			'view_id': view_id,
			'target': 'current',
			'nodestroy': True,
		}
		
		
	def copy(self, defaults=None):
		if not defaults:
			defaults = {}
		if not self.unrevisioned_name:
			self.unrevisioned_name = self.name
		if self.env.context.get('provision_revision_history'):
			prev_name = self.name
			revno = self.revision_number
			self.write({'revision_number': revno + 1,'name': '%s-%02d' % (self.unrevisioned_name,revno + 1)})
			defaults.update({'name': prev_name,'revision_number': revno,'revised':True,'active': True,'state': 'cancel',
				'current_revision_id': self.id,'unrevisioned_name': self.unrevisioned_name,
				'gm_comments':self.gm_comments,'finance_check':self.finance_check,'finance_check_remark':self.finance_check_remark})
		return super(OrchidProvisionForm, self).copy(defaults)

	def action_view_revision(self):
		action = self.env["ir.actions.actions"]._for_xml_id("orchid_asp_gulf.action_od_asp_provision_revision_view")
		action['domain'] = [('id','in',self.old_revision_ids.ids)]
		return action




		




class OrchidProvisionVmLine(models.Model):
	_name = "od.provision.vm.line"
	_description = "VM Lines"

	provision_id= fields.Many2one('od.asp.provision.form', string="Provision", ondelete='cascade', copy=False)
	vcpu = fields.Float(string="vCPU")
	vram = fields.Float(string="vRAM")
	disk_id= fields.Many2one('od.disk.master', string="Disk", ondelete='restrict')
	disk_qty= fields.Float(string="Disk Quantity")
	ha = fields.Selection([('Yes','Yes'),('No','No')], string="HA", default='No')
	os_id = fields.Many2one('od.os.master', string="OS", ondelete='restrict')
	license_1 =fields.Many2one('od.license', string='License 1', ondelete='cascade')
	license_2 =fields.Many2one('od.license', string='License 2', ondelete='cascade')
	license_3 =fields.Many2one('od.license', string='License 3', ondelete='cascade')
	license_4 =fields.Many2one('od.license', string='License 4', ondelete='cascade')
	license_5 =fields.Many2one('od.license', string='License 5', ondelete='cascade')
	license_6 =fields.Many2one('od.license', string='License 6', ondelete='cascade')

class OrchidMHS(models.Model):
	_name = "od.provision.mhs"
	_description = "MHS"

	provision_id= fields.Many2one('od.asp.provision.form', string="Provision", ondelete='cascade', copy=False)
	total_no_of_u_space= fields.Char(string="Total No of  U Space")
	total_no_of_devices= fields.Char(string="Total No of Devices")
	total_power= fields.Char(string="Total Power")
	no_of_servers= fields.Char(string="No of Servers")
	no_of_storage= fields.Char(string="No of Storage")
	no_of_firewalls= fields.Char(string="No of Firewalls")
	dedicated_access_port= fields.Selection([('Yes','Yes'),('No','No')], string="Dedicated Access Port")
	dedicated_backup_console= fields.Selection([('Yes','Yes'),('No','No')], string="Dedicated Backup  Console")
	backup_storage= fields.Char(string="Backup Storage")
	total_public_ip= fields.Char(string="Total Public IPs")
	license_1 =fields.Many2one('od.license', string='License 1', ondelete='cascade')
	license_2 =fields.Many2one('od.license', string='License 2', ondelete='cascade')


class OrchidCLS(models.Model):
	_name = "od.provision.cls"
	_description = "CLS"

	provision_id= fields.Many2one('od.asp.provision.form', string="Provision", ondelete='cascade', copy=False)
	total_no_of_u_space= fields.Char(string="Total No of  U Space")
	total_no_of_devices= fields.Char(string="Total No of Devices")
	total_power= fields.Char(string="Total Power")
	no_of_servers= fields.Char(string="No of Servers")
	no_of_storage= fields.Char(string="No of Storage")
	no_of_firewalls= fields.Char(string="No of Firewalls")
	dedicated_access_port= fields.Selection([('Yes','Yes'),('No','No')], string="Dedicated Access Port")
	total_public_ip= fields.Char(string="Total Public IPs")





			

		



		
	