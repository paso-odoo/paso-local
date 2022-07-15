# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    cal_event_id = fields.Many2one(
        comodel_name='calendar.event', string='Appointment')
    invoice_type = fields.Selection(
        [('cash', 'Cash'), ('insurance', 'Insurance')], 'Invoice Type')
    invoice_sub_type = fields.Selection([
        ('internal', 'Internal'),
        ('portable', 'Portable'),
        ('os', 'OS'),
        ('insurance', 'Insurance')
    ], string="Invoice Sub Type")
    resource_id = fields.Many2one(
        comodel_name='medical.resources', string='Resource')
    branch_location_id = fields.Many2one(
        comodel_name='medical.locations',
        string='Location'
    )

    @api.constrains('invoice_type', 'invoice_sub_type')
    def _validate_invoice_sub_type(self):
        for record in self:
            if record.invoice_type == "cash" and not record.invoice_sub_type in ['internal', 'portable']:
                raise ValidationError(_("For cash invoice type, sub type can be internal or portable"))
            if record.invoice_type == "insurance" and not record.invoice_sub_type in ['os', 'insurance']:
                raise ValidationError(_("For insurance invoice type, sub type can be os or insurance"))

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['invoice_type'] = self.invoice_type
        invoice_vals['invoice_sub_type'] = self.invoice_sub_type
        invoice_vals['resource_id'] = self.resource_id.id
        invoice_vals['branch_location_id'] = self.branch_location_id.id
        return invoice_vals
