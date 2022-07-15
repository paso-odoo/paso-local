# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class CrmLead(models.Model):
    _name = "crm.lead"
    _inherit = ["crm.lead", "website.seo.metadata", "website.published.mixin"]

    appointment_type_id = fields.Many2one(
        comodel_name='nueromed.appointment.type', string='Call Type')
    is_published = fields.Boolean(
        string="Application", default=False, readonly=True, copy=False)
    is_reservation = fields.Boolean(
        related='appointment_type_id.is_reservation',
        help="This is used to enable appointment button on CRM lead when selected")

    def _compute_website_url(self):
        super(CrmLead, self)._compute_website_url()
        for appointment_type in self:
            if self.appointment_type.id:
                appointment_type.website_url = '/calendar'

    def action_open_appointment_view(self):
        return {
            'type': 'ir.actions.act_url',
            'crm_id': self.id,
            'url': "/calendar?crm_lead=%s" % self.id,
            'target': 'new',
        }

    def _compute_meeting_count(self):
        super()._compute_meeting_count()
        if self.ids:
            meeting_data = self.env['calendar.event'].sudo().read_group([
                ('lead_id', 'in', self.ids)
            ], ['lead_id'], ['lead_id'])
            mapped_data = {m['lead_id'][0]: m['lead_id_count'] for m in meeting_data}
        else:
            mapped_data = dict()
        for lead in self:
            lead.meeting_count = mapped_data.get(lead.id, 0)

    def action_schedule_meeting(self):
        """ Open meeting's calendar view to schedule meeting on current opportunity.
            :return dict: dictionary value for created Meeting view
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        partner_ids = self.env.user.partner_id.ids
        if self.partner_id:
            partner_ids.append(self.partner_id.id)

        action['domain'] = [
            ('lead_id', '=', self.id),
        ]
        action['context'] = {
            'default_opportunity_id': self.id if self.type == 'opportunity' else False,
            'default_partner_id': self.partner_id.id,
            'default_partner_ids': partner_ids,
            'default_team_id': self.team_id.id,
            'default_name': self.name,
        }
        return action
