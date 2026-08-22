# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = 'res.users'

    dayflow_role = fields.Selection([
        ('employee', 'Employee'),
        ('hr_admin', 'HR / Admin')
    ], string='Dayflow Role', compute='_compute_dayflow_role', store=True, help="Assigned Dayflow Security Role")

    @api.depends('groups_id')
    def _compute_dayflow_role(self):
        emp_group = self.env.ref('dayflow_hr.group_dayflow_employee', raise_if_not_found=False)
        admin_group = self.env.ref('dayflow_hr.group_dayflow_hr_admin', raise_if_not_found=False)
        for user in self:
            if admin_group and admin_group in user.groups_id:
                user.dayflow_role = 'hr_admin'
            elif emp_group and emp_group in user.groups_id:
                user.dayflow_role = 'employee'
            else:
                user.dayflow_role = False

    @api.model
    def register_dayflow_user(self, employee_id, email, password, role, name=None):
        """
        Server-side registration helper for Dayflow HRMS.
        
        :param employee_id: Unique Employee ID string
        :param email: Unique Email / Login string
        :param password: Password string
        :param role: 'Employee' or 'HR/Admin' (or 'employee'/'hr_admin')
        :param name: Optional Full Name (defaults to Email local-part if omitted)
        :return: Dict with success status, user_id, employee_id, role, message
        """
        # 1. Input Sanitization & Validation
        if not employee_id or not str(employee_id).strip():
            raise ValidationError("Employee ID is required.")
        if not email or not str(email).strip():
            raise ValidationError("Email address is required.")
        if not password or not str(password).strip():
            raise ValidationError("Password is required.")
        if not role or not str(role).strip():
            raise ValidationError("Role is required.")

        emp_code = str(employee_id).strip()
        user_email = str(email).strip().lower()
        raw_password = str(password).strip()
        role_str = str(role).strip()

        # Email format validation
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, user_email):
            raise ValidationError("Invalid email address format.")

        # Role normalization
        if role_str.lower() in ['employee', 'emp']:
            target_role = 'employee'
        elif role_str.lower() in ['hr/admin', 'hr_admin', 'hr', 'admin']:
            target_role = 'hr_admin'
        else:
            raise ValidationError("Invalid role. Allowed roles are 'Employee' or 'HR/Admin'.")

        # 2. Uniqueness Checks
        # Login/Email uniqueness
        existing_user = self.sudo().search([('login', '=', user_email)], limit=1)
        if existing_user:
            raise ValidationError(f"A user with email/login '{user_email}' already exists.")

        # Employee ID uniqueness
        existing_emp = self.env['hr.employee'].sudo().search([('employee_code', '=', emp_code)], limit=1)
        if existing_emp:
            raise ValidationError(f"An employee with Employee ID '{emp_code}' already exists.")

        # 3. Security Group Determination
        emp_group = self.env.ref('dayflow_hr.group_dayflow_employee')
        admin_group = self.env.ref('dayflow_hr.group_dayflow_hr_admin')
        base_group = self.env.ref('base.group_user')

        groups = [(4, base_group.id), (4, emp_group.id)]
        if target_role == 'hr_admin':
            groups.append((4, admin_group.id))

        user_name = name.strip() if name and str(name).strip() else user_email.split('@')[0].replace('.', ' ').title()

        # 4. User Creation (Odoo native password hashing via res.users)
        user_vals = {
            'name': user_name,
            'login': user_email,
            'email': user_email,
            'password': raw_password,
            'groups_id': groups,
            'active': True,
        }
        new_user = self.sudo().create(user_vals)
        new_user.sudo().write({'password': raw_password})

        # 5. Linked HR Employee Profile Creation / Verification
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', new_user.id)], limit=1)
        if not employee:
            emp_vals = {
                'name': user_name,
                'user_id': new_user.id,
                'work_email': user_email,
                'employee_code': emp_code,
                'identification_id': emp_code,
            }
            employee = self.env['hr.employee'].sudo().create(emp_vals)
        else:
            employee.sudo().write({
                'employee_code': emp_code,
                'identification_id': emp_code,
                'work_email': user_email,
            })

        return {
            'status': 'success',
            'user_id': new_user.id,
            'employee_id': employee.id,
            'employee_code': emp_code,
            'login': user_email,
            'role': target_role,
        }
