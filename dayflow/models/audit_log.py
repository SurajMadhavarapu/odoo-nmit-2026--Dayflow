# -*- coding: utf-8 -*-
"""
Dayflow - Audit Log Model
Lightweight, append-only record of important HR changes.

INTEGRATION CONTRACT:
  model  : dayflow.audit.log
  Access : HR Admin read-only via UI; no one can create/edit/delete manually.
           Written automatically via sudo() calls in employee.py, payroll.py, leave.py.

  fields :
    user_id      Many2one res.users   who made the change
    timestamp    Datetime             when (auto-set on create)
    model_name   Char                 technical model name
    record_id    Integer              ID of the changed record
    record_name  Char                 human-readable label
    record_ref   Char (computed)      "ModelName#ID (label)" — shown in views
    action       Selection            create|update|approve|reject|submit|confirm
    field_name   Char                 changed field
    old_value    Char                 previous value
    new_value    Char                 new value

  To write an audit entry from your model:
    self.env['dayflow.audit.log'].sudo().create({
        'user_id':     self.env.uid,
        'model_name':  self._name,
        'record_id':   record.id,
        'record_name': record.display_name,
        'action':      'approve',   # or update|reject|submit|create
        'field_name':  'state',
        'old_value':   'pending',
        'new_value':   'approved',
    })
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DayflowAuditLog(models.Model):
    _name = 'dayflow.audit.log'
    _description = 'Dayflow HR Audit Log'
    _order = 'timestamp desc'
    # Suppress Odoo auto write_uid/write_date on this model (it's append-only)
    _log_access = False

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Changed By',
        required=True,
        ondelete='set null',
        index=True,
    )
    timestamp = fields.Datetime(
        string='Timestamp',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )
    model_name = fields.Char(
        string='Model',
        required=True,
    )
    record_id = fields.Integer(
        string='Record ID',
        required=True,
    )
    record_name = fields.Char(
        string='Record Label',
    )
    record_ref = fields.Char(
        string='Record',
        compute='_compute_record_ref',
        store=True,
        help='Human-readable reference shown in the audit list view',
    )
    action = fields.Selection(
        selection=[
            ('create',  'Created'),
            ('update',  'Updated'),
            ('approve', 'Approved'),
            ('reject',  'Rejected'),
            ('submit',  'Submitted'),
            ('confirm', 'Confirmed'),
            ('archive', 'Archived'),
            ('other',   'Other'),
        ],
        string='Action',
        required=True,
    )
    field_name = fields.Char(string='Field')
    old_value = fields.Char(string='Previous Value')
    new_value = fields.Char(string='New Value')

    # ------------------------------------------------------------------
    # Computed record reference
    # ------------------------------------------------------------------
    @api.depends('model_name', 'record_id', 'record_name')
    def _compute_record_ref(self):
        for rec in self:
            parts = []
            if rec.model_name:
                parts.append(rec.model_name)
            if rec.record_id:
                parts.append(f'#{rec.record_id}')
            if rec.record_name:
                parts.append(f'({rec.record_name})')
            rec.record_ref = ' '.join(parts)

    # ------------------------------------------------------------------
    # Display name
    # ------------------------------------------------------------------
    def name_get(self):
        result = []
        action_labels = dict(self._fields['action'].selection)
        for rec in self:
            ts = str(rec.timestamp)[:16] if rec.timestamp else ''
            user = rec.user_id.name or 'Unknown'
            action = action_labels.get(rec.action, rec.action)
            result.append((rec.id, f'[{ts}] {user} — {action}'))
        return result

    # ------------------------------------------------------------------
    # Immutability
    # ------------------------------------------------------------------
    def write(self, vals):
        raise UserError(_('Audit log records are immutable and cannot be modified.'))

    def unlink(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError(
                _('Audit log records can only be deleted by system administrators.')
            )
        return super().unlink()
