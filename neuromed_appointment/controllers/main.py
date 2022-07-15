# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.appointment.controllers.main import Appointment
from dateutil.relativedelta import relativedelta
from babel.dates import format_datetime, format_date
from odoo import http, _, fields
from odoo.http import request
from datetime import datetime
from odoo.tools import plaintext2html, DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo.tools.misc import get_lang
from werkzeug.exceptions import NotFound
import pytz
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.base.models.ir_ui_view import keep_query
import json

class CustomWebsiteCalendar(Appointment):

    @http.route([
        '/calendar',
        '/calendar/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=True)
    def calendar_appointments(self, page=1, **kwargs):
        return request.render('appointment.appointments_list_layout', self._prepare_appointments_list_data(**kwargs))

    def _prepare_appointments_list_data(self, **kwargs):
        domain = self._appointments_base_domain(kwargs.get('filter_appointment_type_ids'))
        appointment_types = request.env['calendar.appointment.type'].search(domain)
        if kwargs.get('crm_lead'):
            return {
                'appointment_types': appointment_types,
                'crm_id': kwargs.get('crm_lead'),
            }
        return {
            'appointment_types': appointment_types,
        }

    @http.route(['/calendar/<model("calendar.appointment.type"):appointment_type>'], type='http', auth="public", website=True, sitemap=True)
    def calendar_appointment_type(self, appointment_type, filter_employee_ids=None, timezone=None, state=False, **kwargs):
        appointment_type = appointment_type.sudo()
        request.session['timezone'] = timezone or appointment_type.appointment_tz
        try:
            filter_employee_ids = json.loads(filter_employee_ids) if filter_employee_ids else []
        except json.decoder.JSONDecodeError:
            raise ValueError()
        medical_params = {
            'resource_id': kwargs.get('resource_id', False),
            'location_id': kwargs.get('location_id', False),
            'service_id': kwargs.get('service_id', False),
            'crm_id': kwargs.get('crm_id') if kwargs.get('crm_id') and kwargs.get('crm_id') != 'None' and kwargs.get('crm_id') != 'False' else 0
        }
        if appointment_type.assign_method == 'chosen' and not filter_employee_ids:
            suggested_employees = appointment_type.employee_ids
        else:
            suggested_employees = appointment_type.employee_ids.filtered(lambda emp: emp.id in filter_employee_ids)
        employee_id = kwargs.get('employee_id')
        if not suggested_employees and employee_id and int(employee_id) in appointment_type.employee_ids.ids:
            suggested_employees = request.env['hr.employee'].sudo().browse(int(employee_id))
        default_employee = suggested_employees[0] if suggested_employees else request.env['hr.employee']
        if kwargs.get('resource_id') != 'None':
            slots = appointment_type.sudo().with_context(medical_params=medical_params)._get_appointment_slots(
                request.session['timezone'], default_employee)
        else:
            slots = appointment_type._get_appointment_slots(request.session['timezone'], default_employee)
        formated_days = [
            format_date(fields.Date.from_string('2021-03-0%s' % str(day + 1)), "EEE", get_lang(request.env).code) for
            day in range(7)]
        if kwargs.get('location_id') and kwargs.get('resource_id') and kwargs.get('service_id') and kwargs.get('resource_id') != 'None':
            slot_single = request.env['calendar.appointment.slot'].sudo().search([('appointment_type_id', '=', appointment_type.id), ('resource_id', '=', (int(kwargs.get('resource_id'), False))), ('product_id', '=', (int(kwargs.get('service_id'), False))), ('location_id', '=', (int(kwargs.get('location_id'), False)))], limit=1)
        else:
            slot_single = False
        if kwargs.get('location_id') and kwargs.get('location_id') != 'None':
            location = request.env['medical.locations'].sudo().search([('id', '=', int(kwargs.get('location_id'), False))])
        else:
            location = False
        return request.render("appointment.appointment_info", {
            'appointment_type': appointment_type,
            'suggested_employees': suggested_employees,
            'main_object': appointment_type,
            'timezone': request.session['timezone'],
            'slots': slots,
            'state': state,
            'neuromed_duration': slot_single.neuromed_duration if slot_single and slot_single.neuromed_duration else appointment_type.appointment_duration,
            'location_name': location.name if location and location.name else appointment_type.location,
            'filter_appointment_type_ids': kwargs.get('filter_appointment_type_ids'),
            'formated_days': formated_days,
            'resource_id': kwargs.get('resource_id', False),
            'location_id': kwargs.get('location_id', False),
            'service_id': kwargs.get('service_id', False),
            'crm_id': kwargs.get('crm_id', False),
        })

    @http.route([
        '/calendar/<model("calendar.appointment.type"):appointment_type>/appointment',
    ], type='http', auth='public', website=True, sitemap=True)
    def calendar_appointment(self, appointment_type, filter_employee_ids=None, timezone=None, failed=False, **kwargs):
        """
        Rewrite this method to pass resource and location in 'get_appointment_slots'
        method to filter out the slots.
        """
        if not kwargs and appointment_type.slot_ids:
            resource_id = appointment_type.slot_ids[0].resource_id.id or None
            location_id = appointment_type.slot_ids[0].location_id.id or None
            service_id = appointment_type.slot_ids[0].product_id.id or None
            crm_id = None
        else:
            resource_id = kwargs.get('resource_id')
            location_id = kwargs.get('location_id')
            service_id = kwargs.get('service_id')
            crm_id = kwargs.get('crm_id')
        return request.redirect('/calendar/%s?resource_id=%s&location_id=%s&service_id=%s&crm_id=%s&state=%s' % (slug(appointment_type), resource_id, location_id, service_id, crm_id, kwargs.get('state') or False))

    @http.route(['/calendar/<model("calendar.appointment.type"):appointment_type>/info'], type='http', auth="public",
                website=True, sitemap=True)
    def calendar_appointment_form(self, appointment_type, employee_id, date_time, duration, **kwargs):
        partner_data_new = {}
        partner_data = {}
        if request.env.user.partner_id != request.env.ref('base.public_partner'):
            partner_data = request.env.user.partner_id.read(fields=['name', 'mobile', 'country_id', 'email'])[0]
        if kwargs.get('crm_id') and kwargs.get('crm_id') != 'None' and kwargs.get('crm_id') != 'False' and not request.env.user._is_public() and (request.env.user.has_group('sales_team.group_sale_manager') or request.env.user.has_group('sales_team.group_sale_salesman')):
            crm_object = request.env['crm.lead'].search([('id', '=', int(kwargs.get('crm_id')))])
            if crm_object.partner_id:
                partner_data_new = crm_object.partner_id.read(fields=['name', 'mobile', 'country_id', 'email'])[0]
        day_name = format_datetime(datetime.strptime(date_time, dtf), 'EEE', locale=get_lang(request.env).code)
        date_formated = format_datetime(datetime.strptime(date_time, dtf), locale=get_lang(request.env).code)
        product_id = int(kwargs.get('service_id')) if kwargs.get('service_id') and kwargs.get('service_id') != 'None' else False
        Product = request.env['product.product'].sudo().search([('id', '=', product_id)])
        location_id = int(kwargs.get('location_id')) if kwargs.get('location_id') and kwargs.get('location_id') != 'None' else False
        Location = request.env['medical.locations'].sudo().search([('id', '=', location_id)])
        resource_id = int(kwargs.get('resource_id')) if kwargs.get('resource_id') and kwargs.get('resource_id') != 'None' else False
        Resource = request.env['medical.resources'].sudo().search([('id', '=', resource_id)])
        return request.render("appointment.appointment_form", {
            'crm_id': kwargs.get('crm_id') if kwargs.get('crm_id') and kwargs.get('crm_id') != 'None' and kwargs.get('crm_id') != 'False' else False,
            'partner_data': partner_data_new or partner_data,
            'appointment_type': appointment_type,
            'datetime': date_time,
            'datetime_locale': day_name + ' ' + date_formated,
            'datetime_str': date_time,
            'employee_id': employee_id,
            'countries': request.env['res.country'].search([]),
            'resource_id': resource_id,
            'service_id': product_id,
            'location_id': location_id,
            'lead_id': int(kwargs.get('crm_id')) if kwargs.get('crm_id') and kwargs.get('crm_id') != 'None' and kwargs.get('crm_id') != 'False' else False,
            'resource_name': Resource.name if Resource else '',
            'location_name': Location.name if Location else '',
            'service_name': Product.display_name if Product else '',
            'duration': float(duration),
            'main_object': appointment_type,
            'duration_str': duration,
        })

    @http.route(['/calendar/<model("calendar.appointment.type"):appointment_type>/submit'], type='http', auth="public",
                website=True, methods=["POST"])
    def calendar_appointment_submit(self, appointment_type, datetime_str, duration_str, employee_id, name, phone, email,
                                    **kwargs):
        timezone = request.session['timezone'] or appointment_type.appointment_tz
        tz_session = pytz.timezone(timezone)
        date_start = tz_session.localize(fields.Datetime.from_string(datetime_str)).astimezone(pytz.utc)
        duration = float(duration_str)
        date_end = date_start + relativedelta(hours=duration)
        employee = request.env['hr.employee'].sudo().browse(int(employee_id)).exists()
        if employee not in appointment_type.sudo().employee_ids:
            raise NotFound()
        product_id = int(kwargs.get('product_id')) if kwargs.get('product_id') and kwargs.get('product_id') != 'None' else False
        Product = request.env['product.product'].sudo().search([('id', '=', product_id)])
        appointment_duration = Product.duration_of_service if Product.duration_of_service > 0 else duration
        resource_id = int(kwargs.get('resource_id')) if kwargs.get('resource_id') and kwargs.get('resource_id') != 'None' else False
        Resource = request.env['medical.resources'].sudo().browse(int(resource_id))
        if Resource.id:
            if not Resource.calendar_verify_availability(date_start, date_end):
                return request.redirect('/calendar/%s/appointment?failed=employee' % appointment_type.id)
        date_start = tz_session.localize(fields.Datetime.from_string(datetime_str)).astimezone(pytz.utc)
        date_end = date_start + relativedelta(hours=float(appointment_duration))
        crm_id = int(kwargs.get('crm_id')) if kwargs.get('crm_id') and kwargs.get('crm_id') != 'None' else None
        if Resource.id:
            if not Resource.calendar_verify_availability(date_start, date_end):
                return request.redirect('/calendar/%s/appointment?state=failed-employee&resource_id=%s&location_id=%s&service_id=%s&crm_id=%s' % (appointment_type.id, resource_id, kwargs.get('location_id', None), product_id, crm_id))
        # Also check the user has rights to access crm [in case crm id is added manually in url]
        if crm_id and not request.env.user._is_public() and (
                request.env.user.has_group('sales_team.group_sale_manager') or request.env.user.has_group(
                'sales_team.group_sale_salesman')):
            crm_obj = request.env['crm.lead'].browse(crm_id)
            Partner = crm_obj.partner_id
        else:
            Partner = self._get_customer_partner() or request.env['res.partner'].sudo().search([('email', '=like', email)],
                                                                                           limit=1)
        if Partner:
            if not Partner.calendar_verify_availability(date_start, date_end):
                return request.redirect('/calendar/%s/appointment?state=failed-partner&resource_id=%s&location_id=%s&service_id=%s&crm_id=%s' % (appointment_type.id, resource_id, kwargs.get('location_id', False), product_id, crm_id))
            if not Partner.mobile:
                Partner.write({'mobile': phone})
            if not Partner.email:
                Partner.write({'email': email})
        else:
            Partner = Partner.create({
                'name': name,
                'mobile': Partner._phone_format(phone, country=self._get_customer_country()),
                'email': email,
            })
        description_bits = []
        description = ''
        if phone:
            description_bits.append(_('Mobile: %s', phone))
        if email:
            description_bits.append(_('Email: %s', email))
        for question in appointment_type.question_ids:
            key = 'question_' + str(question.id)
            if question.question_type == 'checkbox':
                answers = question.answer_ids.filtered(lambda x: (key + '_answer_' + str(x.id)) in kwargs)
                if answers:
                    description_bits.append('%s: %s' % (question.name, ', '.join(answers.mapped('name'))))
            elif question.question_type == 'text' and kwargs.get(key):
                answers = [line for line in kwargs[key].split('\n') if line.strip()]
                description_bits.append('%s:<br/>%s' % (question.name, plaintext2html(kwargs.get(key).strip())))
            elif kwargs.get(key):
                description_bits.append('%s: %s' % (question.name, kwargs.get(key).strip()))
        if description_bits:
            description = '<ul>' + ''.join(['<li>%s</li>' % bit for bit in description_bits]) + '</ul>'

        categ_id = request.env.ref('appointment.calendar_event_type_data_online_appointment')
        alarm_ids = appointment_type.reminder_ids and [(6, 0, appointment_type.reminder_ids.ids)] or []
        Employee = request.env['hr.employee'].sudo().browse(int(employee_id))
        partner_ids = list(set([Employee.user_id.partner_id.id] + [Partner.id]))
        location_id = int(kwargs.get('location_id')) if kwargs.get('location_id') and kwargs.get('location_id') != 'None' else False
        stage = request.env['neuromed.calendar.event.stages'].sudo().search([], limit=1)
        event = request.env['calendar.event'].with_context(mail_notify_author=True, allowed_company_ids=employee.user_id.company_ids.ids).sudo().create({
            'name': _('%s with %s', appointment_type.name, name),
            'start': date_start.strftime(dtf),
            'stage_id': stage.id if stage else False,
            'start_date': date_start.strftime(dtf),
            'stop': date_end.strftime(dtf),
            'allday': False,
            'duration': appointment_duration,
            'description': description,
            'alarm_ids': alarm_ids,
            'location': appointment_type.location,
            'partner_ids': [(4, pid, False) for pid in partner_ids],
            'categ_ids': [(4, categ_id.id, False)],
            'appointment_type_id': appointment_type.id,
            'user_id': Employee.user_id.id,
            'resource_id': resource_id,
            'service_id': product_id,
            'location_id': location_id,
            'lead_id': crm_id,
            'opportunity_id': crm_id,
        })
        event.attendee_ids.write({'state': 'accepted'})
        return request.redirect(
            '/calendar/view/%s?partner_id=%s&%s' % (event.access_token, Partner.id, keep_query('*', state='new')))

    @http.route(['/calendar/<int:appointment_type_id>/update_available_slots'], type="json", auth="public",
                website=True)
    def calendar_appointment_update_available_slots(self, appointment_type_id, employee_id=None, timezone=None,
                                                    **kwargs):
        """
            Route called when the employee or the timezone is modified to adapt the possible slots accordingly
        """
        medical_params = {
            'resource_id': kwargs.get('resource_id', False),
            'location_id': kwargs.get('location_id', False),
            'service_id': kwargs.get('service_id', False),
            'crm_id': kwargs.get('crm_id') if kwargs.get('crm_id') or kwargs.get('crm_id') != 'None' else 0
        }
        appointment_type = request.env['calendar.appointment.type'].browse(int(appointment_type_id))
        request.session['timezone'] = timezone or appointment_type.appointment_tz
        employee = request.env['hr.employee'].sudo().browse(int(employee_id)) if employee_id else None
        slots = appointment_type.sudo().with_context(medical_params=medical_params)._get_appointment_slots(request.session['timezone'], employee)
        return request.env.ref('appointment.appointment_calendar')._render({
            'appointment_type': appointment_type,
            'slots': slots,
        })

    @http.route([
        '/calendar/cancel/<string:access_token>',
        '/calendar/<string:access_token>/cancel'
    ], type='http', auth="public", website=True)
    def calendar_appointment_cancel(self, access_token, partner_id, **kwargs):
        event = request.env['calendar.event'].sudo().search([('access_token', '=', access_token)], limit=1)
        appointment_type = event.appointment_type_id
        if not event:
            return request.not_found()
        if fields.Datetime.from_string(
                event.allday and event.start_date or event.start) < datetime.now() + relativedelta(
                hours=event.appointment_type_id.min_cancellation_hours):
            return request.redirect('/calendar/view/' + access_token + '?state=no-cancel&partner_id=%s' % partner_id)
        event.sudo().action_cancel_meeting([int(partner_id)])
        return request.redirect('/calendar/%s/appointment?state=cancel&resource_id=%s&location_id=%s&service_id=%s&crm_id=%s&state=cancel' % (slug(appointment_type), event.resource_id.id or None, event.location_id.id or None, event.service_id.id or None, event.opportunity_id.id or None))


    @http.route(['/calendar/get_all'], type='json', auth="public", methods=['POST'], website=True)
    def get_all(self, type_id, **kwargs):
        result = request.env['calendar.appointment.type'].get_slot_resources_locations(type_id)
        return result

    @http.route(['/calendar/get_locations_services_by_resource'], type='json', auth="public", methods=['POST'], website=True)
    def get_locations_services_by_resource(self, type_id, res_id, **kwargs):
        result = request.env['calendar.appointment.type'].get_locations_services_by_resource(type_id, res_id)
        return result

    @http.route(['/calendar/get_resources_services_by_location'], type='json', auth="public", methods=['POST'], website=True)
    def get_resources_services_by_location(self, type_id, location_id, **kwargs):
        result = request.env['calendar.appointment.type'].get_resources_services_by_location(type_id, location_id)
        return result

    @http.route(['/calendar/get_resources_locations_by_service'], type='json', auth="public", methods=['POST'], website=True)
    def get_resources_locations_by_service(self, type_id, service_id, **kwargs):
        result = request.env['calendar.appointment.type'].get_resources_locations_by_service(type_id, service_id)
        return result

    @http.route(['/calendar/get_accepting_reservation'], type='json', auth="public", methods=['POST'], website=True)
    def get_accepting_reservation(self, type_id, **kwargs):
        result = request.env['calendar.appointment.type'].get_accepting_reservation(type_id)
        return result
