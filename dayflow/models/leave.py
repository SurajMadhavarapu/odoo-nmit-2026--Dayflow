# -*- coding: utf-8 -*-
"""
Dayflow — Leave Request Model
Handles employee leave applications and HR/Admin approval workflow.

Owner: Mani (HR Core / Data Layer)
Integration consumers: Kunam (Leave UI/workflow), Harshith (Dashboard leave card)

Workflow:
  Employee creates request → status=pending
  HR/Admin approves        → status=approved
  HR/Admin rejects         → status=rejected

Business rules enforced here (NOT only in UI):
- End date cannot be before start date.
- Employees cannot approve their own leave.
- Only HR/Admin group can call approve/reject actions.
- Approved/rejected requests cannot be directly edited by employees.
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class DayflowLeaveRequest(models.Model):
    _name = 'dayflow.leave.request'
    _description = 'Dayflow Leave Request'
    _order = 'create_date desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # enables chatter

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
        default=lambda self: self._default_employee(),
    )
    leave_type = fields.Selection(
        selection=[
            ('paid', 'Paid Leave'),
            ('sick', 'Sick Leave'),
            ('unpaid', 'Unpaid Leave'),
        ],
        string='Leave Type',
        required=True,
        tracking=True,
    )
    date_from = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
    )
    remarks = fields.Text(
        string='Remarks',
        help='Reason for leave request',
    )
    status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='pending',
        required=True,
        tracking=True,
        index=True,
    )
    hr_comment = fields.Text(
        string='HR / Admin Comment',
        help='Comment added by HR or Admin during approval/rejection',
        tracking=True,
    )
    approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Actioned By',
        readonly=True,
        copy=False,
        help='HR/Admin user who approved or rejected this request',
    )
    action_date = fields.Datetime(
        string='Action Date',
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    number_of_days = fields.Integer(
        string='Number of Days',
        compute='_compute_number_of_days',
        store=True,
    )
    display_name = fields.Char(
        string='Label',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('date_from', 'date_to')
    def _compute_number_of_days(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                delta = rec.date_to - rec.date_from
                rec.number_of_days = delta.days + 1
            else:
                rec.number_of_days = 0

    @api.depends('employee_id', 'leave_type', 'date_from')
    def _compute_display_name(self):
        type_map = {'paid': 'Paid', 'sick': 'Sick', 'unpaid': 'Unpaid'}
        for rec in self:
            emp = rec.employee_id.name or 'Employee'
            ltype = type_map.get(rec.leave_type, '')
            date = str(rec.date_from) if rec.date_from else ''
            rec.display_name = '%s — %s Leave (%s)' % (emp, ltype, date)

    # ------------------------------------------------------------------
    # Default: pre-fill employee from current logged-in user
    # ------------------------------------------------------------------
    def _default_employee(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        )
        return employee.id if employee else False

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                if rec.date_to < rec.date_from:
                    raise ValidationError(
                        'End date cannot be before start date on leave request "%s".'
                        % rec.display_name
                    )

    @api.constrains('date_from')
    def _check_not_too_far_past(self):
        """Prevent backdating leave requests more than 30 days."""
        for rec in self:
            if rec.date_from:
                days_diff = (fields.Date.today() - rec.date_from).days
                if days_diff > 30 and rec.status == 'pending':
                    raise ValidationError(
                        'Cannot apply for leave more than 30 days in the past.'
                    )

    # ------------------------------------------------------------------
    # Workflow actions — called by buttons in the view
    # ------------------------------------------------------------------
    def _assert_hr_admin(self):
        """Raise if the current user is not in the HR/Admin group."""
        if not self.env.user.has_group('dayflow.group_dayflow_hr_admin'):
            raise UserError('Only HR/Admin users can approve or reject leave requests.')

    def action_approve(self):
        """HR/Admin approves the leave request."""
        self._assert_hr_admin()
        for rec in self:
            if rec.status != 'pending':
                raise UserError('Only pending requests can be approved.')
            # Prevent self-approval
            employee_user = rec.employee_id.user_id
            if employee_user and employee_user.id == self.env.uid:
                raise UserError('You cannot approve your own leave request.')
            old_status = rec.status
            rec.write({
                'status': 'approved',
                'approved_by': self.env.uid,
                'action_date': fields.Datetime.now(),
            })
            rec._log_audit('status', old_status, 'approved')
            rec.message_post(
                body='Leave request <b>approved</b> by %s.' % self.env.user.name
            )

    def action_reject(self):
        """HR/Admin rejects the leave request."""
        self._assert_hr_admin()
        for rec in self:
            if rec.status != 'pending':
                raise UserError('Only pending requests can be rejected.')
            old_status = rec.status
            rec.write({
                'status': 'rejected',
                'approved_by': self.env.uid,
                'action_date': fields.Datetime.now(),
            })
            rec._log_audit('status', old_status, 'rejected')
            rec.message_post(
                body='Leave request <b>rejected</b> by %s.' % self.env.user.name
            )

    def action_reset_to_pending(self):
        """Allow HR/Admin to reset a rejected request back to pending if needed."""
        self._assert_hr_admin()
        for rec in self:
            if rec.status not in ('rejected',):
                raise UserError('Only rejected requests can be reset to pending.')
            rec.write({
                'status': 'pending',
                'approved_by': False,
                'action_date': False,
            })

    # ------------------------------------------------------------------
    # Prevent employees from editing approved/rejected requests
    # ------------------------------------------------------------------
    def write(self, vals):
        for rec in self:
            if rec.status in ('approved', 'rejected'):
                # HR/Admin can still update comment or status
                if not self.env.user.has_group('dayflow.group_dayflow_hr_admin'):
                    raise UserError(
                        'Leave request "%s" is already %s and cannot be modified.'
                        % (rec.display_name, rec.status)
                    )
        return super().write(vals)

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
