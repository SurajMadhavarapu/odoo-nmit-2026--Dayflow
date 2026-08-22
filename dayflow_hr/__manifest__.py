# -*- coding: utf-8 -*-
{
    'name': 'Dayflow HRMS',
    'summary': 'Human Resource Management System for Dayflow',
    'description': """
Dayflow HRMS Module
===================
Human Resource Management System covering Employee Management, Attendance, Leave, Payroll, and Dashboards.
    """,
    'author': 'Dayflow Hackathon Team',
    'website': 'https://github.com/SurajMadhavarapu/odoo-nmit-2026--Dayflow',
    'category': 'Human Resources',
    'version': '17.0.1.0.0',
    'depends': [
        'base',
        'hr',
        'hr_attendance',
        'hr_holidays',
    ],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
