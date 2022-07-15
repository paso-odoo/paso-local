# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class MedicalResourceTypes(models.Model):
    _name = 'medical.resource.types'
    _description = 'Resource Types'
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)


class MedicalResourceExcludeDates(models.Model):
    _name = 'medical.resource.exclude.dates'
    _description = 'Resource Exclude Dates'

    resource_id = fields.Many2one(
        comodel_name='medical.resources',
        string='Resource'
    )
    date_from = fields.Date(string='From', default=fields.Date.today, required=True)
    date_to = fields.Date(string='To', default=fields.Date.today, required=True)


class MedicalResources(models.Model):
    _name = 'medical.resources'
    _description = 'Resources'
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    description = fields.Text()
    working_hours_id = fields.Many2one(
        comodel_name='resource.calendar',
        string='Working Hours'
    )
    type_id = fields.Many2one(
        comodel_name='medical.resource.types',
        string='Type',
    )
    exclude_date_ids = fields.One2many(
        comodel_name='medical.resource.exclude.dates',
        inverse_name='resource_id',
        string='Exclude Dates',
    )

    def calendar_verify_availability(self, date_start, date_end):
        """ verify availability of the resource between 2 datetimes on their calendar
        """
        if bool(self.env['calendar.event'].search_count([
            ('resource_id', 'in', self.ids),
            '|', '&', ('start', '<', fields.Datetime.to_string(date_end)),
                      ('stop', '>', fields.Datetime.to_string(date_start)),
                 '&', ('allday', '=', True),
                      '|', ('start_date', '=', fields.Date.to_string(date_end)),
                           ('start_date', '=', fields.Date.to_string(date_start))])):
            return False
        return True
