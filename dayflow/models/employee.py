# -*- coding: utf-8 -*-
"""
Dayflow – Employee Model
Owner: Mani (HR Core)

Extends Odoo's hr.employee with Dayflow-specific fields.
This is the CENTRAL entity — all attendance, leave, and payroll records
reference hr.employee via Many2one.

INTEGRATION CONTRACT (stable — do not rename without telling Suraj):
  Base model : hr.employee
  Canonical Employee ID field : df_employee_id   (Char, unique)
  Phone field      : df_phone
  Address field    : df_address
  Documents        : df_document_ids  → dayflow.employee.document
  Attendance       : df_attendance_ids → dayflow.attendance  (Kunam owns)
  Leave            : df_leave_ids     → dayflow.leave.request (Kunam owns)
  Payroll          : df_payroll_ids   → dayflow.payroll      (Mani owns)
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class DayflowEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Dayflow Employee (extended)'

    # ------------------------------------------------------------------
    # Canonical Dayflow Employee ID
    # ------------------------------------------------------------------
    df_employee_id = fields.Char(
        string='Dayflow Employee ID',
        required=True,
        copy=False,
        index=True,
        help='Unique Dayflow employee code, e.g. DF-001. '
             'Used as the business-facing identifier across all modules.',
    )

    # ------------------------------------------------------------------
    # Personal / Contact — editable by employee (address, phone, picture)
    # hr.employee already provides image_1920 for profile picture.
    # ------------------------------------------------------------------
    df_phone = fields.Char(
        string='Phone Number',
        help='Employee editable. Personal mobile/contact number.',
    )
    df_address = fields.Text(
        string='Address',
        help='Employee editable. Residential address.',
    )
    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')

    # ------------------------------------------------------------------
    # Job / Employment information
    # hr.employee already has: job_id, job_title, department_id,
    #   work_email, work_phone, company_id, parent_id, coach_id
    # We add what is missing for Dayflow:
    # ------------------------------------------------------------------
    date_joined = fields.Date(
        string='Date Joined',
        help='Date the employee joined the organisation.',
    )
    employment_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
    ], string='Employment Type', default='full_time')

    # ------------------------------------------------------------------
    # Reverse relations — owned by other modules, exposed here for
    # the employee record view and dashboards.
    # Attendance + Leave are Kunam's; Payroll is Mani's.
    # ------------------------------------------------------------------
    df_attendance_ids = fields.One2many(
        comodel_name='dayflow.attendance',
        inverse_name='employee_id',
        string='Attendance Records',
        readonly=True,
    )
    df_leave_ids = fields.One2many(
        comodel_name='dayflow.leave.request',
        inverse_name='employee_id',
        string='Leave Requests',
        readonly=True,
    )
    df_payroll_ids = fields.One2many(
        comodel_name='dayflow.payroll',
        inverse_name='employee_id',
        string='Payroll Records',
        readonly=True,
    )
    df_document_ids = fields.One2many(
        comodel_name='dayflow.employee.document',
        inverse_name='employee_id',
        string='Documents',
    )

    # ------------------------------------------------------------------
    # Computed counts — useful for smart buttons / dashboards
    # ------------------------------------------------------------------
    df_attendance_count = fields.Integer(
        string='Attendance Records',
        compute='_compute_df_attendance_count',
    )
    df_leave_count = fields.Integer(
        string='Leave Requests',
        compute='_compute_df_leave_count',
    )

    @api.depends('df_attendance_ids')
    def _compute_df_attendance_count(self):
        for emp in self:
            emp.df_attendance_count = len(emp.df_attendance_ids)

    @api.depends('df_leave_ids')
    def _compute_df_leave_count(self):
        for emp in self:
            emp.df_leave_count = len(emp.df_leave_ids)

    # ------------------------------------------------------------------
    # SQL constraint — Dayflow Employee ID must be unique
    # ------------------------------------------------------------------
    _sql_constraints = [
        (
            'df_employee_id_unique',
            'UNIQUE(df_employee_id)',
            'Dayflow Employee ID must be unique.',
        ),
    ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('df_phone')
    def _check_df_phone(self):
        for emp in self:
            if emp.df_phone and not re.match(r'^\+?[\d\s\-]{7,15}$', emp.df_phone):
                raise ValidationError(
                    'Phone number "%s" is not valid. '
                    'Use digits, spaces, hyphens, or a leading +.' % emp.df_phone
                )

    @api.constrains('date_joined')
    def _check_date_joined(self):
        from datetime import date
        for emp in self:
            if emp.date_joined and emp.date_joined > date.today():
                raise ValidationError('Date joined cannot be in the future.')


class DayflowEmployeeDocument(models.Model):
    """
    Employee document store.
    Employees can upload/view their own documents.
    HR/Admin can view and manage all documents.
    """
    _name = 'dayflow.employee.document'
    _description = 'Dayflow Employee Document'
    _order = 'employee_id, document_type'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(
        string='Document Name',
        required=True,
    )
    document_type = fields.Selection([
        ('id_proof',      'ID Proof'),
        ('address_proof', 'Address Proof'),
        ('certificate',   'Certificate / Degree'),
        ('contract',      'Employment Contract'),
        ('other',         'Other'),
    ], string='Document Type', required=True)
    file = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    note = fields.Text(string='Note')
    active = fields.Boolean(default=True)
