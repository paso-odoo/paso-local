# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_type = fields.Selection(
        [('cash', 'Cash'),
         ('insurance', 'Insurance')], 'Invoice Type')
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

    def action_register_payment(self):
        res = super().action_register_payment()
        res['context']['default_branch_location_id'] = self.branch_location_id.id
        return res
