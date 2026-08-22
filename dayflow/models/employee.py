# -*- coding: utf-8 -*-
"""
Dayflow — Employee Model
Extends Odoo's built-in hr.employee to add Dayflow-specific fields.
We extend rather than replace to avoid duplicating Odoo's existing HR infrastructure
(contracts, payslips, org chart, user linking, etc.).

Owner: Mani (HR Core / Data Layer)
Integration consumers: Harshith (Dashboard), Kunam (Attendance/Leave UI), Suraj (Auth)
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class DayflowEmployee(models.Model):
    _inherit = 'hr.employee'

    # ------------------------------------------------------------------
    # Dayflow-specific identifier
    # ------------------------------------------------------------------
    dayflow_employee_id = fields.Char(
        string='Employee ID',
        required=True,
        copy=False,
        index=True,
        help='Unique Dayflow employee identifier, e.g. DF-001',
    )

    # ------------------------------------------------------------------
    # Personal information (editable by employee for allowed fields)
    # ------------------------------------------------------------------
    phone_number = fields.Char(
        string='Phone Number',
        help='Personal contact number',
    )
    address_line1 = fields.Char(string='Address Line 1')
    address_line2 = fields.Char(string='Address Line 2')
    city = fields.Char(string='City')
    state_region = fields.Char(string='State / Region')
    postal_code = fields.Char(string='Postal Code')
    country_name = fields.Char(string='Country')

    # ------------------------------------------------------------------
    # Job information (HR/Admin managed)
    # ------------------------------------------------------------------
    date_of_joining = fields.Date(
        string='Date of Joining',
        help='Official joining date',
    )
    employment_type = fields.Selection(
        selection=[
            ('full_time', 'Full-Time'),
            ('part_time', 'Part-Time'),
            ('contract', 'Contract'),
            ('intern', 'Intern'),
        ],
        string='Employment Type',
        default='full_time',
    )

    # ------------------------------------------------------------------
    # Status / archival
    # ------------------------------------------------------------------
    # hr.employee already has 'active' field — we use it directly.
    # Archived employees keep historical attendance/leave/payroll.

    # ------------------------------------------------------------------
    # Relationships (reverse links — defined on child models via Many2one)
    # ------------------------------------------------------------------
    attendance_ids = fields.One2many(
        comodel_name='dayflow.attendance',
        inverse_name='employee_id',
        string='Attendance Records',
    )
    leave_request_ids = fields.One2many(
        comodel_name='dayflow.leave.request',
        inverse_name='employee_id',
        string='Leave Requests',
    )
    payroll_id = fields.One2many(
        comodel_name='dayflow.payroll',
        inverse_name='employee_id',
        string='Payroll Records',
    )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        (
            'dayflow_employee_id_unique',
            'UNIQUE(dayflow_employee_id)',
            'Employee ID must be unique across all employees.',
        ),
    ]

    @api.constrains('phone_number')
    def _check_phone_number(self):
        for rec in self:
            if rec.phone_number and not re.match(r'^\+?[\d\s\-]{7,20}$', rec.phone_number):
                raise ValidationError(
                    'Phone number "%s" is not valid. Use digits, spaces, hyphens, or a leading +.'
                    % rec.phone_number
                )

    @api.constrains('date_of_joining')
    def _check_date_of_joining(self):
        for rec in self:
            if rec.date_of_joining and rec.date_of_joining > fields.Date.today():
                raise ValidationError('Date of Joining cannot be in the future.')

    # ------------------------------------------------------------------
    # Computed display name helper (used by related models)
    # ------------------------------------------------------------------
    def name_get(self):
        result = []
        for rec in self:
            name = rec.name or 'Employee'
            if rec.dayflow_employee_id:
                name = '[%s] %s' % (rec.dayflow_employee_id, name)
            result.append((rec.id, name))
        return result
