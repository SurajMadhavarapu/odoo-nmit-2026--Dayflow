# -*- coding: utf-8 -*-
"""
Dayflow – Leave Request Model
Owner: KUNAM (Attendance & Leave workflow/UI)
Stub author: Mani (HR Core) — handed off to Kunam for full implementation.

NOTE TO KUNAM:
  This file contains the Leave Request model stub with fields, constraints,
  and workflow action signatures. The approval workflow calls into
  dayflow.attendance — you own both, so wire them together in your branch.
  The _mark_attendance_as_leave() stub below shows the intended integration
  point but intentionally does NOT call dayflow.attendance directly here
  to avoid cross-branch coupling.

INTEGRATION CONTRACT (stable — do not rename without telling Suraj):
  Model name    : dayflow.leave.request
  Employee FK   : employee_id  → hr.employee (Many2one)
  Leave types   : paid | sick | unpaid
  Status values : draft (Pending) | approved | Rejected
  Workflow      : Employee applies (draft) → HR approves/rejects
  Auth group    : dayflow.group_dayflow_hr_admin  (approve/reject)
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class DayflowLeaveRequest(models.Model):
    _name = 'dayflow.leave.request'
    _description = 'Dayflow Leave Request'
    _order = 'date_from desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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
        default=lambda self: self._default_employee(),
    )
    leave_type = fields.Selection(
        selection=[
            ('paid',   'Paid Leave'),
            ('sick',   'Sick Leave'),
            ('unpaid', 'Unpaid Leave'),
        ],
        string='Leave Type',
        required=True,
        tracking=True,
    )
    date_from = fields.Date(
        string='From Date',
        required=True,
        tracking=True,
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        tracking=True,
    )
    number_of_days = fields.Integer(
        string='Number of Days',
        compute='_compute_number_of_days',
        store=True,
    )
    remarks = fields.Text(
        string='Remarks',
        help='Reason for leave — filled by employee.',
    )

    # ------------------------------------------------------------------
    # Workflow / status
    # ------------------------------------------------------------------
    status = fields.Selection(
        selection=[
            ('draft',    'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    hr_comment = fields.Text(
        string='HR Comment',
        tracking=True,
        help='HR/Admin comment on approval or rejection.',
    )
    approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Reviewed By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_date = fields.Datetime(
        string='Reviewed On',
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Default employee = currently logged-in employee's hr.employee record
    # ------------------------------------------------------------------
    def _default_employee(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        )
        return employee.id if employee else False

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    @api.depends('date_from', 'date_to')
    def _compute_number_of_days(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                delta = rec.date_to - rec.date_from
                rec.number_of_days = delta.days + 1
            else:
                rec.number_of_days = 0

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_to < rec.date_from:
                    raise ValidationError('End date cannot be before start date.')

    @api.constrains('employee_id', 'date_from', 'date_to', 'status')
    def _check_overlapping_leave(self):
        for rec in self:
            if rec.status == 'rejected':
                continue
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('id', '!=', rec.id),
                ('status', '!=', 'rejected'),
                ('date_from', '<=', rec.date_to),
                ('date_to',   '>=', rec.date_from),
            ]
            if self.search(domain, limit=1):
                raise ValidationError(
                    'This employee already has a leave request overlapping '
                    'the selected date range.'
                )

    # ------------------------------------------------------------------
    # Workflow actions — HR/Admin only
    # ------------------------------------------------------------------
    def action_approve(self):
        """Approve a pending leave request. HR/Admin only."""
        self._check_hr_access()
        for rec in self:
            if rec.status != 'draft':
                raise UserError('Leave request is already %s.' % rec.status)
            if rec.employee_id.user_id == self.env.user:
                raise UserError('You cannot approve your own leave request.')
            rec.write({
                'status':        'approved',
                'approved_by':   self.env.uid,
                'approved_date': fields.Datetime.now(),
            })
            # Audit trail
            self.env['dayflow.audit.log'].sudo().log(
                model='dayflow.leave.request',
                res_id=rec.id,
                action='approve',
                field_name='status',
                old_value='draft',
                new_value='approved',
            )
            # ---------------------------------------------------------
            # INTEGRATION POINT FOR KUNAM:
            # After approval, mark attendance records for the leave days.
            # Kunam: call self._sync_attendance_for_leave(rec) here once
            # your attendance model is in place.
            # Example:
            #   rec._sync_attendance_for_leave()
            # See INTEGRATION_CONTRACT.md §Attendance for the method signature.
            # ---------------------------------------------------------

    def action_reject(self):
        """Reject a pending leave request. HR/Admin only."""
        self._check_hr_access()
        for rec in self:
            if rec.status != 'draft':
                raise UserError('Leave request is already %s.' % rec.status)
            rec.write({
                'status':        'rejected',
                'approved_by':   self.env.uid,
                'approved_date': fields.Datetime.now(),
            })
            self.env['dayflow.audit.log'].sudo().log(
                model='dayflow.leave.request',
                res_id=rec.id,
                action='reject',
                field_name='status',
                old_value='draft',
                new_value='rejected',
            )

    def action_reset_to_draft(self):
        """Reset a rejected leave request back to Pending. HR/Admin only."""
        self._check_hr_access()
        for rec in self:
            rec.write({
                'status':        'draft',
                'approved_by':   False,
                'approved_date': False,
            })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _check_hr_access(self):
        """Raise if the current user is not in the HR/Admin group."""
        if not self.env.user.has_group('dayflow.group_dayflow_hr_admin'):
            raise UserError(
                'Only HR/Admin users can approve or reject leave requests.'
            )
