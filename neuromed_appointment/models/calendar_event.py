# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class NeuromedCalendarEventStages(models.Model):
    _name = 'neuromed.calendar.event.stages'

    name = fields.Char('Stages')
    is_quotation = fields.Boolean("Enable Quotation Button")
    is_noshow = fields.Boolean("Is this No Show stage")


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    stage_id = fields.Many2one(comodel_name='neuromed.calendar.event.stages')
    is_quotation = fields.Boolean(related='stage_id.is_quotation')

    quotation_count = fields.Integer(
        compute='_compute_quotation_count',string='Quotation Count')
    order_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='cal_event_id', string='Orders')
    lead_id = fields.Many2one(comodel_name='crm.lead')
    service_id = fields.Many2one(comodel_name='product.product')
    resource_id = fields.Many2one(comodel_name='medical.resources')
    location_id = fields.Many2one(comodel_name='medical.locations', string='Location of appointment')

    def action_sale_quotations_new(self):
        attendee = self._get_online_attendee()
        sale_order = self.env['sale.order'].create({
            'partner_id': attendee.partner_id.id,
            'company_id': self.env.company.id,
            'cal_event_id': self.id,
            'opportunity_id': self.lead_id.id,
            'order_line': [(0, 0, {
                'product_id': self.service_id.id,
                'name': self.service_id.name,
                'product_uom_qty': 1,
            })],
            'resource_id': self.resource_id.id,
            'branch_location_id': self.location_id.id,
        })
        if sale_order:
            return
        return UserError(_("There is some error."))

    def _get_online_attendee(self):
        # Remove the employees from the attendee
        if len(self.attendee_ids.ids) > 1:
            attendee = self.attendee_ids.filtered(
                lambda ai: ai.partner_id.id not in self.appointment_type_id.employee_ids.mapped("user_partner_id").ids)
        else:
            attendee = self.attendee_ids
        return attendee

    def _compute_quotation_count(self):
        for meeting in self:
            quotation_cnt = 0
            for order in meeting.order_ids:
                if order.state in ('draft', 'sent'):
                    quotation_cnt += 1
            meeting.quotation_count = quotation_cnt


    def action_view_sale_quotation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        attendee = self._get_online_attendee()
        action['context'] = {
            'search_default_partner_id': attendee.partner_id.id,
            'default_partner_id': attendee.partner_id.id,
            'default_cal_event_id': self.id
        }
        action['domain'] = [('cal_event_id', '=', self.id), ('state', 'in', ['draft', 'sent'])]
        quotations = self.mapped('order_ids').filtered(lambda l: l.state in ('draft', 'sent'))
        if len(quotations) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action


    def action_cancel_reschedule(self):
        return {
            'type': 'ir.actions.act_url',
            'url': "/calendar/cancel/%s" % self.access_token ,
            'target': 'new',
        }

    @api.model
    def change_appointment_state(self):
        records = self.search([('start', '<', fields.Date.today())])
        no_show_stage = self.env['neuromed.calendar.event.stages'].search([('is_noshow', '=', True)])
        if no_show_stage and records:
            for record in records:
                if not record.stage_id.is_quotation:
                    record.stage_id = no_show_stage[0]

    def _get_public_fields(self):
        vals = super(CalendarEvent, self)._get_public_fields()
        additional_fields = ['location_id','resource_id','service_id']
        for field in self._fields.keys():
            if field not in vals:
                additional_fields.append(field)
        vals.update(additional_fields)
        return vals
