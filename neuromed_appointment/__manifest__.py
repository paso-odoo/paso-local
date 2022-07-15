# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Neuromed Appointment",

    'summary': """
        Calendar Appointment modification""",

    'description': """
        Calendar Appointment modification
    """,

    'author': 'odooPS',

    'website': 'https://www.odoo.com',
    
    'category': 'Customizations/Online Appointment',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['crm', 'sale_management', 'website_appointment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/calendar_cron.xml',
        'wizard/slot_config_wizard_view.xml',
        'wizard/account_payment_register_view.xml',
        'views/account_move_views.xml',
        'views/medical_locations_views.xml',
        'views/medical_resources_views.xml',
        'views/product_template_views.xml',
        'views/neuromed_appointment_type_views.xml',
        'views/neuromed_calendar_event_stages_views.xml',
        'views/crm_lead_views.xml',
        'views/calendar_appointment_views.xml',
        'views/calendar_event_views.xml',
        'views/sale_order_views.xml',
        'views/website_calendar_templates.xml',
        'views/appointment.xml',
        'views/account_payment_view.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'neuromed_appointment/static/src/js/custom_website_calendar.js',
        ],
    },

    'installable': True,
}
