# -*- coding: utf-8 -*-
"""
Dayflow - Audit Log Model
Owner: Mani (HR Core)

Append-only log for important HR changes.
HR Admin can read; nobody can create/edit/delete manually.
All writes go through .sudo() from models (employee, payroll, leave).

INTEGRATION CONTRACT:
  model  : dayflow.audit.log
  To write from any model:
    self.env['dayflow.audit.log'].sudo().create({
        'user_id':     self.env.uid,
        'model_name':  self._name,
        'record_id':   record.id,
        'record_name': record.display_name,
        'action':      'approve',   # see selection values below
        'field_name':  'state',
        'old_value':   'pending',
        'new_value':   'approved',
    })

  action selection values (stable):
    create | update | approve | reject | submit | confirm | archive | other
"""

from odoo import fields, models


class DayflowAuditLog(models.Model):
    _name = 'dayflow.audit.log'
    _description = 'Dayflow HR Audit Log'
    _order = 'timestamp desc'
    _log_access = False   # suppress Odoo's own write_date/create_date overhead on this model

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Changed By',
        required=True,
        ondelete='set null',
        readonly=True,
        index=True,
    )
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        index=True,
    )
    model_name = fields.Char(
        string='Model',
        required=True,
        readonly=True,
        help='Technical model name, e.g. dayflow.payroll',
    )
    record_id = fields.Integer(
        string='Record ID',
        readonly=True,
    )
    record_name = fields.Char(
        string='Record',
        readonly=True,
    )
    record_ref = fields.Char(
        string='Reference',
        compute='_compute_record_ref',
        store=True,
        readonly=True,
    )
    action = fields.Selection(
        selection=[
            ('create',  'Create'),
            ('update',  'Update'),
            ('approve', 'Approve'),
            ('reject',  'Reject'),
            ('submit',  'Submit'),
            ('confirm', 'Confirm'),
            ('archive', 'Archive'),
            ('other',   'Other'),
        ],
        string='Action',
        required=True,
        readonly=True,
        index=True,
    )
    field_name = fields.Char(
        string='Field',
        readonly=True,
    )
    old_value = fields.Char(
        string='Previous Value',
        readonly=True,
    )
    new_value = fields.Char(
        string='New Value',
        readonly=True,
    )

    def _compute_record_ref(self):
        for rec in self:
            if rec.model_name and rec.record_id:
                rec.record_ref = '%s#%d (%s)' % (
                    rec.model_name, rec.record_id, rec.record_name or ''
                )
            else:
                rec.record_ref = ''
