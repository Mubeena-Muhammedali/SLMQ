# -*- coding: utf-8 -*-
from odoo import fields, models,_
import xlsxwriter
from io import BytesIO
import base64
from datetime import datetime
from odoo.exceptions import UserError


class OrchidAssetRegisterWiz(models.TransientModel):
    _name = 'od.asset.register.wiz'
    _description = 'Asset Register Wizard'

    date_from = fields.Date(string="Date from")
    date_to = fields.Date(string="Date to")
    category_ids = fields.Many2many('account.asset.category', string="Categories")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    excel_file = fields.Binary(string='Dowload Report Excel',readonly="1")
    file_name = fields.Char(string='Excel File',readonly="1")
    report_type = fields.Selection([('All','All'),('Running','Running')], string="Mode", default="Running")

    def get_asset_data(self):
        domain=[('company_id','=',self.company_id.id)]
        if self.report_type=='All':
            t_domain=('state','in',('open','close'))
            domain.append(t_domain)
        if self.report_type=='Running':
            t_domain=('state','=','open')
            domain.append(t_domain)
        if self.date_to:
            t_domain=('od_purchase_date','<=',self.date_to)
            domain.append(t_domain)
        if self.category_ids:
            t_domain=('category_id','in',self.category_ids.ids)
            domain.append(t_domain)
        asset_ids = self.env['account.asset.asset'].search(domain)
        category_ids = asset_ids.category_id.ids
        data_dict={}
        print("dommmmmmmmmmmmm",domain)
        for categ in category_ids:
            name_qry='''SELECT name FROM account_asset_category WHERE id=%s'''%(categ)
            self._cr.execute(name_qry)
            categ_name =  self._cr.fetchone()
            categ_name = categ_name[0] if categ_name else ''
            data_dict[categ]={'categ_name':categ_name,
                            'assets':[],
                            'total_original_value':0,
                            'total_opening_depr_amt':0,
                            'total_qty':0,
                            'total_opening_asset_amt':0,
                            'total_asset_addition':0,
                            'total_asset_deletion':0,
                            'total_purchase_value':0,
                            'total_net_asset':0,
                            'total_period_depr_amt':0,
                            'total_closing_value':0,
                            }

        if not asset_ids:
            raise UserError(_("No data !!!"))
        fdate = datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%d/%m/%Y')
        tdate = datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%d/%m/%Y')
        if asset_ids:
            for asset_id in asset_ids:
                categ=asset_id.category_id.id
                name = asset_id.name
                ref=asset_id.code
                asset_life=asset_id.method_number
                po_date=datetime.strptime(str(asset_id.od_purchase_date), '%Y-%m-%d').strftime('%d/%m/%Y')
                original_value=asset_id.value
                opening_depr_amt=0
                opening_depr_qry='''SELECT COALESCE(SUM(amount),0) 
                                    FROM account_asset_depreciation_line 
                                    WHERE asset_id=%s AND move_check is true AND depreciation_date<'%s' '''%(asset_id.id,self.date_from)

                self._cr.execute(opening_depr_qry)
                opening_depr =  self._cr.fetchone()
                opening_depr_amt = opening_depr[0] if opening_depr else 0
                opening_depr_amt+=asset_id.salvage_value
                qty=0#????dbt
                opening_asset_amt=original_value-opening_depr_amt#???dbt

                asset_addition=0
                print("hvvvvvvv",asset_id.od_purchase_date >= self.date_from and asset_id.od_purchase_date <= self.date_to)
                if not (asset_id.od_purchase_date >= self.date_from and asset_id.od_purchase_date <= self.date_to):
                    asset_addition =0.00
                    print("if yessss",asset_addition)
                else:
                    asset_addition =asset_id.od_cost
                    opening_depr_amt=0
                    opening_asset_amt=0
                    original_value=0
                    print("if nooooooooo",asset_addition)
                asset_deletion=0
                # purchase_value=(opening_asset_amt+asset_addition)-asset_deletion
                purchase_value=original_value+asset_addition
                net_asset=(opening_asset_amt+asset_addition)-asset_deletion
                period_depr_amt=0
                period_depr_qry='''SELECT COALESCE(SUM(amount),0) 
                                    FROM account_asset_depreciation_line 
                                    WHERE asset_id=%s AND move_check is true 
                                    AND depreciation_date>='%s' AND depreciation_date<='%s' '''%(asset_id.id,self.date_from,self.date_to)

                self._cr.execute(period_depr_qry)
                period_depr =  self._cr.fetchone()
                # print("hhhhhhhhhhhh",period_depr_qry)
                period_depr_amt = period_depr[0] if period_depr else 0
                # print("vvvvvbn",period_depr,period_depr_amt)
                closing_value = net_asset-period_depr_amt
                asset_vals={
                'name':name,
                'ref':ref,
                'asset_life':asset_life,
                'po_date':po_date,
                'original_value':original_value,
                'opening_depr_amt':opening_depr_amt,
                'qty':qty,
                'opening_asset_amt':opening_asset_amt,
                'asset_addition':asset_addition,
                'asset_deletion':asset_deletion,
                'purchase_value':purchase_value,
                'net_asset':net_asset,
                'period_depr_amt':period_depr_amt,
                'closing_value':closing_value,
                }
                data_dict[categ]['assets'].append(asset_vals)
                data_dict[categ]['total_original_value']+=original_value
                data_dict[categ]['total_opening_depr_amt']+=opening_depr_amt
                data_dict[categ]['total_qty']+=qty
                data_dict[categ]['total_opening_asset_amt']+=opening_asset_amt
                data_dict[categ]['total_asset_addition']+=asset_addition
                data_dict[categ]['total_asset_deletion']+=asset_deletion
                data_dict[categ]['total_purchase_value']+=purchase_value
                data_dict[categ]['total_net_asset']+=net_asset
                data_dict[categ]['total_period_depr_amt']+=period_depr_amt
                data_dict[categ]['total_closing_value']+=closing_value

        return data_dict,category_ids







    def generate_excel(self):
        # self.ensure_one()
        print("jjdddddd")
        data_dict,category_ids = self.get_asset_data()
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet_name = 'Asset Register'
        sheet= workbook.add_worksheet(sheet_name)
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'fg_color': '#D7E4BC',
            'border': 0,
            'font_size':14}) 
        header_style = workbook.add_format({
            'bold': True,
            'align': 'center',
            'fg_color':'#b2b2b2',
            'border':0})
        sub_header_style = workbook.add_format({
            'bold': True,
            'border':0})
        tot_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'border': 0})
        tot_format1 = workbook.add_format({
            'bold': True,
            'align': 'right',
            'num_format': '#,##0.00',
            'border': 0})
        row_num_style = workbook.add_format({'num_format': '#,##0.00'}) 

        row=0
        col=0
        row_merge=row
        col=0
        col_merge=col+15
        sheet.merge_range(row,col,row,col_merge,sheet_name,title_format)
        row = row+2
        sheet.write(row,col,self.company_id.name,sub_header_style)
        col = 0
        if self.date_from:
            fdate = datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%d/%m/%Y')
            row=row+1
            sheet.write(row,col,"Date from")
            col = col+1
            sheet.write(row,col,fdate)
        if self.date_to:
            tdate = datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%d/%m/%Y')
            col=0
            row=row+1
            sheet.write(row,col,"Date to")
            col = col+1
            sheet.write(row,col,tdate)

        headers = ['Sl No.','Code','Particulars','Asset Life','Date of Purchase','Original Value','Opening Accum. Depreciation'
                    ,'Qty','Opening Assets Value','Additions','Deletion','Total Purchase Value','Net Assets',
                    'Depreciation for the period','Closing Value']
        col = 0
        row=row+2
        for head in headers:
            sheet.write(row,col,head,header_style)
            col+=1
        # sheet.set_column('A:A',27)
        sheet.set_column('B:B',15)
        sheet.set_column('C:C',25)
        sheet.set_column('E:E',15)
        sheet.set_column('D:D',10)
        sheet.set_column('F:P',20)
        col=0
        total_original_value=0
        total_opening_depr_amt=0
        total_qty=0
        total_opening_asset_amt=0
        total_asset_addition=0
        total_asset_deletion=0
        total_purchase_value=0
        total_net_asset=0
        total_period_depr_amt=0
        total_closing_value=0
        row+=1
        for category_id in category_ids:
            sl_no=0
            col=0
            categ_dict = data_dict.get(category_id)
            print("gddsssss",categ_dict)
            col+=1
            col_merge+=col+10
            sheet.merge_range(row,col,row,col_merge,categ_dict.get('categ_name'),sub_header_style)
            for asset in categ_dict.get('assets'):
                sl_no+=1
                col=0
                row+=1
                sheet.write(row,col,sl_no)
                col+=1
                sheet.write(row,col,asset.get('ref'))
                col+=1
                sheet.write(row,col,asset.get('name'))
                col+=1
                sheet.write(row,col,asset.get('asset_life'))
                col+=1
                sheet.write(row,col,asset.get('po_date'))
                col+=1
                sheet.write(row,col,asset.get('original_value'),row_num_style)
                col+=1
                sheet.write(row,col,asset.get('opening_depr_amt'),row_num_style)
                col+=1
                sheet.write(row,col,asset.get('qty'),row_num_style)
                col+=1
                sheet.write(row,col,asset.get('opening_asset_amt'),row_num_style)
                col+=1
                sheet.write(row,col,asset.get('asset_addition'),row_num_style)
                col+=1
                sheet.write(row,col,asset.get('asset_deletion'),row_num_style)
                col+=1
                sheet.write(row,col,asset.get('purchase_value'),row_num_style)
                col+=1
                sheet.write(row,col,asset.get('net_asset'),row_num_style)
                col+=1
                sheet.write(row,col,asset.get('period_depr_amt'),row_num_style)
                col+=1
                sheet.write(row,col,asset.get('closing_value'),row_num_style)
            col=0
            row+=1
            col_merge=col+4
            sheet.merge_range(row,col,row,col_merge,"Total",tot_format)
            col=col_merge+1
            sheet.write(row,col,categ_dict.get('total_original_value'),tot_format1)
            col+=1
            sheet.write(row,col,categ_dict.get('total_opening_depr_amt'),tot_format1)
            col+=1
            sheet.write(row,col,categ_dict.get('total_qty'),tot_format1)
            col+=1
            sheet.write(row,col,categ_dict.get('total_opening_asset_amt'),tot_format1)
            col+=1
            sheet.write(row,col,categ_dict.get('total_asset_addition'),tot_format1)
            col+=1
            sheet.write(row,col,categ_dict.get('total_asset_deletion'),tot_format1)
            col+=1
            sheet.write(row,col,categ_dict.get('total_purchase_value'),tot_format1)
            col+=1
            sheet.write(row,col,categ_dict.get('total_net_asset'),tot_format1)
            col+=1
            sheet.write(row,col,categ_dict.get('total_period_depr_amt'),tot_format1)
            col+=1
            sheet.write(row,col,categ_dict.get('total_closing_value'),tot_format1)

            total_original_value+=categ_dict.get('total_original_value')
            total_opening_depr_amt+=categ_dict.get('total_opening_depr_amt')
            total_qty+=categ_dict.get('total_qty')
            total_opening_asset_amt+=categ_dict.get('total_opening_asset_amt')
            total_asset_addition+=categ_dict.get('total_asset_addition')
            total_asset_deletion+=categ_dict.get('total_asset_deletion')
            total_purchase_value+=categ_dict.get('total_purchase_value')
            total_net_asset+=categ_dict.get('total_net_asset')
            total_period_depr_amt+=categ_dict.get('total_period_depr_amt')
            total_closing_value+=categ_dict.get('total_closing_value')
            row+=2

        col=0
        col_merge=col+4
        sheet.merge_range(row,col,row,col_merge,"Grand Total",tot_format)
        col=col_merge+1
        sheet.write(row,col,total_original_value,tot_format1)
        col+=1
        sheet.write(row,col,total_opening_depr_amt,tot_format1)
        col+=1
        sheet.write(row,col,total_qty,tot_format1)
        col+=1
        sheet.write(row,col,total_opening_asset_amt,tot_format1)
        col+=1
        sheet.write(row,col,total_asset_addition,tot_format1)
        col+=1
        sheet.write(row,col,total_asset_deletion,tot_format1)
        col+=1
        sheet.write(row,col,total_purchase_value,tot_format1)
        col+=1
        sheet.write(row,col,total_net_asset,tot_format1)
        col+=1
        sheet.write(row,col,total_period_depr_amt,tot_format1)
        col+=1
        sheet.write(row,col,total_closing_value,tot_format1)

        filename= sheet_name+'.xlsx'
        workbook.close()
        output.seek(0)
        excel_file = base64.encodestring(output.read())
        self.excel_file = excel_file
        self.file_name =filename

        return {            
        'type': 'ir.actions.act_window',            
        'view_type': 'form',            
        'view_mode': 'form',            
        'res_model': 'od.asset.register.wiz',            
        'res_id': self.id,           
        'target': 'new',            
        }















