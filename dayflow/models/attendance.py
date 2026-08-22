# -*- coding: utf-8 -*-
"""
Dayflow - Attendance Model
One record per employee per calendar day.

INTEGRATION CONTRACT:
  model  : dayflow.attendance
  fields :
    employee_id   Many2one hr.employee   required
    date          Date                   required, unique per employee
    check_in      Datetime               optional
    check_out     Datetime               optional; must be > check_in
    worked_hours  Float (computed)       hours between check_in and check_out
    status        Selection              present | absent | half_day | leave
    notes         Text                   optional

  Button actions (call via type="object" in views):
    action_check_in()   — sets check_in, status=present
    action_check_out()  — sets check_out, refines status
    get_or_create_today(employee_id) — @api.model helper for Kunam's UI
"""

from odoo import api, fields, models, _
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
        index=True,
    )
    check_in = fields.Datetime(
        string='Check In',
    )
    check_out = fields.Datetime(
        string='Check Out',
    )
    worked_hours = fields.Float(
        string='Worked Hours',
        compute='_compute_worked_hours',
        store=True,
        readonly=True,
        help='Total hours worked (check_out minus check_in)',
    )
    status = fields.Selection(
        selection=[
            ('present',  'Present'),
            ('absent',   'Absent'),
            ('half_day', 'Half Day'),
            ('leave',    'Leave'),
        ],
        string='Status',
        required=True,
        default='absent',
        index=True,
    )
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Computed: worked hours
    # ------------------------------------------------------------------
    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.worked_hours = delta.total_seconds() / 3600.0
            else:
                rec.worked_hours = 0.0

    # ------------------------------------------------------------------
    # Auto-derive status when times change
    # ------------------------------------------------------------------
    @api.onchange('check_in', 'check_out')
    def _onchange_derive_status(self):
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            hours = delta.total_seconds() / 3600.0
            self.status = 'present' if hours >= 7 else 'half_day'

    # ------------------------------------------------------------------
    # SQL constraints
    # ------------------------------------------------------------------
    _sql_constraints = [
        (
            'unique_employee_date',
            'UNIQUE(employee_id, date)',
            'An attendance record for this employee on this date already exists.',
        ),
    ]

    # ------------------------------------------------------------------
    # API constraints
    # ------------------------------------------------------------------
    @api.constrains('check_in', 'check_out')
    def _check_times(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                if rec.check_out <= rec.check_in:
                    raise ValidationError(
                        _('Check-out time must be after check-in time for %s on %s.')
                        % (rec.employee_id.name, rec.date)
                    )

    @api.constrains('date')
    def _check_not_future(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date and rec.date > today:
                raise ValidationError(
                    _('Attendance date cannot be in the future.')
                )

    # ------------------------------------------------------------------
    # Row-level security helper
    # ------------------------------------------------------------------
    def _assert_own_or_hr(self):
        if self.env.su:
            return
        if self.env.user.has_group('dayflow.group_dayflow_hr_admin'):
            return
        for rec in self:
            if rec.employee_id.user_id.id != self.env.uid:
                raise ValidationError(
                    _('You are not allowed to modify attendance records for other employees.')
                )

    def write(self, vals):
        self._assert_own_or_hr()
        return super().write(vals)

    def unlink(self):
        self._assert_own_or_hr()
        return super().unlink()

    # ------------------------------------------------------------------
    # Business actions (called from form buttons)
    # ------------------------------------------------------------------
    def action_check_in(self):
        self.ensure_one()
        self._assert_own_or_hr()
        if self.check_in:
            raise ValidationError(_('Already checked in for today.'))
        self.check_in = fields.Datetime.now()
        self.status = 'present'

    def action_check_out(self):
        self.ensure_one()
        self._assert_own_or_hr()
        if not self.check_in:
            raise ValidationError(_('Cannot check out without checking in first.'))
        if self.check_out:
            raise ValidationError(_('Already checked out for today.'))
        self.check_out = fields.Datetime.now()
        hours = (self.check_out - self.check_in).total_seconds() / 3600.0
        self.status = 'present' if hours >= 7 else 'half_day'

    # ------------------------------------------------------------------
    # Utility: get or create today's record for an employee (for Kunam)
    # ------------------------------------------------------------------
    @api.model
    def get_or_create_today(self, employee_id):
        today = fields.Date.context_today(self)
        record = self.search([
            ('employee_id', '=', employee_id),
            ('date', '=', today),
        ], limit=1)
        if not record:
            record = self.create({
                'employee_id': employee_id,
                'date': today,
                'status': 'absent',
            })
        return record
