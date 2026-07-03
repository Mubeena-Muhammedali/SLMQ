from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import base64


class HrPayslip(models.Model):
	_inherit = 'hr.payslip'

	od_payslip_sent = fields.Boolean(string="Email Sent", copy=False, default=False)

	def _prepare_line_values(self, line, account_id, date, debit, credit):
		res = super(HrPayslip, self)._prepare_line_values(line, account_id, date, debit, credit)
		if self.employee_id.x_studio_cost_center:
			res.update({'orchid_cc_id':self.employee_id.x_studio_cost_center.id})
		return res

	def od_button_send_payslip(self):
		user = self.env.user
		template_id = self.env.ref('orchid_somfy_ksa_v16.mail_template_payslip_done')
		generate=self.env['mail.template'].browse(template_id.id)
		ctx  = self.env.context.copy()
		print("self.sudo().employee_id",self.sudo().employee_id,self.id)
		recipients = []
		recipients.append(self.sudo().employee_id.work_email)
		recipients = list(filter(None,recipients))
		ctx['email_to'] = ','.join(recipients)
		ctx['email_cc'] = ''
		ctx['name'] = self.name
		ctx['subject'] = self.name+" - "+self.number
		date_from = datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%B %Y')
		ctx['content'] = 'Attached is your payslip for the period '+str(date_from)
		attachment_name=self.name
		# Generate the report in PDF
		pdf_content, content_type = self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf('orchid_payroll_v16.action_report_od_payslip', res_ids=self.id)
		print("reee",pdf_content)
		# Create the attachment
		attachment = self.env['ir.attachment'].create({
			'name': f"{self.name}_payslip.pdf",
			'type': 'binary',
			'datas': base64.b64encode(pdf_content),
			'res_model': 'hr.payslip',
			'res_id': self.id,
			'mimetype': 'application/pdf',
		})
		
		generate.attachment_ids = [(6,0,[attachment.id])]
		generate.sudo().with_context(ctx).send_mail(self.id,force_send=True)
		self.od_payslip_sent = True	

	def action_payslip_done(self):
		res = super(HrPayslip, self).action_payslip_done()
		for slip in self:
			slip.od_button_send_payslip()
		return res
