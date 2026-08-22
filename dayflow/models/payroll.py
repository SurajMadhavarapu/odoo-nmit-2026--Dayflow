# -*- coding: utf-8 -*-
"""
Dayflow - Payroll / Salary Structure Model
Hackathon MVP: one payroll record per employee per pay period.

INTEGRATION CONTRACT:
  model  : dayflow.payroll
  fields :
    employee_id          Many2one hr.employee   required
    pay_period           Char                   e.g. "August 2026"
    currency_id          Many2one res.currency  defaults to company currency
    basic_salary         Monetary               required
    house_rent_allowance Monetary               default 0
    transport_allowance  Monetary               default 0
    other_allowances     Monetary               default 0
    gross_salary         Monetary (computed)    sum of earnings
    provident_fund       Monetary               default 0
    tax_deduction        Monetary               default 0
    other_deductions     Monetary               default 0
    total_deductions     Monetary (computed)    sum of deductions
    net_salary           Monetary (computed)    gross - total_deductions
    state                Selection              draft | confirmed | paid
    notes                Text                   HR internal notes

  Actions:
    action_confirm()     HR: draft → confirmed
    action_mark_paid()   HR: confirmed → paid
    action_reset_draft() HR: any → draft

  Permissions:
    Employee : read own record only (enforced at model + ACL level)
    HR Admin : full CRUD
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class DayflowPayroll(models.Model):
    _name = 'dayflow.payroll'
    _description = 'Dayflow Payroll / Salary Structure'
    _order = 'employee_id, pay_period desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    pay_period = fields.Char(
        string='Pay Period',
        required=True,
        help='e.g. "August 2026"',
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    state = fields.Selection(
        selection=[
            ('draft',     'Draft'),
            ('confirmed', 'Confirmed'),
            ('paid',      'Paid'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Earnings
    # ------------------------------------------------------------------
    basic_salary = fields.Monetary(
        string='Basic Salary',
        currency_field='currency_id',
        required=True,
        default=0.0,
        tracking=True,
    )
    house_rent_allowance = fields.Monetary(
        string='HRA',
        currency_field='currency_id',
        default=0.0,
        help='House Rent Allowance',
        tracking=True,
    )
    transport_allowance = fields.Monetary(
        string='Transport Allowance',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    other_allowances = fields.Monetary(
        string='Other Allowances',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    gross_salary = fields.Monetary(
        string='Gross Salary',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    # ------------------------------------------------------------------
    # Deductions
    # ------------------------------------------------------------------
    provident_fund = fields.Monetary(
        string='PF Deduction',
        currency_field='currency_id',
        default=0.0,
        help='Provident Fund contribution',
        tracking=True,
    )
    tax_deduction = fields.Monetary(
        string='Tax Deduction',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    other_deductions = fields.Monetary(
        string='Other Deductions',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    total_deductions = fields.Monetary(
        string='Total Deductions',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    # ------------------------------------------------------------------
    # Net
    # ------------------------------------------------------------------
    net_salary = fields.Monetary(
        string='Net Salary',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )

    notes = fields.Text(
        string='Notes',
        help='Internal HR notes — not visible to employees in the UI',
    )

    # ------------------------------------------------------------------
    # Computed totals
    # ------------------------------------------------------------------
    @api.depends(
        'basic_salary', 'house_rent_allowance', 'transport_allowance', 'other_allowances',
        'provident_fund', 'tax_deduction', 'other_deductions',
    )
    def _compute_totals(self):
        for rec in self:
            gross = (
                rec.basic_salary
                + rec.house_rent_allowance
                + rec.transport_allowance
                + rec.other_allowances
            )
            deductions = (
                rec.provident_fund
                + rec.tax_deduction
                + rec.other_deductions
            )
            rec.gross_salary = gross
            rec.total_deductions = deductions
            rec.net_salary = gross - deductions

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains(
        'basic_salary', 'house_rent_allowance', 'transport_allowance', 'other_allowances',
        'provident_fund', 'tax_deduction', 'other_deductions',
    )
    def _check_non_negative(self):
        monetary_fields = [
            'basic_salary', 'house_rent_allowance', 'transport_allowance', 'other_allowances',
            'provident_fund', 'tax_deduction', 'other_deductions',
        ]
        for rec in self:
            for fname in monetary_fields:
                if rec[fname] < 0:
                    raise ValidationError(
                        _('Salary field "%s" cannot be negative.') % fname
                    )

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_confirm(self):
        self.ensure_one()
        if not self.env.user.has_group('dayflow.group_dayflow_hr_admin'):
            raise UserError(_('Only HR/Admin users can confirm payroll records.'))
        if self.state != 'draft':
            raise UserError(_('Only draft records can be confirmed.'))
        self.write({'state': 'confirmed'})
        self._audit_salary('confirm')

    def action_mark_paid(self):
        self.ensure_one()
        if not self.env.user.has_group('dayflow.group_dayflow_hr_admin'):
            raise UserError(_('Only HR/Admin users can mark payroll as paid.'))
        if self.state != 'confirmed':
            raise UserError(_('Only confirmed records can be marked as paid.'))
        self.write({'state': 'paid'})
        self._audit_salary('paid')

    def action_reset_draft(self):
        self.ensure_one()
        if not self.env.user.has_group('dayflow.group_dayflow_hr_admin'):
            raise UserError(_('Only HR/Admin users can reset payroll records.'))
        self.write({'state': 'draft'})

    # ------------------------------------------------------------------
    # Security: employees cannot write payroll
    # ------------------------------------------------------------------
    def write(self, vals):
        if not self.env.user.has_group('dayflow.group_dayflow_hr_admin') and not self.env.su:
            raise UserError(
                _('Employees cannot modify salary/payroll records. Contact HR.')
            )
        # Audit all salary field changes
        salary_fields = {
            'basic_salary', 'house_rent_allowance', 'transport_allowance',
            'other_allowances', 'provident_fund', 'tax_deduction', 'other_deductions',
        }
        for rec in self:
            for fname in salary_fields & set(vals.keys()):
                self.env['dayflow.audit.log'].sudo().create({
                    'user_id': self.env.uid,
                    'model_name': self._name,
                    'record_id': rec.id,
                    'record_name': rec.display_name,
                    'action': 'update',
                    'field_name': fname,
                    'old_value': str(rec[fname]),
                    'new_value': str(vals[fname]),
                })
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group('dayflow.group_dayflow_hr_admin') and not self.env.su:
            raise UserError(_('Employees cannot delete payroll records.'))
        return super().unlink()

    def _audit_salary(self, action):
        self.env['dayflow.audit.log'].sudo().create({
            'user_id': self.env.uid,
            'model_name': self._name,
            'record_id': self.id,
            'record_name': self.display_name,
            'action': action if action in ('confirm', 'update') else 'update',
            'field_name': 'state',
            'old_value': '',
            'new_value': self.state,
        })
