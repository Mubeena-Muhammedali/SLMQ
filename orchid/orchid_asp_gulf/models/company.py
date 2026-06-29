# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Nicolas Bessi (Camptocamp)

from odoo import fields,models,api

class HeaderImage(models.Model):
    """Logo allows you to define multiple logo per company"""
    _name = "ir.header_img"
   
    company_id  = fields.Many2one('res.company', 'Company')
    img  =fields.Binary('Image', attachment=True)
    name =fields.Char('Name', required =True, help="Name of Image")
    type =fields.Char('Type', required =True, help="Image type(png,gif,jpeg)")
   


class res_company(models.Model):
    """Override company to add Header object link a company can have many header and logos"""

    _inherit = "res.company"
    header_image =fields.Many2many('ir.header_img',
                                    'company_img_rel',
                                                    'company_id',
                                                    'img_id',
                                                    'Available Images',
                                                )
    
