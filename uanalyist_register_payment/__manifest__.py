# -*- coding: utf-8 -*-
{
    'name': "Uanalyist Register Payment",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Customizations/Register Payment',
    'version': '0.1',

    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'wizard/views.xml',
    ],

    'application': True,
}
