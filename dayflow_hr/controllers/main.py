# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessDenied, ValidationError

class DayflowAuthController(http.Controller):

    @http.route(['/dayflow/auth/register', '/api/dayflow/signup'], type='json', auth='none', methods=['POST'], csrf=False)
    def register(self, **kwargs):
        """
        JSON API endpoint for Dayflow User Registration.
        Endpoint: POST /dayflow/auth/register
        Payload: { "employee_id": "EMP001", "email": "user@example.com", "password": "SecretPassword123", "role": "Employee", "name": "John Doe" }
        """
        data = kwargs or getattr(request, 'params', {}) or {}
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
        except ValidationError as e:
            return {'status': 'error', 'code': 'validation_error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'code': 'server_error', 'message': 'Registration failed. Please verify user details.'}

    @http.route(['/dayflow/auth/login', '/api/dayflow/login'], type='json', auth='none', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        """
        JSON API endpoint for Dayflow User Login using native Odoo session authentication.
        Endpoint: POST /dayflow/auth/login
        Payload: { "login": "user@example.com", "password": "SecretPassword123" }
        """
        data = kwargs or getattr(request, 'params', {}) or {}
        login = data.get('login') or data.get('email')
        password = data.get('password')

        if not login or not password:
            return {'status': 'error', 'code': 'missing_credentials', 'message': 'Email/login and password are required.'}

        try:
            # Native Odoo Session Authentication
            uid = request.session.authenticate(request.db, login, password)
            if not uid:
                return {'status': 'error', 'code': 'invalid_credentials', 'message': 'Invalid email/login or password.'}

            user = request.env['res.users'].browse(uid)
            if not user.active:
                return {'status': 'error', 'code': 'inactive_user', 'message': 'User account is inactive.'}

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
        except AccessDenied:
            return {'status': 'error', 'code': 'invalid_credentials', 'message': 'Invalid email/login or password.'}
        except Exception as e:
            return {'status': 'error', 'code': 'auth_failed', 'message': 'Authentication failed.'}

    @http.route('/dayflow/auth/logout', type='json', auth='user', methods=['POST'], csrf=False)
    def logout(self, **kwargs):
        """
        JSON API endpoint for Dayflow User Logout using native Odoo session termination.
        Endpoint: POST /dayflow/auth/logout
        """
        try:
            request.session.logout(keep_db=True)
            return {'status': 'success', 'message': 'Logged out successfully.'}
        except Exception as e:
            return {'status': 'error', 'message': 'Logout failed.'}

    @http.route(['/dayflow/auth/me', '/api/dayflow/session'], type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def me(self, **kwargs):
        """
        JSON API endpoint to fetch currently authenticated user and linked employee info.
        Endpoint: GET /dayflow/auth/me
        """
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'code': 'unauthorized', 'message': 'User is not authenticated.'}

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

    # =========================================================================
    # WEB UI ROUTE - Serves Dayflow HRMS Frontend Single Page Application (SPA)
    # =========================================================================
    @http.route(['/', '/dayflow/app', '/dayflow/login'], type='http', auth='none', website=True)
    def render_app(self, **kwargs):
        """
        Serves the Dayflow HRMS Single Page Application UI.
        """
        return request.render('dayflow_hr.dayflow_app_template', {})
