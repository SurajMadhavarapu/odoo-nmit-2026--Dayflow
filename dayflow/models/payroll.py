# -*- coding: utf-8 -*-
"""
Dayflow — Payroll / Salary Model
MVP salary structure. Employees can view (read-only), HR/Admin can update.

Owner: Mani (HR Core / Data Layer)
Integration consumers: Harshith (Dashboard salary card), Suraj (auth/access)

Kept intentionally simple for hackathon MVP:
- Basic earnings / deductions / net salary
- One active payroll record per employee
- All changes are audit-logged
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class DayflowPayroll(models.Model):
    _name = 'dayflow.payroll'
    _description = 'Dayflow Payroll / Salary Structure'
    _order = 'employee_id, effective_date desc'
    _rec_name = 'display_name'

    # ------------------------------------------------------------------
    # Core fields
    # ------------------------------------------------------------------
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
    )
    effective_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today,
        help='Date from which this salary structure is active',
    )

    # Earnings
    basic_salary = fields.Float(
        string='Basic Salary',
        required=True,
        digits=(12, 2),
    )
    house_rent_allowance = fields.Float(
        string='House Rent Allowance (HRA)',
        digits=(12, 2),
        default=0.0,
    )
    transport_allowance = fields.Float(
        string='Transport Allowance',
        digits=(12, 2),
        default=0.0,
    )
    other_allowances = fields.Float(
        string='Other Allowances',
        digits=(12, 2),
        default=0.0,
    )
    gross_salary = fields.Float(
        string='Gross Salary',
        compute='_compute_gross_and_net',
        store=True,
        digits=(12, 2),
    )

    # Deductions
    tax_deduction = fields.Float(
        string='Tax Deduction',
        digits=(12, 2),
        default=0.0,
    )
    provident_fund = fields.Float(
        string='Provident Fund (PF)',
        digits=(12, 2),
        default=0.0,
    )
    other_deductions = fields.Float(
        string='Other Deductions',
        digits=(12, 2),
        default=0.0,
    )
    total_deductions = fields.Float(
        string='Total Deductions',
        compute='_compute_gross_and_net',
        store=True,
        digits=(12, 2),
    )

    # Net
    net_salary = fields.Float(
        string='Net Salary',
        compute='_compute_gross_and_net',
        store=True,
        digits=(12, 2),
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.ref('base.INR', raise_if_not_found=False),
    )
    notes = fields.Text(string='Notes')

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------
    display_name = fields.Char(
        string='Label',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends(
        'basic_salary', 'house_rent_allowance',
        'transport_allowance', 'other_allowances',
        'tax_deduction', 'provident_fund', 'other_deductions',
    )
    def _compute_gross_and_net(self):
        for rec in self:
            gross = (
                rec.basic_salary
                + rec.house_rent_allowance
                + rec.transport_allowance
                + rec.other_allowances
            )
            deductions = (
                rec.tax_deduction
                + rec.provident_fund
                + rec.other_deductions
            )
            rec.gross_salary = gross
            rec.total_deductions = deductions
            rec.net_salary = gross - deductions

    @api.depends('employee_id', 'effective_date')
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or 'Employee'
            date = str(rec.effective_date) if rec.effective_date else ''
            rec.display_name = 'Payroll — %s (%s)' % (emp, date)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('basic_salary')
    def _check_basic_salary(self):
        for rec in self:
            if rec.basic_salary < 0:
                raise ValidationError('Basic salary cannot be negative.')

    @api.constrains('tax_deduction', 'provident_fund', 'other_deductions')
    def _check_deductions(self):
        for rec in self:
            for field_name in ('tax_deduction', 'provident_fund', 'other_deductions'):
                val = getattr(rec, field_name)
                if val < 0:
                    raise ValidationError('%s cannot be negative.' % field_name.replace('_', ' ').title())

    # ------------------------------------------------------------------
    # Override write to enforce permissions and audit salary changes
    # ------------------------------------------------------------------
    def write(self, vals):
        # Only HR/Admin can update salary records
        if not self.env.user.has_group('dayflow.group_dayflow_hr_admin'):
            raise UserError('Only HR/Admin users can modify salary records.')

        # Editable source fields that can actually appear in vals.
        # net_salary / gross_salary / total_deductions are computed+stored fields —
        # they are NEVER passed in vals; Odoo recomputes them automatically.
        # Including them here caused: AttributeError: 'dayflow.payroll' object
        # has no attribute 'net' (cache miss before first compute run).
        auditable_fields = [
            'basic_salary',
            'house_rent_allowance',
            'transport_allowance',
            'other_allowances',
            'tax_deduction',
            'provident_fund',
            'other_deductions',
        ]

        # Capture old computed net_salary before the write so we can log the
        # before/after net change as a summary entry.
        old_net_by_id = {rec.id: rec.net_salary for rec in self}

        for rec in self:
            for field in auditable_fields:
                if field in vals:
                    self.env['dayflow.audit.log'].sudo().create({
                        'user_id': self.env.uid,
                        'model_name': self._name,
                        'record_id': rec.id,
                        'record_name': rec.display_name,
                        'action': 'salary_update',
                        'field_name': field,
                        'old_value': str(getattr(rec, field)),
                        'new_value': str(vals[field]),
                    })

        result = super().write(vals)

        # After write, log the resulting net_salary change if any source field changed.
        if any(f in vals for f in auditable_fields):
            for rec in self:
                new_net = rec.net_salary  # safely read after compute has run
                old_net = old_net_by_id.get(rec.id, 0.0)
                if new_net != old_net:
                    self.env['dayflow.audit.log'].sudo().create({
                        'user_id': self.env.uid,
                        'model_name': self._name,
                        'record_id': rec.id,
                        'record_name': rec.display_name,
                        'action': 'salary_update',
                        'field_name': 'net_salary',
                        'old_value': str(old_net),
                        'new_value': str(new_net),
                    })

        return result
