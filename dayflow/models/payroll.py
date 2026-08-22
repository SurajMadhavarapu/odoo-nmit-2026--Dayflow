# -*- coding: utf-8 -*-
"""
Dayflow – Payroll / Salary Model
Owner: Mani (HR Core)

INTEGRATION CONTRACT (stable — do not rename without telling Suraj):
  Model name  : dayflow.payroll
  Employee FK : employee_id  → hr.employee (Many2one)
  Fields      : basic_salary, allowances, deductions, net_salary (computed),
                currency_id, effective_date, notes
  Permissions : Employees READ own record only (enforced at ACL + model level)
                HR/Admin  READ + WRITE all records
  Audit       : All salary field changes are automatically logged to
                dayflow.audit.log
"""

from odoo import models, fields, api
from odoo.exceptions import UserError


class DayflowPayroll(models.Model):
    _name = 'dayflow.payroll'
    _description = 'Dayflow Payroll / Salary Structure'
    _order = 'effective_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ------------------------------------------------------------------
    # Employee relationship — the single source of truth for who this
    # payroll record belongs to. Never duplicate employee fields here.
    # ------------------------------------------------------------------
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Salary components
    # ------------------------------------------------------------------
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    basic_salary = fields.Monetary(
        string='Basic Salary',
        currency_field='currency_id',
        required=True,
        tracking=True,
    )
    allowances = fields.Monetary(
        string='Allowances',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='Total allowances — HRA, transport, medical, etc.',
    )
    deductions = fields.Monetary(
        string='Deductions',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help='Total deductions — tax, PF, loan repayments, etc.',
    )
    net_salary = fields.Monetary(
        string='Net Salary',
        currency_field='currency_id',
        compute='_compute_net_salary',
        store=True,
        tracking=True,
        help='Computed: basic_salary + allowances - deductions',
    )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    effective_date = fields.Date(
        string='Effective From',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    notes = fields.Text(
        string='Notes / Remarks',
        help='Internal HR notes. Not visible to employees.',
    )

    # ------------------------------------------------------------------
    # Computed net salary
    # ------------------------------------------------------------------
    @api.depends('basic_salary', 'allowances', 'deductions')
    def _compute_net_salary(self):
        for rec in self:
            rec.net_salary = rec.basic_salary + rec.allowances - rec.deductions

    # ------------------------------------------------------------------
    # Audit trail — automatically log every salary field change
    # ------------------------------------------------------------------
    def write(self, vals):
        audit_fields = {'basic_salary', 'allowances', 'deductions'}
        for rec in self:
            for fname in audit_fields.intersection(vals.keys()):
                old_val = getattr(rec, fname, None)
                new_val = vals[fname]
                if old_val != new_val:
                    self.env['dayflow.audit.log'].sudo().log(
                        model='dayflow.payroll',
                        res_id=rec.id,
                        action='update',
                        field_name=fname,
                        old_value=str(old_val),
                        new_value=str(new_val),
                    )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Prevent employees from creating payroll records
    # ACL in ir.model.access.csv is the primary guard; this is a
    # second line of defence in case ACL is misconfigured.
    # ------------------------------------------------------------------
    @api.model
    def create(self, vals):
        if not self.env.user.has_group('dayflow.group_dayflow_hr_admin'):
            raise UserError('Only HR/Admin can create payroll records.')
        return super().create(vals)
