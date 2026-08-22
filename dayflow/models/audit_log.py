# -*- coding: utf-8 -*-
"""
Dayflow – Audit Log Model

Lightweight audit trail for critical HR changes.
Records: who, when, what model/record, what action, old/new value.

Usage (from other models):
    self.env['dayflow.audit.log'].sudo().log(
        model='dayflow.payroll',
        res_id=self.id,
        action='update',
        field_name='basic_salary',
        old_value='50000',
        new_value='55000',
    )
"""

from odoo import models, fields, api


class DayflowAuditLog(models.Model):
    _name = 'dayflow.audit.log'
    _description = 'Dayflow HR Audit Log'
    _order = 'timestamp desc'

    # Who
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Changed By',
        default=lambda self: self.env.uid,
        readonly=True,
        index=True,
    )

    # When
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )

    # What record
    model_name = fields.Char(
        string='Model',
        readonly=True,
        index=True,
    )
    record_id = fields.Integer(
        string='Record ID',
        readonly=True,
        index=True,
    )
    # Human-readable reference
    record_ref = fields.Char(
        string='Record Reference',
        readonly=True,
        help='Display name of the changed record at the time of the change',
    )

    # What happened
    action = fields.Selection(
        selection=[
            ('create', 'Created'),
            ('update', 'Updated'),
            ('approve', 'Approved'),
            ('reject', 'Rejected'),
            ('archive', 'Archived'),
            ('other', 'Other'),
        ],
        string='Action',
        readonly=True,
    )
    field_name = fields.Char(string='Field', readonly=True)
    old_value = fields.Text(string='Previous Value', readonly=True)
    new_value = fields.Text(string='New Value', readonly=True)
    notes = fields.Text(string='Additional Notes', readonly=True)

    # ------------------------------------------------------------------
    # Convenience factory method
    # ------------------------------------------------------------------
    @api.model
    def log(
        self,
        model,
        res_id,
        action,
        field_name=None,
        old_value=None,
        new_value=None,
        notes=None,
    ):
        """
        Create an audit log entry.

        Args:
            model (str): Odoo model technical name, e.g. 'dayflow.payroll'
            res_id (int): ID of the changed record
            action (str): one of create|update|approve|reject|archive|other
            field_name (str): optional field that changed
            old_value (str): optional previous value (cast to str)
            new_value (str): optional new value (cast to str)
            notes (str): optional free-text notes
        """
        # Try to get a human-readable name for the record
        record_ref = ''
        try:
            rec = self.env[model].browse(res_id)
            record_ref = rec.display_name or str(res_id)
        except Exception:
            record_ref = str(res_id)

        return self.create({
            'user_id': self.env.uid,
            'timestamp': fields.Datetime.now(),
            'model_name': model,
            'record_id': res_id,
            'record_ref': record_ref,
            'action': action,
            'field_name': field_name,
            'old_value': str(old_value) if old_value is not None else False,
            'new_value': str(new_value) if new_value is not None else False,
            'notes': notes,
        })
