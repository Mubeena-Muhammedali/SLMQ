# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

from odoo.tools import float_repr
import xlrd
import base64

class OrchidPricelistPriceChange(models.Model):
    _name = "od.pricelist.price.change"
    _inherit = ['mail.thread']
    _description="Pricelist Price Change"

    name = fields.Char(string="Name", tracking=True)
    partner_id = fields.Many2one('res.partner', string="Customer", tracking=True)
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist", tracking=True)
    vbr_id = fields.Many2one('orchid.volume.rebate', string="Volume Rebate", tracking=True)
    price_type = fields.Selection([('pricelist','Pricelist'),('vbr','Volume Rebate'),('create_vbr','Create Volume Rebate'),('create_pricelist','Create Pricelist')], string="Option", tracking=True)
    line_ids = fields.One2many('od.pricelist.price.change.line','price_id',string="Lines", copy=False)
    user_id = fields.Many2one('res.users', string="Initiated User", tracking=True)
    manger_id = fields.Many2one('res.users',related="user_id.od_reporting_manger_id", string="Reporting Manager", tracking=True)
    date = fields.Date(string="Date", tracking=True, default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)
    state = fields.Selection([('draft','Draft'),('submit','Submitted'),('pre_approve','Pre-Approved'),('approve','Approved'),('gm_approve','Approved'),('refuse','Refused')],default="draft")
    refuse_reason = fields.Text(string="Refuse Reason")
    data_file = fields.Binary(string='Data', default=False)

    def button_upload(self):
        value_data = self.read_xl_file()
        print("value",value_data)
        if not value_data:
            raise Warning(_('Nothing to Upload.'))
        for value in value_data:
            pricelist_applied_on = value[0]
            categ_code = value[1]
            product_code = value[2]
            # product_tmpl_code = value[3]
            orchid_group_code = value[3]
            orchid_type_code = value[4]
            orchid_brand_code = value[5]
            fixed_price=value[6]
            percent_price=value[7]
            price_type='pricelist'
            if fixed_price:
                compute_price='fixed'
            if percent_price:
                compute_price='percentage'

            orchid_brand_id =  False
            orchid_type_id =  False
            orchid_group_id =  False

            product_tmpl_id = False
            product_id = False
            categ_id = False

            if pricelist_applied_on=='2_product_category':
                if not categ_code:
                    raise UserError (_("Applied on is Category but no category code given !!!"))
                categ_id = self.env['product.category'].search([('od_code','=',str(categ_code))])
                if not categ_id:
                    raise UserError(_("No category with code '%s' is not found!!")%(categ_code))
            if pricelist_applied_on=='1_product': 
                if not product_code:
                    raise UserError (_("Applied on is Product but no  Product code given !!!"))
                product_tmpl_id = self.env['product.template'].search([('default_code','=',str(product_code))])
                if not product_tmpl_id:
                    raise UserError(_("No Product with code '%s' is not found!!")%(product_code))
            if pricelist_applied_on=='0_product_variant': 
                if not product_code:
                    raise UserError (_("Applied on is Product Variant but no Product code given !!!"))
                product_id = self.env['product.product'].search([('default_code','=',str(product_code))])
                if not product_id:
                    raise UserError(_("No Product with code '%s' is not found!!")%(product_code))
            if pricelist_applied_on=='2_rproduct_brand':
                if not orchid_brand_code:
                    raise UserError (_("Applied on is Brand but no Brand given !!!"))
                orchid_brand_id = self.env['orchid.product.brand'].search([('code','=',str(orchid_brand_code))])
                if not orchid_brand_id:
                    raise UserError(_("No Product Brand with code '%s' is not found!!")%(orchid_brand_code))
            if pricelist_applied_on=='2_qproduct_ftype':
                if not orchid_type_code:
                    raise UserError (_("Applied on is Product Type but no Product Type given !!!"))
                orchid_type_id = self.env['orchid.product.type'].search([('code','=',str(orchid_type_code))])
                if not orchid_type_id:
                    raise UserError(_("No Product Type with code '%s' is not found!!")%(orchid_type_code))
            if pricelist_applied_on=='2_qproduct_group':
                if not orchid_group_code:
                    raise UserError (_("Applied on is Group but no Group given !!!"))
                orchid_group_id = self.env['orchid.product.group'].search([('code','=',str(orchid_group_code))])
                if not orchid_group_id:
                    raise UserError(_("No Product Group with code '%s' is not found!!")%(orchid_group_code))

            vals={
            'price_id':self.id,
            'compute_price':compute_price,
            'fixed_price':fixed_price,
            'percent_price':percent_price,
            'pricelist_applied_on':pricelist_applied_on,
            'orchid_brand_id':orchid_brand_id and orchid_brand_id.id,
            'orchid_type_id':orchid_type_id and orchid_type_id.id,
            'orchid_group_id':orchid_group_id and orchid_group_id.id,
            'product_tmpl_id':product_tmpl_id and product_tmpl_id.id,
            'product_id':product_id and product_id.id,
            'categ_id':categ_id and categ_id.id,
            }
            # print("valllllllllllll",vals)
            line_id = self.env['od.pricelist.price.change.line'].create(vals)
            line_id._get_pricelist_item_name_price()





    def read_xl_file(self):
        book = xlrd.open_workbook(file_contents=base64.b64decode(self.data_file))
        sheet = book.sheet_by_index(0)
        values_sheet = []
        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            values = []
            for colx, cell in enumerate(row, 1):
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        str(cell.value) if is_float else str(int(cell.value)))
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(
                        cell.value, book.datemode))
                    values.append(
                        dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT
                                    ) if is_datetime else dt.
                        strftime(DEFAULT_SERVER_DATE_FORMAT))
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append(u'True' if cell.value else u'False')
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s"
                          ) % {
                              'row':
                              rowx,
                              'col':
                              colx,
                              'cell_value':
                              xlrd.error_text_from_code.get(
                                  cell.value,
                                  _("unknown error code %s") % cell.value)
                          })
                else:
                    values.append(cell.value)
            values_sheet.append(values)
        del values_sheet[0]
        return values_sheet

    def unlink(self):
        if self.state!='draft':
            raise UserError(_("Only draft records can be deleted!!!"))
        return super(OrchidPricelistPriceChange, self).unlink()
        
    def get_form_url(self):
        action = self.env.ref('orchid_somfy_ksa_v16.action_od_pricelist_price_change')
        form_id = self.id
        url_link = "%s/?db=%s#id=%s&action=%s&view_type=form" % (
            self.env['ir.config_parameter'].get_param('web.base.url'),
             self.env.cr.dbname,
             form_id,
             action.id  or False,
             )
        return url_link

    def send_email_notification(self, recipient_email, recipient_name,cc_email, content):
        ## Get email template
        template_id = self.env.ref('orchid_somfy_ksa_v16.pricelist_price_change_notification_template')
        generate=self.env['mail.template'].browse(template_id.id)
        ctx  = self.env.context.copy()
        recipients = []
        # recipients.append('jack.moussa@somfy.com')
        if isinstance(recipient_email, list):
            recipients.extend(recipient_email)
        else:
            recipients.append(recipient_email)
        recipients = list(filter(None,recipients))
        cc_recipients=[]
        for cc in cc_email:
            cc_recipients.append(cc)
        cc_recipients = list(filter(None,cc_recipients))
        today_date = fields.date.today().strftime('%d/%m/%Y')
        price_type ="Volume Rebate" if self.price_type=='vbr' else "Pricelist"
        ctx['name'] =price_type+' price change Notification- ' + today_date
        ctx['email_to'] = ','.join(recipients)
        ctx['email_cc'] = ','.join(cc_recipients)
        ctx['subject'] = price_type+' price change Notification'   
        ctx['company_id'] = self.env.company
        # ctx['content'] = "An Account opening form for "+self.partner+" has been submitted"
        ctx['content'] = content
        # ctx['recipient_name'] = 'Jack Moussa'
        ctx['recipient_name'] = recipient_name
        print("hhhhhhhhh",ctx)
        generate.sudo().with_context(ctx).send_mail(self.id,force_send=True)
        return True

    @api.onchange('price_type','date')
    def onchange_name(self):
        for rec in self:
            if rec.price_type and rec.date:
                price_type = dict(rec._fields['price_type'].selection).get(rec.price_type)
                name=str(price_type)+"-"+str(rec.date)
                rec.name=name

    @api.onchange('partner_id','price_type')
    def onchange_partner(self):
        for record in self:
            if record.line_ids:
                record.line_ids.unlink()
            record.pricelist_id = False
            record.vbr_id = False
            if record.partner_id:
                if record.price_type == 'create_pricelist':
                    pricelist_id = record.partner_id.property_product_pricelist and record.partner_id.property_product_pricelist.id
                    if pricelist_id:
                        raise UserError(_("pricelist already created for this customer !!"))
                    record.vbr_id = False
                elif record.price_type == 'pricelist':
                    pricelist_id = record.partner_id.property_product_pricelist and record.partner_id.property_product_pricelist.id
                    if not pricelist_id:
                        raise UserError(_("No pricelist set for this customer !!"))
                    record.pricelist_id = pricelist_id
                    record.vbr_id = False
                elif record.price_type == 'create_vbr':
                    rebate_id = record.partner_id.od_rebate_id and record.partner_id.od_rebate_id.id
                    if rebate_id:
                        raise UserError(_("Volume Rebate already created for this customer !!"))
                    record.pricelist_id = False
                elif record.price_type == 'vbr':
                    rebate_id = record.partner_id.od_rebate_id and record.partner_id.od_rebate_id.id
                    if not rebate_id:
                        raise UserError(_("No Volume Rebate set for this customer !!"))
                    record.pricelist_id = False
                    record.vbr_id = rebate_id

    def button_get_lines(self):
        for record in self:
            if record.line_ids:
                record.line_ids.unlink()
            if record.price_type == 'pricelist' and record.pricelist_id:
                # print("oooooofffffffffff",lines)
                lines = []
                for pl in self.env['product.pricelist.item'].search([('pricelist_id','=',record.pricelist_id.id)]):
                    vals ={
                    'pricelist_line_id':pl.id,
                    'name':pl.name,
                    'pricelist_applied_on':pl.applied_on,
                    'old_price':pl.price,
                    'compute_price':pl.compute_price,
                    'fixed_price':pl.fixed_price,
                    'percent_price':pl.percent_price,
                    'orchid_brand_id':pl.orchid_brand_id and pl.orchid_brand_id.id,
                    'orchid_type_id':pl.orchid_type_id and pl.orchid_type_id.id,
                    'orchid_group_id':pl.orchid_group_id and pl.orchid_group_id.id,
                    'product_id':pl.product_id and pl.product_id.id,
                    'categ_id':pl.categ_id and pl.categ_id.id,
                    'product_tmpl_id':pl.product_tmpl_id and pl.product_tmpl_id.id,
                    'od_product_segment_id':pl.od_product_segment_id and pl.od_product_segment_id.id,
                    'price_type':record.price_type,
                    }
                    print("valssssss",vals)
                    lines.append((0,0,vals))
                record.line_ids = lines
                print("lllllllllllllllllkkkkk")
            elif record.price_type == 'vbr' and record.vbr_id:
                    # print("kkkkjjjjjj",lines)
                    lines = []
                    for pl in self.env['orchid.volume.rebate.line'].search([('rebate_id','=',record.vbr_id.id)]):
                        name ,price = self.get_vbr_old_name_price(pl)
                        vals ={
                        'vbr_line_id':pl.id,
                        'name':name,
                        'vbr_applied_on':pl.applied_on,
                        'old_price':price,
                        # 'compute_price':pl.compute_price,
                        # 'fixed_price':pl.fixed_price,
                        'rebate_percent':pl.rebate_volume_per,
                        'product_tmpl_id':pl.product_id and pl.product_id.id,
                        'categ_id':pl.categ_id and pl.categ_id.id,
                        'price_type':record.price_type,
                        }
                        lines.append((0,0,vals))
                    record.line_ids = lines

    def get_vbr_old_name_price(self,pl):
        for item in pl:
            name =  False
            price = False
            if item.categ_id and item.applied_on == '2_product_category':
                name = _("Category: %s") % (item.categ_id.display_name)
            elif item.product_id and item.applied_on == '1_product':
                name = _("Product: %s") % (item.product_id.display_name)
            else:
                name = _("All Products")
            price = _("%s %%", item.rebate_volume_per)
            return name,price

    def button_submit(self):
        # mail will be sent to line manager(reporting manager)
        if not self.line_ids:
            raise UserError(_("No lines added!!!"))
        if self.price_type == 'create_pricelist':
            pricelist_id = self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id
            if pricelist_id:
                raise UserError(_("pricelist already created for this customer !!"))
        elif self.price_type == 'create_vbr':
            rebate_id = self.partner_id.od_rebate_id and self.partner_id.od_rebate_id.id
            if rebate_id:
                raise UserError(_("Volume Rebate already created for this customer !!"))

        for line in self.line_ids:

            if self.price_type in ('pricelist','create_pricelist'):
                if (line.pricelist_line_id and not line.price):
                    line.unlink()
            if self.price_type in ('vbr','create_vbr'):
                if (line.vbr_line_id and not line.price):
                    line.unlink()
        
        if self.user_id.has_group('orchid_somfy_ksa_v16.od_group_account_opening_form_approve_user'):
            # in case of samer, jack
            bu_manager_group_id = self.env.ref('orchid_somfy_ksa_v16.od_group_bu_manager_approve_user')
            bu_manager_id = bu_manager_group_id.users
            if not bu_manager_id:
                raise UserError(_("Please set Country Manager!!"))
            bu_manager_id = bu_manager_id[0]
            recipient_email = bu_manager_id.login
            recipient_name = bu_manager_id.name
        else:
            # samer
            country_manager_group_id = self.env.ref('orchid_somfy_ksa_v16.od_group_account_opening_form_approve_user')
            country_manager_id = country_manager_group_id.users
            if not country_manager_id:
                raise UserError(_("Please set Country Manager!!"))
            country_manager_id = country_manager_id[0]
            recipient_email = country_manager_id.login
            recipient_name = country_manager_id.name
        price_type ="Volume Rebate" if self.price_type in ('vbr','create_vbr') else "Pricelist"
        content = ""
        if self.price_type in ('vbr','pricelist'):
            content = price_type+" price change "+str(self.name)+" has been submitted by "+self.user_id.name
        if self.price_type in ('create_pricelist','create_vbr'):
            content = "Request to create a new "+price_type+" for customer "+ str(self.partner_id.name)+ "has been submitted by "+self.user_id.name
        
        cc_email=[]
        self.send_email_notification(recipient_email, recipient_name,cc_email, content)
        self.state = 'submit'
    
    def button_pre_approve(self):
        if self.user_id.has_group('orchid_somfy_ksa_v16.od_group_account_opening_form_approve_user'):
            self.button_approve()
        else:
            recipient_email = []
            for user_id in self.env.ref('orchid_somfy_ksa_v16.od_group_account_opening_form_approve_user').users:
                if not user_id.partner_id.email:
                    raise UserError(_("No email defined in partner master for the user '%s' ")%(user_id.name))
                recipient_email.append(user_id.partner_id.email)

            recipient_name = "All"
            
            price_type ="Volume Rebate" if self.price_type in ('vbr','create_vbr') else "Pricelist"
            content = ""
            if self.price_type in ('vbr','pricelist'):
                content = price_type+" price change "+str(self.name)+" has been verified and pre-approved by "+self.manger_id.name
            if self.price_type in ('create_pricelist','create_vbr'):
                content = "Request to create a new "+price_type+" for customer "+ str(self.partner_id.name)+" has been verified and pre-approved by "+self.manger_id.name

            cc_email=[]
            self.send_email_notification(recipient_email, recipient_name,cc_email, content)
            self.state='pre_approve'


    def button_refuse(self, reason):
        if self.env.user.id==self.user_id.id:
            raise UserError(_("You are not allowed to perform this operation !!!"))
        self.refuse_reason = reason
        recipient_email = self.user_id.login
        recipient_name = self.user_id.name
        price_type ="Volume Rebate" if self.price_type in ('vbr','create_vbr') else "Pricelist"
        content = ""
        if self.price_type in ('vbr','pricelist'):
            content = price_type+" price change "+str(self.name)+" has been refused. \nNote: "+str(reason)
        if self.price_type in ('create_pricelist','create_vbr'):
            content = "Request to create a new "+price_type+" for customer "+ str(self.partner_id.name)+" has been refused. \nNote: "+str(reason)

        cc_email=[]
        self.send_email_notification(recipient_email, recipient_name,cc_email, content)
        self.state='refuse'

    def button_reset_to_draft(self):
        self.state='draft'

    def button_approve(self):
        # recipient_email = 'jack.moussa@somfy.com'
        # recipient_name = 'Jack Moussa'

        # recipient_user_id = self.env['res.users'].search([('od_final_code','=','final')])
        # if not recipient_user_id:
        #     raise UserError(_("No user found with code 'final' "))
        # if not recipient_user_id.partner_id.email:
        #     raise UserError(_("No email defined in partner master for the user '%s' ")%(recipient_user_id.name))
        # recipient_email = recipient_user_id.partner_id.email
        recipient_email = []
        for user_id in self.env.ref('orchid_somfy_ksa_v16.od_group_bu_manager_approve_user').users:
            if not user_id.partner_id.email:
                raise UserError(_("No email defined in partner master for the user '%s' ")%(user_id.name))
            recipient_email.append(user_id.partner_id.email)
        recipient_name = "All"
        
        # price_type ="Volume Rebate" if self.price_type=='vbr' else "Pricelist"
        price_type ="Volume Rebate" if self.price_type in ('vbr','create_vbr') else "Pricelist"
        content = ""
        if self.price_type in ('vbr','pricelist'):
            content = price_type+" price change "+str(self.name)+" has been verified and submitted for approval by "+self.env.user.name
        if self.price_type in ('create_pricelist','create_vbr'):
            content = "Request to create a new "+price_type+" for customer "+ str(self.partner_id.name)+" has been verified and submitted for approval by "+self.env.user.name

        cc_email=[]
        self.send_email_notification(recipient_email, recipient_name,cc_email, content)
        self.state='approve'
    
    def button_gm_approve(self):
        if self.env.user.id==self.user_id.id:
            raise UserError(_("You are not allowed to perform this operation !!!"))
        for line in self.line_ids:
            if line.price_type == 'pricelist':
                if line.pricelist_line_id and line.price:
                    if line.fixed_price:
                        line.pricelist_line_id.fixed_price = line.fixed_price
                    elif line.percent_price:
                        line.pricelist_line_id.percent_price = line.percent_price

                elif line.price:
                    vals = {
                    'pricelist_id':line.price_id.pricelist_id.id,
                    'applied_on':line.pricelist_applied_on,
                    'product_id':line.product_id and line.product_id.id,
                    'product_tmpl_id':line.product_tmpl_id and line.product_tmpl_id.id,
                    'categ_id':line.categ_id and line.categ_id.id,
                    'orchid_brand_id':line.orchid_brand_id and line.orchid_brand_id.id,
                    'orchid_type_id':line.orchid_type_id and line.orchid_type_id.id,
                    'orchid_group_id':line.orchid_group_id and line.orchid_group_id.id,
                    'od_product_segment_id':line.od_product_segment_id and line.od_product_segment_id.id,
                    'compute_price':line.compute_price,
                    'percent_price':line.percent_price,
                    'fixed_price':line.fixed_price
                    }
                    line.pricelist_line_id = self.env['product.pricelist.item'].create(vals).id

            

            if line.price_type == 'vbr':
                if line.vbr_line_id and line.price:
                    line.vbr_line_id.rebate_volume_per = line.rebate_percent
                elif line.price:
                    vals = {
                    'rebate_id':line.price_id.vbr_id.id,
                    'applied_on':line.vbr_applied_on,
                    'product_id':line.product_tmpl_id and line.product_tmpl_id.id,
                    'categ_id':line.categ_id and line.categ_id.id,
                    'rebate_volume_per':line.rebate_percent
                    }
                    line.vbr_line_id = self.env['orchid.volume.rebate.line'].create(vals).id

        if self.price_type == 'create_pricelist':
                
            pricelist_id = self.env['product.pricelist'].create({
                'name':self.partner_id.name,
                'partner_id':self.partner_id.id,
                'currency_id':1,
                })
            self.pricelist_id = pricelist_id.id
            self.partner_id.property_product_pricelist = pricelist_id.id
            for line in self.line_ids:
                line_vals = {
                'pricelist_id':pricelist_id.id,
                'applied_on':line.pricelist_applied_on,
                'product_id':line.product_id and line.product_id.id,
                'product_tmpl_id':line.product_tmpl_id and line.product_tmpl_id.id,
                'categ_id':line.categ_id and line.categ_id.id,
                'orchid_brand_id':line.orchid_brand_id and line.orchid_brand_id.id,
                'orchid_type_id':line.orchid_type_id and line.orchid_type_id.id,
                'orchid_group_id':line.orchid_group_id and line.orchid_group_id.id,
                'compute_price':line.compute_price,
                'percent_price':line.percent_price,
                'fixed_price':line.fixed_price
                }
                line.pricelist_line_id = self.env['product.pricelist.item'].create(line_vals).id

        if self.price_type == 'create_vbr':
            
            vbr_id = self.env['orchid.volume.rebate'].create({
                'name':self.partner_id.name+"(VBR)",
                'partner_id':self.partner_id.id,
                })
            self.vbr_id = vbr_id.id
            self.partner_id.od_rebate_id = vbr_id.id
            for line in self.line_ids:
                line_vals = {
                    'rebate_id':vbr_id.id,
                    'applied_on':line.vbr_applied_on,
                    'product_id':line.product_tmpl_id and line.product_tmpl_id.id,
                    'categ_id':line.categ_id and line.categ_id.id,
                    'rebate_volume_per':line.rebate_percent
                    }
                line.vbr_line_id = self.env['orchid.volume.rebate.line'].create(line_vals).id

        recipient_email = self.user_id.login
        recipient_name = self.user_id.name
        cc_email = [self.user_id.od_reporting_manger_id.login,'zia.urrahman@somfy.com']
        # price_type ="Volume Rebate" if self.price_type=='vbr' else "Pricelist"
        price_type ="Volume Rebate" if self.price_type in ('vbr','create_vbr') else "Pricelist"
        content = ""
        if self.price_type in ('vbr','pricelist'):
            content = price_type+" price change "+str(self.name)+" has been approved"
        if self.price_type in ('create_pricelist','create_vbr'):
            content = "Request to create a new "+price_type+" for customer "+ str(self.partner_id.name)+" has been approved"

        self.send_email_notification(recipient_email, recipient_name,cc_email, content)

        self.state = 'gm_approve'

class OrchidPricelistPriceChangeLine(models.Model):
    _name = "od.pricelist.price.change.line"
    _inherit = ['mail.thread']
    _description="Pricelist Price Change Line"

    price_id =  fields.Many2one('od.pricelist.price.change', string='Price change', ondelete='cascade')
    name = fields.Char(string="Applied on")
    old_price = fields.Char(string="Old Price")
    price = fields.Char(string="New Price")
    compute_price = fields.Selection([('percentage','Percentage(discount)'),('fixed','Fixed Price')], string="Compute Price")
    fixed_price = fields.Float(string="New Fixed Price")
    percent_price = fields.Float(string="New Percentage")
    rebate_percent = fields.Float(string="New Rebate Voulume%")
    pricelist_applied_on = fields.Selection([
        ('3_global', 'All Products'),
        ('2_product_category', 'Product Category'),
        ('1_product_segment', "Product Segment"),
        ('1_product', 'Product'),
        ('0_product_variant', 'Product Variant'),
        ('2_rproduct_brand','Product Brand'),
        ('2_qproduct_ftype','Product Type'),
        ('2_qproduct_group','Product Group')], "Apply On",
        default='3_global',
        help='Pricelist Item applicable on selected option')
    vbr_applied_on = fields.Selection([
    ('2_product_category', 'Product Line'),
    ('1_product', 'Product'),
    ], "Apply On", help='Rebate Item applicable on selected option')


    orchid_brand_id =  fields.Many2one('orchid.product.brand', string='Brand')
    orchid_type_id =  fields.Many2one('orchid.product.type', string='Type')
    orchid_group_id =  fields.Many2one('orchid.product.group', string='Group')

    product_tmpl_id = fields.Many2one('product.template', 'Product',check_company=True,help="Specify a product if this rule only applies to one product. Keep empty otherwise.")
    product_id = fields.Many2one('product.product', 'Product Variant',check_company=True,help="Specify a product if this rule only applies to one product. Keep empty otherwise.")
    categ_id = fields.Many2one('product.category', 'Product Line',help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")

    company_id = fields.Many2one('res.company', 'Company',readonly=True, related='price_id.company_id', store=True)
    pricelist_line_id = fields.Many2one('product.pricelist.item', string="Pricelist Line")
    vbr_line_id = fields.Many2one('orchid.volume.rebate.line', string="Volume Rebate")
    price_type = fields.Selection([('pricelist','Pricelist'),('vbr','Volume Rebate')],related='price_id.price_type', string="Option", tracking=True)
    od_product_segment_id = fields.Many2one('od.product.segment', string="Product Segment")



    @api.onchange('rebate_percent','categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'orchid_brand_id', 'orchid_type_id', 'orchid_group_id','od_product_segment_id')
    def _get_pricelist_item_name_price(self):
        print("gerddddddddddddd")

        for item in self:
            if item.categ_id and ((item.pricelist_applied_on == '2_product_category') or (item.vbr_applied_on == '2_product_category')):
                item.name = _("Category: %s") % (item.categ_id.display_name)
            elif item.product_tmpl_id and ((item.pricelist_applied_on == '1_product') or (item.vbr_applied_on == '1_product')):
                item.name = _("Product: %s") % (item.product_tmpl_id.display_name)
            elif item.product_id and item.pricelist_applied_on == '0_product_variant':
                item.name = _("Variant: %s") % (item.product_id.with_context(display_default_code=False).display_name)
            elif item.od_product_segment_id and item.pricelist_applied_on == '1_product_segment':
                item.name = _("Product Segment: %s") % (item.od_product_segment_id.name)
            elif item.orchid_brand_id:
                item.name = _("Product Brand: %s") % (item.orchid_brand_id.display_name)
            elif item.orchid_type_id:
                item.name = _("Product Type: %s") % (item.orchid_type_id.display_name)
            elif item.orchid_group_id:
                item.name = _("Product Group: %s") % (item.orchid_group_id.display_name)
            else:
                item.name = _("All Products")
            if item.price_type in ('pricelist','create_pricelist'):
                if item.compute_price == 'fixed':
                    decimal_places = self.env['decimal.precision'].precision_get('Product Price')
                    # if item.currency_id.position == 'after':
                    #     item.price = "%s %s" % (
                    #         float_repr(
                    #             item.fixed_price,
                    #             decimal_places,
                    #         ),
                    #         item.currency_id.symbol,
                    #     )
                    item.price = "%s" % (
                        float_repr(
                            item.fixed_price,
                            decimal_places,
                        ),
                    )
                elif item.compute_price == 'percentage':
                    item.price = _("%s %% discount", item.percent_price)
                    print("jjjjjjjjjjjjjjjjjjjj",item.price)
                # else:
                #     item.price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount, price=item.price_surcharge)
            elif item.price_type in ('vbr','create_vbr'):
                item.price = _("%s %%", item.rebate_percent)
            else:
                print("vggggggg")
                item.price = False
