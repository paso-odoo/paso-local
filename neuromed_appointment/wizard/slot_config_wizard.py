# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import fields, models, api

class ModelName(models.TransientModel):
    _name = 'slot.config.wizard'
    _description = 'Slot config'

    resource_id = fields.Many2one(
        comodel_name='medical.resources', string='Resource',
    )
    product_id = fields.Many2one(
        comodel_name='product.product', string='Service',
    )
    location_id = fields.Many2one(
        comodel_name='medical.locations', string='Location',
    )
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    duration = fields.Float(string='Duration')
    start_hour = fields.Float(string='From Hour (0:00 - 24:00)')
    end_hour = fields.Float(string='To Hour (0:00 - 24:00)')
    break_time = fields.Float(string='Break time', default=0)
    limit_per_day = fields.Integer(default=0)
    monday = fields.Boolean('Monday')
    tuesday = fields.Boolean('Tuesday')
    wednesday = fields.Boolean('Wednesday')
    thursday = fields.Boolean('Thursday')
    friday = fields.Boolean('Friday')
    saturday = fields.Boolean('Saturday')
    sunday = fields.Boolean('Sunday')

    exclude_date_ids = fields.One2many(
        comodel_name='medical.resource.exclude.dates',
        inverse_name='resource_id',
        string='Exclude Dates', related='resource_id.exclude_date_ids'
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.duration = self.product_id.duration_of_service

    def daterange(self, date_from, date_to):
        for n in range(int((date_to - date_from).days)):
            yield date_from + timedelta(n)

    def generate_slots(self):
        active_model = self.env['calendar.appointment.type'].browse(self._context.get('active_ids'))
        duration = self.duration
        weekday = []
        if self.monday: weekday.append(1)
        if self.tuesday: weekday.append(2)
        if self.wednesday: weekday.append(3)
        if self.thursday: weekday.append(4)
        if self.friday: weekday.append(5)
        if self.saturday: weekday.append(6)
        if self.sunday: weekday.append(7)
        if duration <= 0.00:
            duration = self.product_id.duration_of_service

        data_slots = []
        for day in weekday:
            start_hour = self.start_hour
            end_hour = self.end_hour
            if self.limit_per_day > 0:
                for i in range(0, self.limit_per_day):
                    end_hour = start_hour + self.duration
                    if end_hour <= self.end_hour:
                        data_slots.append(
                            (0, 0,
                                {'weekday': str(day),
                                    'resource_id': self.resource_id.id,
                                    'product_id': self.product_id.id,
                                    'location_id': self.location_id.id,
                                    'date_from': self.date_from,
                                    'date_to': self.date_to,
                                    'neuromed_duration': self.product_id.duration_of_service if self.product_id.duration_of_service > 0 else self.duration,
                                    'start_hour': start_hour,
                                    'end_hour': end_hour,
                                }
                            )
                        )
                        start_hour += (duration + self.break_time)
            elif self.limit_per_day == 0:
                while start_hour < 24 and end_hour <= self.end_hour:
                    end_hour = start_hour + self.duration
                    if end_hour <= self.end_hour:
                        data_slots.append(
                            (0, 0,
                                {'weekday': str(day),
                                  'resource_id': self.resource_id.id,
                                  'product_id': self.product_id.id,
                                  'location_id': self.location_id.id,
                                  'date_from': self.date_from,
                                  'date_to': self.date_to,
                                  'neuromed_duration': self.product_id.duration_of_service if self.product_id.duration_of_service > 0 else self.duration,
                                  'start_hour': start_hour,
                                  'end_hour': end_hour,
                                }
                            )
                        )
                        start_hour += (duration + self.break_time)
        if data_slots:
            active_model.write({'slot_ids': data_slots})
