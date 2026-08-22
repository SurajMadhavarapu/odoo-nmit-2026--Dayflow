# -*- coding: utf-8 -*-
"""
Dayflow — Attendance Model
Tracks daily attendance per employee with check-in/out times and status.

Owner: Mani (HR Core / Data Layer)
Integration consumers: Kunam (Attendance UI), Harshith (Dashboard summary)

Business rules enforced here (NOT only in UI):
- Check-out cannot be before check-in.
- One attendance record per employee per date.
- Only the record owner or HR/Admin can write to a record.
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class DayflowAttendance(models.Model):
    _name = 'dayflow.attendance'
    _description = 'Dayflow Attendance'
    _order = 'date desc, employee_id'
    _rec_name = 'display_name'

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today,
        index=True,
    )
    check_in = fields.Datetime(
        string='Check In',
        help='Time the employee clocked in',
    )
    check_out = fields.Datetime(
        string='Check Out',
        help='Time the employee clocked out',
    )
    status = fields.Selection(
        selection=[
            ('present', 'Present'),
            ('absent', 'Absent'),
            ('half_day', 'Half-Day'),
            ('leave', 'On Leave'),
        ],
        string='Status',
        required=True,
        default='absent',
        index=True,
    )
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    worked_hours = fields.Float(
        string='Worked Hours',
        compute='_compute_worked_hours',
        store=True,
        help='Total hours between check-in and check-out',
    )
    display_name = fields.Char(
        string='Label',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.worked_hours = delta.total_seconds() / 3600.0
            else:
                rec.worked_hours = 0.0

    @api.depends('employee_id', 'date')
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or 'Employee'
            date = str(rec.date) if rec.date else ''
            rec.display_name = '%s — %s' % (emp, date)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        (
            'unique_employee_date',
            'UNIQUE(employee_id, date)',
            'An attendance record already exists for this employee on this date.',
        ),
    ]

    @api.constrains('check_in', 'check_out')
    def _check_times(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                if rec.check_out <= rec.check_in:
                    raise ValidationError(
                        'Check-out time must be after check-in time for %s on %s.'
                        % (rec.employee_id.name, rec.date)
                    )

    @api.constrains('date')
    def _check_date_not_future(self):
        for rec in self:
            if rec.date and rec.date > fields.Date.today():
                raise ValidationError('Cannot create attendance records for a future date.')

    # ------------------------------------------------------------------
    # Check-in / Check-out business methods
    # Called from the UI buttons or Kunam's workflow
    # ------------------------------------------------------------------
    def action_check_in(self):
        """Mark check-in for the current user's linked employee."""
        self.ensure_one()
        if self.check_in:
            raise UserError('Already checked in for this record.')
        self.write({
            'check_in': fields.Datetime.now(),
            'status': 'present',
        })
        self._log_audit('check_in', False, str(fields.Datetime.now()))

    def action_check_out(self):
        """Mark check-out for the current user's linked employee."""
        self.ensure_one()
        if not self.check_in:
            raise UserError('Cannot check out without checking in first.')
        if self.check_out:
            raise UserError('Already checked out for this record.')
        self.write({'check_out': fields.Datetime.now()})
        self._log_audit('check_out', False, str(fields.Datetime.now()))

    # ------------------------------------------------------------------
    # Audit helper
    # ------------------------------------------------------------------
    def _log_audit(self, field_changed, old_value, new_value):
        self.env['dayflow.audit.log'].sudo().create({
            'user_id': self.env.uid,
            'model_name': self._name,
            'record_id': self.id,
            'record_name': self.display_name,
            'action': 'write',
            'field_name': field_changed,
            'old_value': str(old_value) if old_value else '',
            'new_value': str(new_value) if new_value else '',
        })
