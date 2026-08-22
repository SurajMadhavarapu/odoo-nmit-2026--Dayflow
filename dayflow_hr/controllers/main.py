# -*- coding: utf-8 -*-
import json
# pyrefly: ignore [missing-import]
from odoo import http, fields  # type: ignore
from odoo.http import request, Response  # type: ignore
from odoo.exceptions import AccessDenied, ValidationError, UserError  # type: ignore


class DayflowAuthController(http.Controller):

    # =========================================================================
    # AUTHENTICATION ENDPOINTS
    # =========================================================================

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
            request.env.cr.commit()
            return res
        except ValidationError as e:
            request.env.cr.rollback()
            return {'status': 'error', 'code': 'validation_error', 'message': str(e)}
        except Exception as e:
            request.env.cr.rollback()
            return {'status': 'error', 'code': 'server_error', 'message': f'Registration failed: {str(e)}'}

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

            user = request.env['res.users'].sudo().browse(uid)
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
            request.env.cr.rollback()
            return {'status': 'error', 'code': 'invalid_credentials', 'message': 'Invalid email/login or password.'}
        except Exception as e:
            request.env.cr.rollback()
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
    # CORE PROFILE & EMPLOYEE DIRECTORY API
    # =========================================================================

    @http.route('/dayflow/api/profile', type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def get_profile(self, **kwargs):
        """
        GET /dayflow/api/profile
        Resolves the logged-in employee via request.env.user.
        """
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        emp = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not emp:
            return {'status': 'error', 'message': 'No employee profile found linked to current user.'}

        return {
            'status': 'success',
            'data': {
                'id': emp.id,
                'employee_code': emp.employee_code or 'N/A',
                'name': emp.name,
                'work_email': emp.work_email or user.login,
                'df_phone': emp.df_phone or '',
                'df_address': emp.df_address or '',
                'df_employment_type': emp.df_employment_type or 'full_time',
                'df_joining_date': str(emp.df_joining_date) if emp.df_joining_date else '',
                'df_role': emp.df_role or 'employee',
                'df_emergency_contact': emp.df_emergency_contact or '',
                'df_emergency_phone': emp.df_emergency_phone or '',
                'df_attendance_count': emp.df_attendance_count,
                'df_leave_count': emp.df_leave_count,
            }
        }

    @http.route('/dayflow/api/employees', type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def get_employees(self, **kwargs):
        """
        GET /dayflow/api/employees
        Lists employees for organizational directory (HR/Admin only).
        """
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        if not user.has_group('dayflow_hr.group_dayflow_hr_admin'):
            return {'status': 'error', 'message': 'Access denied. HR/Admin privilege required.'}

        employees = request.env['hr.employee'].sudo().search([('df_active', '=', True)], order='employee_code, name')
        result = []
        for e in employees:
            result.append({
                'id': e.id,
                'employee_code': e.employee_code or 'N/A',
                'name': e.name,
                'work_email': e.work_email or '',
                'df_role': e.df_role or 'employee',
                'df_employment_type': e.df_employment_type or 'full_time',
                'df_phone': e.df_phone or '',
            })
        return {
            'status': 'success',
            'data': {
                'total': len(result),
                'employees': result
            }
        }

    # =========================================================================
    # ATTENDANCE API
    # =========================================================================

    @http.route('/dayflow/api/attendance/me', type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def get_my_attendance(self, **kwargs):
        """
        GET /dayflow/api/attendance/me
        Fetches today's attendance and recent history for the logged-in employee.
        """
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        emp = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not emp:
            return {'status': 'error', 'message': 'No employee profile linked to current user.'}

        today_rec = request.env['dayflow.attendance'].sudo().get_or_create_today(emp.id)
        history_recs = request.env['dayflow.attendance'].sudo().search(
            [('employee_id', '=', emp.id)], limit=10, order='date desc'
        )

        history = []
        for h in history_recs:
            history.append({
                'id': h.id,
                'date': str(h.date),
                'check_in': fields.Datetime.to_string(h.check_in) if h.check_in else False,
                'check_out': fields.Datetime.to_string(h.check_out) if h.check_out else False,
                'worked_hours': round(h.worked_hours, 2),
                'status': h.status,
            })

        is_hr = user.has_group('dayflow_hr.group_dayflow_hr_admin')
        hr_stats = {}
        if is_hr:
            today = fields.Date.context_today(request.env['dayflow.attendance'])
            all_today = request.env['dayflow.attendance'].sudo().search([('date', '=', today)])
            hr_stats = {
                'total_employees': request.env['hr.employee'].sudo().search_count([('df_active', '=', True)]),
                'present_today': sum(1 for a in all_today if a.status == 'present'),
                'on_leave_today': sum(1 for a in all_today if a.status == 'leave'),
                'pending_leaves': request.env['dayflow.leave.request'].sudo().search_count([('state', '=', 'pending')]),
            }

        return {
            'status': 'success',
            'data': {
                'today': {
                    'id': today_rec.id,
                    'date': str(today_rec.date),
                    'check_in': fields.Datetime.to_string(today_rec.check_in) if today_rec.check_in else False,
                    'check_out': fields.Datetime.to_string(today_rec.check_out) if today_rec.check_out else False,
                    'worked_hours': round(today_rec.worked_hours, 2),
                    'status': today_rec.status,
                    'is_checked_in': bool(today_rec.check_in and not today_rec.check_out),
                },
                'history': history,
                'hr_stats': hr_stats if is_hr else None
            }
        }

    @http.route('/dayflow/api/attendance/checkin', type='json', auth='user', methods=['POST'], csrf=False)
    def attendance_check_in(self, **kwargs):
        """
        POST /dayflow/api/attendance/checkin
        Calls Mani's action_check_in() on today's attendance record.
        """
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        emp = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not emp:
            return {'status': 'error', 'message': 'No employee profile found.'}

        try:
            today_rec = request.env['dayflow.attendance'].sudo().get_or_create_today(emp.id)
            today_rec.with_user(user.id).action_check_in()
            request.env.cr.commit()
            return {
                'status': 'success',
                'message': 'Check-in recorded successfully.',
                'data': {
                    'attendance': {
                        'id': today_rec.id,
                        'date': str(today_rec.date),
                        'check_in': fields.Datetime.to_string(today_rec.check_in),
                        'status': today_rec.status,
                    }
                }
            }
        except (ValidationError, UserError) as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': f'Check-in failed: {str(e)}'}

    @http.route('/dayflow/api/attendance/checkout', type='json', auth='user', methods=['POST'], csrf=False)
    def attendance_check_out(self, **kwargs):
        """
        POST /dayflow/api/attendance/checkout
        Calls Mani's action_check_out() on today's attendance record.
        """
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        emp = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not emp:
            return {'status': 'error', 'message': 'No employee profile found.'}

        try:
            today_rec = request.env['dayflow.attendance'].sudo().get_or_create_today(emp.id)
            today_rec.with_user(user.id).action_check_out()
            request.env.cr.commit()
            return {
                'status': 'success',
                'message': 'Check-out recorded successfully.',
                'data': {
                    'attendance': {
                        'id': today_rec.id,
                        'date': str(today_rec.date),
                        'check_out': fields.Datetime.to_string(today_rec.check_out),
                        'worked_hours': round(today_rec.worked_hours, 2),
                        'status': today_rec.status,
                    }
                }
            }
        except (ValidationError, UserError) as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': f'Check-out failed: {str(e)}'}

    # =========================================================================
    # LEAVE MANAGEMENT API
    # =========================================================================

    @http.route('/dayflow/api/leave/me', type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def get_my_leaves(self, **kwargs):
        """
        GET /dayflow/api/leave/me
        Fetches leave requests for the logged-in employee (and pending requests for HR/Admin).
        """
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        emp = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not emp:
            return {'status': 'error', 'message': 'No employee profile found.'}

        is_hr = user.has_group('dayflow_hr.group_dayflow_hr_admin')
        my_leaves = request.env['dayflow.leave.request'].sudo().search(
            [('employee_id', '=', emp.id)], order='date_from desc'
        )

        leaves_list = []
        for l in my_leaves:
            leaves_list.append({
                'id': l.id,
                'leave_type': l.leave_type,
                'leave_type_label': dict(l._fields['leave_type'].selection).get(l.leave_type, l.leave_type),
                'date_from': str(l.date_from),
                'date_to': str(l.date_to),
                'number_of_days': l.number_of_days,
                'remarks': l.remarks or '',
                'state': l.state,
                'hr_comment': l.hr_comment or '',
                'approved_by': l.approved_by.name if l.approved_by else '',
            })

        pending_approvals = []
        if is_hr:
            all_pending = request.env['dayflow.leave.request'].sudo().search(
                [('state', '=', 'pending')], order='date_from asc'
            )
            for p in all_pending:
                pending_approvals.append({
                    'id': p.id,
                    'employee_id': p.employee_id.id,
                    'employee_name': p.employee_id.name,
                    'employee_code': p.employee_id.employee_code or 'N/A',
                    'leave_type': p.leave_type,
                    'leave_type_label': dict(p._fields['leave_type'].selection).get(p.leave_type, p.leave_type),
                    'date_from': str(p.date_from),
                    'date_to': str(p.date_to),
                    'number_of_days': p.number_of_days,
                    'remarks': p.remarks or '',
                    'state': p.state,
                })

        return {
            'status': 'success',
            'data': {
                'my_leaves': leaves_list,
                'pending_count': sum(1 for l in leaves_list if l['state'] == 'pending'),
                'approved_count': sum(1 for l in leaves_list if l['state'] == 'approved'),
                'pending_approvals': pending_approvals if is_hr else []
            }
        }

    @http.route('/dayflow/api/leave', type='json', auth='user', methods=['POST'], csrf=False)
    def create_leave_request(self, **kwargs):
        """
        POST /dayflow/api/leave
        Submits a new leave request for the logged-in employee.
        """
        data = kwargs or getattr(request, 'params', {}) or {}
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        emp = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not emp:
            return {'status': 'error', 'message': 'No employee profile linked to user.'}

        leave_type = data.get('leave_type')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        remarks = data.get('remarks', '')

        if not leave_type or not date_from or not date_to:
            return {'status': 'error', 'message': 'Leave type, start date, and end date are required.'}

        try:
            leave = request.env['dayflow.leave.request'].with_user(user.id).create({
                'employee_id': emp.id,
                'leave_type': leave_type,
                'date_from': date_from,
                'date_to': date_to,
                'remarks': remarks,
            })
            leave.action_submit()
            request.env.cr.commit()
            return {
                'status': 'success',
                'message': 'Leave request submitted for approval.',
                'data': {
                    'leave_id': leave.id,
                    'state': leave.state,
                }
            }
        except (ValidationError, UserError) as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': f'Leave submission failed: {str(e)}'}

    @http.route(['/dayflow/api/leave/<int:leave_id>/approve', '/dayflow/api/leave/approve'], type='json', auth='user', methods=['POST'], csrf=False)
    def approve_leave(self, leave_id=None, **kwargs):
        """
        POST /dayflow/api/leave/<id>/approve
        HR Admin approves a leave request.
        """
        data = kwargs or getattr(request, 'params', {}) or {}
        target_id = leave_id or data.get('id') or data.get('leave_id')
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        if not user.has_group('dayflow_hr.group_dayflow_hr_admin'):
            return {'status': 'error', 'message': 'Access denied. Only HR/Admin can approve leave requests.'}

        if not target_id:
            return {'status': 'error', 'message': 'Leave ID is required.'}

        try:
            leave = request.env['dayflow.leave.request'].browse(target_id)
            if not leave.exists():
                return {'status': 'error', 'message': f'Leave request #{target_id} not found.'}
            leave.with_user(user.id).action_approve()
            request.env.cr.commit()
            return {
                'status': 'success',
                'message': f'Leave request #{target_id} approved.',
                'data': {
                    'id': leave.id,
                    'state': leave.state
                }
            }
        except (ValidationError, UserError) as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': f'Approval failed: {str(e)}'}

    @http.route(['/dayflow/api/leave/<int:leave_id>/reject', '/dayflow/api/leave/reject'], type='json', auth='user', methods=['POST'], csrf=False)
    def reject_leave(self, leave_id=None, **kwargs):
        """
        POST /dayflow/api/leave/<id>/reject
        HR Admin rejects a leave request.
        """
        data = kwargs or getattr(request, 'params', {}) or {}
        target_id = leave_id or data.get('id') or data.get('leave_id')
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        if not user.has_group('dayflow_hr.group_dayflow_hr_admin'):
            return {'status': 'error', 'message': 'Access denied. Only HR/Admin can reject leave requests.'}

        if not target_id:
            return {'status': 'error', 'message': 'Leave ID is required.'}

        try:
            leave = request.env['dayflow.leave.request'].browse(target_id)
            if not leave.exists():
                return {'status': 'error', 'message': f'Leave request #{target_id} not found.'}
            leave.with_user(user.id).action_reject()
            request.env.cr.commit()
            return {
                'status': 'success',
                'message': f'Leave request #{target_id} rejected.',
                'data': {
                    'id': leave.id,
                    'state': leave.state
                }
            }
        except (ValidationError, UserError) as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            request.env.cr.rollback()
            return {'status': 'error', 'message': f'Rejection failed: {str(e)}'}

    # =========================================================================
    # PAYROLL API
    # =========================================================================

    @http.route('/dayflow/api/payroll/me', type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def get_my_payroll(self, **kwargs):
        """
        GET /dayflow/api/payroll/me
        Fetches salary statements for the logged-in employee.
        """
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        emp = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not emp:
            return {'status': 'error', 'message': 'No employee profile linked.'}

        payrolls = request.env['dayflow.payroll'].sudo().search(
            [('employee_id', '=', emp.id)], order='pay_period desc'
        )

        result = []
        for p in payrolls:
            result.append({
                'id': p.id,
                'pay_period': p.pay_period,
                'basic_salary': p.basic_salary,
                'house_rent_allowance': p.house_rent_allowance,
                'transport_allowance': p.transport_allowance,
                'other_allowances': p.other_allowances,
                'gross_salary': p.gross_salary,
                'provident_fund': p.provident_fund,
                'tax_deduction': p.tax_deduction,
                'other_deductions': p.other_deductions,
                'total_deductions': p.total_deductions,
                'net_salary': p.net_salary,
                'state': p.state,
                'currency': p.currency_id.symbol or '₹',
            })

        latest = result[0] if result else None

        return {
            'status': 'success',
            'data': {
                'latest': latest,
                'history': result
            }
        }

    @http.route(['/dayflow/api/payroll/<int:employee_id>', '/dayflow/api/payroll/employee'], type='json', auth='user', methods=['GET', 'POST'], csrf=False)
    def get_employee_payroll(self, employee_id=None, **kwargs):
        """
        GET /dayflow/api/payroll/<employee_id>
        Fetches salary records for a specific employee (HR Admin only or own record).
        """
        data = kwargs or getattr(request, 'params', {}) or {}
        target_emp_id = employee_id or data.get('employee_id')
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'User is not authenticated.'}

        if not user.has_group('dayflow_hr.group_dayflow_hr_admin'):
            own_emp = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
            if not own_emp or own_emp.id != target_emp_id:
                return {'status': 'error', 'message': 'Access denied. You can only view your own payroll.'}

        payrolls = request.env['dayflow.payroll'].sudo().search(
            [('employee_id', '=', target_emp_id)], order='pay_period desc'
        )

        result = []
        for p in payrolls:
            result.append({
                'id': p.id,
                'employee_name': p.employee_id.name,
                'pay_period': p.pay_period,
                'basic_salary': p.basic_salary,
                'gross_salary': p.gross_salary,
                'total_deductions': p.total_deductions,
                'net_salary': p.net_salary,
                'state': p.state,
                'currency': p.currency_id.symbol or '₹',
            })

        return {
            'status': 'success',
            'data': {
                'payrolls': result
            }
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
