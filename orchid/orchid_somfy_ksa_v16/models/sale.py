from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.tools import float_compare
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, float_round


class SaleOrder(models.Model):
	_inherit = "sale.order"

	od_gross_weight = fields.Float(string='Gross Weight',compute='total_gross_weight', tracking=True)
	od_cbm = fields.Float(string='Total CBM',compute='total_gross_weight',digits=(12, 12), tracking=True)
	od_transportation = fields.Selection([('sea', 'Sea'),('road', 'Road'),('air', 'Air'),('express', 'Express')], string='Transportation',default='road', tracking=True)
	od_purchase_id = fields.Many2one('purchase.order', readonly=True, string="Purchase Order", tracking=True)
	od_service = fields.Boolean(string="Service Invoice", tracking=True)
	od_transaction_type = fields.Selection([('Transfer', 'Transfer'),('STD', 'STD'),('Marketing', 'Marketing'),('Return', 'Return'),('Office Use', 'Office Use'),('Quality', 'Quality'),('Warranty', 'Warranty'),('In House', 'In House'),('Loyalty','Loyalty'),('Service','Service')], string='Transaction Type', default='STD', tracking=True)
	od_route_id = fields.Many2one('stock.route', string='Route', default=lambda self: self.env.ref('purchase_stock.route_warehouse0_buy').id, tracking=True)
	
	od_adjustment_qty_status = fields.Selection([('no_approval','No Approval Needed'),('need_approval', 'Need Approval'),('approved','Approved')], default='no_approval', string="Adj Qty Status", tracking=True, copy=False)
	od_delivery_charge = fields.Boolean(string='Delivery charge applicable', default=False, tracking=True)
	od_local_transportation_id = fields.Many2one('od.local.transport.charge.master', string="Delivery Location", tracking=True)
	od_submission_mail_sent = fields.Boolean(string="Submission Mail Sent",default=False)
	od_readonly_group = fields.Boolean(string="Is Salesperson?", compute="_od_is_readonly")
	od_margin_visibile = fields.Boolean(string="Margin Button Visibility", default=False, compute="od_compute_margin_visibility")
	od_terms_conditions = fields.Html(string="Terms & Conditions")

	def od_get_default_terms(self):
		for order in self:
			terms = """<!-- first page -->
						<div class="row"  style="font-size:11px;">
							<div class="col-6">
								<div class="col-12">
									<center>
										<b>
											GENERAL TERMS OF SALE FOR CUSTOMERS<br/>
											<i>Applicable as of from 01st January 2026<br/>
											(“Effective Date”)</i><br/><br/>
										</b>
									</center>
								</div>
							</div>
							<!-- middle -->
							<div class="col-1">&#160;</div>

							<!-- right side -->
							<div class="col-5">&#160;</div>
						</div>

						<div class="row" style="font-size:9px;">
							<!-- left side -->
							<div class="col-6">
								<div class="col-12" style="background-color:#FF7F00"><b>I.&#160;SCOPE</b></div><br/>
								<div class="col-12"  style="text-align: justify;">
									These General Terms of Sale, together with the Price List, (the “Conditions”) shall apply to the products under several brands (“Products”) and/or services (“Services”) sold by Somfy Somfy Saudi Arabia Co LLC (“Seller”) a company incorporated and regulated by Jebel Ali Free Zone Authority, having its registered office located at Building# 8260,Al Muhammadiyah, Ab Baun District, Postal Code 23622, Jeddah, Kingdom of Saudi Arabia,  to customers (“Customer”), which are located in , Kingdom of Saudi Arabia. Customers shall mean all categories of customers including, but not limited to, manufacturers, OEM, installers, distributors etc. Seller and Customer are hereinafter referred to as collectively the “Parties” and individually the “Party”.<br/>  

									The Seller categorizes its customers according to their predominant business activity and grants suitable pricing conditions accordingly.<br/>

									Any order placed with the Seller implies the full acceptance of these Conditions by the Customer.<br/> 

									These Conditions shall exclusively apply at the exclusion of any contrary conditions included in the Customer’s documents, including but not limited to general conditions of purchasing and orders, which shall have no effect whatsoever unless a specific agreement has been concluded in writing between the Parties. Also, these Conditions supersede any previous versions of terms and conditions of sales. <br/><br/> 

								</div>

								<div class="col-12" style="background-color:#FF7F00">
								  <b>II.&nbsp;PRODUCTS AND SERVICES</b>
								</div>
								<br/>

								<!-- 1. Information on Products -->
								<div class="col-12">
								  <b>1.&nbsp;Information on Products.</b>
								</div>

								<div class="col-12" style="text-align: justify;">
									The information and photos printed on catalogues, brochures and leaflets are given as an indication and are not binding upon the Seller and therefore are not contractual. The Seller fulfills its obligation of information about the Products in the datasheets, configuration manuals and Product leaflets. The Seller reserves the right at any time to modify the Product as well as the related technical and commercial information and documentation.<br/>
									The Customer is responsible   for informing its own customers of the conditions of installation (including configuration and potential restriction), conditions of use of the Products and the safety measures to be taken. If required, the Customer shall adapt and complete the information and conditions depending on the category of Products and customers. <br/>
								</div>

								<br/>

								<!-- 2. Category of Products -->
								<div class="col-12">
								  <b>2.&nbsp;Category of Products</b>
								</div>

								<div class="col-12" style="text-align: justify;">
									The Seller markets several families of products which are intended solely for installation by professionals in the field of home automation and motorization. This is due to their technical nature, as such products require specific and/or specialized knowledge to ensure that they meet the needs and constraints of the end user.<br/> 
									The Customer acknowledges that the Products are solely for the distribution or resale purposes, either in full or parts thereof. The Seller shall provide the Products to the Customer on a non-exclusive basis.<br/> 
									In the event of the resale to professionals who do not justify:<br/>
									    (i) a distribution activity aimed at professionals, or <br/>
									    (ii) an installation activity, or <br/>
									    (iii) the supply and installation of an integrated product,<br/>
									the Customer is liable for lack of advice or information in the event of an improper and inadequate installation or assembly. In such case, the Customer shall indemnify the Seller against any liability arising out of user claims on this basis and the Seller reserves the right to suspend all new orders and/or terminate the commercial relationship by providing written notice.<br/>
									It is the sole responsibility of the Customer to ensure it pays particular attention to the supply of safety instructions and adapted and up-to-date notices for the concerned family products which may be updated from time to time, especially when mandatory under any specific applicable norm.<br/>
									Consequently, due to the nature of the professional products defined above and the direct impact of the presentation of Products on interne to the brand's image of the Seller, the Customer shall comply with the below obligations in case of resale of the Products by and/or the internet.The Customer undertakes:<br/> 
									    1) That these Products are marketed in a space dedicated to professionals, either on its own website or on any other website of online sales of its customers.<br/>
									    2) To specify on this dedicated space that the Products presented must be installed by professionals and that the installation instructions accompanying the products are intended for professionals.<br/>
									    3) To provide exhaustive information on the safety instructions to be followed and the risks incurred in the event of non-compliant installation.
									    4) That the website does not contain any advertisements, arguments and/or product descriptions based on false or misleading claims, indications or presentations.<br/>
									    5) To market Products under conditions that do not harm the brand image of the Seller.<br/>
									    6) To ensure that the Website does not contain any unsuitable sales pitches and/or product descriptions likely to lead to a distortion, depreciation and devaluation of the Products and the brand.<br/>
									    7) Not to associate the Products with terms, words or expressions that are not directly related to the type of Products and that do not respect the qualitative image of the Products.<br/>
									    8) All of the above-mentioned obligations also apply to the positions held on the marketplaces.<br/>
								</div>

								<br/>

								<!-- 3. Services -->
								<div class="col-12">
								  <b>3.&nbsp;Services</b>
								</div>

								<div class="col-12" style="text-align: justify;">
									If the Customer has contracted the Seller to install Products or other goods or provide other services at the Customer’s premises, or at the premises of a customer of the Customer (“Premises”), the Customer shall, at its expense, ensure that:<br/>
									a) the Premises are safely accessible to the Seller’s service technicians (Technicians), and adequate and safe power and lighting is available, on the date agreed for the supply of the services.<br/>
								    b) the Technicians are provided with such induction/site training as is appropriate and which the Seller and the Customer deem necessary having regard to the nature of the services.<br/>
								    c) the Technicians will not be exposed to any danger or threat to their health or safety, or to their equipment, in connection with the supply of the services.<br/>
								    d) the consent of the owner and or authorized occupier of the Premises, or of any neighboring property which may be impacted by the supply of the services, has been obtained regarding the supply of the services.<br/>
								    e) the supply of the Services will not detrimentally impact any property proximate to the Premises or the environment generally; and<br/>
								    f) the completed services will not likely be at risk of damage or failure to correctly operate as a consequence of the shortcomings of the condition of the Premises.<br/>
								    g) The Customer acknowledges that the Technicians may refuse, in their absolute discretion, to undertake the services if the Premises are not in the condition prescribed above or for any other environmental, health or safety issue. The Seller shall not be subject to or incur any penalty or liability for any claim, loss, damage, or obligation, direct or indirect, consequential, or otherwise, arising out of any delay in the supply or non-supply of the services regardless of the reason.<br/><br/>
								</div>

								<!-- III. ORDERING AND LOGISTIC REQUIREMENTS -->
								<div class="col-12" style="background-color:#FF7F00;">
									<b>III.&nbsp;ORDERING AND LOGISTIC REQUIREMENTS</b>
								</div>
								<br/>

								<div class="col-12"><b>4.&nbsp;Orders</b></div>
								<div class="col-12" style="text-align: justify;">
									The Seller provided quotation (the “Quotation”) to the Customer in electronic format, which form integrant part with this Conditions. Once the Customer has verified the product details in the Quotation, the Customer shall confirm its acceptance of this Quotation by sending a signed and stamped copy or in writing by sending written confirmation by e-mail, including the Quotation number.<br/>
									All Products sales are complete and final only after acceptance of the Customer as defined above and conditions defined in the Quotation will apply.<br/>

									In case of events preventing the full continuity of the Seller activities (such as pandemic situation leading to shortages on raw materials and components), or in case of unavailability of the stock or delay in delivery, the Seller may suspend or propose partial delivery of Order. The Customer will be notified accordingly.<br/>

									The unavailability of a product due to a shortage of stock or the delay of a service will not give right to any compensation from the Seller.<br/>
									
									To improve Customer’s satisfaction, the Seller requests the Customer to indicate as early as possible any 
								</div>

								<!-- IV. remaining next page(2) starting -->
								<div class="col-12" style="text-align:justify">
									(VAT), duties, or other governmental charges. Such taxes and duties, if applicable, shall be borne and paid by the Customer. The Seller shall issue invoices to the Customer in <b>Saudi Riyal (SAR)</b>. The Euro prices stated in the quotation will be converted to Saudi Riyal using the official exchange rate published by the <b>Central Bank of Saudi Arabia</b> on its portal. The exchange rate applicable on the <b>date of invoice issuance</b>> shall be used for conversion.<br/>
								</div>
								<br/>

								<div class="col-12"><b>11.&nbsp;Modification of Price</b></div>
								<div class="col-12" style="text-align: justify;">
									The Seller reserves the right to modify the price of the Products, by giving at least one (1) month notice to the Customer. Following this notification, and before the Products are shipped, the Seller may adjust Price, to take into account any significant increase in the cost of raw materials, metals, fuels or other production related costs.<br/>

									The Seller will refuse systematical, unilateral and/or automatic deductions on the sales invoice by the Customer, without The Seller prior written approval.<br/> 

									The pricing conditions are granted taking into account the activity of the Customer concerned in the context of its last purchases or taking into account its new declared activity (manufacturer, installer, distributor). In the event of a change in the Customer's activity, the Customer must inform the Seller within 6 (six) months of such change of activity so that the relevant pricing terms corresponding to its new activity can be applied. If the Seller has reason to believe that the Customer has changed its activity without having notified the Seller accordingly, the Seller may clarify the situation with the Customer and require evidence of the claimed main activity of the Customer in relation to the latest purchases. In case of evidence of change of activity, the Seller may apply the pricing conditions corresponding to the new activity of the Customer to all new Orders placed with the Seller.<br/>
								</div>

								<br/>

								<div class="col-12"><b>12.&nbsp;Payment Terms</b></div>
								<div class="col-12" style="text-align: justify;">
									The Seller shall invoice the Customer upon Product’s expedition, meaning when the Product is handed over to the carrier or made available to the Customer.<br/>

									Subject to any applicable laws, payment terms may be agreed in writing by the Parties.<br/>

									Unless otherwise agreed in writing by the Parties, no discount shall be granted for early payments by Customer.<br/>
									
									The Seller reserves the right to defer or terminate the special terms of payment granted to Customer in case of significant change in any of the criteria that justified the granted of the special terms, and for instance the degradation of the Customer’s financial situation, the withdrawal of guarantees, late payment, unfair behavior by the Customer towards The Seller.<br/>
									In addition, in case of unfavorable opinion from the Seller’s credit insurance on the Customer, the Seller may require any additional protective measures in order to ensure proper performance of the Customer’s obligations, such as, but not limited to, down payment or advanced payment of the Order. Payments made by Customer shall apply first to the oldest outstanding debt and then to the interest charges.<br/>

									Sums owed by The Seller to the Customer shall not be withheld or compensated by Customer for any cause. In any case The Seller should not be required at more expensive payment condition than the one granted to the Customer by The Seller.<br/>

									The Seller is not responsible for any fund transfers done by the customer, through any other bank accounts other than that mentioned in the official sales document (Sales Invoice).  The Customer acknowledges that any payment made to a bank account other than the Seller’s officially designated account, as specified in this contract shall be at the Customer’s own risk.  The Seller shall not be held liable of any loss or damages resulting from the Customer acting on emails or communications that do not originate from the Seller’s email domain, or that purport to be from a Seller’s representative but are fraudulent in nature. The Customer agrees to exercise due diligence and vigilance when verifying payment instructions.  Any failure to do so will absolve the Seller of responsibility for any consequences arising from such actions.<br/>
								</div>

								<br/>

								<div class="col-12"><b>13.&nbsp;Consequences of default or late payments</b></div>
								<div class="col-12" style="text-align: justify;">
									In the event of default of payment on the due date by the Customer, late payment penalties shall apply on each payment due from the due date of payment as printed on the invoice pursuant to the Order. Interest charges shall be equal to Seven percent(7%) of the late payment amount exclusive of tax .  They are payable immediately.Interest charges shall be calculated as follows:Interest charges = (rate x late payment amount exclusive of tax) x (number of overdue days / 365. Late payment penalties are not exclusive from any compensation for the damages suffered, if any.<br/>

									In addition, the Seller may suspend pending and new Orders and shall inform the Customer accordingly. When the situation has been remedied by Customer, the Seller shall send a notification to the Customer.Remaining payment, including invoices not yet due, shall become immediately payable without prior formal notification.When the situation has not been remedied within a reasonable period, the Seller reserves the right to terminate the sale and seek the return of the Products, without prejudice to any other legal remedies available.<br/>

									All down payments made may be retained as damages for the cancellation of the sale and wear and tear of the Products.<br/>

									The Products delivered and unpaid shall be returned to the Seller at the Customer’s expenses and risks, and the Seller and/or its freight company, or employees shall be authorized to access, possibly with a judicial officer, Customer’s premises to draw up a complete inventory of the Products and to recover the unpaid Products.<br/>

									The outstanding deliveries may be withheld without incurring any liability to the Customer until full payment of the said Products is made to the Seller.<br/>
								</div>

								<br/>

								<div class="col-12"><b>14.&nbsp;Reservation of Ownership</b></div>
								<div class="col-12" style="text-align: justify;">
									<b>The Seller shall retain ownership of all Products until complete payment by the Customer is made to The Seller. Payment shall only be deemed effective when cashed in by The Seller. In the event of non-payment by the Customer of all or part of the price owed, The Seller shall repossess the Products delivered to the Customer at Customer’s expenses and risks. This repossession does not exclude further legal proceedings that The Seller may exercise.<br/>
									Notwithstanding the retention of title, the Customer shall bear all risks of loss or damage to the Products upon delivery of the Products to the Customer.<br/>
									In the frame of its current business, the Customer is allowed to resell the delivered Products before complete payment to The Seller, unless the Customer is subject to bankruptcy proceedings. The Customer shall not, however, bail, pledge, mortgage, grant a lien over, lease or assign the Products by any other way of security. If the Customer sold Products subject to the reservation of title, the Customer will undertake to inform The Seller of the identity of the subsequent buyers and The Seller can claim against the subsequent buyers the price of the Products unpaid by the Customer, without prejudice to any other right The Seller may be entitled to.</b><br/><br/>
								</div>

								<!-- V. LEGAL REQUIREMENTS -->
								<div class="col-12" style="background-color:#FF7F00;">
									<b>V.&nbsp;LEGAL REQUIREMENTS</b>
								</div>
								<br/>

								<div class="col-12"><b>15.&nbsp;Warranty</b></div>
								<div class="col-12" style="text-align: justify;">
									The Seller shall ensure the Product are free from all defects of material or manufacturing acknowledged by the Seller during the entire contractual warranty period indicated in the warranty terms in force and in the conditions and limits of use set by the Seller in the Product leaflets or any other documentation or information intended for the Customers. Warranty terms in force are available on the website and forms integral part with these Conditions.<br/>

									Unless otherwise provided in the applicable laws, the Product are covered exclusively by the contractual warranty granted by the Seller. Any other warranties, legal or not, including the legal liability for hidden defects or any general civil liability of the Seller are expressly excluded.<br/>

									The warranty period includes the repairing or replacement (at Seller’s discretion) of the Product acknowledged defective after inspection by the Seller, excluding compensation for any other prejudice whatsoever.<br/>

									Outside the scope of application of this contractual warranty, the Seller shall provide an after-sales service for its Products, by quotation.<br/>
								</div>
								<br/>

								<div class="col-12"><b>16.&nbsp;Liability</b></div>
								<div class="col-12" style="text-align: justify;">
									Either party shall perform its obligations under the Order(s) in compliance with the applicable laws.<br/>

									The Customer shall not modify the Products supplied and in particular shall not modify or remove any warnings concerning the dangers of improper use of the Products or use the Products for any purpose other than the ones defined. In case of breach, the Customer shall indemnify Seller internally against any
								</div>

								<!-- V.remaining 3rd page starting -->
								<br/>

								<div class="col-12"><b>21.&nbsp;Ethics & Anti-Corruption</b></div>
								<div class="col-12" style="text-align: justify;">
									Both Parties shall conduct their obligations in compliance with all applicable laws and regulations, committing to adhere to anti-corruption and anti-money laundering laws applicable, including but not limited to the U.S. Foreign Corrupt Practices Act (FCPA), the OECD Anti-Bribery Convention, the French Anti-corruption Law (Sapin II), and the EU Whistleblowing Directive.<br/>

									The Parties are expected to maintain accurate records and implement appropriate internal controls to prevent corruption, in a manner reflecting the scale and nature of their operations. Both Parties should endeavor to provide relevant anti-corruption training to their personnel and to establish effective reporting mechanisms for any suspected instances of corruption.<br/>

									The Customer additionally agrees to abide by the Seller’s Ethics Charter and Anti-corruption Code of Conduct, as detailed on the Seller's website (https://www.somfy-group.com/en-en/commitment/ethics-and-anticorruption). The Seller encourages the adoption of specific compliance measures that are proportionate to the size and capabilities of the business, with the goal of adhering to the spirit of the specified compliance rules and the intent of this clause.<br/> 

									In this frame, the Customer expressly allows the Seller to perform any audit and agrees to respond in good faith to any related questionnaire. Failure to comply with anti-corruption obligations constitutes a material breach of these Conditions and may result in termination of the contractual relationship.<br/>

									In case the Customer would like to report any unethical behaviour identified in the course of the business with the Seller, a whistleblowing line is available for internal and external stakeholders: compliance.somfy.com/somfy/alert. The related procedure is available on the Seller's website (www.somfy.com).<br/>
								</div>

								<br/>

								<div class="col-12"><b>22.&nbsp;Export Control</b></div>
								<div class="col-12" style="text-align: justify;">
									In the event of importation or resale of the Products by the Customer, the Customer is solely responsible for ensuring that the importation or resale does not violate the laws and regulations in force in the country of importation and for bearing all costs associated with making the Products compliant with these laws and regulations. The Seller will not be liable for any violation and is entitled to indemnification from the Customer for any related claims and expenses.<br/>

									If the Customer transfers Products delivered by the Seller to a third party, the Customer shall comply with all applicable national and international Trade Control Laws (imposed by the United Nations, the European Union, the United Kingdom, the United States, or any other jurisdiction relevant to the Customer and Seller’s business relationship) and shall not engage in any actions that could cause the Seller to be in violation of these laws. The Customer shall in particular guarantee that this transfer (1) will not violate any embargoes, (2) is not intended for prohibited uses (such as weapons or nuclear technology), (3) does not involve any parties listed on national and international sanctioned parties’ lists, and (4) complies with all re-export requirements.<br/>
									<b>No re-export to Sanctioned countries</b>
									    1. Section I : The Customer warrants that it will not re-export, directly or indirectly, any goods, technology, or services supplied by the Seller to any country or entity subject to sanctions or export restrictions, including but not limited to Russia, Belarus, or other countries designated by the relevant authorities.<br/>
									    2. The Customer is encouraged to make every feasible effort to track the end-use of the Products within the commercial chain and promptly notify the Seller of any actions by third parties that may undermine the intent of this provision.<br/>
									    3. Section II : Article 12g of the EU Regulation 833/2014 and 8g of the EU Regulation 765/2006. This section applies to any goods and technologies sold, supplied, transferred or exported between the Seller and the Customer that fall under the scope of Article 12g of Council Regulation (EU) No 833/2014 and Article 8g of Council Regulation (EU) No 765/2006.<br/>
									    4. Moreover, this clause refers directly to the “compliance certificate” that must be acknowledged by the Customer.<br/>
									    a. The Customer shall not sell, export or re-export, including transit operations, directly or indirectly, to Russia or Belarus or for use in the Russian Federation or in Belarus any goods and technologies described in section II here above.<br/>
									    b. The Customer shall undertake its best efforts to ensure that the purpose of paragraph (1) is not frustrated by any third parties further down the commercial chain, including by possible resellers.<br/>
									    c. The Customer shall set up and maintain an adequate monitoring mechanism to detect conduct by any third parties further down the commercial chain, including possible resellers, that would frustrate the purpose of paragraph (1) of the section II.<br/>
									    d. (Without prejudice of [INSERT ARTICLE ON LIABILITY], any violation of paragraphs (1), (2) or (3) of the section II shall constitute a material breach of an essential element of the contractual relation between the Customer and the Seller. The Seller shall be entitled to seek, as appropriate remedies, a penalty of 2% of the Customer’s annual turnover for the calendar year preceding the year in which the breach occurred, and / or the termination of all existing and unfulfilled business agreements with immediate effect, as well as the discontinuation of further business relations with the Customer.<br/> 
									    e. The Customer shall immediately inform the Seller about any problems in applying paragraphs (1), (2) or (3) of the section II, including any relevant activities by third parties that could frustrate the purpose of paragraph (1) of the section II. The Customer shall make available to the Seller information concerning compliance with the obligations under paragraphs (1), (2) and (3) of the section II within two weeks of the simple request of such information.”<br/><br/>
								</div>

								<!-- VI. INTELLECTUAL PROPERTY -->
								<div class="col-12" style="background-color:#FF7F00;">
									<b>VI.&nbsp;INTELLECTUAL PROPERTY</b>
								</div>
								<br/>

								<div class="col-12" style="text-align: justify;">
									The Seller markets the following families of Products and Services:<br/>
								    • SOMFY-branded Products & Services<br/>
								    • SIMU – branded Products & Services<br/>
								    • BFT -branded Products & Services<br/>
									In general, all trademarks, logos and service marks (collectively the “Trademarks”) that appear on the Products & Services are registered, unregistered or otherwise protected Seller rademarks or are licenses for use by the Seller by third parties. Other trademarks are proprietary marks and are registered to their respective owners.<br/>

									The Seller retains all Intellectual rights concerning the Products and/or Services, their representation, designation, pictures and all technical documentations. The Customer acknowledges that the Seller is exclusively responsible for all Intellectual Property Rights relating to the Products and/or Services, including Seller verbal, semi-figurative and figurative trademarks and all other Industrial Property Rights and copyrights attached to the Products and/or Services and that no rights of exploitation of those rights are conferred on it, other than the sole right to use the Products and/or Services under the conditions covered herein.<br/>

									The Customer expressly refrains from using the Products and/or Services for any object other than the one for which they were designed.<br/>

									Any other use of Products and/or Services, the Seller’s trademarks, logos or any domain names, trade names and more generally of any element belonging to the Seller (text,photography, visual element, etc.) or to any company of its group constitutes infringement of rights and sanctioned as such in relation to the Intellectual property code unless authorized by the Seller.<br/>
									
									The Seller will be able to give its prior and written consent regarding the use of its trademarks, logos and/or visuals for the purpose of carrying out operations by the Customer to promote the resale of Products and/or Services. In this case, the Customer undertakes to respect the Seller's user charter and graphic charter and to make faithful and loyal reproductions of the marks, logos, and visuals transmitted by the Seller and not to create any risk of confusion between the Seller or any brands of its group and one of them or several of its competitors.<br/>

									Similarly, any use of visuals authorized by the Seller will have to use the word "copyright" and the name of the photographer as transmitted, in a visible way.<br/>
									
									More generally, the Customer undertakes not to infringe Seller’s Intellectual Property rights in any way, and undertakes, among other things, not to damage Seller's brand image, trademarks, domain names, range names, products or services used by and/or owned by the Seller. <br/>
									
									The Customer shall refrain from using the Seller name or any other registered Trademarks, in whatever spelling, in any domain name registered by the Customer. The Customer agrees to transfer to the Seller or deactivate any domain names purchased prior to the release date of this Conditions which use the Seller name or any other registered Trademark.<br/>
									
									Customers who are aware of any infringement of the Intellectual Property rights held by the Seller must immediately inform the Seller in writing and provide any information in its possession. Within the limits
								</div>
									


							</div>

							<!-- middle -->
							<div class="col-1">&#160;</div>

							<!-- right side -->
							<div class="col-5">
								<!-- III remaining -->
								<div class="col-12" style="text-align:justify">
									project leading to high-volume Orders.<br/>
								</div>
								<br/>

								<div class="col-12"><b>5.&nbsp;Delivery Time</b></div>
								<div class="col-12" style="text-align: justify;">
									The Products ordered by Customer will be delivered within a period described in the offer of dispatch in force for the Customer. Unless otherwise agreed in writing by the Parties, the delivery dates mentioned in the Acknowledgement of Receipt are given as an indication, based on supply and transport possibilities.<br/>

									A delay on delivery of less than six (6) weeks from the delivery date provided in the Quotation shall not give rise to any claim of liquidated damages or justify the Order’s cancellation.<br/>

									The offer of dispatch and logistic services in effect can be communicated to the Customer on request.<br/>
								</div>

								<br/>

								<div class="col-12"><b>6.&nbsp;Transport and Shipping Conditions</b></div>
								<div class="col-12" style="text-align: justify;">
									Products are delivered according to the incoterms fixed by mutual agreement between the Seller and the Customer and specified in the quotation. Incoterms clarify who is responsible for costs, risks and tasks involved in the transportation and delivery of goods.<br/>

									In any case, the Seller is responsible for exports formalities and if the Incoterms defines that the Seller will organize the transport, the transportation costs will be borne by the Customer.<br/>

									The Seller informs the Customer that some of the Products may contain lithium batteries. Consequently, when the Customer arranges the transport or initiates a return, the Customers undertakes to comply with all international regulations relating to the transport of dangerous goods, including but not limited to ADR, IATA, IMDG and RID regulations.<br/>

									Unless otherwise agreed between the Parties, the risk for loss or damages to the Products shall pass to the Customer when delivery of the Products has been made to the carrier. In case the Product is not delivered by carrier, the risk for loss or damages to the Products shall pass to the Customer upon delivery at Seller’s premises.<br/>

									The Customer undertakes to obtain and maintain proper insurance contract from a creditworthy insurance company covering any damages that may occur during transportation of the Products.<br/>
								</div>

								<br/>

								<div class="col-12"><b>7.&nbsp;Reception of Products</b></div>
								<div class="col-12" style="text-align: justify;">
									The Customer is responsible for inspecting the Products upon delivery and to notify all visible defects immediately to the carrier on the delivery note.<br/> 

									In the event of shortage, damage, loss, theft, or any other defect, it is the Customer responsibility to inform the by email or letter with acknowledgment of receipt, within three (3) days from delivery, unless inapplicable pursuant to a mandatory provision of an international convention on transport of goods. A copy of the notification shall be sent to the Seller within the same timeframe. No complaint or return of Products shall be taken into consideration, after three (3) days following delivery, except prior express consent from the Seller.<br/>
								</div>

								<br/>

								<div class="col-12"><b>8.&nbsp;Notice & Packaging</b></div>
								<div class="col-12" style="text-align: justify;">
									The Seller informs the Client that for the products delivered in industrial packaging only one paper notice is sent by the Seller for all Products of one industrial packaging. It is Client’s responsibility to ensure that its own customers are adequately informed about the conditions of installation (including configuration), product usage, and necessary safety precautions, by enhancing and supplementing the information provided by the Seller according to the Client's own product range and its own typology of customers and by providing to its own customers with all documentation necessary to comply with the standards and regulations in force. The Client has the possibility to order additional notices to the Seller. The Parties agree that the Seller has fulfilled its normative obligations regarding the provision of safety, installation and operating instructions on the Products.”<br/>
								</div>

								<br/>

								<div class="col-12"><b>9.&nbsp;Returns</b></div>
								<div class="col-12" style="text-align: justify;">
									No return of Products shall be made unless expressly authorized by the Seller. All request for return of Products shall contain a copy of the original purchasing invoice of the related Product. A return of Products can give rise to a credit note under the following conditions.<br/>
								    1) Error of the Seller: when the Products delivered to the Customer are not in compliance with the Products listed in the Quotation (Product Code, quantity…) the Customer shall inform the Seller within three (3) working days from the delivery of the Product of such error. The Seller shall then retrieve the Product from the Customer’s premises. A credit note with a value of 100% of the net price invoiced, exclusive of tax, of the retrieved Product, shall be established by The Seller, provided that the conditions stipulated in 4, hereafter, are also met. The Seller will have to replace at his own expenses and in the shortest possible time the delivered Products which conspicuous defect or noncompliance defect have been duly proved by the Customer.<br/>

								    2) Error of Customer: A return shall be authorized by The Seller provided that a written request is sent by the Customer within thirty (30) Calendar days from the receipt of the Product. The Product shall be returned to The Seller at Customer’s expenses and risks and within five (5) working days from the date of acceptance by The Seller of such return.Upon receipt of the Product, a credit note with a value of 100% of the net price invoiced, exclusive of tax, of the related Product shall be established by The Seller, provided that the conditions stipulated in 4, hereafter, are also met. However, The Seller shall not accept any return in case of repeated errors by the Customer.<br/>

								    3) Subject to Clause Risk Transfer above, The Seller may examine, on a case by case basis, the possibility of accepting returns for any other reasons than those provided in 1) and 2) hereunder, as long as the Product is standard and was manufactured within the previous year. The Product shall be returned at Customer’s expenses and risks and within five (5) working days from the date of acceptance by The Seller of such return.  Upon receipt of the Product, Seller will establish a credit note, provided that the conditions mentioned in 4, hereafter, are also met. The credit note amount will take into account the condition of the returned product. The Seller may apply a depreciation scale reflecting the state of the product at the time of receipt, ensuring a fair and consistent valuation process for all returns.<br/>
								    4) Any return is subject to the following cumulative conditions:<br/>
								        a. The Seller’s customer service has previously approved the return in writing.<br/>
								        b. A copy of the agreement of return and of the original purchasing invoice of the related Product are attached to the returned Product,<br/>
								        c. The Products are new and undamaged,<br/>
								        d. The Products are returned in their complete undamaged packaging (including leaflets, screws, cardboard and accessories),<br/>
								        e. The Products are not a sub-part of a product,<br/><br/>
								</div>

								<!-- IV. PRICING AND CONDITIONS-->
								<div class="col-12" style="background-color:#FF7F00;">
									<b>IV.&nbsp;PRICING AND CONDITIONS</b>
								</div>
								<br/>

								<div class="col-12"><b>10.&nbsp;Applicable Prices</b></div>
								<div class="col-12" style="text-align: justify;">
									Prices shall be those in force at the date on the day of the Product’s delivery as determined by the Seller acting in its sole discretion.<br/>
									All prices quoted are in <b>Euro (€)</b> and are exclusive of any applicable value-added tax 
								</div>
								<br/>

								<!-- V. remaining -->
								<div class="col-12" style="text-align:justify">
									product liability claims of third parties if and to the extent that the damage was caused by the Customer/ and or its subcontractors.<br/>

									The Seller shall under no circumstances be held liable or engaged in any way, if it is demonstrated that the Products have not been installed and used in respect of the instructions and limits of use indicated by the Seller, and not in compliance with the existing standards and the state of the art, for motorizing or automating appropriate Products. <br/>

									In relation to the supply of services, to the extent permitted by law, the Seller’s liability is limited, at the Seller's election, to supplying the service again or providing for the cost of having the services supplied again, insofar as the liability of the Seller and the damages are proved. <br/>

									Neither Party shall be liable for any indirect and consequential damage suffered by the other Party, such as loss of turn over, loss of income loss of clients, loss of orders, any commercial disruption or loss of profit. The Seller shall indemnify the Customer only for duly proved direct damages. <br/>
									 
									The Seller's liability under the sale of the Products will not exceed an amount equivalent to the amount of Orders affected by the damage or the sum of 250,000 euros, whichever is lower. <br/>

									Mandatory statutory claims of either Party are not affected hereby. <br/>

									If Seller is prompted to issue a product recall due to a product defect in the Products, the Customer shall assist the Seller and take all reasonable measures ordered by the Seller.<br/>
								</div>

								<br/>

								<div class="col-12"><b>17.&nbsp;Termination</b></div>
								<div class="col-12" style="text-align: justify;">
									Seller may at any time immediately terminate these Conditions on written notice to the Customer:<br/>
								    a. If the Customer commits a material breach of any provision of these Conditions which is incapable of remedy; <br/> 
								    b. If the Customer commits a material breach of any provision of these Conditions which are capable of remedy but which the Customer fails to remedy within thirty (30) days after receipt of notice by the Seller specifying the breach and requiring, it to be remedied;<br/>
								    c. If the Customer engages in or is proven guilty of unethical or illegal practices; <br/>
								    d. If the Customer operating licenses are withdrawn, cancelled, suspended or expires and are not renewed within a period of forty-five (45) days or more;<br/> 
								    e. If the Customer suffers an insolvency event, (as determined by the Seller); and<br/>
								    f. If the Product is withdrawn from the market in the  United Arab Emirates, for any reason. <br/>
								    g. If in the absence of a mandatory requirement under the UAE Commercial Agency Laws, the Customer registers these Conditions.<br/>

								The Seller may at any time during the Initial period terminate these Conditions for convenience by providing thirty (30) days written notice to the Customer.<br/> 

								The Parties acknowledge and agree that a court order shall not be required to give effect to any termination or non-renewal of these Conditions in accordance with its terms. <br/>

								Upon the termination of these Conditions for any reason, the Customer shall:<br/>
								    a. Within three (3) months from the termination date, cease to sell and offer to sell the Products in the territory and shall cease all use of the Trade Marks;<br/>
								    b. Return or destroy, at the Seller’s discretion, within thirty (30) days after the termination date, all samples of the Products in the possession or the control of the Customer;<br/><br/>
								    c. Provide to the Seller a list of names of all past and present customers from the Products in the territory which are known to the Customer; and<br/>
								    d. Pay all outstanding unpaid invoices rendered by the Seller in respect of the Products within thirty (30) days after the termination date. <br/>

								Termination of these Conditions for any reason shall:<br/>
								    (a) be without prejudice to any obligation of any Party which has accrued prior to such termination or non- renewal (or shall thereafter accrue in respect of the period before such termination or non-renewal); and<br/>
								    (b) not affect any provision of these Conditions which is expressly or by implication intended to come into effect on, or to continue in effect after such termination or non- renewal.<br/>
								</div>

								<br/>

								<div class="col-12"><b>18.&nbsp;Hardship</b></div>
								<div class="col-12" style="text-align: justify;">
									In case the execution of a Party obligations becomes excessively expensive due to the occurrence of an unforeseeable financial or material circumstances (the “Unforeseeable event”), the Parties undertake to renegotiate in good faith the term of their agreement. During the negotiation, the Parties will suspend their respective obligations related to the sale of the Products concerned by the Unforeseeable event. If Parties fail to reach an agreement, they would have to mutually agree to terminate the agreement.<br/>
								</div>

								<br/>

								<div class="col-12"><b>19.&nbsp;Force Majeure</b></div>
								<div class="col-12" style="text-align: justify;">
									Neither Party shall be liable in event of partial or failure in performance of any obligation, especially in case of delay in delivery under the Conditions as a result of any occurrence or contingency beyond its reasonable control which prevent Parties from performing their obligations and for the duration and within the limit of the effects of said cases and circumstances on said obligations. The occurrence of any event described hereunder shall authorize The Seller to suspend related Orders ipso jure or to postpone its execution, without any indemnity, cost or damages for The Seller. <br/>
									A force majeure event is notably: war, act of terrorism, strikes, pandemics, epidemics, infectious diseases, quarantines, or other viral outbreaks, disruption of transportation, shortage of energy, water, raw materials or disruption of the Seller’s suppliers, capacity constraints, acts or omission of any government, natural disaster, accidents or any event leading to the unemployment of all or a part of The Seller’s premises and any event beyond the reasonable control of the Parties. The Party affected by a force majeure event as described above shall informed the other Party of its impossibility to perform its obligations. <br/> 
									 
									 If the force majeure event continues, or is reasonably expected to continue, for a period of three (3) consecutive months, the Party affected shall be entitled to cancel all or any part of the impacted orders previously confirmed, without any liability of the other Party.<br/>
								</div>

								<br/>

								<div class="col-12"><b>20.&nbsp;Confidentiality</b></div>
								<div class="col-12" style="text-align: justify;">
									As part of their commercial relationship, the Seller may be required to provide the Customer with certain information relating to the Products, such as technical data sheets, commercial and financial information or customs codes.<br/>
									The Customer undertakes to keep such information confidential. Documents, data and information of any nature whatsoever provided by the Seller shall remain its property and may not be disclosed or used for purposes other than the performance of the Order without the prior written consent of the Seller. <br/>
									The Customer, its managers, employees, subcontractors and agents shall be bound to secrecy and confidentiality on all such information and data provided by the Seller and on all matters not in the public domain relating to or arising from the Order.<br/>
									In case of doubt as to the confidential nature of any information, it is the Customer's responsibility to seek information from the Seller.<br/>
									The Seller reserves the right to require the Customer's employees or managers to whom Seller's information and data is disclosed to sign a written confidentiality undertaking. <br/>
								</div>

								<!-- VI.remaining -->
								<div class="col-12" style="text-align:justify">
									permitted by law, the Seller will not be liable to the Customer and/or third parties for any claim set on Intellectual Property rights relating to the Products and/or Services.<br/><br/>
								</div>

								<!-- VII. PERSONAL DATA -->
								<div class="col-12" style="background-color:#FF7F00;">
									<b>VII.&nbsp;PROCESSING OF PERSONAL DATA</b>
								</div>
								<br/>

								<div class="col-12" style="text-align: justify;">
									SOMFY may process the personal data of the Client for the purposes of managing the contractual relationship, executing, and monitoring the Orders for Products placed by the Client, for the entire duration of the contractual relationship and for the time necessary to achieve the intended purposes.
									SOMFY complies with the provisions of Regulation (EU) 2016/679 of the European Parliament and of the Council of April 27, 2016 (GDPR), and any applicable regulations ratifying, transposing, or replacing Regulation (EU) 2016/679 on the protection of personal data. In accordance with these provisions, the Client has the right to access, rectify, and delete their personal data, the right to limit processing, and the right to data portability. The Client also has the right to lodge a complaint with the competent supervisory authority. The Client can write at any time to dpo@somfy.com to exercise any of their rights. For more information on the processing of their data, the Client may consult SOMFY's Privacy Policy, available on https://www.somfy-group.com/en-en/privacy-policy<br/><br/>
								</div>

								<!-- VIII. LAW & JURISDICTION -->
								<div class="col-12" style="background-color:#FF7F00;">
									<b>VIII.&nbsp;APPLICABLE LAW & JURISDICTION</b>
								</div>
								<br/>

								<div class="col-12" style="text-align: justify;">
									These Conditions and any dispute or claim arising out of or in connection with it or its subject matter or formation (including non-contractual disputes or claims) shall be governed by and construed in accordance with the laws of the Dubai International Financial Centre (DIFC), Dubai United Arab Emirates. <br/>

									If any dispute arises out of these Conditions, Seller and Customer shall use commercially reasonable endeavors to attempt to promptly settle any such dispute by negotiation, involving senior executives of each Party.<br/>

									If the representatives of each Party referred to above are unable to settle any dispute within sixty (60) days of such dispute being referred to them, then the Parties shall agree to submit any such dispute to the exclusive jurisdiction of the courts of the DIFC. <br/><br/>
								</div>

								<!-- IX. MISCELLANEOUS -->
								<div class="col-12" style="background-color:#FF7F00;">
									<b>IX.&nbsp;MISCELLANEOUS</b>
								</div>
								<br/>

								<div class="col-12" style="text-align: justify;">
									These Conditions shall be written and construed in the English language, and all questions of interpretation of these Conditions shall be resolved by reference to the same as written in English. If these Conditions are translated into the Arabic language or any other foreign language, the English version will prevail for all purposes, including any disputes or claims that may be resolved by a legal proceeding.<br/>  

									The Customer shall not translate or register these Conditions or any corresp ondence or documents in connection with these Conditions with any authorities without the express prior written consent of the Seller, such consent to expressly refer to this clause. These Conditions may not be translated into Arabic without the prior written consent of the Seller. <br/> 

									The Seller and Customer shall be independent contractors and nothing in these Conditions is intended to make either Party a general or special agent, agency relationship, legal representative, subsidiary, joint venturer, partnership, fiduciary, employee or servant of the other for any purpose.  Neither Party shall act on behalf of the other without the other Party’s prior written consent, and neither Party shall be liable to any third party for any act or omission of the other Party or for any obligation or debt incurred by such Party. The Customer must prominently identify itself in all dealings with customers, lessors, contractors, suppliers, public officials, employees and others as the customer/ purchaser pursuant to these Conditions.
									No failure of either Party to enforce all or any part of these Conditions shall be interpreted as a waiver of all or any part of these Conditions.<br/>

									The Seller reserves the right to modify these Conditions at any time. Any derogations, modifications and/or additions to the Conditions will only be valid if expressly accepted in writing by the Seller. In addition to these Conditions, the Parties may agree on a specific sales agreement. If there is any conflict between the Conditions and such agreed sales agreement, the latter will prevail<br/>
								</div>
								

								
								



							</div>


						</div>"""
			order.od_terms_conditions = terms

	@api.depends('order_line','order_line.margin_percent')
	def od_compute_margin_visibility(self):
		for order in self:
			if order.partner_id.od_margin_control:
				if any(line.margin_percent<0.15 for line in order.order_line.filtered(lambda x:x.product_id.detailed_type=='product')):
					order.od_margin_visibile = True
				else:
					order.od_margin_visibile = False
			else:
				order.od_margin_visibile = False

	def action_update_reason(self,reason):
		for line in self.order_line:
			if line.margin_percent<0.15:
				line.write({'od_margin_reason':reason})
			else:
				line.write({'od_margin_reason':False})
		self.action_confirm()

	# @api.depends('company_id', 'partner_id', 'amount_total')
	# def _compute_partner_credit_warning(self):
	# 	for order in self:
	# 		order.with_company(order.company_id)
	# 		order.partner_credit_warning = ''
	# 		show_warning = order.state in ('draft', 'sent') and \
	# 					   order.company_id.account_use_credit_limit
	# 		if show_warning:
	# 			updated_credit = order.partner_id.commercial_partner_id.credit + (order.amount_total * order.currency_rate)
				
	# 			updated_credit_euro = order.partner_id.commercial_partner_id.od_credit_euro + (order.amount_total * order.currency_rate)
	# 			order.partner_credit_warning = self.env['account.move']._build_credit_warning_message(
	# 				order, updated_credit)
				
	@api.model
	def default_get(self, fields):
		res = super(SaleOrder,self).default_get(fields)
		if ((self.env.user.has_group('sales_team.group_sale_salesman') or self.env.user.has_group('sales_team.group_sale_salesman_all_leads')) and not (self.env.user.has_group('sales_team.group_sale_manager'))):
			res['od_readonly_group']=True
		else:
			res['od_readonly_group'] = False
		return res


	@api.depends('partner_id')
	def _od_is_readonly(self):
		for record in self:
			if ((record.env.user.has_group('sales_team.group_sale_salesman') or record.env.user.has_group('sales_team.group_sale_salesman_all_leads')) and not (record.env.user.has_group('sales_team.group_sale_manager'))):
				record.od_readonly_group=True
			else:
				record.od_readonly_group = False

	def _get_invoiceable_lines(self, final=False):
		"""Return the invoiceable lines for order `self`."""
		down_payment_line_ids = []
		invoiceable_line_ids = []
		pending_section = None
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

		for line in self.order_line:
			if line.display_type == 'line_section':
				# Only invoice the section if one of its lines is invoiceable
				pending_section = line
				continue
			if line.display_type != 'line_note' and float_is_zero(line.product_uom_qty, precision_digits=precision) and float_is_zero(line.product_uom_qty, precision_digits=precision) and (line.od_free_qty or line.od_adjustment_qty) :
				print("heredddddd")
				invoiceable_line_ids.append(line.id)
			if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
				continue
			if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
				if line.is_downpayment:
					# Keep down payment lines separately, to put them together
					# at the end of the invoice, in a specific dedicated section.
					down_payment_line_ids.append(line.id)
					continue
				if pending_section:
					invoiceable_line_ids.append(pending_section.id)
					pending_section = None
				invoiceable_line_ids.append(line.id)

		return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)
		
	def od_button_adj_qty_submission(self):
		if self.od_adjustment_qty_status == 'need_approval':
			template_id = self.env.ref('orchid_somfy_ksa_v16.od_sale_confirmation_mail_template')
			generate=self.env['mail.template'].browse(template_id.id)
			ctx  = self.env.context.copy()
			recipients = []
			cc_recipients=[]
			recipient_name = ""
			if self.od_transaction_type == 'Marketing':
				recipient_user_id = self.env['res.users'].search([('od_final_code','=','final')])
				if not recipient_user_id:
					raise UserError(_("No user found with code 'final' "))
				if not recipient_user_id.partner_id.email:
					raise UserError(_("No email defined in partner master for the user '%s' ")%(recipient_user_id.name))
				recipient_email = recipient_user_id.partner_id.email
				recipient_name = recipient_user_id.partner_id.name
				recipients.append(recipient_email)


				# recipients.append('jack.moussa@somfy.com')
				cc_email= ['zia.urrahman@somfy.com',self.user_id and self.user_id.login]
				# recipient_name = "Jack"
				for cc in cc_email:
					cc_recipients.append(cc)
			else:
				recipients.append('zia.urrahman@somfy.com')
				cc_email= ['ejaz.ramzan@somfy.com']
				for cc in cc_email:
					cc_recipients.append(cc)
				recipient_name = "Zia"

			recipients = list(filter(None,recipients))
			cc_recipients = list(filter(None,cc_recipients))
			ctx['email_to'] = ','.join(recipients)
			ctx['email_cc'] = ','.join(cc_recipients)
			ctx['subject'] = 'Sale Order Submission'	
			ctx['company_id'] = self.env.company
			ctx['content'] = "Sales Order "+str(self.name)+" for "+str(self.od_transaction_type)+" has been submitted by "+str(self.user_id.name)
			ctx['recipient_name'] = recipient_name
			generate.sudo().with_context(ctx).send_mail(self.id,force_send=True)
			self.od_submission_mail_sent = True
			return True


	@api.onchange('partner_id')
	def od_user_id_change(self):
		for sale in self:
			if sale.partner_id:
				# sale.user_id = sale.partner_id.od_user_id and sale.partner_id.od_user_id.id or self.env.user.id
				sale.user_id = sale.partner_id.user_id and sale.partner_id.user_id.id or self.env.user.id

	def onchange_od_adjustment_qty(self):
		for line in self.order_line:
			if line.od_adjustment_qty>0:
				self.od_adjustment_qty_status='need_approval'
				break;
			else:
				self.od_adjustment_qty_status='no_approval'

	@api.onchange('od_route_id')
	def onchange_od_route_id(self):
		for sale in self:
			for line in sale.order_line:
				line.route_id = sale.od_route_id.id
	

	@api.depends('order_line','order_line.od_gross_weight')
	def total_gross_weight(self):
		for record in self:
			gross=0
			cbm=0
			for line in self.order_line:
				gross=gross+line.od_gross_weight
				cbm = cbm+((line.product_uom_qty+line.od_adjustment_qty+line.od_free_qty)*line.product_id.od_cbm_vol)
			record.od_gross_weight=gross
			record.od_cbm=cbm

	# @api.model_create_multi
	# def create(self,vals_list):
	# 	for vals in vals_list:
	# 		SequenceObj = self.env['ir.sequence']
	# 		if vals.get('od_service',False):
	# 			st_number = SequenceObj.next_by_code('od.service.invoice.sale')
	# 			vals['name'] = st_number
	# 	return super().create( vals_list)


	def _prepare_invoice(self):
		"""
		to pass customised values.
		"""
		self.ensure_one()
		res = super()._prepare_invoice()
		od_contact_person_id = False
		for contact_id in self.partner_id.child_ids:
			od_contact_person_id = contact_id.id
		picking_ids = self.picking_ids.filtered(lambda x:x.state=='done')
		picking_ids =picking_ids.sorted('id')
		total_qty_done = 0
		delivery_number = ""
		od_gbw_ref_no = ""
		for picking_id in picking_ids:
			delivery_number=picking_id.name
			od_gbw_ref_no = picking_id.od_gbw_ref_no
			qty_qry = """SELECT coalesce(SUM(sml.qty_done),0) FROM stock_move_line sml
						 LEFT JOIN stock_picking sp ON sp.id=sml.picking_id
						 WHERE sml.picking_id=%s AND sml.state='done' """%(picking_id.id)
			self._cr.execute(qty_qry)
			qty = self._cr.fetchone()[0]
			total_qty_done = qty
		res.update({
			'od_gross_weight':self.od_gross_weight,
			# 'od_warehouse_id':self.warehouse_id and self.warehouse_id.id,
			'od_transportation':self.od_transportation,
			'od_transaction_type':self.od_transaction_type,
			'od_contact_person_id':od_contact_person_id,
			'od_packing_list_no':delivery_number,
			'od_packing_qty':total_qty_done,
			'od_cbm_vol':self.od_cbm,
			'od_gbw_ref_no':od_gbw_ref_no,
			'od_local_transportation_id':self.od_local_transportation_id and self.od_local_transportation_id.id,
			'currency_id':self.company_id.currency_id.id,#all invoices should be in company currency
			})
		return res
	

	#to update purchase order id
	def action_confirm(self):
		if self.partner_id and self.partner_id.od_lic_expiry_date:
			today_date = fields.Date.today()
			if self.partner_id.od_lic_expiry_date<today_date:
				raise UserError(_("License for this customer has been expired!!"))
		if self.partner_credit_warning and not (self.env.user.has_group('account.group_account_manager')):
		# if self.partner_credit_warning:
			msg= _('%s has over due invoices', self.partner_id.name)
			# print("msgggg",msg)
			# print("hhhhhhhhhhh",self.partner_credit_warning)
			if self.partner_credit_warning==msg:
				print("heresssssssssss")
				raise UserError(_("Account is blocked for over due invoices !!!"))
			else:
				raise UserError(_("Account is blocked as credit limit exceeded!!!"))
		for line in self.order_line:
			line.onchange_reserved_qty()
			# updating qty
			line.od_check_quants()
		res = super().action_confirm()
		qry =(''' SELECT id FROM purchase_order WHERE origin = '%s' ''')%(self.name)
		self.env.cr.execute(qry)
		result=self.env.cr.fetchall()
		result = [z[0] for z in result]
		if result:
			self.od_purchase_id = result[0]
		# confirmation email
		self.od_send_confirmation_email()
		if self.od_adjustment_qty_status=='need_approval':
			raise UserError(_("Adjustment quantity is not approved!!!"))

		for line in self.order_line:
			if line.sudo().product_id.categ_id:
				line.sudo().product_id.categ_id.od_get_sale_qty()
		return res

	def od_get_form_url(self):
		# action = 283
		action = self.env.ref('sale.action_orders')
		form_id = self.id
		url_link = "%s/?db=%s#id=%s&action=%s&view_type=form" % (
			self.env['ir.config_parameter'].get_param('web.base.url'),
			 self.env.cr.dbname,
			 form_id,
			 action.id  or False,
			 )
		print("urllllllllll",url_link)
		return url_link

	def od_send_confirmation_email(self):
		template_id = self.env.ref('orchid_somfy_ksa_v16.od_sale_confirmation_mail_template')
		generate=self.env['mail.template'].browse(template_id.id)
		ctx  = self.env.context.copy()
		recipients = []
		# recipients.append('salesadmin@somfyksa.com')
		logistic_user_id = self.env['res.users'].search([('name','=','Logistics')])
		if logistic_user_id and logistic_user_id.email:
			recipients.append(logistic_user_id.email)
		recipients.append('zia.urrahman@somfy.com')
		recipient_name = 'All'
		recipients = list(filter(None,recipients))

		ctx['name'] = 'Sale Order Confirmation Notification'
		ctx['email_to'] = ','.join(recipients)
		ctx['email_cc'] = ''
		ctx['subject'] = 'Sale Order Confirmation Notification'
		ctx['recipient_name'] = recipient_name
		ctx['company_id'] = self.env.company
		ctx['content'] = "Sale Order "+str(self.name)+" for "+ str(self.partner_id.name)+ " has been confirmed by "+ str(self.user_id.name)

		generate.sudo().with_context(ctx).send_mail(self.id,force_send=True)


	def button_update_custom_duty_line(self):
		for record in self:
			# if (record.od_service) or (record.od_transaction_type in ('Marketing','Warranty','Office Use','In House')):
				# pass
			condition=False
			if any(line.product_id.detailed_type!='service' for line in self.order_line):
				condition=True
			if condition and (not record.od_service) and (record.od_transaction_type not in ('Marketing','Warranty','Office Use','In House')):
				line_sum=0
				line_sum_cbm=0
				price_unit=0
				custom_price_unit=0
				line_sum_custom=0

				custom_product = self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id
				delivery_product = self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin').id
				for line in record.order_line.filtered(lambda r:r.product_id.id not in (custom_product,delivery_product) and r.product_id.detailed_type!='service'):
					# price_subtotal = (line.price_unit * (1 - (line.discount / 100.0)))*(line.product_uom_qty+line.od_free_qty+line.od_adjustment_qty)
					price_subtotal = line.price_subtotal
					line_sum +=price_subtotal
					country_code = line.product_id.orchid_country_id.code
					if country_code!='SA':
						line_sum_custom+=price_subtotal
					date = fields.Date.context_today(self)
					rate_id = self.env['orchid.cbm.rate'].search([('name','<=',date)],limit=1, order='name desc')
					if not rate_id:
						raise UserError(_("CBM Rate is not set!!!"))
					cbm = line.product_id.od_cbm_vol*(line.product_uom_qty+line.od_free_qty+line.od_adjustment_qty)*rate_id.rate
					line_sum_cbm +=cbm
				price_unit=0.05*(line_sum)
				custom_price_unit=0.05*(line_sum_custom)
				custom_duty_line_id=record.order_line.filtered(lambda r:r.product_id.id==custom_product)
				delivery_admin_line_id=record.order_line.filtered(lambda r:r.product_id.id==delivery_product)
				if custom_duty_line_id:
					custom_duty_line_id.price_unit=custom_price_unit
					if not(custom_price_unit > 0):
						custom_duty_line_id.unlink()
				if delivery_admin_line_id:
					delivery_admin_line_id.price_unit=line_sum_cbm
				if record.od_delivery_charge:
					record.button_update_local_transportation_line()
				# if not delivery_admin_line_id:
				# 	record.od_create_delivery_admin_line()
				# if not custom_duty_line_id and custom_price_unit>0:
				# 	record.od_create_custom_duty_line()
				

	def od_create_custom_duty_line(self):
		for record in self:
			line_sum=0
			price_unit=0
			for line in record.order_line.filtered(lambda r:r.product_id.detailed_type!='service' and r.product_id.orchid_country_id.code!='SA'):
				print("kovvvvvv")
				# price_subtotal = (line.price_unit * (1 - (line.discount / 100.0)))*(line.product_uom_qty+line.od_free_qty+line.od_adjustment_qty)
				price_subtotal = line.price_subtotal
				line_sum +=price_subtotal
			price_unit=0.05*(line_sum)
			line_vals={
			'sequence':500,
			'order_id':record.id,
			'display_type':False,
			'product_id':self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id,
			'product_uom':1,
			'product_uom_qty':1,
			'price_unit':price_unit,
			# 'tax_id':[(6,0,[])]
			}
			if price_unit>0:
				record.env['sale.order.line'].create(line_vals)

	def od_create_local_transportation_line(self):
		for record in self:
			cost=total_cbm=total_cost=0
			cost = record.od_local_transportation_id.cost
			total_cbm = record.od_cbm
			print("hhhhhhhhhhhh",total_cbm,cost)
			print("hhhhhhhhhhhh",type(total_cbm),type(cost))
			total_cost = total_cbm*cost
			if total_cbm<1:
				total_cost = cost*1
			line_vals={
			'sequence':500,
			'order_id':record.id,
			'display_type':False,
			'product_id':self.env.ref('orchid_somfy_ksa_v16.od_product_local_transportation').id,
			'product_uom':1,
			'product_uom_qty':1,
			'price_unit':total_cost,
			# 'tax_id':[(6,0,[])]
			}
			record.env['sale.order.line'].create(line_vals)

	def button_update_local_transportation_line(self):
		for record in self:
			if (not record.od_service) and (record.od_delivery_charge) and (record.od_transaction_type not in ('Marketing','Warranty','Office Use','In House')):
				cost=total_cbm=total_cost=0
				cost = record.od_local_transportation_id.cost
				total_cbm = record.od_cbm
				total_cost = total_cbm*cost
				if total_cbm<1:
					total_cost = cost*1
				transportation_product = self.env.ref('orchid_somfy_ksa_v16.od_product_local_transportation').id
				
				transportation_line_id=record.order_line.filtered(lambda r:r.product_id.id==transportation_product)
				if transportation_line_id:
					transportation_line_id.price_unit=total_cost
				if not transportation_line_id:
					record.od_create_local_transportation_line()

	def od_create_delivery_admin_line(self):
		for record in self:
			line_sum=0
			price_unit=0
			for line in record.order_line.filtered(lambda r:r.product_id.detailed_type!='service'):
				print("kovvvvvv")
				date = fields.Date.context_today(self)
				rate_id = self.env['orchid.cbm.rate'].search([('name','<=',date)],limit=1, order='name desc')
				if not rate_id:
					raise UserError(_("CBM Rate is not set!!!"))
				cbm = line.product_id.od_cbm_vol*(line.product_uom_qty+line.od_free_qty+line.od_adjustment_qty)*rate_id.rate
				line_sum +=cbm
			price_unit=(line_sum)
			line_vals={
			'sequence':501,
			'order_id':record.id,
			'display_type':False,
			'product_id':self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin').id,
			'product_uom':1,
			'product_uom_qty':1,
			'price_unit':price_unit,
			# 'tax_id':[(6,0,[])]
			}
			record.env['sale.order.line'].create(line_vals)

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			SequenceObj = self.env['ir.sequence']
			if vals.get('od_service',False):
				st_number = SequenceObj.next_by_code('od.service.invoice.sale')
				vals['name'] = st_number
		results = super().create(vals_list)
		for res in results:
			res.od_get_default_terms()
			if (not res.od_service) and (res.od_transaction_type not in ('Marketing','Warranty','Office Use','In House')):
				if any(line.product_id.detailed_type!='service' for line in res.order_line):
					# res.od_create_custom_duty_line()
					# res.od_create_delivery_admin_line()
					res.onchange_od_adjustment_qty()
					if res.od_delivery_charge:
						res.od_create_local_transportation_line()

		return res

	def action_cancel(self):
		# reversing adjustment and non moving status if approved
		self.onchange_od_adjustment_qty()
		# self.check_non_moving_so()
		return super().action_cancel()
	
	def od_approve_adjustment_qty(self):
		if self.od_adjustment_qty_status=='need_approval':
			attachment = self.env['ir.attachment']
			attachments = attachment.search([('res_model', '=', 'sale.order'), ('res_id', '=', self.id)])
			if attachments:
				self.od_adjustment_qty_status='approved'
			else:
				raise UserError(_('No Attachments found!!'))

	def od_action_reserve(self):
		res = super(SaleOrder, self).od_action_reserve()
		for line in self.order_line:
			line.onchange_reserved_qty()
		return res

	def od_action_unreserve(self):
		res = super(SaleOrder, self).od_action_unreserve()
		for line in self.order_line:
			line.onchange_reserved_qty()
		return res

class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"

	od_free_qty=fields.Float(string="Free quantity", digits=dp.get_precision('Product Unit of Measure'))
	od_adjustment_qty=fields.Float(string="Adjustment quantity", digits=dp.get_precision('Product Unit of Measure'))
	od_gross_weight = fields.Float(string='Gross Weight',compute="compute_gross_weight")
	od_transaction_type = fields.Many2one('od.transaction.type', string="Transaction Type", default=lambda self: self.env['od.transaction.type'].search([('code','=','SALE')], limit=1).id)
	od_product_stock_qty = fields.Float(string="Available Qty",digits='Product Unit of Measure', readonly=True)
	od_reserved_qty = fields.Float(string="Reserved Qty",digits='Product Unit of Measure', readonly=True, tracking=True)
	od_readonly_group = fields.Boolean(string="Is Salesperson?", related="order_id.od_readonly_group")
	od_readonly_product = fields.Boolean(string="Is Readonly Product?", default=False, compute="od_onchange_readonly_pdt")
	od_margin_reason = fields.Char(string="Reason")
	od_pricelist_percent = fields.Char(string="Pricelist Applied", compute="od_compute_pricelist_percent", store=True)

	@api.depends('product_id', 'product_uom', 'product_uom_qty')
	def od_compute_pricelist_percent(self):
		for line in self:
			if not line.product_id or line.display_type or not line.order_id.pricelist_id:
				line.od_pricelist_percent = False
			else:
				pricelist_item_id = line.order_id.pricelist_id._get_product_rule(
					line.product_id,
					line.product_uom_qty or 1.0,
					uom=line.product_uom,
					date=line._get_order_date(),
				)
				print("pricelist_item_id",pricelist_item_id)
				pricelist_item_id = self.env['product.pricelist.item'].browse(pricelist_item_id)

				line.od_pricelist_percent = pricelist_item_id and pricelist_item_id.price or False

	@api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced','od_adjustment_qty')
	def _compute_invoice_status(self):
		
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		for line in self:
			if line.state not in ('sale', 'done'):
				line.invoice_status = 'no'
			elif line.is_downpayment and line.untaxed_amount_to_invoice == 0:
				line.invoice_status = 'invoiced'
			elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
				print("toooooo")
				line.invoice_status = 'to invoice'
			
			# change on 8 june to enable invoicing even if product qty is zero but either adj or free qty is non zero
			elif float_is_zero(line.product_uom_qty, precision_digits=precision) and (not float_is_zero(line.od_adjustment_qty, precision_digits=precision)):
				print("line.......",line.invoice_lines)
				adj_invoiced = 0
				for il in line.invoice_lines:
					adj_invoiced+=il.od_adjustment_qty
				if adj_invoiced == line.od_adjustment_qty:
					line.invoice_status = 'invoiced'
				else:
					line.invoice_status = 'to invoice'
				print("adj_invoiced",adj_invoiced,line.invoice_status)
			# elif not float_is_zero(line.od_free_qty, precision_digits=precision):
			# 	print("toooooo")
			# 	line.invoice_status = 'to invoice'
			#-----------------------------------------------

			elif line.state == 'sale' and line.product_id.invoice_policy == 'order' and\
					line.product_uom_qty >= 0.0 and\
					float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
				line.invoice_status = 'upselling'
			elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
				print("invoiceeeeeeeeeeeeeeeeeeeeeeee",line.name,line.qty_invoiced, line.product_uom_qty,float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision))
				line.invoice_status = 'invoiced'
			else:
				line.invoice_status = 'no'
			print("liii",line.name,line.invoice_status)
		# print(s)
		
	def od_check_quants(self):
		for line in self:
			if line.product_id.type!='service':
				if line.od_product_stock_qty < line.product_uom_qty:
					raise UserError(_("Not enough quantity available for the product '%s' ")%(line.product_id.name))

	def unlink(self):
		for line in self:
			product_ids = []
			product_ids.append(line.env.ref('orchid_somfy_ksa_v16.od_product_local_transportation').id)
			# product_ids.append(line.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id)
			product_ids.append(line.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin').id)
			if line.product_id.id in product_ids:
				raise UserError("You cannot unlink this line!!")
			print("khgffffff",line.price_unit,line.product_id.name)
			if line.product_id.id==line.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id and line.price_unit>0:
				raise UserError("You cannot unlink this line!!")
			return super(SaleOrderLine,line).unlink()

	@api.onchange('product_id','order_id.warehouse_id')
	def onchange_reserved_qty(self):
		for line in self:
			if line.product_id:
				# line.od_gross_weight=(line.product_uom_qty+line.od_free_qty)*line.product_id.od_ttl_weight
				# line.od_product_stock_qty=line.free_qty_today
				# -- get_qry = SELECT  sum(reserved_qty) FROM orchid_reserved_sale_report_view WHERE product_id=%s
				# get_qry = '''SELECT  sum(coalesce(quantity,0)) as total_qty,sum(coalesce(reserved_quantity,0)) as reserved_qty FROM stock_quant WHERE product_id=%s AND location_id=%s '''%(line.product_id.id,line.order_id.warehouse_id.lot_stock_id.id)
				#hardcoded the location to dubai stock as suggested by srijith on 16 dec 2021
				get_qry = '''SELECT  sum(coalesce(quantity,0)) as total_qty,sum(coalesce(reserved_quantity,0)) as reserved_qty 
				FROM stock_quant WHERE product_id=%s AND location_id=%s '''%(line.product_id.id,line.order_id.warehouse_id.lot_stock_id.id)
				self._cr.execute(get_qry)
				result = self._cr.dictfetchall()
				total_qty =reserved_qty= 0
				print("resultttt",result)
				if result:
					for res in result:
						if res['total_qty']==None:
							res['total_qty']=0
						if res['reserved_qty']==None:
							res['reserved_qty']=0
						total_qty=total_qty+res['total_qty']
						reserved_qty=reserved_qty+res['reserved_qty']
				line.od_reserved_qty=reserved_qty
				line.od_product_stock_qty =(total_qty-reserved_qty)

			else:
				line.od_product_stock_qty=0
				line.od_reserved_qty=0

	@api.depends('product_id','od_readonly_group')
	def od_onchange_readonly_pdt(self):
		for line in self:
			print("kuytttttttttttttttttt")
			# readonly pdt
			# if line.od_readonly_group and line.product_id.detailed_type=='service' and line.product_id.od_readonly:
			# od_readonly_product = True
			if line.od_readonly_group:
				line.od_readonly_product = True
				if line.product_id and line.product_id.detailed_type=='service' and not (line.product_id.od_readonly):
					line.od_readonly_product = False
				# if line.product_id and line.product_id.detailed_type=='service' and not (line.product_id.od_readonly):
				# 	line.od_readonly_product = False
			else:
				line.od_readonly_product = False
				if line.product_id and line.product_id.detailed_type=='service' and line.product_id.od_readonly:
					line.od_readonly_product = True
				


	def write(self, values):
		result = super().write(values)
		print (">>>>>>>>>>>>>>>>>>>>>><<<<<>LLllllllllllllllllllllllllllllll")
		if 'product_id' in values:
			product_id = values['product_id']
			order_id = self.order_id.id
			product = self.env['product.product'].search([('id','=',product_id)])
			existing_lines = self.env['sale.order.line'].search([
				('order_id', '=', order_id),
				('product_id', '=', product_id),
				('id', '!=', self.id)  
			])
			print("existing_lines",existing_lines)
			
			if existing_lines:
				raise ValidationError(_("Duplicate lines for product '%s' ")%(product.display_name))
		
		if 'od_adjustment_qty' in values:
			print ("mmmmmmmmmmmm",values)
			# if values['od_adjustment_qty']!=0:
			self.order_id.onchange_od_adjustment_qty()
		return result	

	@api.model_create_multi
	def create(self, vals_list):
		result = super().create(vals_list)
		print (">>>>>>>>>>>>>>>>>>>>>><<<<<>L")
		for values in vals_list:

			order_id = values.get('order_id')
			product_id = values.get('product_id')
			product = self.env['product.product'].search([('id','=',product_id)])
			existing_lines = self.env['sale.order.line'].search([
				('order_id', '=', order_id),
				('product_id', '=', product_id)
			])
			# If there is an existing line with the same product, raise an error
			if existing_lines and  len(existing_lines)>1:
				raise ValidationError(_("Duplicate lines for product '%s' ")%(product.display_name))
		
			if 'od_adjustment_qty' in values:
				# if values['od_adjustment_qty']!=0:
				result.order_id.onchange_od_adjustment_qty()
		return result

	@api.depends('product_uom_qty','od_free_qty','od_adjustment_qty')
	def compute_gross_weight(self):
		for line in self:
			line.od_gross_weight=(line.product_uom_qty+line.od_free_qty+line.od_adjustment_qty)*line.product_id.od_ttl_weight
	
	def _prepare_invoice_line(self, **optional_values):
		res = super()._prepare_invoice_line(**optional_values)
		# conver price unit to company currency since all invoices should be made in company currency
		sar_price = self.currency_id._convert(self.price_unit,self.company_id.currency_id,self.company_id, fields.Date.today())
		res.update({
			'od_free_qty': self.od_free_qty,
			'od_adjustment_qty': self.od_adjustment_qty,
			'od_transaction_type': self.od_transaction_type.id,
			'od_ttl_qty': self.product_uom_qty + self.od_free_qty+self.od_adjustment_qty,
			'orchid_country_id' : self.product_id and self.product_id.orchid_country_id and self.product_id.orchid_country_id.id or False,
			'od_margin_reason':self.od_margin_reason,
			'price_unit': sar_price,
			})
		return res

	def _action_launch_stock_rule(self, previous_product_uom_qty=False):
		"""overridden to include adjstmnt nd free qty"""

		if self._context.get("skip_procurement"):
			return True
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		procurements = []
		for line in self:
			line = line.with_company(line.company_id)
			if line.state != 'sale' or not line.product_id.type in ('consu', 'product'):
				continue
			qty = line._get_qty_procurement(previous_product_uom_qty)
			total_qty = line.product_uom_qty + line.od_free_qty+line.od_adjustment_qty#orchid_change

			# if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:#orchid_change
			if float_compare(qty, total_qty, precision_digits=precision) == 0:#orchid_change
				continue

			group_id = line._get_procurement_group()
			if not group_id:
				group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
				line.order_id.procurement_group_id = group_id
			else:
				# In case the procurement group is already created and the order was
				# cancelled, we need to update certain values of the group.
				updated_vals = {}
				if group_id.partner_id != line.order_id.partner_shipping_id:
					updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
				if group_id.move_type != line.order_id.picking_policy:
					updated_vals.update({'move_type': line.order_id.picking_policy})
				if updated_vals:
					group_id.write(updated_vals)

			values = line._prepare_procurement_values(group_id=group_id)
			# product_qty = line.product_uom_qty - qty#orchid_change
			product_qty = total_qty - qty#orchid_change

			line_uom = line.product_uom
			quant_uom = line.product_id.uom_id
			product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
			procurements.append(self.env['procurement.group'].Procurement(
				line.product_id, product_qty, procurement_uom,
				line.order_id.partner_shipping_id.property_stock_customer,
				line.name, line.order_id.name, line.order_id.company_id, values))
		if procurements:
			self.env['procurement.group'].run(procurements)

		# This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
		orders = self.mapped('order_id')
		for order in orders:
			pickings_to_confirm = order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
			if pickings_to_confirm:
				# Trigger the Scheduler for Pickings
				pickings_to_confirm.action_confirm()
		return True