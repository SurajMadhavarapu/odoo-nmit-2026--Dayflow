# -*- coding: utf-8 -*-
"""
Dayflow - hr.employee extension
Suraj : employee_code field + SQL uniqueness constraint
Mani  : all other df_* profile fields, back-references, validation, audit trail

CANONICAL EMPLOYEE ID: employee_code  (do NOT use df_employee_id)
"""
import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ------------------------------------------------------------------
    # CANONICAL EMPLOYEE ID — Suraj owns this field, do not rename
    # ------------------------------------------------------------------
    employee_code = fields.Char(
        string='Employee ID',
        copy=False,
        index=True,
        help="Canonical Dayflow Employee ID",
    )

    _sql_constraints = [
        ('employee_code_uniq', 'unique(employee_code)', 'The Employee ID must be unique across all employees!'),
    ]

    # ------------------------------------------------------------------
    # Employment details — Mani
    # ------------------------------------------------------------------
    df_employment_type = fields.Selection(
        selection=[
            ('full_time', 'Full-Time'),
            ('part_time', 'Part-Time'),
            ('contract',  'Contract'),
            ('intern',    'Intern'),
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
        help='Used for UI routing. Security is enforced via Odoo groups, not this field.',
    )

    # ------------------------------------------------------------------
    # Personal self-service fields (employee-editable)
    # ------------------------------------------------------------------
    df_phone = fields.Char(
        string='Personal Phone',
    )
    df_address = fields.Text(
        string='Home Address',
    )
    df_date_of_birth = fields.Date(
        string='Date of Birth',
        groups='dayflow_hr.group_dayflow_hr_admin',
    )
    df_gender = fields.Selection(
        selection=[
            ('male',              'Male'),
            ('female',            'Female'),
            ('other',             'Other'),
            ('prefer_not_to_say', 'Prefer not to say'),
        ],
        string='Gender',
        groups='dayflow_hr.group_dayflow_hr_admin',
    )
    df_emergency_contact = fields.Char(string='Emergency Contact Name')
    df_emergency_phone   = fields.Char(string='Emergency Contact Phone')

    # ------------------------------------------------------------------
    # Archive flag
    # ------------------------------------------------------------------
    df_active = fields.Boolean(
        string='Dayflow Active',
        default=True,
        help='Uncheck to archive. Historical records are preserved.',
    )

    # ------------------------------------------------------------------
    # Back-references (for Harshith's dashboard and Kunam's views)
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
    # Computed counts (stat buttons for dashboard)
    # ------------------------------------------------------------------
    df_attendance_count = fields.Integer(
        string='Attendance',
        compute='_compute_df_counts',
    )
    df_leave_count = fields.Integer(
        string='Leaves',
        compute='_compute_df_counts',
    )

    def _compute_df_counts(self):
        for rec in self:
            rec.df_attendance_count = len(rec.df_attendance_ids)
            rec.df_leave_count = len(rec.df_leave_ids)

    # ------------------------------------------------------------------
    # Stat button actions
    # ------------------------------------------------------------------
    def action_open_attendance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attendance',
            'res_model': 'dayflow.attendance',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_open_leaves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leave Requests',
            'res_model': 'dayflow.leave.request',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('employee_code')
    def _check_employee_code_format(self):
        pattern = re.compile(r'^[A-Za-z0-9_\-]+$')
        for rec in self:
            if rec.employee_code and not pattern.match(rec.employee_code):
                raise ValidationError(
                    _('Employee ID "%s" is invalid. Use only letters, digits, hyphens, or underscores.')
                    % rec.employee_code
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
        audited = {
            'employee_code', 'work_email', 'job_id', 'department_id',
            'df_employment_type', 'df_role', 'df_active',
        }
        for rec in self:
            for fname in audited & set(vals.keys()):
                old = rec[fname]
                if isinstance(old, models.BaseModel):
                    old = old.display_name
                self.env['dayflow.audit.log'].sudo().create({
                    'user_id':     self.env.uid,
                    'model_name':  self._name,
                    'record_id':   rec.id,
                    'record_name': rec.display_name,
                    'action':      'update',
                    'field_name':  fname,
                    'old_value':   str(old) if old else '',
                    'new_value':   str(vals[fname]),
                })
        return super().write(vals)
