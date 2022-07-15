# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class MedicalResourceExcludeDates(models.Model):
    _name = 'medical.location.exclude.dates'
    _description = 'Resource Exclude Dates'

    location_id = fields.Many2one(
        comodel_name='medical.locations',
        string='Location'
    )
    date_from = fields.Date(string='From', default=fields.Date.today, required=True)
    date_to = fields.Date(string='To', default=fields.Date.today, required=True)


class MedicalLocations(models.Model):
    _name = 'medical.locations'
    _description = 'Locations'
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    address = fields.Text()
    city = fields.Char()
    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country',
    )
    state_id = fields.Many2one(
        comodel_name='res.country.state', string='State',
        domain="[('country_id', '=', country_id)]"
    )
    phone = fields.Char()
    email = fields.Char()
    website = fields.Char('Website Link')
    exclude_date_ids = fields.One2many(
        comodel_name='medical.location.exclude.dates',
        inverse_name='location_id',
        string='Exclude Dates',
    )
