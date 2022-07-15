# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AnalyticProductConfiguration(models.Model):
    _name = 'analytic.product.configuration'
    _description ='Analytic Product Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'product_id'

    account_id = fields.Many2one('account.analytic.account', string='Analytic Account', tracking=True)
    product_id = fields.Many2one('product.product', string='Product', tracking=True)
    commission_condition = fields.Selection([('amount', 'Based On Quantity'), ('percentage', 'Based On Price')],
                                            string='Commission Type', tracking=True)
    invoice_type = fields.Selection([('cash', 'Cash'), ('insurance', 'Insurance')], string='Invoice Type')
    invoice_sub_type = fields.Selection([
        ('internal', 'Internal'),
        ('portable', 'Portable'),
        ('os', 'OS'),
        ('insurance', 'Insurance')
    ], string="Invoice Sub Type")
    location_id = fields.Many2one(comodel_name='medical.locations', string='Location')
    comm_amount = fields.Float(string='Amount', tracking=True)
    comm_percentage = fields.Float(string='Percentage', tracking=True)

    @api.constrains('invoice_type', 'invoice_sub_type')
    def _validate_invoice_sub_type(self):
        for record in self:
            if record.invoice_type == "cash" and not record.invoice_sub_type in ['internal', 'portable']:
                raise ValidationError(
                    ("For cash invoice type, sub type can be internal or portable"))
            if record.invoice_type == "insurance" and not record.invoice_sub_type in ['os', 'insurance']:
                raise ValidationError(
                    ("For insurance invoice type, sub type can be os or insurance"))
