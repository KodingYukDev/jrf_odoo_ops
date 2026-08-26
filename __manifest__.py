{
    'name': 'JRF - Job Request Form',
    'version': '17.0.1.0.0',
    'summary': 'Cross-department job request, review, acceptance, and PDF printout',
    'category': 'Operations',
    'author': 'KodingYuk',
    'license': 'LGPL-3',
    'depends': ['hr', 'mail'],
    'data': [
        'security/jrf_security.xml',
        'security/ir.model.access.csv',
        'views/jrf_request_views.xml',
        'report/jrf_report.xml',
    ],
    'application': True,
    'installable': True,
}
