# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Shiprocket Shipping",
    'description': "Send your parcels through shiprocket and track them online",
    'category': 'Inventory/Delivery',
    'sequence': 316,
    'version': '1.0',
    'application': True,
    'depends': ['delivery', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking.xml',
        'wizard/channel_view.xml',
        'wizard/service_view.xml',
    ],
    'license': 'OEEL-1',
}
