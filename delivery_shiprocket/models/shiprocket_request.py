# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.exceptions import UserError, AccessError
import requests
from werkzeug.urls import url_join
import re
import string
from odoo import fields, _

class ShipRocket():

    def __init__(self, token, carrier):
        """
        Initial parameters for making api requests.
        """
        self.token = token
        self.carrier = carrier
        self.url = 'https://apiv2.shiprocket.in/v1/'
        self.header = {'Content-Type': 'application/json', 'Authorization': 'Bearer {}' .format(token)}

    def _make_api_request(self, endpoint, request_type='get', data=None):
        """
        make an api call, return response for multiple api requests of shiprocket
        """
        access_url = url_join(self.url, endpoint)
        if endpoint == 'external/auth/login':
            self.header = {'Content-Type': 'application/json'}
        try:
            if request_type == 'get':
                response = requests.get(access_url, headers=self.header, json=data)
            else:
                response = requests.post(access_url, headers=self.header, json=data)
            response_json = response.json()
            print("response_json---------------------",response_json)
            # check for any error in response
            # need to uncomment in main production
            # if response.status_code != 200 and response_json.get('message'):
            #     raise UserError(_('Shiprocket returned an error: %s', response_json.get('message')))
            return response
        except Exception as e:
            raise e

    def authorize_generate_token(self):
        """
        Generate access token from shiprocket credentials.
        """
        data = {
            'email': self.carrier.sudo().shiprocket_email if self.carrier.sudo().shiprocket_email else '',
            'password': self.carrier.sudo().shiprocket_password if self.carrier.sudo().shiprocket_password else ''
        }
        auth = self._make_api_request('external/auth/login', 'post', data)
        return auth

    def fetch_shiprocket_channels(self):
        """
        Import all active channels from shiprocket
        https://apiv2.shiprocket.in/v1/external/channels
        """
        channels = self._make_api_request('external/channels')
        channels = channels.json()
        channels = {c['name']: c['id'] for c in channels.get('data')}
        if channels:
            return channels
        else:
            raise UserError(_("You have no channels linked to your Shiprocket Account."))

    def fetch_shiprocket_carriers(self):
        """
        Import all available courier services from shiprocket
        https://apiv2.shiprocket.in/v1/external/courier/courierListWithCounts
        """
        carriers = self._make_api_request('external/courier/courierListWithCounts')
        carriers = carriers.json()
        if carriers and carriers.get('courier_data'):
            for carrier_data in carriers.get('courier_data'):
                carrier = request.env['shiprocket.carrier.service'].search([('name', '=', carrier_data.get('name'))])
                if not carrier:
                    request.env['shiprocket.carrier.service'].create({'name': carrier_data.get('name'), 'carrier_code': carrier_data.get('id')})
        else:
            raise UserError(_("Courier service not available in your Shiprocket account."))

    def _check_required_value(self, carrier, recipient, shipper, order=False, picking=False):
        """
        Check if the required value are present in order to process an API call.
        return True or an error if a value is missing.
        """
        carrier = carrier.sudo()
        recipient_required_field = ['street', 'city', 'country_id']
        if not carrier.shiprocket_access_token:
            raise UserError(_("The {} carrier is missing (Missing field(s) :\n Access Token)", carrier.name))
        if not order and not picking:
            raise UserError(_("Sale Order/Stock Picking is missing."))
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The customer address is incorrect (Missing field(s) :\n {})") % ", ".join(res).replace("_id", "")
        shipper_required_field = ['street', 'city', 'state_id', 'country_id']
        if not shipper.mobile and not shipper.phone:
            shipper_required_field.append('phone')
        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            return _("The pickup address is incorrect (Missing field(s) :\n {})") % ", ".join(res).replace("_id", "")
        if order:
            if not order.order_line:
                raise UserError(_("Please provide at least one item to ship."))
            error_lines = order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type != 'service' and not line.display_type)
            if error_lines:
                return _("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n {}") % ", ".join(error_lines.product_id.mapped('name'))
        return True

    def rate_request(self, carrier, recipient, shipper, order=False, picking=False, is_return=False):
        """
        Get shipment rate from shiprocket
        https://apiv2.shiprocket.in/v1/external/courier/serviceability/
        https://apiv2.shiprocket.in/v1/external/courier/international/serviceability
        """
        is_india = recipient.country_id.code == 'IN' and shipper.country_id.code == 'IN'
        self._check_required_value(carrier, recipient, shipper, order=order, picking=picking)
        dict_response = {'price': 0.0, 'currency': False, 'error_found': False, 'courier_name': False, 'courier_code': False}
        packages = carrier._get_packages_from_order(order, carrier.shiprocket_default_package_type_id)
        weight_in_kg = sum(pack.weight for pack in packages)
        print("weight_in_kg-----------------------",weight_in_kg)
        # weight_in_kg = carrier._shiprocket_convert_weight(order._get_estimated_weight())
        data = {'pickup_postcode': shipper.zip,
                'delivery_postcode': recipient.zip,
                'cod': 0 if carrier.shiprocket_payment_method == '0' else 1,
                'weight': weight_in_kg,
                'delivery_country': recipient.country_id.code}
        try:
            if is_india:
                rate_request = self._make_api_request('external/courier/serviceability/', 'get', data)
            else:
                data['cod'] = 0
                rate_request = self._make_api_request('external/courier/international/serviceability', 'get', data)
            print("rate_request.status_code--------------------",rate_request.status_code, rate_request)
            if rate_request.status_code == 200:
                rate_request = rate_request.json()
                if rate_request.get('data'):
                    available_couriers = rate_request.get('data').get('available_courier_companies')
                    print("available_couriers--------------------------------------",available_couriers)
                    if is_india:
                        rate_dict = {c.get('courier_name'): {'rate': c.get('rate'), 'call_before_delivery': c.get('call_before_delivery'), 'etd_hrs': c.get('etd_hours'), 'rating': c.get('rating')} for c in available_couriers}
                    else:
                        rate_dict = {c.get('courier_name'): {'rate': c.get('rate').get('rate'), 'call_before_delivery': c.get('call_before_delivery'), 'etd_hrs': c.get('etd_hours'), 'rating': c.get('rating')} for c in available_couriers}
                    print("rate dict=---------------------------",rate_dict)
                    rate_list = [dict_line.get('rate') for dict_line in rate_dict.values()]
                    etd_list = [dict_line.get('etd_hrs') for dict_line in rate_dict.values()]
                    rating_list = [dict_line.get('rating') for dict_line in rate_dict.values()]
                    call_before_list = [dict_line.get('call_before_delivery') for dict_line in rate_dict.values()]
                    print("rate_list---------------------------",rate_list)
                    if carrier.shiprocket_courier_filter == 'default_courier' and carrier.shiprocket_courier_id:
                        courier_name = carrier.shiprocket_courier_id.name if carrier.shiprocket_courier_id.name else False
                    elif carrier.shiprocket_courier_filter == 'call_before_delivery' and 'Available' in call_before_list:
                        courier_name = list(rate_dict.keys())[list(call_before_list).index('Available')] if rate_dict and list(rate_dict.keys())[list(call_before_list).index('Available')] else ''
                    elif carrier.shiprocket_courier_filter == 'lowest_etd':
                        print("inside lowest etfd--------------------------------",rate_dict)
                        courier_name = list(rate_dict.keys())[list(etd_list).index(min(etd_list))] if rate_dict and list(rate_dict.keys())[list(etd_list).index(min(etd_list))] else ''
                    elif carrier.shiprocket_courier_filter == 'high_ratings':
                        print("inside high ratings---------------------------",rating_list)
                        courier_name = list(rate_dict.keys())[list(rating_list).index(max(rating_list))] if rate_dict and list(rate_dict.keys())[list(rating_list).index(max(rating_list))] else ''
                    else:
                        courier_name = list(rate_dict.keys())[list(rate_list).index(min(rate_list))] if rate_dict and list(rate_dict.keys())[list(rate_list).index(min(rate_list))] else ''
                    print("courier_name---------------------------",courier_name)
                    if rate_dict and rate_dict.get(courier_name):
                        rate_list = [rate_dict.get(courier_name).get('rate')]
                    else:
                        dict_response['error_found'] = (_('Shiprocket Carrier - {} is not available.' .format(courier_name)))
                    if courier_name:
                        carrier.product_id.description_sale = 'Courier: ' + courier_name  #for sale.order.line - courier name
                        dict_response['courier_name'] = courier_name
                    carrier = request.env['shiprocket.carrier.service'].search([('name', '=', dict_response['courier_name'])], limit=1)
                    if carrier and carrier.carrier_code and is_india:
                        dict_response['courier_code'] = carrier.carrier_code
                    print("rate_list------------------------",rate_list)
                    if rate_list:
                        if order.currency_id.name == 'INR':
                            dict_response.update({'price': min(rate_list), 'currency': 'INR'})
                        else:
                            quote_currency = request.env['res.currency'].with_context(active_test=False).search([('name', '=', 'INR')], limit=1)
                            price = quote_currency._convert(float(min(rate_list)), order.currency_id, order.company_id, order.date_order or fields.Date.today())
                            dict_response.update({'price': price, 'currency': order.currency_id.name})
            else:
                dict_response['error_found'] = rate_request.json().get('message')
        except AccessError:
            dict_response['error_found'] = (_("Shiprocket rate request failed."))
        print("dict_response-----------------------",dict_response)
        return dict_response

    def _get_shipping_params(self, picking, carrier):
        """
        Returns Shipping data from delivery order for create an order and generate invoice.
        """
        if picking.sale_id.partner_invoice_id.phone:
            chars = re.escape(string.punctuation)
            number = re.sub(r'['+chars+']', '', picking.sale_id.partner_invoice_id.phone.replace(" ", ''))
            num = number[-10:]
        else:
            chars = re.escape(string.punctuation)
            number = re.sub(r'['+chars+']', '', picking.sale_id.partner_invoice_id.mobile.replace(" ", ''))
            num = number[-10:]
        delivery_packages = picking.carrier_id._get_packages_from_picking(picking, picking.carrier_id.shiprocket_default_package_type_id)
        print("delivery_packages--------------------",delivery_packages)
        result = []
        for pkg in delivery_packages:
            res = {
                  "order_id": "{}-{}".format(picking.name, picking.sale_id.name),
                  "order_date": picking.sale_id.date_order.strftime("%Y-%m-%d"),
                  "channel_id": carrier.shiprocket_channel_code,
                  "comment": picking.note,
                  "billing_customer_name": picking.sale_id.partner_invoice_id.name,
                  "billing_last_name": picking.sale_id.partner_invoice_id.name,
                  "billing_address": picking.sale_id.partner_invoice_id.street,
                  "billing_address_2": picking.sale_id.partner_invoice_id.street2,
                  "billing_city": picking.sale_id.partner_invoice_id.city,
                  "billing_pincode": picking.sale_id.partner_invoice_id.zip,
                  "billing_state": picking.sale_id.partner_invoice_id.state_id.name,
                  "billing_country": picking.sale_id.partner_invoice_id.country_id.name,
                  "billing_email": picking.sale_id.partner_invoice_id.email,
                  "billing_phone": num,
                  "shipping_is_billing": True if picking.sale_id.partner_invoice_id == picking.partner_id else False,
                  "shipping_customer_name": picking.partner_id.name,
                  "shipping_last_name": picking.partner_id.name,
                  "shipping_address": picking.partner_id.street,
                  "shipping_address_2": picking.partner_id.street2,
                  "shipping_city": picking.partner_id.city,
                  "shipping_pincode": picking.partner_id.zip,
                  "shipping_country": picking.partner_id.country_id.name,
                  "shipping_state": picking.partner_id.state_id.name,
                  "shipping_email": picking.partner_id.email,
                  "shipping_phone": num,
                  "order_items": [],
                  "payment_method": "Prepaid" if carrier.shiprocket_payment_method == '0' else 'COD',
                  "shipping_charges": picking.carrier_price,
                  "giftwrap_charges": 0,
                  "transaction_charges": 0,
                  "total_discount": 0,
                  "sub_total": picking.sale_id.amount_total,
                  "length": pkg.dimension['length']/10 if pkg.dimension['length'] else 0.5,  # convert mm to cm
                  "breadth": pkg.dimension['width']/10 if pkg.dimension['width'] else 0.5,   # convert mm to cm
                  "height": pkg.dimension['height']/10 if pkg.dimension['height'] else 0.5,  # convert mm to cm
                  "weight": pkg.weight,
                }
            for line in picking.sale_id.order_line:
                res.get('order_items').append({
                    "name": line.product_id.name,
                    "sku": line.product_id.default_code,
                    "units": line.product_uom_qty,
                    "selling_price": line.price_subtotal/line.product_uom_qty,
                    "discount": ((line.price_unit * line.product_uom_qty) * line.discount)/100 if line.discount else 0,
                    "tax": line.tax_id.amount if line.tax_id else 0,
                 })
            result.append(res)
        return result

    def send_shipping(self, picking, carrier, is_return=False):
        """
        Create a Shiprocket Order and generate AWB, Invoice, Label.
        Returns the dictionary with order_id, shipment_id, tracking_number,
        exact_price and courier_name for delivery order.
        https://apiv2.shiprocket.in/v1/external/orders/create/adhoc
        https://apiv2.shiprocket.in/v1/external/courier/assign/awb
        https://apiv2.shiprocket.in/v1/external/orders/print/invoice
        https://apiv2.shiprocket.in/v1/external/courier/generate/label
        """
        dict_response = {'order_id': 0, 'shipment_id': 0, 'status': False, 'tracking_number': 0, 'label_url': '', 'invoice_url': '', 'exact_price': '', 'courier_name': ''}
        param = self._get_shipping_params(picking, carrier)
        print("param-----------------------",param)
        # 5/0
        try:
            rate_request = self.rate_request(carrier, picking.partner_id, picking.picking_type_id.warehouse_id.partner_id, order=picking.sale_id, picking=picking, is_return=is_return)
            # check for error in result
            if rate_request.get('error_message'):
                return rate_request
            elif rate_request and rate_request.get('courier_name'):
                dict_response.update({'exact_price': rate_request.get('price'), 'courier_name': rate_request.get('courier_name'), 'courier_code': rate_request.get('courier_code') if rate_request.get('courier_code') else False})
                # dict_response['exact_price'] = rate_request.get('price')
                # dict_response['courier_name'] = rate_request.get('courier_name')
                # dict_response['courier_code'] = rate_request.get('courier_code') if rate_request.get('courier_code') else False
            res = self._make_api_request('external/orders/create/adhoc', 'post', param)
            print("res------------------------", res, res.json())
            if res and res.status_code == 200:
                result = res.json()
                print("result-------------create--------",result)
                dict_response.update({'order_id': result.get('order_id') if result.get('order_id') else False, 'shipment_id': result.get('shipment_id') if result.get('shipment_id') else False, 'status': result.get('status') if result.get('status') else False})
                # dict_response['order_id'] = result.get('order_id') if result.get('order_id') else False
                # dict_response['shipment_id'] = result.get('shipment_id') if result.get('shipment_id') else False
                # dict_response['status'] = result.get('status') if result.get('status') else False
                if result.get('shipment_id'):
                    data = {"shipment_id": result.get('shipment_id'), "courier_id": rate_request.get('courier_code')}
                    print("data-----------------for awwb==----",data)
                    aws_response = self._make_api_request('external/courier/assign/awb', 'post', data)
                    aws_data = aws_response.json()
                    print("aws_response----------------------",aws_data,aws_response)
                    dict_response['tracking_number'] = aws_data.get('response').get('data').get('awb_code') if aws_data and aws_data.get('response') and aws_data.get('response').get('data').get('awb_code') else False
                    print("dict_response---------------283------",dict_response)
                    label_data = {"shipment_id": [result.get('shipment_id')]}
                    if carrier.shiprocket_invoice_generate:
                        invoice_data = {"ids": [result.get('order_id')]}
                        invoice_response = self._make_api_request('external/orders/print/invoice', 'post', invoice_data)
                        invoice_result = invoice_response.json()
                        dict_response['invoice_url'] = invoice_result.get('invoice_url') if invoice_result and invoice_result.get('invoice_url') else False
                    if carrier.shiprocket_label_generate:
                        label_response = self._make_api_request('external/courier/generate/label', 'post', label_data)
                        print("label_response0000------------------------",label_response,label_response.json())
                        label_result = label_response.json()
                        dict_response['label_url'] = label_result.get('label_url') if label_result and label_result.get('label_url') else False
                    print("dict-------------response---------------------",dict_response)
        except AccessError:
            dict_response['error_found'] = (_("Shiprocket order generation failed."))
        return dict_response

    def request_pickup(self, picking, carrier):
        """
        API calls for Pickup request and Generate Manifests.
        https://apiv2.shiprocket.in/v1/external/courier/generate/pickup
        https://apiv2.shiprocket.in/v1/external/manifests/generate
        """
        if picking and picking.shiprocket_shipment_id:
            pickup_data = {"shipment_id": [picking.shiprocket_shipment_id]}
        # pickup requests
        pickup_requests = self._make_api_request('external/courier/generate/pickup', 'post', pickup_data)
        pickup_response = pickup_requests.json()
        print("pickup_requests-------------------------", pickup_response,pickup_requests)
        # remove 400 here for main production
        if pickup_requests.status_code in [200, 400] and carrier.shiprocket_manifests_generate:
            manifest_response = self._make_api_request('external/manifests/generate', 'post', pickup_data)
            print("manifest_response-------------------",manifest_response)
            manifest_result = manifest_response.json()
            print("manifest_response------------------------", manifest_result)
            if manifest_result and manifest_result.get('manifest_url'):
                return manifest_result
        else:
            return pickup_response

    def track_shipment(self, shipment_id):
        """
        Returns the tracking url if awb is generated successfully.
        https://apiv2.shiprocket.in/v1/external/courier/track/shipment/{}
        """
        tracking_response = self._make_api_request('external/courier/track/shipment/{}' .format(shipment_id), 'get', {})
        print("tracking_response===============================",tracking_response)
        if tracking_response.status_code == 200:
            tracking_data = tracking_response.json()
            print("tracking_data-00-------------------------",tracking_data)
            if tracking_data and tracking_data.get('tracking_data').get('track_url'):
                return tracking_data.get('tracking_data').get('track_url')

    def send_cancelling(self, picking):
        """
        For cancelling shipment order from shiprocket.
        https://apiv2.shiprocket.in/v1/external/orders/cancel
        """
        if picking.shiprocket_order_id:
            data = {'ids': [picking.shiprocket_order_id]}
            try:
                cancel_response = self._make_api_request('external/orders/cancel', 'post', data)
                print("cancel_response-------------------------",cancel_response,cancel_response.json())
                cancel_result = cancel_response.json()
            except IOError:
                raise UserError("Shiprocket cannot process for cancel shipment.")
            return cancel_result


        # if request.env.company.generate_invoice == True:
        #   invoice_data = {
        #     "ids": [res.get('order_id')]
        #   }
        #   invoice_url_api = 'https://apiv2.shiprocket.in/v1/external/orders/print/invoice'
        #   try:
        #       req = requests.post(invoice_url_api, headers=headers ,json=invoice_data)
        #       response_text = req.content
        #       decode_data = response_text.decode('utf-8')
        #       data = json.loads(decode_data)
        #       invoice_url = data.get('invoice_url')
        #   except Exception as e:
        #       raise UserError(_(e))
        # else:
        #     invoice_url = None
        #
        #
        # if request.env.company.generate_label == True:
        # label_data = {
        #     "shipment_id": [result.get('shipment_id')],
        # }
        # label_response =

        # label_url_api = 'https://apiv2.shiprocket.in/v1/external/courier/generate/label'
        # try:
        #   req = requests.post(label_url_api, headers=headers, json=label_data)
        #   response_text = req.content
        #   decode_data = response_text.decode('utf-8')
        #   data = json.loads(decode_data)
        #   label_url = data.get('label_url')
        # except Exception as e:
        #   raise UserError(_(e))
        # else:
        #     label_url = None
        #
        # tracking_link = ''
        #
        # order_id = res.get('order_id')
        # channel = param.get('channel_id')
        # shipment_id = res.get("shipment_id")
        #
        # tracking_link += str(order_id)
        # dict_response['tracking_link'] = tracking_link
        # dict_response['tracking_number'] = tracking_link
        # dict_response['invoice_url'] = invoice_url
        # dict_response['label_url'] = label_url
        #
        # picking.env.cr.commit()
        # return dict_response

