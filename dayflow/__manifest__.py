# -*- coding: utf-8 -*-
{
    'name': 'Dayflow - Human Resource Management System',
    'version': '16.0.1.0.0',
    'summary': 'Every workday, perfectly aligned.',
    'description': """
        Dayflow HRMS — Odoo × NMIT Bangalore Hackathon 2026.

        Core HR module covering:
          - Employee profile management (extends hr.employee)
          - Attendance tracking with check-in/check-out
          - Leave request and approval workflow
          - Payroll / salary structure (read-only for employees)
          - HR Audit trail for salary and leave changes

        Team:
          Mani     — Employee, Payroll, Security, Audit (this module)
          Kunam    — Attendance & Leave workflow/UI
          Harshith — Dashboard, demo, testing
          Suraj    — Architecture, auth, integration
    """,
    'author': 'Dayflow Team — Odoo × NMIT Hackathon 2026',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',   # chatter / messaging / tracking on records
        'hr',     # extends hr.employee
    ],
    'data': [
        # Security must be loaded first — groups needed before views
        'security/security.xml',
        'security/ir.model.access.csv',

        # Views — Employee & Payroll (Mani owns)
        'views/employee_views.xml',
        'views/payroll_views.xml',
        'views/audit_log_views.xml',

        # Views — Attendance & Leave (Kunam owns; stubs provided)
        'views/attendance_views.xml',
        'views/leave_views.xml',

        # Menu (integrates all sections)
        'views/menu_views.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
