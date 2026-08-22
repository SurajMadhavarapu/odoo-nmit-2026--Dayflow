# -*- coding: utf-8 -*-
from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_code = fields.Char(
        string='Employee ID',
        copy=False,
        index=True,
        help="Canonical Dayflow Employee ID"
    )

    _sql_constraints = [
        ('employee_code_uniq', 'unique(employee_code)', 'The Employee ID must be unique across all employees!'),
    ]
