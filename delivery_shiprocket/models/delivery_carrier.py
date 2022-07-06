# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests
import base64
from odoo import api, fields, models, _
from datetime import timedelta, datetime
from odoo.exceptions import UserError
from .shiprocket_request import ShipRocket

class DeliverCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('shiprocket', 'Shiprocket')
    ], ondelete={'shiprocket': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    shiprocket_email = fields.Char("Shiprocket Username", groups="base.group_system", help="Enter your Username from Shiprocket account.")
    shiprocket_password = fields.Char("Shiprocket Password", groups="base.group_system", help="Enter your Password from Shiprocket account.")
    shiprocket_access_token = fields.Text("Shiprocket Access Token", groups="base.group_system", help="Generate access token by Shiproket credentials")
    shiprocket_api_url = fields.Char("URL", default="https://apiv2.shiprocket.in/v1/")
    shiprocket_token_create_date = fields.Datetime("Access Token Created On")
    shiprocket_token_expiry_date = fields.Datetime("Access Token Expires On")
    shiprocket_channel = fields.Char(string="Shiprocket Channel")
    shiprocket_channel_code = fields.Char(string="Shiprocket Channel Code")
    shiprocket_default_package_type_id = fields.Many2one("stock.package.type", string="Shiprocket Package Type")
    shiprocket_payment_method = fields.Selection([('0', 'Prepaid'), ('1', 'COD')], default="0", string="Shiprocket Payment Method")
    shiprocket_label_generate = fields.Boolean("Generate Label")
    shiprocket_invoice_generate = fields.Boolean("Generate Invoice")
    shiprocket_manifests_generate = fields.Boolean("Generate Manifest")

    shiprocket_courier_filter = fields.Selection([('default_courier', 'Default Carrier'), ('lowest_rate', 'Lowest Rate'), ('call_before_delivery', 'Call Before Delivery'), ('lowest_etd', 'Lowest Estimated Time'), ('high_ratings', 'Highest Ratings')], default='lowest_rate', string='Shipment Based on')
    shiprocket_courier_name = fields.Char(string="Default Carrier")
    shiprocket_courier_id = fields.Char(string="Default Carrier Code")


    def _compute_can_generate_return(self):
        super(DeliverCarrier, self)._compute_can_generate_return()
        self.filtered(lambda c: c.delivery_type == 'shiprocket').write({'can_generate_return': True})


    def action_generate_access_token(self):
        """ Return the generated access token from
            shiprocket username and password.
        """
        if self.delivery_type == 'shiprocket' and self.shiprocket_email and self.shiprocket_password and self.shiprocket_api_url:
            sr = ShipRocket(self.sudo().shiprocket_access_token, self)
            response = sr.authorize_generate_token()
            if response.status_code == 200:
                response = response.json()
                self.shiprocket_access_token = response.get('token')
                # self.shiprocket_token_create_date = datetime.now()
                self.shiprocket_token_create_date = datetime.fromisoformat(response.get('created_at'))
                self.shiprocket_token_expiry_date = datetime.now() + timedelta(days=9)
                type = 'success'
                message = _("Access Token is generated successfully!")
            else:
                type = 'danger'
                message = _("Please check shiprocket credentials!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': type,
                    'message': message,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }


    def cron_shiprocket_access_token(self):
        shiprocket_carriers = self.search([('delivery_type', '=', 'shiprocket')])
        for carrier in shiprocket_carriers:
            sr = ShipRocket(carrier.shiprocket_access_token, carrier)
            response = sr.authorize_generate_token()
            if response.status_code == 200:
                response = response.json()
                carrier.shiprocket_access_token = response.get('token')
                print("datetime.fromisoformat(response.get('created_at'))-----------",datetime.fromisoformat(response.get('created_at')))
                carrier.shiprocket_token_create_date = datetime.fromisoformat(response.get('created_at'))
                carrier.shiprocket_token_expiry_date = datetime.fromisoformat(response.get('created_at')) + timedelta(days=10)
                type = 'success'
                message = _("Access Token is generated successfully!")
            else:
                type = 'danger'
                message = _("Please check shiprocket credentials!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': type,
                    'message': message,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }


    def action_get_channels(self):
        """ Return the list of channels configured by the customer
        on its shiprocke account.
        """
        if self.delivery_type == 'shiprocket' and self.sudo().shiprocket_access_token:
            sr = ShipRocket(self.shiprocket_access_token, self)
            channels = sr.fetch_shiprocket_channels()
            print("channels------------------",channels)
            if channels:
                action = self.env["ir.actions.actions"]._for_xml_id("delivery_shiprocket.act_delivery_shiprocket_channels")
                action['context'] = {
                    'channel_types': channels,
                    'default_delivery_carrier_id': self.id,
                }
                return action
        else:
            raise UserError('A Access Token is required in order to load your Shiprocket Channels.')


    def action_get_couriers(self):
        """ Return the list of carriers configured by the customer
        on its shiprocket account.
        """
        if self.delivery_type == 'shiprocket' and self.sudo().shiprocket_access_token:
            sr = ShipRocket(self.shiprocket_access_token, self)
            carriers = sr.fetch_shiprocket_carriers()
            print("carriers------------------", carriers)
            if carriers:
                action = self.env["ir.actions.actions"]._for_xml_id("delivery_shiprocket.act_delivery_shiprocket_carriers")
                action['context'] = {
                    'carrier_names': carriers,
                    'default_delivery_carrier_id': self.id,
                }
                return action
        else:
            raise UserError('A Access Token is required in order to load your Shiprocket Channels.')


    # def _shiprocket_convert_weight(self, weight):
    #     """ Return the weight for a Shiprocket order weight in KG."""
    #     weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
    #     return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)



    def shiprocket_rate_shipment(self, order):
        """ Return the rates for a quotation/SO."""
        sr = ShipRocket(self.shiprocket_access_token, self)
        print("order------------------------",order)
        result = sr.rate_request(self, order.partner_shipping_id, order.warehouse_id.partner_id, order)
        if result['error_found']:
            return {'success': False,
                    'price': 0.0,
                    'error_message': result['error_found'],
                    'warning_message': False}
        price = float(result['price'])
        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': False,
                'courier_name': result['courier_name']}


    def shiprocket_send_shipping(self, pickings):
        """ It creates a Shiprocket order.
        Once the order is generated. It will post as message the tracking
        links and the shipping labels, manifests and invoices.
        """
        sr = ShipRocket(self.sudo().shiprocket_access_token, self)
        res = []
        print("picking------------------",pickings)
        for picking in pickings:
            shipping = sr.send_shipping(picking, self)
            print("shipping---------------------------",shipping)
            if shipping:
                picking.shiprocket_order_id = shipping.get('order_id') if shipping.get('order_id') else False
                picking.shiprocket_shipment_id = shipping.get('shipment_id') if shipping.get('shipment_id') else False
                # need to change awb when available
                picking.carrier_tracking_ref = shipping.get('shipment_id') if shipping.get('shipment_id') else False
                picking.shiprocket_status = shipping.get('status') if shipping.get('status') else ''
                # picking.shiprocket_invoice_url = shipping.get('invoice_url') if shipping.get('invoice_url') else ''
                # picking.shiprocket_label_url = shipping.get('label_url') if shipping.get('label_url') else ''
                # picking.shiprocket_manifest_url = shipping.get('manifest_url') if shipping.get('manifest_url') else ''
                picking.message_post(body='Shiprocket order generated!') if shipping.get('order_id') else False
                if shipping.get('invoice_url'):
                    self.create_attachment_shiprocket(picking, shipping.get('invoice_url'), 'Invoice')
                if shipping.get('label_url'):
                    self.create_attachment_shiprocket(picking, shipping.get('label_url'), 'Label')
                # if shipping.get('manifest_url'):
                #     self.create_attachment_shiprocket(picking, shipping.get('manifest_url'), 'Manifest')
                # rate_request = self.shiprocket_rate_shipment(picking.sale_id)
                # print("rate_request--------------------",rate_request)
                # if rate_request and rate_request.get('courier_name'):
                picking.shipment_courier = shipping.get('courier_name')
                # shipping.update({'exact_price': shipping.get('price')})
                res.append(shipping)
        print("res=---------------------",res)
        return res


    def create_attachment_shiprocket(self, picking, url, name):
        """ Create attachments for Shiprocket Invoice, Label
        and Manifest.
        """
        response = requests.Session().get(url, timeout=30)
        if response.status_code == 200 and response.content:
            attachment = self.env['ir.attachment'].search([('name', '=', '%s Shiprocket %s' % (name, picking.name))])
            if not attachment:
                self.env['ir.attachment'].create({
                    'name': '%s Shiprocket %s' % (name, picking.name),
                    'res_model': 'stock.picking',
                    'res_id': picking.id,
                    'res_name': picking.name,
                    'datas': base64.b64encode(response.content),
                    'mimetype': 'application/pdf'
                })


    def shiprocket_get_tracking_link(self, picking):
        """ Returns the tracking links from a picking. Shiprocket returns one
        tracking link by package.
        """
        print("shiprocket_get_tracking_link---------------------",picking)
        sr = ShipRocket(self.shiprocket_access_token, self)
        shipment_id = picking.shiprocket_shipment_id
        track_url = sr.track_shipment(shipment_id)
        print("track_url--------------------",track_url)
        return track_url

    def shiprocket_cancel_shipment(self, picking):
        """ Cancel shipment from shiprocket requests.
        """
        sr = ShipRocket(self.sudo().shiprocket_access_token, self)
        cancel_shipment = sr.send_cancelling(picking)
        print("cancel_shipment----------------------",cancel_shipment)
        if cancel_shipment and cancel_shipment.get('status') == 200:
            picking.write({
                'carrier_tracking_ref': '',
                'carrier_price': 0.0,
                'shiprocket_status': 'REQUEST FOR CANCEL'
            })
            raise UserError(_(cancel_shipment.get('message')))
        else:
            raise UserError(_('Cannot cancel a Shipment!'))


    #     boxes = self._compute_boxes(picking, self)
    #     price = 0.0
    #     for box in boxes:
    #         sr = ShipRocket(self.sudo().shiprocket_access_token, self)
    #         result = sr.rate_request(self, picking.sale_id.partner_shipping_id,
    #                                  picking.sale_id.warehouse_id.partner_id, picking.sale_id, picking, box['weight'])
    #         if result and result.get('price'):
    #             price += float(result.get('price'))
    #             print("price-------------------",price)
    #     print("price-----final price-------------------",price)
    #     5/0


    #     res = []
    #     ep = EasypostRequest(self.sudo().easypost_production_api_key if self.prod_environment else self.sudo().easypost_test_api_key, self.log_xml)
    #     for picking in pickings:
    #         result = ep.send_shipping(self, picking.partner_id, picking.picking_type_id.warehouse_id.partner_id, picking=picking)
    #         if result.get('error_message'):
    #             raise UserError(result['error_message'])
    #         rate = result.get('rate')
    #         if rate['currency'] == picking.company_id.currency_id.name:
    #             price = float(rate['rate'])
    #         else:
    #             quote_currency = self.env['res.currency'].search([('name', '=', rate['currency'])], limit=1)
    #             price = quote_currency._convert(float(rate['rate']), picking.company_id.currency_id, self.env.company, fields.Date.today())
    #
    #         # return tracking information
    #         carrier_tracking_link = ""
    #         for track_number, tracker_url in result.get('track_shipments_url').items():
    #             carrier_tracking_link += '<a href=' + tracker_url + '>' + track_number + '</a><br/>'
    #
    #         carrier_tracking_ref = ' + '.join(result.get('track_shipments_url').keys())
    #
    #         labels = []
    #         for track_number, label_url in result.get('track_label_data').items():
    #             label = requests.get(label_url)
    #             labels.append(('LabelEasypost-%s.%s' % (track_number, self.easypost_label_file_type), label.content))
    #
    #         logmessage = _("Shipment created into Easypost<br/>"
    #                        "<b>Tracking Numbers:</b> %s<br/>") % (carrier_tracking_link)
    #         if picking.sale_id:
    #             for pick in picking.sale_id.picking_ids:
    #                 pick.message_post(body=logmessage, attachments=labels)
    #         else:
    #             picking.message_post(body=logmessage, attachments=labels)
    #
    #         shipping_data = {'exact_price': price,
    #                          'tracking_number': carrier_tracking_ref}
    #         res = res + [shipping_data]
    #         # store order reference on picking
    #         picking.ep_order_ref = result.get('id')
    #         if picking.carrier_id.return_label_on_delivery:
    #             self.get_return_label(picking)
    #     return res



    # def _compute_boxes(self, picking, carrier):
    #     """
    #     """
    #     boxes = []
    #     print("picking.package_ids-------------------------",picking.package_ids)
    #     for package in picking.package_ids:
    #         package_lines = picking.move_line_ids.filtered(lambda sml: sml.result_package_id.id == package.id)
    #         print("package_lines----------------------",package_lines)
    #         parcel_value = sum(sml.sale_price for sml in package_lines)
    #         print("parcel_value-----------------",parcel_value)
    #         weight_in_kg = carrier._shiprocket_convert_weight(package.shipping_weight)
    #         print("weight_in_kg--------------------",weight_in_kg)
    #         boxes.append({
    #             'weight': str(weight_in_kg),
    #             'parcelValue': parcel_value,
    #             'contentDescription': ' '.join(["%d %s" % (line.qty_done, re.sub('[\W_]+', ' ', line.product_id.name or '')) for line in package_lines])[:50],
    #         })
    #     print("boxes--------------------1--------",boxes)
    #     lines_without_package = picking.move_line_ids.filtered(lambda sml: not sml.result_package_id)
    #     print("lines_without_package-----------------------",lines_without_package)
    #     if lines_without_package:
    #         parcel_value = sum(sml.sale_price for sml in lines_without_package)
    #         weight_in_kg = carrier._shiprocket_convert_weight(sum(sml.qty_done * sml.product_id.weight for sml in lines_without_package))
    #         print("weight_in_kg----------------2-----------",weight_in_kg)
    #         boxes.append({
    #             'weight': str(weight_in_kg),
    #             'parcelValue': parcel_value,
    #             'contentDescription': ' '.join(["%d %s" % (line.qty_done, re.sub('[\W_]+', ' ', line.product_id.name or '')) for line in lines_without_package])[:50],
    #         })
    #     print("boxes-------22--------------------",boxes)
    #     return boxes



    #
    # def easypost_get_return_label(self, pickings, tracking_number=None, origin_date=None):
    #     ep = EasypostRequest(self.sudo().easypost_production_api_key if self.prod_environment else self.sudo().easypost_test_api_key, self.log_xml)
    #     result = ep.send_shipping(self, pickings.partner_id, pickings.picking_type_id.warehouse_id.partner_id, picking=pickings, is_return=True)
    #     if result.get('error_message'):
    #         raise UserError(result['error_message'])
    #     rate = result.get('rate')
    #     if rate['currency'] == pickings.company_id.currency_id.name:
    #         price = rate['rate']
    #     else:
    #         quote_currency = self.env['res.currency'].search([('name', '=', rate['currency'])], limit=1)
    #         price = quote_currency._convert(float(rate['rate']), pickings.company_id.currency_id, self.env.company, fields.Date.today())
    #
    #     # return tracking information
    #     carrier_tracking_link = ""
    #     for track_number, tracker_url in result.get('track_shipments_url').items():
    #         carrier_tracking_link += '<a href=' + tracker_url + '>' + track_number + '</a><br/>'
    #
    #     carrier_tracking_ref = ' + '.join(result.get('track_shipments_url').keys())
    #
    #     labels = []
    #     for track_number, label_url in result.get('track_label_data').items():
    #         label = requests.get(label_url)
    #         labels.append(('%s-%s-%s.%s' % (self.get_return_label_prefix(), 'blablabla', track_number, self.easypost_label_file_type), label.content))
    #     pickings.message_post(body='Return Label', attachments=labels)
    #
    #
    # def easypost_get_tracking_link(self, picking):
    #     """ Returns the tracking links from a picking. Easypost reutrn one
    #     tracking link by package. It specific to easypost since other delivery
    #     carrier use a single link for all packages.
    #     """
    #     ep = EasypostRequest(self.sudo().easypost_production_api_key if self.prod_environment else self.sudo().easypost_test_api_key, self.log_xml)
    #     if picking.ep_order_ref:
    #         tracking_urls = ep.get_tracking_link(picking.ep_order_ref)
    #     else:
    #         tracking_urls = []
    #         for code in picking.carrier_tracking_ref.split('+'):
    #             tracking_urls += ep.get_tracking_link_from_code(code.strip())
    #     return len(tracking_urls) == 1 and tracking_urls[0][1] or json.dumps(tracking_urls)
    #
    # def easypost_cancel_shipment(self, pickings):
    #     # Note: Easypost API not provide shipment/order cancel mechanism
    #     raise UserError(_("You can't cancel Easypost shipping."))
    #
    # def _easypost_get_services_and_package_types(self):
    #     """ Get the list of services and package types by carrier
    #     type. They are stored in 2 dict stored in 2 distinct static json file.
    #     The dictionaries come from an easypost doc parsing since packages and
    #     services list are not available with an API request. The purpose of a
    #     json is to replace the static file request by an API request if easypost
    #     implements a way to do it.
    #     """
    #     base_url = self.get_base_url()
    #     response_package = requests.get(url_join(base_url, '/delivery_easypost/static/data/package_types_by_carriers.json'))
    #     response_service = requests.get(url_join(base_url, '/delivery_easypost/static/data/services_by_carriers.json'))
    #     packages = response_package.json()
    #     services = response_service.json()
    #     return packages, services
    #
    # @api.onchange('delivery_type')
    # def _onchange_delivery_type(self):
    #     if self.delivery_type == 'easypost':
    #         self = self.sudo()
    #         if not self.easypost_test_api_key or not self.easypost_production_api_key:
    #             carrier = self.env['delivery.carrier'].search([('delivery_type', '=', 'easypost'), ('company_id', '=', self.env.company.id)], limit=1)
    #             if carrier.easypost_test_api_key and not self.easypost_test_api_key:
    #                 self.easypost_test_api_key = carrier.easypost_test_api_key
    #             if carrier.easypost_production_api_key and not self.easypost_production_api_key:
    #                 self.easypost_production_api_key = carrier.easypost_production_api_key
    #
    # def _generate_services(self, rates):
    #     """ When a user do a rate request easypost returns
    #     a rates for each service available. However some services
    #     could not be guess before a first API call. This method
    #     complete the list of services for the used carrier type.
    #     """
    #     services_name = [rate.get('service') for rate in rates]
    #     existing_services = self.env['easypost.service'].search_read([
    #         ('name', 'in', services_name),
    #         ('easypost_carrier', '=', self.easypost_delivery_type)
    #     ], ["name"])
    #     for service_name in set([service['name'] for service in existing_services]) ^ set(services_name):
    #         self.env['easypost.service'].create({
    #             'name': service_name,
    #             'easypost_carrier': self.easypost_delivery_type
    #         })

    #
    # def _get_delivery_type(self):
    #     """ Override of delivery to return the easypost delivery type."""
    #     res = super()._get_delivery_type()
    #     if self.delivery_type != 'easypost':
    #         return res
    #     return self.easypost_delivery_type
