# -*- coding: utf-8 -*-
{
    'name': 'Dayflow HRMS',
    'summary': 'Human Resource Management System for Dayflow',
    'description': """
Dayflow HRMS Module
===================
Human Resource Management System covering Employee Management,
Attendance, Leave, Payroll, and Dashboards.

Team:
  Suraj    — Architecture, authentication, integration (auth controller, res_users extension)
  Mani     — Employee profile, attendance, leave, payroll, audit trail, security
  Kunam    — Attendance & leave workflow UI
  Harshith — Dashboards, UX, demo presentation
    """,
    'author': 'Dayflow Hackathon Team',
    'website': 'https://github.com/SurajMadhavarapu/odoo-nmit-2026--Dayflow',
    'category': 'Human Resources',
    'version': '17.0.1.0.0',
    'depends': [
        'base',
        'mail',           # chatter / tracking on leave, payroll
        'hr',             # hr.employee base model
    ],
    'data': [
        # ── Security (load first — groups must exist before views reference them) ──
        'security/hr_security.xml',
        'security/ir.model.access.csv',

        # ── Employee & Payroll views (Mani) ──
        'views/employee_views.xml',
        'views/payroll_views.xml',
        'views/audit_log_views.xml',

        # ── Attendance & Leave views (stubs for Kunam to extend) ──
        'views/attendance_views.xml',
        'views/leave_views.xml',

        # ── Top-level menus ──
        'views/menu_views.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
