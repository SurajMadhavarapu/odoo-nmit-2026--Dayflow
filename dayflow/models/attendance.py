# -*- coding: utf-8 -*-
"""
Dayflow – Attendance Model
Owner: KUNAM (Attendance & Leave workflow/UI)
Stub author: Mani (HR Core) — handed off to Kunam for full implementation.

NOTE TO KUNAM:
  This is your model. The fields, constraints, and computed values are
  provided as a clean starting point. Add your check-in/check-out workflow
  methods (action_check_in, action_check_out) and any UI-specific logic here.
  Reference hr.employee via employee_id — do NOT add a separate df_employee_id
  Char field here; use the Many2one to hr.employee.

INTEGRATION CONTRACT (stable — do not rename without telling Suraj):
  Model name    : dayflow.attendance
  Employee FK   : employee_id  → hr.employee (Many2one)
  Date field    : date          (Date, unique per employee)
  Check-in      : check_in     (Datetime)
  Check-out     : check_out    (Datetime)
  Worked hours  : working_hours (Float, computed)
  Status values : present | absent | half_day | leave
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DayflowAttendance(models.Model):
    _name = 'dayflow.attendance'
    _description = 'Dayflow Attendance'
    _order = 'date desc, employee_id'

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
    )
    check_in = fields.Datetime(string='Check In')
    check_out = fields.Datetime(string='Check Out')

    status = fields.Selection([
        ('present',  'Present'),
        ('absent',   'Absent'),
        ('half_day', 'Half Day'),
        ('leave',    'Leave'),
    ], string='Status', required=True, default='absent')

    working_hours = fields.Float(
        string='Working Hours',
        compute='_compute_working_hours',
        store=True,
    )
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # SQL constraint — one record per employee per date
    # ------------------------------------------------------------------
    _sql_constraints = [
        (
            'unique_employee_date',
            'UNIQUE(employee_id, date)',
            'An attendance record already exists for this employee on this date.',
        ),
    ]

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('check_in', 'check_out')
    def _compute_working_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.working_hours = delta.total_seconds() / 3600.0
            else:
                rec.working_hours = 0.0

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('check_in', 'check_out')
    def _check_times(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                if rec.check_out <= rec.check_in:
                    raise ValidationError(
                        'Check-out time must be after check-in time.'
                    )

    @api.constrains('check_in', 'date')
    def _check_checkin_matches_date(self):
        for rec in self:
            if rec.check_in and rec.date:
                if rec.check_in.date() != rec.date:
                    raise ValidationError(
                        'Check-in datetime must be on the same date as the attendance record.'
                    )

    # ------------------------------------------------------------------
    # KUNAM: Add action_check_in() and action_check_out() here.
    # Suggested signature:
    #
    #   @api.model
    #   def action_check_in(self, employee_id=None):
    #       ...
    #
    #   def action_check_out(self):
    #       ...
    # ------------------------------------------------------------------
