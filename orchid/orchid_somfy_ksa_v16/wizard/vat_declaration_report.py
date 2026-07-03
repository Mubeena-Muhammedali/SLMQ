from odoo import api, fields, models
import pandas as pd
from datetime import datetime, date, timedelta
from io import BytesIO
import base64
from odoo.exceptions import UserError


class OrchidVatDeclarationReport(models.TransientModel):  
    _name = 'orchid.vat.declaration.report.wiz' 
    _description = 'Vat Declaration Report'

    from_date = fields.Date(string="Start Date", required=True)    
    to_date = fields.Date(string="End Date", required=True)
    excel_file = fields.Binary(string='Excel Report',readonly="1")
    file_name = fields.Char(string='Excel File',readonly="1")
    company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)
    
    def vat_data(self):
        data_ls = []
        sale_service = 0
        sale_pdt = 0
        nominal_sale = 0
        inter_loc = 0
        purchase_service = 0
        import_purchases = 0

        where_qry = "WHERE ai.state IN ('posted') AND ai.invoice_date BETWEEN '"+str(self.from_date)+"' AND '"+str(self.to_date)+"' AND ai.od_expert_prgm_inv is not true"
        qry = """
                SELECT 
                    date_part('year',ai.invoice_date) as year,
                    date_part('month',ai.invoice_date) as month,
                    ai.invoice_date as doc_date,
                    ai.name as doc_no,
                    partner.name as partner_name,
                    ai.od_revenue_type as revenue_type,
                    pc.name->>'en_US' AS country,
                    ai.amount_untaxed_signed as tax_base_amount,
                    ai.amount_tax_signed as tax_amount,
                    ai.move_type as move_type

                FROM account_move ai
                LEFT JOIN res_partner partner ON partner.id=ai.partner_id
                LEFT JOIN res_country pc ON pc.id=partner.country_id

            """+where_qry
        self._cr.execute(qry)
        results = self._cr.dictfetchall()
        for result in results:
            print("resulttt",result)
            move_type = result['move_type']
            revenue_type = result['revenue_type']
            revenue_type_name = ""
            tax_categ = ""
            tax_code = ""
            if result['tax_amount']:
                tax_code = "VAT @ 15%"
            ref = ""
            partner_type = ""
            if revenue_type == 'itl':
                partner_type = "ITL"
                revenue_type_name = "Inter Location Stock Transfer"
                inter_loc+=result['tax_amount']
            elif revenue_type == 'purchase_service':
                partner_type = "Vendor"
                purchase_service+=result['tax_amount']
                revenue_type_name = "Purchase Invoice-Services"
            elif revenue_type in ('sale_service','sale_product','nominal_sale'):
                partner_type = "Customer"
                if revenue_type == 'sale_service':
                    revenue_type_name = "Sales Invoice-Services"
                    sale_service+=result['tax_amount']
                elif revenue_type== 'sale_product':
                    revenue_type_name = "Sales Invoice-Products"
                    sale_pdt+=result['tax_amount']
                else:
                    revenue_type_name = "Nominal Sales"
                    nominal_sale+=result['tax_amount']

            if move_type in ('out_invoice','out_refund'):
                tax_categ = 'Output VAT'
                ref = "Elec Motors, Controls & Accessories"
            elif move_type in ('in_invoice','in_refund'):
                tax_categ = 'Input VAT'
                ref="Purchase Invoice - Services"

            data ={
                'Company Name/Code': self.company_id.name,
                'Company VAT No.': self.company_id.vat,
                'Period/Month': result['month'],
                'Year': result['year'],
                'Tax Code': tax_code,
                'Document Date': result['doc_date'],
                'Posting Date': result['doc_date'],
                'Doc Number': result['doc_no'],
                'Ref nbr (type of goods, services, etc.)':ref,
                'Vendor/Customer Nbr.':partner_type,
                'Customer/Supplier Name':result['partner_name'],
                'Type of Revenue / Expenses':revenue_type_name,
                'Country':result['country'],
                'Tax Base Amount':abs(result['tax_base_amount']),
                'Output/Input Tax':abs(result['tax_amount']),
                'Tax Base':"",
                'Difference':"",
                'Gross':"",
                'Tax Category':tax_categ,
            }
            data_ls.append(data)
        return data_ls,sale_service,sale_pdt,nominal_sale,purchase_service,inter_loc,import_purchases



    
    def generate_excel(self):
        result,sale_service,sale_pdt,nominal_sale,purchase_service,inter_loc,import_purchases = self.vat_data()
        header_rage ='A1:S1'
        dataframe= pd.DataFrame(result,columns=["Company Name/Code","Company VAT No.","Period/Month","Year","Tax Code","Document Date","Posting Date"
            ,"Doc Number","Ref nbr (type of goods, services, etc.)","Vendor/Customer Nbr.","Customer/Supplier Name","Type of Revenue / Expenses",
            "Country","Tax Base Amount","Output/Input Tax","Tax Base","Difference","Gross","Tax Category"])

        dataframe.style.set_properties(subset=["Tax Base Amount","Output/Input Tax","Tax Base","Difference","Gross"], **{'text-align': 'right'})
        dataframe.sort_values(by='Vendor/Customer Nbr.')
        filename ='VatDeclarationReport.xlsx'
        from_date =datetime.strptime(str(self.from_date),'%Y-%m-%d').strftime('%d-%m-%Y')
        to_date =datetime.strptime(str(self.to_date),'%Y-%m-%d').strftime('%d-%m-%Y')
        title="VAT Declaration Report- "+ from_date +" to " +to_date

        writer = pd.ExcelWriter(filename, engine='xlsxwriter')
        fp = BytesIO()
        writer.book.filename = fp
        dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
        workbook  = writer.book
        worksheet = writer.sheets['Sheet1']
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'fg_color': '#D7E4BC',
            'border': 0}) 
        header_style = workbook.add_format({
            'bold': True,
            'align': 'center',
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
        
        worksheet.merge_range(header_rage,title, title_format)  
        for col_num, value in enumerate(dataframe.columns.values):
            worksheet.write(2, col_num, value, header_style)
            size=len(value)+8
            worksheet.set_column(col_num,col_num,size)
        worksheet.set_column('F:F',50)
        # worksheet.set_column('I:I',45)
        # worksheet.set_column('J:J',45)
        worksheet.set_column('L:L',45)
        # worksheet.set_column('N:N',20,row_num_style)
        # worksheet.set_column('O:O',20,row_num_style)
        # worksheet.set_column('P:P',20,row_num_style)
        # worksheet.set_column('Q:Q',20,row_num_style)
        # worksheet.set_column('R:R',20,row_num_style)
        
        worksheet.set_column('O:S',20,row_num_style)
        # worksheet.set_column('W:W',20,row_num_style)
        # worksheet.set_column('X:X',20,row_num_style)
        # worksheet.set_column('Y:Y',20,row_num_style)
        # worksheet.set_column('Z:Z',20,row_num_style)
        # worksheet.set_column('AA:AA',20,row_num_style)
        # worksheet.set_column('AB:AB',20,row_num_style)
        # worksheet.set_column('AC:AC',20,row_num_style)
        # worksheet.set_column('AD:AD',20,row_num_style)
        # worksheet.set_column('AE:AE',20,row_num_style)
        # worksheet.set_column('AF:AF',20,row_num_style)
        # worksheet.set_column('AG:AG',20,row_num_style)

        start_row=len(dataframe.index)+5
        sale_service_row=start_row+1
        sale_pdt_row=start_row+2
        nominal_sale_row=start_row+3
        inter_loc_row=start_row+4
        purchase_service_row=start_row+5
        import_purchases_row=start_row+6
        col = 10
        rcm_col = col+1
        input_col = col+2
        output_col = col+3
        total_heading=""
        worksheet.write(start_row, col, total_heading, title_format)
        worksheet.write(start_row, rcm_col, "RCM", title_format)
        worksheet.write(start_row, input_col, "Input Tax", title_format)
        worksheet.write(start_row, output_col, "Output Tax", title_format)

        worksheet.write(sale_service_row, col, "Sale Invoices - Services", tot_format)
        worksheet.write(sale_pdt_row, col, "Sale Invoices - Products", tot_format)
        worksheet.write(nominal_sale_row, col, "Nominal Sales", tot_format)
        worksheet.write(inter_loc_row, col, "Inter Location Stock Transfer", tot_format)
        worksheet.write(purchase_service_row, col, "Purchase Invoice - Services", tot_format)
        worksheet.write(import_purchases_row, col, "VAT on import Purchases", tot_format)

        worksheet.write(sale_service_row, output_col, abs(sale_service), tot_format1)
        worksheet.write(sale_pdt_row, output_col, abs(sale_pdt), tot_format1)
        worksheet.write(nominal_sale_row, output_col, abs(nominal_sale), tot_format1)
        worksheet.write(inter_loc_row, output_col, abs(inter_loc), tot_format1)
        worksheet.write(purchase_service_row, input_col, abs(purchase_service), tot_format1)
        worksheet.write(import_purchases_row, input_col, abs(import_purchases), tot_format1)




        writer.close()
        excel_file = base64.encodebytes(fp.getvalue())
        self.write({'excel_file':excel_file,'file_name':filename})
        fp.close()
        return {
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'orchid.vat.declaration.report.wiz',
              'res_id': self.id,
              'type': 'ir.actions.act_window',
              'target': 'new'
              }