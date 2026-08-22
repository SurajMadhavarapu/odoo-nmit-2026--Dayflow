# -*- coding: utf-8 -*-
"""
Dayflow – Attendance Model

Team contract:
  model   : dayflow.attendance
  fields  : employee_id, date, check_in, check_out, status, notes
  states  : present | absent | half_day | leave
  rules   : one record per employee per date; check_out >= check_in
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DayflowAttendance(models.Model):
    _name = 'dayflow.attendance'
    _description = 'Dayflow Attendance Record'
    _order = 'date desc, employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # chatter for audit

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today,
        index=True,
        tracking=True,
    )
    check_in = fields.Datetime(
        string='Check In',
        tracking=True,
    )
    check_out = fields.Datetime(
        string='Check Out',
        tracking=True,
    )
    status = fields.Selection(
        selection=[
            ('present', 'Present'),
            ('absent', 'Absent'),
            ('half_day', 'Half Day'),
            ('leave', 'On Leave'),
        ],
        string='Status',
        required=True,
        default='absent',
        tracking=True,
    )
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Computed: working hours
    # ------------------------------------------------------------------
    working_hours = fields.Float(
        string='Working Hours',
        compute='_compute_working_hours',
        store=True,
        help='Hours between check-in and check-out',
    )

    @api.depends('check_in', 'check_out')
    def _compute_working_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.working_hours = delta.total_seconds() / 3600.0
            else:
                rec.working_hours = 0.0

    # ------------------------------------------------------------------
    # SQL constraint: one record per employee per date
    # ------------------------------------------------------------------
    _sql_constraints = [
        (
            'unique_employee_date',
            'UNIQUE(employee_id, date)',
            'An attendance record already exists for this employee on this date.',
        ),
    ]

    # ------------------------------------------------------------------
    # Python constraints
    # ------------------------------------------------------------------
    @api.constrains('check_in', 'check_out')
    def _check_times(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                if rec.check_out < rec.check_in:
                    raise ValidationError(
                        'Check-out time cannot be earlier than check-in time.'
                    )

    @api.constrains('check_in', 'date')
    def _check_in_date_match(self):
        for rec in self:
            if rec.check_in and rec.date:
                if rec.check_in.date() != rec.date:
                    raise ValidationError(
                        'Check-in datetime must fall on the same date as the attendance record date.'
                    )

    # ------------------------------------------------------------------
    # Auto-set status based on check-in presence
    # ------------------------------------------------------------------
    @api.onchange('check_in', 'check_out')
    def _onchange_times_set_status(self):
        """Convenience: auto-suggest status when times are entered."""
        if self.check_in and self.check_out:
            hours = (self.check_out - self.check_in).total_seconds() / 3600.0
            if hours >= 4:
                self.status = 'present'
            elif hours > 0:
                self.status = 'half_day'
        elif self.check_in:
            self.status = 'present'

    # ------------------------------------------------------------------
    # Employee check-in action (called from UI button / Kunam's workflow)
    # ------------------------------------------------------------------
    @api.model
    def action_check_in(self, employee_id):
        """
        Create or update today's attendance record with check-in time.
        Returns the attendance record.
        """
        today = fields.Date.today()
        now = fields.Datetime.now()
        record = self.search([
            ('employee_id', '=', employee_id),
            ('date', '=', today),
        ], limit=1)
        if record:
            if record.check_in:
                raise ValidationError('Already checked in today.')
            record.write({'check_in': now, 'status': 'present'})
        else:
            record = self.create({
                'employee_id': employee_id,
                'date': today,
                'check_in': now,
                'status': 'present',
            })
        return record

    def action_check_out(self):
        """Check out the current employee. Called on the record directly."""
        self.ensure_one()
        if not self.check_in:
            raise ValidationError('Cannot check out without a check-in record.')
        if self.check_out:
            raise ValidationError('Already checked out today.')
        now = fields.Datetime.now()
        hours = (now - self.check_in).total_seconds() / 3600.0
        status = 'present' if hours >= 4 else 'half_day'
        self.write({'check_out': now, 'status': status})
