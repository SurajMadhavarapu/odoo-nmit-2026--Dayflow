# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class DayflowAuthController(http.Controller):

    @http.route('/api/dayflow/signup', type='json', auth='none', methods=['POST'], csrf=False)
    def signup(self, **kwargs):
        """
        JSON API endpoint for Dayflow User Registration.
        Payload: { "employee_id": "EMP001", "email": "user@example.com", "password": "SecretPassword123", "role": "Employee", "name": "John Doe" }
        """
        data = request.jsonrequest or kwargs
        employee_id = data.get('employee_id')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        name = data.get('name')

        try:
            res = request.env['res.users'].sudo().register_dayflow_user(
                employee_id=employee_id,
                email=email,
                password=password,
                role=role,
                name=name
            )
            return res
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/dayflow/login', type='json', auth='none', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        """
        JSON API endpoint for Dayflow User Login using native Odoo session authentication.
        Payload: { "login": "user@example.com", "password": "SecretPassword123" }
        """
        data = request.jsonrequest or kwargs
        login = data.get('login') or data.get('email')
        password = data.get('password')

        if not login or not password:
            return {'status': 'error', 'message': 'Login and password are required.'}

        try:
            # Native Odoo Session Authentication
            uid = request.session.authenticate(request.db, login, password)
            if not uid:
                return {'status': 'error', 'message': 'Invalid login credentials or inactive user.'}

            user = request.env['res.users'].browse(uid)
            employee = request.env['hr.employee'].sudo().search([('user_id', '=', uid)], limit=1)

            # Determine Dayflow Role
            emp_group = request.env.ref('dayflow_hr.group_dayflow_employee', raise_if_not_found=False)
            admin_group = request.env.ref('dayflow_hr.group_dayflow_hr_admin', raise_if_not_found=False)

            if admin_group and admin_group in user.groups_id:
                role = 'hr_admin'
            elif emp_group and emp_group in user.groups_id:
                role = 'employee'
            else:
                role = 'unassigned'

            return {
                'status': 'success',
                'session_id': request.session.sid,
                'uid': uid,
                'login': user.login,
                'name': user.name,
                'role': role,
                'employee_id': employee.id if employee else False,
                'employee_code': employee.employee_code if employee else False,
            }
        except Exception as e:
            return {'status': 'error', 'message': f'Authentication failed: {str(e)}'}

    @http.route('/api/dayflow/session', type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def session_info(self, **kwargs):
        """
        JSON API endpoint to check currently authenticated session info.
        """
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

        emp_group = request.env.ref('dayflow_hr.group_dayflow_employee', raise_if_not_found=False)
        admin_group = request.env.ref('dayflow_hr.group_dayflow_hr_admin', raise_if_not_found=False)

        if admin_group and admin_group in user.groups_id:
            role = 'hr_admin'
        elif emp_group and emp_group in user.groups_id:
            role = 'employee'
        else:
            role = 'unassigned'

        return {
            'status': 'authenticated',
            'uid': user.id,
            'login': user.login,
            'name': user.name,
            'role': role,
            'employee_id': employee.id if employee else False,
            'employee_code': employee.employee_code if employee else False,
        }
