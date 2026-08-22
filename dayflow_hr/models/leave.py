# -*- coding: utf-8 -*-
"""
Dayflow - Leave Request Model
Owner: Mani (HR Core) | UI: Kunam

Full apply → pending → approve/reject workflow.

INTEGRATION CONTRACT (stable — do not rename):
  model  : dayflow.leave.request
  fields :
    employee_id    Many2one hr.employee   required; defaults to logged-in employee
    leave_type     Selection              paid | sick | unpaid
    date_from      Date                   required
    date_to        Date                   required; >= date_from
    number_of_days Integer (computed)
    remarks        Text
    state          Selection              draft | pending | approved | rejected
    hr_comment     Text                   HR/Admin fills on decision
    approved_by    Many2one res.users     auto-set
    approved_date  Datetime               auto-set

  Workflow (type="object" from form buttons):
    action_submit()          employee: draft → pending
    action_approve()         HR Admin: pending → approved
    action_reject()          HR Admin: pending → rejected
    action_reset_to_draft()  HR Admin: rejected/pending → draft

  Security groups used:
    dayflow_hr.group_dayflow_employee
    dayflow_hr.group_dayflow_hr_admin
"""

from datetime import timedelta
from odoo import api, fields, models, _
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
        ondelete='cascade',
        index=True,
        default=lambda self: self._default_employee(),
        tracking=True,
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
        string='From',
        required=True,
        tracking=True,
    )
    date_to = fields.Date(
        string='To',
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
        help='Reason for leave — filled by employee',
    )

    # ------------------------------------------------------------------
    # Workflow state
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[
            ('draft',    'Draft'),
            ('pending',  'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # HR/Admin decision fields
    # ------------------------------------------------------------------
    hr_comment = fields.Text(
        string='HR Comment',
        tracking=True,
    )
    approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Decided By',
        readonly=True,
        tracking=True,
    )
    approved_date = fields.Datetime(
        string='Decision Date',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Default: populate with current user's linked employee record
    # ------------------------------------------------------------------
    def _default_employee(self):
        emp = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        )
        return emp.id if emp else False

    # ------------------------------------------------------------------
    # Computed: number_of_days
    # ------------------------------------------------------------------
    @api.depends('date_from', 'date_to')
    def _compute_number_of_days(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to >= rec.date_from:
                rec.number_of_days = (rec.date_to - rec.date_from).days + 1
            else:
                rec.number_of_days = 0

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_('End date cannot be before start date.'))

    @api.constrains('date_from', 'date_to', 'employee_id', 'state')
    def _check_no_overlap(self):
        """Block overlapping approved/pending leaves for the same employee."""
        for rec in self:
            if rec.state not in ('approved', 'pending'):
                continue
            if not (rec.date_from and rec.date_to and rec.employee_id):
                continue
            overlap = self.sudo().search([
                ('employee_id', '=', rec.employee_id.id),
                ('id', '!=', rec.id),
                ('state', 'in', ('approved', 'pending')),
                ('date_from', '<=', rec.date_to),
                ('date_to', '>=', rec.date_from),
            ], limit=1)
            if overlap:
                raise ValidationError(
                    _('Employee %s already has an overlapping leave request (%s to %s).')
                    % (rec.employee_id.name, overlap.date_from, overlap.date_to)
                )

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Employee submits: draft → pending."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft requests can be submitted.'))
        if not self.env.user.has_group('dayflow_hr.group_dayflow_hr_admin'):
            emp = self.env['hr.employee'].search(
                [('user_id', '=', self.env.uid)], limit=1
            )
            if self.employee_id != emp:
                raise UserError(_('You can only submit your own leave requests.'))
        self.write({'state': 'pending'})
        self.message_post(body=_('Leave request submitted — awaiting HR approval.'))
        self._audit('submit')

    def action_approve(self):
        """HR Admin approves: pending → approved."""
        self.ensure_one()
        if not self.env.user.has_group('dayflow_hr.group_dayflow_hr_admin'):
            raise UserError(_('Only HR/Admin users can approve leave requests.'))
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be approved.'))
        self.write({
            'state': 'approved',
            'approved_by': self.env.uid,
            'approved_date': fields.Datetime.now(),
        })
        self._sync_attendance_for_leave()
        self.message_post(body=_('Approved by %s.') % self.env.user.name)
        self._audit('approve')

    def action_reject(self):
        """HR Admin rejects: pending → rejected."""
        self.ensure_one()
        if not self.env.user.has_group('dayflow_hr.group_dayflow_hr_admin'):
            raise UserError(_('Only HR/Admin users can reject leave requests.'))
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be rejected.'))
        self.write({
            'state': 'rejected',
            'approved_by': self.env.uid,
            'approved_date': fields.Datetime.now(),
        })
        self.message_post(body=_('Rejected by %s.') % self.env.user.name)
        self._audit('reject')

    def action_reset_to_draft(self):
        """Allow HR to reset rejected/pending back to draft."""
        self.ensure_one()
        if self.state not in ('rejected', 'pending'):
            raise UserError(_('Only rejected or pending requests can be reset.'))
        self.write({
            'state': 'draft',
            'hr_comment': False,
            'approved_by': False,
            'approved_date': False,
        })

    # ------------------------------------------------------------------
    # Internal: sync attendance on approval
    # Kunam may override _sync_attendance_for_leave() without touching this file
    # ------------------------------------------------------------------
    def _sync_attendance_for_leave(self):
        if not (self.date_from and self.date_to):
            return
        current = self.date_from
        Att = self.env['dayflow.attendance'].sudo()
        while current <= self.date_to:
            att = Att.search([
                ('employee_id', '=', self.employee_id.id),
                ('date', '=', current),
            ], limit=1)
            if att:
                att.write({'status': 'leave'})
            else:
                Att.create({
                    'employee_id': self.employee_id.id,
                    'date': current,
                    'status': 'leave',
                })
            current += timedelta(days=1)

    # ------------------------------------------------------------------
    # Internal: audit log
    # ------------------------------------------------------------------
    def _audit(self, action):
        self.env['dayflow.audit.log'].sudo().create({
            'user_id': self.env.uid,
            'model_name': self._name,
            'record_id': self.id,
            'record_name': self.display_name,
            'action': action,
            'field_name': 'state',
            'old_value': '',
            'new_value': self.state,
        })

    # ------------------------------------------------------------------
    # Security: block employees from writing HR-only fields directly
    # ------------------------------------------------------------------
    def write(self, vals):
        is_hr = self.env.user.has_group('dayflow_hr.group_dayflow_hr_admin')
        if not is_hr and not self.env.su:
            blocked = {'hr_comment', 'approved_by', 'approved_date'} & set(vals.keys())
            if blocked:
                raise UserError(
                    _('You are not authorised to modify HR-only fields: %s')
                    % ', '.join(blocked)
                )
            if 'state' in vals and vals['state'] != 'pending':
                raise UserError(
                    _('Use the Submit button to change leave request status.')
                )
        return super().write(vals)
