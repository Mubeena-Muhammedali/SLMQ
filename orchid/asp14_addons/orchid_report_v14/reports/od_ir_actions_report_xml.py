# -*- coding: utf-8 -*-
from odoo import fields,models,api
from odoo import tools

class ir_actions_report_xml(models.Model):
    _inherit = 'ir.actions.report.xml'
    
    avilable_in_ddl =fields.boolean(string='Available In DDL',help="Template Names Can be used,\naccount.report_partnerledger_od1,\naccount.report_partnerledger_od2\n,account.report_partnerledger_od3\n,account.report_partnerledger_od4")
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
