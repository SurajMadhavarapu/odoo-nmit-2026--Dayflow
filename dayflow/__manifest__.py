# -*- coding: utf-8 -*-
{
    'name': 'Dayflow - Human Resource Management System',
    'version': '16.0.1.0.0',
    'summary': 'Every workday, perfectly aligned.',
    'description': """
        Dayflow HRMS — Odoo × NMIT Bangalore Hackathon 2026.
        Core HR module covering employee management, attendance tracking,
        leave management, payroll visibility, and full audit trail.
    """,
    'author': 'Mani (HR Core) | Suraj (Arch) | Kunam (Attendance/Leave UI) | Harshith (Dashboard)',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',       # chatter / messaging on records
        'hr',         # extends hr.employee
    ],
    'data': [
        # Security — always load first
        'security/security.xml',
        'security/ir.model.access.csv',

        # Views
        'views/employee_views.xml',
        'views/attendance_views.xml',
        'views/leave_views.xml',
        'views/payroll_views.xml',
        'views/audit_log_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
