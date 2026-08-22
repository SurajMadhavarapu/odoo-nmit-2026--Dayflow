# -*- coding: utf-8 -*-
"""
Dayflow – Employee Model
Extends Odoo's built-in hr.employee to avoid duplication.
Adds Dayflow-specific fields: employee_id (unique code), department/job
info lives on the base model, salary is linked via dayflow.payroll.

Team contract (do NOT rename these without telling Suraj + teammates):
  model      : hr.employee  (extended)
  new fields : df_employee_id, df_phone, df_address, df_documents
  relations  : df_attendance_ids, df_leave_ids, df_payroll_id
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class DayflowEmployee(models.Model):
    _inherit = 'hr.employee'

    # ------------------------------------------------------------------
    # Dayflow-specific identity
    # ------------------------------------------------------------------
    df_employee_id = fields.Char(
        string='Employee ID',
        required=True,
        copy=False,
        index=True,
        help='Unique Dayflow employee identifier, e.g. DF-001',
    )

    # ------------------------------------------------------------------
    # Personal / editable by employee themselves
    # ------------------------------------------------------------------
    df_phone = fields.Char(
        string='Phone Number',
        help='Employee can update this field',
    )
    df_address = fields.Text(
        string='Address',
        help='Employee can update this field',
    )

    # ------------------------------------------------------------------
    # Documents (stored as binary; employees can upload their own)
    # ------------------------------------------------------------------
    df_document_ids = fields.One2many(
        comodel_name='dayflow.employee.document',
        inverse_name='employee_id',
        string='Documents',
    )

    # ------------------------------------------------------------------
    # Reverse relations — defined on child models but declared here
    # for easy access and IDE discoverability
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
    df_payroll_id = fields.One2many(
        comodel_name='dayflow.payroll',
        inverse_name='employee_id',
        string='Payroll',
    )

    # ------------------------------------------------------------------
    # Active / archive — hr.employee already has active field; we keep it
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        (
            'df_employee_id_unique',
            'UNIQUE(df_employee_id)',
            'Employee ID must be unique across the system.',
        ),
    ]

    @api.constrains('df_phone')
    def _check_phone(self):
        for rec in self:
            if rec.df_phone and not re.match(r'^\+?[\d\s\-]{7,15}$', rec.df_phone):
                raise ValidationError(
                    f'Phone number "{rec.df_phone}" does not look valid. '
                    'Use digits, spaces, hyphens or a leading +.'
                )

    # ------------------------------------------------------------------
    # Compute display name to include employee ID
    # ------------------------------------------------------------------
    def name_get(self):
        result = []
        for rec in self:
            name = rec.name or ''
            if rec.df_employee_id:
                name = f'[{rec.df_employee_id}] {name}'
            result.append((rec.id, name))
        return result


class DayflowEmployeeDocument(models.Model):
    """Stores employee documents (ID proof, contracts, certificates, etc.)"""
    _name = 'dayflow.employee.document'
    _description = 'Dayflow Employee Document'
    _order = 'create_date desc'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(string='Document Name', required=True)
    document_type = fields.Selection(
        selection=[
            ('id_proof', 'ID Proof'),
            ('contract', 'Employment Contract'),
            ('certificate', 'Certificate'),
            ('other', 'Other'),
        ],
        string='Type',
        default='other',
        required=True,
    )
    file = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    note = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
