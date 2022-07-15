# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
import datetime as dt
from datetime import datetime, timedelta, time
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from odoo.tools.date_utils import end_of
from odoo import api, fields, models


class CalendarAppointmentType(models.Model):
    _inherit = 'calendar.appointment.type'

    is_accepting_reservation = fields.Boolean("Accepting Reservation",
                default=False, help="\
                If checked it will bypass email and phone requirement and make sure the \
                appointment comes from crm only.")


    @api.model
    def get_accepting_reservation(self, type_id):
        if type_id:
            appointment_type = self.sudo().browse(int(type_id))
            return {'state':appointment_type.is_accepting_reservation}


    @api.model
    def get_slot_resources_locations(self, type_id):
        if type_id:
            appointment_type = self.sudo().browse(int(type_id))
            return {
                'resources': appointment_type.sudo().slot_ids.resource_id.name_get(),
                'locations': appointment_type.sudo().slot_ids.location_id.name_get(),
                'services': appointment_type.sudo().slot_ids.product_id.name_get()
            }

    @api.model
    def get_locations_services_by_resource(self, type_id, resource_id):
        appointment_type = self.sudo().browse(int(type_id))
        locations = appointment_type.sudo().slot_ids.filtered(
            lambda si: si.resource_id.id == resource_id).location_id.name_get()
        services = appointment_type.sudo().slot_ids.filtered(
            lambda si: si.resource_id.id == resource_id).product_id.name_get()
        return {'locations': locations, 'services': services}

    @api.model
    def get_resources_services_by_location(self, type_id, location_id):
        appointment_type = self.sudo().browse(int(type_id))
        resources = appointment_type.sudo().slot_ids.filtered(
            lambda si: si.location_id.id == location_id).resource_id.name_get()
        services = appointment_type.sudo().slot_ids.filtered(
            lambda si: si.location_id.id == location_id).product_id.name_get()
        return {'resources': resources, 'services': services}

    @api.model
    def get_resources_locations_by_service(self, type_id, service_id):
        appointment_type = self.sudo().browse(int(type_id))
        resources = appointment_type.sudo().slot_ids.filtered(
            lambda si: si.product_id.id == service_id).resource_id.name_get()
        locations = appointment_type.sudo().slot_ids.filtered(
            lambda si: si.product_id.id == service_id).location_id.name_get()
        return {'resources': resources, 'locations': locations}

    # --------------------------------------
    # Slots Generation
    # --------------------------------------

    def _slots_generate(self, first_day, last_day, timezone, reference_date=None):
        """ Generate all appointment slots (in naive UTC, appointment timezone, and given (visitors) timezone)
            between first_day and last_day (datetimes in appointment timezone)

            :return: [ {'slot': slot_record, <timezone>: (date_start, date_end), ...},
                      ... ]
        """

        medical_params = self._context.get('medical_params', False)
        if not medical_params:
            return super(CalendarAppointmentType, self)._slots_generate(first_day, last_day, timezone, reference_date)

        def append_slot(day, slot):
            if int(round((slot.start_hour % 1) * 60)) == 60:
                slot.start_hour = round(slot.start_hour)
                minutes = 0
            else:
                minutes = int(round((slot.start_hour % 1) * 60))
            local_start = appt_tz.localize(
                datetime.combine(day, time(hour=int(slot.start_hour), minute=minutes)))
            slot_duration = slot.product_id.duration_of_service if slot.product_id.duration_of_service > 0 else slot.neuromed_duration
            local_end = appt_tz.localize(
                datetime.combine(day, time(hour=int(slot.start_hour), minute=minutes)) + relativedelta(hours=slot_duration))
            slots.append({
                self.appointment_tz: (
                    local_start,
                    local_end,
                ),
                timezone: (
                    local_start.astimezone(requested_tz),
                    local_end.astimezone(requested_tz),
                ),
                'UTC': (
                    local_start.astimezone(pytz.UTC).replace(tzinfo=None),
                    local_end.astimezone(pytz.UTC).replace(tzinfo=None),
                ),
                'slot': slot,
                'duration': slot.neuromed_duration or slot.duration,
            })
            local_end += relativedelta(hours=self.appointment_duration)
        appt_tz = pytz.timezone(self.appointment_tz)
        requested_tz = pytz.timezone(timezone)
        resource_id = medical_params.get('resource_id', False)
        location_id = medical_params.get('location_id', False)
        service_id = medical_params.get('service_id', False)
        slots = []
        filtered_slots = self.slot_ids.filtered(
            lambda x: x.resource_id.id == int(resource_id) and x.location_id.id == int(
                location_id) and x.product_id.id == int(service_id))
        for slot in filtered_slots:
            rules = rrule.rruleset()
            if slot.date_from and first_day.date() and slot.date_from > first_day.date():
                first_day = requested_tz.fromutc(datetime.combine(slot.date_from,
                                                                  dt.time.min).astimezone(
                    pytz.UTC).replace(tzinfo=None)).replace(hour=0, minute=0, second=0)
            resource_exclude_dates = slot.resource_id.exclude_date_ids.filtered(
                lambda ed: slot.date_from <= ed.date_from <= slot.date_to and
                           slot.date_from <= ed.date_to <= slot.date_to)
            for red in resource_exclude_dates:
                exc_rule = rrule.rrule(rrule.DAILY,
                                       dtstart=datetime.combine(red.date_from, dt.time.min).astimezone(
                                           pytz.UTC).date(),
                                       until=datetime.combine(red.date_to, dt.time.max).astimezone(
                                           pytz.UTC).date(),
                                       byweekday=int(slot.weekday) - 1)
                rules.exrule(exc_rule)

            location_exclude_dates = slot.location_id.exclude_date_ids.filtered(
                lambda ed: slot.date_from <= ed.date_from <= slot.date_to and
                           slot.date_from <= ed.date_to <= slot.date_to)
            for led in location_exclude_dates:
                exc_rule = rrule.rrule(rrule.DAILY,
                                       dtstart=datetime.combine(led.date_from,
                                                                dt.time.min).astimezone(
                                           pytz.UTC).date(),
                                       until=datetime.combine(led.date_to,
                                                              dt.time.max).astimezone(
                                           pytz.UTC).date(),
                                       byweekday=int(slot.weekday) - 1)
                rules.exrule(exc_rule)

            if slot.start_hour > first_day.hour + first_day.minute / 60.0 and int(slot.weekday) - 1 == first_day.weekday():
                append_slot(first_day.date(), slot)
            if slot.date_to:
                inc_rule = rrule.rrule(rrule.DAILY,
                                       dtstart=first_day.date() + timedelta(days=1),
                                       until=datetime.combine(slot.date_to, datetime.now().time()).astimezone(
                                           pytz.UTC).date(),
                                       byweekday=int(slot.weekday) - 1)

                rules.rrule(inc_rule)
            for day in rules:
                append_slot(day, slot)

        slots = sorted(slots, key=lambda x: x[self.appointment_tz])
        return slots


    def _slots_available(self, slots, first_day, last_day, employee=None):
        """ Fills the slot stucture with an available employee

            :param slots: slots structure generated by _slots_generate
            :param first_day: start datetime in UTC
            :param last_day: end datetime in UTC
            :param employee: if set, only consider this employee
                             if not set, consider all employees assigned to this appointment type
        """
        def is_calendar_available(slot, events, employee):
            """ Returns True if the given slot doesn't collide with given events for the employee
            """
            start_dt = slot['UTC'][0]
            end_dt = slot['UTC'][1]
            event_in_scope = lambda ev: (
                fields.Date.to_date(ev.start) <= fields.Date.to_date(end_dt)
                and fields.Date.to_date(ev.stop) >= fields.Date.to_date(start_dt)
            )

            for ev in events.filtered(event_in_scope):

                if ev.allday:
                    # allday events are considered to take the whole day in the related employee's timezone
                    event_tz = pytz.timezone(ev.event_tz or self.env.user.tz or slot['slot'].appointment_type_id.appointment_tz or 'UTC')
                    ev_start_dt = datetime.combine(fields.Date.from_string(ev.start_date), time.min)
                    ev_stop_dt = datetime.combine(fields.Date.from_string(ev.stop_date), time.max)
                    ev_start_dt = event_tz.localize(ev_start_dt).astimezone(pytz.UTC).replace(tzinfo=None)
                    ev_stop_dt = event_tz.localize(ev_stop_dt).astimezone(pytz.UTC).replace(tzinfo=None)

                    if ev_start_dt < end_dt and ev_stop_dt > start_dt:
                        return False
                elif fields.Datetime.to_datetime(ev.start) < end_dt and fields.Datetime.to_datetime(ev.stop) > start_dt:
                    return False

            return True
        available_employees = [emp.with_context(tz=emp.user_id.tz) for emp in (employee or self.employee_ids)]
        emp = available_employees[0] if available_employees else None
        if emp:
            for slot in slots:
                if slot and slot.get('slot') and slot['slot'].date_from and slot['slot'].date_to:
                    start_date = datetime.combine(slot['slot'].date_from, dt.time.min).astimezone(
                        pytz.UTC).date()
                    end_date = datetime.combine(slot['slot'].date_to, dt.time.max).astimezone(
                        pytz.UTC).date()

                    events = self.env['calendar.event'].search([
                        ('resource_id', '=', slot['slot'].resource_id.id),
                        ('start', '>=', start_date),
                        ('stop', '<=', end_date),
                    ])
                    if is_calendar_available(slot, events, 0):
                        slot['employee_id'] = emp


class CalendarAppointmentSlot(models.Model):
    _inherit = "calendar.appointment.slot"

    resource_id = fields.Many2one(
        comodel_name='medical.resources', string='Resource',
        ondelete='restrict'
    )
    product_id = fields.Many2one(
        comodel_name='product.product', string='Service',
        ondelete='restrict'
    )
    location_id = fields.Many2one(
        comodel_name='medical.locations', string='Location',
        ondelete='restrict'
    )
    date_from = fields.Date(string='From Date', default=lambda self: fields.Date.today())
    date_to = fields.Date(string='To Date', default=lambda self: end_of(fields.Date.today(), 'month'))
    neuromed_duration = fields.Float('Duration', digits=(16, 2), group_operator="avg", readonly=True)

