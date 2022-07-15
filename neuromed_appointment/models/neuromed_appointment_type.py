# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class NueromedAppointmentType(models.Model):
    _name = "nueromed.appointment.type"
    _description = "Appointment Type"

    name = fields.Char("Name")
    is_reservation = fields.Boolean(
        string="Reservation",
        help="This is used to enable appointment button on \
            CRM lead when selected")
