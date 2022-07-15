# -*- coding: utf-8 -*-
{
    'name': "UAnalyst Analytic Items Report",

    'summary': """Analytic report & comm
       """,

    'description': """
        Long description of module's purpose
    """,

    'author': "UAnalyst Khaled salah",
    'website': "http://www.UAnalyst.com",

    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'analytic', 'neuromed_appointment'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/analytic_product_configuration_views.xml',
        'views/account_analytic_line_views.xml',
        'views/views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
