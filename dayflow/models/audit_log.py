# -*- coding: utf-8 -*-
"""
Dayflow — Audit Log Model
Lightweight audit trail for important HR record changes.

Owner: Mani (HR Core / Data Layer)

Records: who changed what, when, on which record, from/to what value.
Prioritises: salary changes, leave approvals/rejections, employee data changes.

Audit records are READ-ONLY — no user should be able to edit or delete them
(enforced via security/ir.model.access.csv — no write/delete for any group).
"""

from odoo import models, fields


class DayflowAuditLog(models.Model):
    _name = 'dayflow.audit.log'
    _description = 'Dayflow Audit Log'
    _order = 'timestamp desc'
    _rec_name = 'display_name'

    # Who
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Changed By',
        required=True,
        ondelete='restrict',
        index=True,
    )
    user_name = fields.Char(
        string='User Name',
        compute='_compute_user_name',
        store=True,
    )

    # When
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        required=True,
        index=True,
    )

    # What record
    model_name = fields.Char(
        string='Model',
        required=True,
        help='Technical model name, e.g. dayflow.payroll',
    )
    record_id = fields.Integer(
        string='Record ID',
        required=True,
        help='Database ID of the changed record',
    )
    record_name = fields.Char(
        string='Record Name',
        help='Human-readable name of the record at time of change',
    )

    # What happened
    action = fields.Selection(
        selection=[
            ('create', 'Created'),
            ('write', 'Modified'),
            ('unlink', 'Deleted'),
            ('check_in', 'Check In'),
            ('check_out', 'Check Out'),
            ('salary_update', 'Salary Updated'),
            ('leave_approved', 'Leave Approved'),
            ('leave_rejected', 'Leave Rejected'),
        ],
        string='Action',
        required=True,
    )
    field_name = fields.Char(
        string='Field Changed',
        help='Name of the field that was modified',
    )
    old_value = fields.Text(
        string='Previous Value',
    )
    new_value = fields.Text(
        string='New Value',
    )

    # Display
    display_name = fields.Char(
        string='Summary',
        compute='_compute_display_name',
        store=True,
    )

    def _compute_user_name(self):
        for rec in self:
            rec.user_name = rec.user_id.name if rec.user_id else 'System'

    def _compute_display_name(self):
        for rec in self:
            user = rec.user_name or 'System'
            action = dict(self._fields['action'].selection).get(rec.action, rec.action)
            model = rec.model_name or ''
            rec.display_name = '[%s] %s — %s — %s' % (
                str(rec.timestamp)[:16] if rec.timestamp else '',
                user,
                action,
                model,
            )
