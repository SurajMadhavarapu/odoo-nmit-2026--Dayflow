# -*- coding: utf-8 -*-
"""
Dayflow - Employee Model
Extends Odoo's hr.employee with all Dayflow-specific HR fields.

INTEGRATION CONTRACT (do not rename without notifying Suraj):
  _inherit : 'hr.employee'
  New fields added on hr.employee:
    df_employee_id         Char   unique employee ID (e.g. DF-001)
    df_phone               Char   personal phone (employee-editable)
    df_address             Text   home address   (employee-editable)
    df_employment_type     Selection  full_time | part_time | contract | intern
    df_joining_date        Date
    df_date_of_birth       Date
    df_gender              Selection  male | female | other | prefer_not_to_say
    df_emergency_contact   Char
    df_emergency_phone     Char
    df_role                Selection  employee | hr_admin
    df_active              Boolean    Dayflow archive flag (separate from hr active)

  Relational back-references (for dashboard widgets):
    df_attendance_ids      One2many -> dayflow.attendance
    df_leave_ids           One2many -> dayflow.leave.request
    df_payroll_ids         One2many -> dayflow.payroll
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class DayflowEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Dayflow Employee Extension'

    # ------------------------------------------------------------------
    # Dayflow Identity
    # ------------------------------------------------------------------
    df_employee_id = fields.Char(
        string='Employee ID',
        required=True,
        copy=False,
        index=True,
        help='Unique Dayflow employee identifier, e.g. DF-001',
    )
    df_employment_type = fields.Selection(
        selection=[
            ('full_time', 'Full-Time'),
            ('part_time', 'Part-Time'),
            ('contract', 'Contract'),
            ('intern', 'Intern'),
        ],
        string='Employment Type',
        default='full_time',
    )
    df_joining_date = fields.Date(
        string='Date of Joining',
    )
    df_role = fields.Selection(
        selection=[
            ('employee', 'Employee'),
            ('hr_admin', 'HR / Admin'),
        ],
        string='Dayflow Role',
        default='employee',
        help='Used for role-based UI routing. Security is enforced via Odoo groups.',
    )

    # ------------------------------------------------------------------
    # Personal (employee-editable self-service fields)
    # ------------------------------------------------------------------
    df_phone = fields.Char(
        string='Personal Phone',
    )
    df_address = fields.Text(
        string='Home Address',
    )
    df_date_of_birth = fields.Date(
        string='Date of Birth',
        groups='dayflow.group_dayflow_hr_admin',
    )
    df_gender = fields.Selection(
        selection=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say'),
        ],
        string='Gender',
        groups='dayflow.group_dayflow_hr_admin',
    )
    df_emergency_contact = fields.Char(
        string='Emergency Contact Name',
    )
    df_emergency_phone = fields.Char(
        string='Emergency Contact Phone',
    )

    # ------------------------------------------------------------------
    # Archive / active
    # ------------------------------------------------------------------
    df_active = fields.Boolean(
        string='Dayflow Active',
        default=True,
        help='Uncheck to archive. Historical records are preserved.',
    )

    # ------------------------------------------------------------------
    # Back-references (consumed by Kunam and Harshith)
    # ------------------------------------------------------------------
    df_attendance_ids = fields.One2many(
        comodel_name='dayflow.attendance',
        inverse_name='employee_id',
        string='Attendance Records',
    )
    df_leave_ids = fields.One2many(
        comodel_name='dayflow.leave.request',
        inverse_name='employee_id',
        string='Leave Requests',
    )
    df_payroll_ids = fields.One2many(
        comodel_name='dayflow.payroll',
        inverse_name='employee_id',
        string='Payroll / Salary',
    )

    # ------------------------------------------------------------------
    # Computed counts (for dashboard stat buttons)
    # ------------------------------------------------------------------
    df_attendance_count = fields.Integer(
        string='Attendance Count',
        compute='_compute_df_counts',
    )
    df_leave_count = fields.Integer(
        string='Leave Count',
        compute='_compute_df_counts',
    )

    def _compute_df_counts(self):
        for rec in self:
            rec.df_attendance_count = len(rec.df_attendance_ids)
            rec.df_leave_count = len(rec.df_leave_ids)

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        (
            'df_employee_id_uniq',
            'UNIQUE(df_employee_id)',
            'Employee ID must be unique across the organisation.',
        ),
    ]

    # ------------------------------------------------------------------
    # API constraints
    # ------------------------------------------------------------------
    @api.constrains('df_employee_id')
    def _check_df_employee_id_format(self):
        pattern = re.compile(r'^[A-Za-z0-9_\-]+$')
        for rec in self:
            if rec.df_employee_id and not pattern.match(rec.df_employee_id):
                raise ValidationError(
                    _('Employee ID "%s" is invalid. Use only letters, digits, hyphens, or underscores.')
                    % rec.df_employee_id
                )

    @api.constrains('work_email')
    def _check_work_email_format(self):
        pattern = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
        for rec in self:
            if rec.work_email and not pattern.match(rec.work_email):
                raise ValidationError(
                    _('Work email "%s" does not look valid.') % rec.work_email
                )

    # ------------------------------------------------------------------
    # Audit trail on important field changes
    # ------------------------------------------------------------------
    def write(self, vals):
        audited = {'df_employee_id', 'work_email', 'job_id', 'department_id',
                   'df_employment_type', 'df_role', 'df_active'}
        for rec in self:
            for fname in audited & set(vals.keys()):
                old = rec[fname]
                if isinstance(old, models.BaseModel):
                    old = old.display_name
                self.env['dayflow.audit.log'].sudo().create({
                    'user_id': self.env.uid,
                    'model_name': self._name,
                    'record_id': rec.id,
                    'record_name': rec.display_name,
                    'action': 'update',
                    'field_name': fname,
                    'old_value': str(old) if old else '',
                    'new_value': str(vals[fname]),
                })
        return super().write(vals)
