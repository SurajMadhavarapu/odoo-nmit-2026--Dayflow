# Dayflow HRMS — Backend Integration Contract

> **Module:** `dayflow_hr`
> **Last updated:** 2026-08-22
> **Branch:** `feature/mani-hr-core`

This is the **stable field contract** for all Dayflow backend models.

> ⚠️ Do NOT rename models, fields, or selection values once integration begins.
> If a change is needed: tell Suraj first, then the affected teammate, then update this file.

---

## Team Ownership

| Domain | Owner | Files |
|--------|-------|-------|
| Auth, registration, session APIs, architecture | **Suraj** | `models/res_users.py`, `controllers/main.py`, `security/hr_security.xml` (groups) |
| Employee profile fields, payroll, attendance model, leave model, audit trail, security rules | **Mani** | `models/hr_employee.py` (df_* fields), `models/attendance.py`, `models/leave.py`, `models/payroll.py`, `models/audit_log.py` |
| Attendance & leave workflow UI | **Kunam** | extend `views/attendance_views.xml`, `views/leave_views.xml` |
| Dashboards, UX, demo presentation | **Harshith** | `views/` dashboards, extend `views/employee_views.xml` |

---

## Security Groups (canonical — do NOT rename)

| XML ID | Name | Purpose |
|--------|------|---------|
| `dayflow_hr.group_dayflow_employee` | Employee | Regular employees |
| `dayflow_hr.group_dayflow_hr_admin` | HR / Admin | HR officers and admins |

**In views:**
```xml
groups="dayflow_hr.group_dayflow_hr_admin"
groups="dayflow_hr.group_dayflow_employee"
```

**In Python:**
```python
self.env.user.has_group('dayflow_hr.group_dayflow_hr_admin')
self.env.user.has_group('dayflow_hr.group_dayflow_employee')
```

---

## 1. Employee

**Base model:** `hr.employee` (Odoo built-in, extended by both Suraj and Mani)

### Canonical Employee ID

| Field | Owner | Notes |
|-------|-------|-------|
| `employee_code` | **Suraj** | **THE canonical Dayflow Employee ID** — unique, indexed |

> `df_employee_id` does NOT exist. Use `employee_code` everywhere.

### Suraj's fields on `hr.employee`

| Field | Type | Notes |
|-------|------|-------|
| `employee_code` | Char (unique) | Canonical employee ID e.g. DF-001 |

### Mani's added df_* fields on `hr.employee`

| Field | Type | Editable by |
|-------|------|-------------|
| `df_employment_type` | Selection: `full_time\|part_time\|contract\|intern` | HR Admin |
| `df_joining_date` | Date | HR Admin |
| `df_role` | Selection: `employee\|hr_admin` | HR Admin (UI routing hint only) |
| `df_phone` | Char | Employee (own) |
| `df_address` | Text | Employee (own) |
| `df_date_of_birth` | Date | HR Admin only |
| `df_gender` | Selection | HR Admin only |
| `df_emergency_contact` | Char | Employee (own) |
| `df_emergency_phone` | Char | Employee (own) |
| `df_active` | Boolean | HR Admin |
| `df_attendance_ids` | One2many → `dayflow.attendance` | Read in views |
| `df_leave_ids` | One2many → `dayflow.leave.request` | Read in views |
| `df_payroll_ids` | One2many → `dayflow.payroll` | Read in views |
| `df_attendance_count` | Integer (computed) | Stat button |
| `df_leave_count` | Integer (computed) | Stat button |

### Existing `hr.employee` fields to use (do NOT duplicate)

| Field | Purpose |
|-------|---------|
| `name` | Full name |
| `work_email` | Work email |
| `job_title` | Job title string |
| `job_id` | Many2one `hr.job` |
| `department_id` | Many2one `hr.department` |
| `image_1920` | Profile picture |
| `active` | Odoo archive flag |
| `user_id` | Linked `res.users` |

---

## 2. Attendance

**Model:** `dayflow.attendance`
**UI Owner:** Kunam

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one `hr.employee` | Required |
| `date` | Date | Required; unique per employee (SQL constraint) |
| `check_in` | Datetime | Optional |
| `check_out` | Datetime | Optional; must be strictly after check_in |
| `worked_hours` | Float (computed, stored) | (check_out - check_in) in hours |
| `status` | Selection | see below |
| `notes` | Text | Optional |

**`status` values (stable):**
```
present   → Present
absent    → Absent
half_day  → Half Day
leave     → Leave
```

**Form button actions:**
```xml
<button name="action_check_in"  type="object"/>
<button name="action_check_out" type="object"/>
```

**Python helper (for Kunam):**
```python
record = self.env['dayflow.attendance'].get_or_create_today(employee_id)
```

**Leave → Attendance sync:**
When `leave.action_approve()` is called, `_sync_attendance_for_leave()` marks
all dates in the leave range as `status='leave'` in `dayflow.attendance`.
Kunam can override `_sync_attendance_for_leave()` without touching `leave.py`.

---

## 3. Leave Request

**Model:** `dayflow.leave.request`
**UI Owner:** Kunam

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one `hr.employee` | Required; defaults to logged-in employee |
| `leave_type` | Selection | `paid\|sick\|unpaid` |
| `date_from` | Date | Required |
| `date_to` | Date | Required; ≥ date_from |
| `number_of_days` | Integer (computed, stored) | Auto |
| `remarks` | Text | Employee fills |
| `state` | Selection | `draft\|pending\|approved\|rejected` |
| `hr_comment` | Text | HR fills on decision |
| `approved_by` | Many2one `res.users` | Auto |
| `approved_date` | Datetime | Auto |

**`state` values (stable):**
```
draft    → Draft
pending  → Pending
approved → Approved
rejected → Rejected
```

**Workflow methods:**
```python
action_submit()          # Employee: draft → pending
action_approve()         # HR Admin: pending → approved
action_reject()          # HR Admin: pending → rejected
action_reset_to_draft()  # HR Admin: rejected/pending → draft
```

---

## 4. Payroll

**Model:** `dayflow.payroll`
**Owner:** Mani

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one `hr.employee` | Required |
| `pay_period` | Char | e.g. "August 2026" |
| `currency_id` | Many2one `res.currency` | Company currency default |
| `basic_salary` | Monetary | Required |
| `house_rent_allowance` | Monetary | Default 0 |
| `transport_allowance` | Monetary | Default 0 |
| `other_allowances` | Monetary | Default 0 |
| `gross_salary` | Monetary (computed) | |
| `provident_fund` | Monetary | Default 0 |
| `tax_deduction` | Monetary | Default 0 |
| `other_deductions` | Monetary | Default 0 |
| `total_deductions` | Monetary (computed) | |
| `net_salary` | Monetary (computed) | gross - deductions |
| `state` | Selection | `draft\|confirmed\|paid` |
| `notes` | Text | HR internal |

**Permissions:**
- Employee: read own only — enforced at ACL + `write()` level
- HR Admin: full CRUD

**Workflow methods (HR Admin only):**
```python
action_confirm()      # draft → confirmed
action_mark_paid()    # confirmed → paid
action_reset_draft()  # any → draft
```

---

## 5. Audit Log

**Model:** `dayflow.audit.log`
**Owner:** Mani

Append-only. HR Admin read-only via UI. Written via `.sudo()` by employee, payroll, leave models.

| Field | Type |
|-------|------|
| `user_id` | Many2one `res.users` |
| `timestamp` | Datetime |
| `model_name` | Char |
| `record_id` | Integer |
| `record_name` | Char |
| `record_ref` | Char (computed) |
| `action` | Selection: `create\|update\|approve\|reject\|submit\|confirm\|archive\|other` |
| `field_name` | Char |
| `old_value` | Char |
| `new_value` | Char |

**Writing from your model:**
```python
self.env['dayflow.audit.log'].sudo().create({
    'user_id':     self.env.uid,
    'model_name':  self._name,
    'record_id':   record.id,
    'record_name': record.display_name,
    'action':      'approve',
    'field_name':  'state',
    'old_value':   'pending',
    'new_value':   'approved',
})
```

---

## Authentication APIs (Suraj owns — do not modify)

```python
env['res.users'].register_dayflow_user(employee_id, email, password, role, name=None)
# employee_id here = employee_code value e.g. "DF-001"
```

HTTP endpoints:
- `POST /api/dayflow/signup`
- `POST /api/dayflow/login`
- `GET/POST /api/dayflow/session`

---

## Demo Credentials (password: `Dayflow@123`)

| Name | Login | Role | employee_code |
|------|-------|------|---------------|
| Priya Sharma | priya.sharma@dayflow.demo | HR Admin | DF-001 |
| Ravi Kumar | ravi.kumar@dayflow.demo | Employee | DF-002 |
| Anita Reddy | anita.reddy@dayflow.demo | Employee | DF-003 |
| Kiran Patel | kiran.patel@dayflow.demo | Employee | DF-004 |

**Pre-loaded demo states:**
- Kiran: sick leave **APPROVED** — attendance 20–21 Aug marked as `leave`
- Ravi: paid leave **DRAFT** — submit live in demo, HR approves
- Anita: unpaid leave **REJECTED**
- Ravi + Anita: payroll **CONFIRMED** | Kiran: payroll **DRAFT** — confirm live

---

## How to Install

```bash
# 1. Copy dayflow_hr/ into your Odoo addons path
cp -r dayflow_hr /path/to/odoo/custom-addons/

# 2. Restart Odoo
# 3. Enable Developer Mode: Settings → General Settings → Activate Developer Mode
# 4. Apps → Update Apps List → search "Dayflow" → Install

# To reload after changes:
./odoo-bin -d <db> -u dayflow_hr
```

---

## Runtime Test Checklist (Suraj / Harshith)

- [ ] Module installs on Odoo 17 without errors
- [ ] `employee_code` unique constraint fires on duplicate
- [ ] Employee cannot read another employee's attendance (record rule)
- [ ] Employee `write()` on payroll raises `UserError`
- [ ] Leave workflow: draft → pending → approved → attendance auto-marked leave
- [ ] Leave workflow: draft → pending → rejected
- [ ] Audit log entries created on salary change
- [ ] HR Admin sees all employees, all attendance, all leave, all payroll
- [ ] Demo data loads: 4 users, 4 employees, 6 attendance rows, 3 leaves, 3 payrolls
