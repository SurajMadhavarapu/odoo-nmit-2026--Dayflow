# Dayflow HRMS — Backend Integration Contract

> **Module:** `dayflow_hr`
> **Last updated:** 2026-08-22
> **Branch:** `feature/mani-hr-core`
> **Odoo version:** 17.0

This is the **stable field and model contract** for all Dayflow backend models.

> ⚠️ Do NOT rename models, fields, selection values, or method names once
> integration begins. If a change is needed: tell Suraj first, then the
> affected teammate, then update this file.

---

## Team Ownership

| Domain | Owner | Files |
|--------|-------|-------|
| Auth, registration, session APIs, architecture | **Suraj** | `models/res_users.py`, `controllers/main.py`, `security/hr_security.xml` (groups) |
| Employee fields, payroll, attendance model, leave model, audit trail, security rules | **Mani** | `models/hr_employee.py` (df_* fields), `models/attendance.py`, `models/leave.py`, `models/payroll.py`, `models/audit_log.py`, all views |
| Dashboards, UX, demo presentation | **Harshith** | extend `views/` dashboards, `views/employee_views.xml` |
| QA / integration verification | **Harshith** | test checklist in this file |

---

## Security Groups (canonical — do NOT rename)

| XML ID | Name | Purpose |
|--------|------|---------|
| `dayflow_hr.group_dayflow_employee` | Employee | Regular employees |
| `dayflow_hr.group_dayflow_hr_admin` | HR / Admin | HR officers and admins (implies Employee group) |

**In views (Odoo 17):**
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

**Base model:** `hr.employee` (Odoo built-in, extended by Suraj and Mani)

### Canonical Employee ID

> `employee_code` is the ONE canonical Dayflow Employee ID.
> `df_employee_id` does NOT exist. Never reference it.

### Suraj's fields on `hr.employee`

| Field | Type | Notes |
|-------|------|-------|
| `employee_code` | Char, unique, indexed | **THE canonical Dayflow Employee ID** e.g. `DF-001` |

### Mani's df_* fields on `hr.employee`

| Field | Type | Editable by |
|-------|------|-------------|
| `df_employment_type` | Selection: `full_time\|part_time\|contract\|intern` | HR Admin |
| `df_joining_date` | Date | HR Admin |
| `df_role` | Selection: `employee\|hr_admin` | HR Admin (UI routing hint; security via groups) |
| `df_phone` | Char | Employee (own) |
| `df_address` | Text | Employee (own) |
| `df_date_of_birth` | Date | HR Admin only |
| `df_gender` | Selection | HR Admin only |
| `df_emergency_contact` | Char | Employee (own) |
| `df_emergency_phone` | Char | Employee (own) |
| `df_active` | Boolean | HR Admin |
| `df_attendance_ids` | One2many → `dayflow.attendance` (inverse: `employee_id`) | Read in views |
| `df_leave_ids` | One2many → `dayflow.leave.request` (inverse: `employee_id`) | Read in views |
| `df_payroll_ids` | One2many → `dayflow.payroll` (inverse: `employee_id`) | Read in views |
| `df_attendance_count` | Integer (computed) | Stat button |
| `df_leave_count` | Integer (computed) | Stat button |

### Standard `hr.employee` fields to use (do NOT duplicate)

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
**Owner:** Mani (model + views)

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one `hr.employee` | Required, indexed |
| `date` | Date | Required; **SQL UNIQUE per employee** |
| `check_in` | Datetime | Optional |
| `check_out` | Datetime | Optional; must be strictly after `check_in` |
| `worked_hours` | Float (computed, stored) | `(check_out - check_in)` in hours |
| `status` | Selection | `present\|absent\|half_day\|leave` |
| `notes` | Text | Optional |

**`status` values (stable — do not rename):**
```
present   Present
absent    Absent
half_day  Half Day
leave     Leave
```

**SQL constraint:** `UNIQUE(employee_id, date)` — one record per employee per day.

**API constraints:**
- `check_out > check_in` (ValidationError if violated)
- `date <= today` (no future records)

**Form button actions (type="object"):**
```xml
<button name="action_check_in"  type="object"/>   <!-- sets check_in, status=present -->
<button name="action_check_out" type="object"/>   <!-- sets check_out, refines status -->
```

**Python helper (for UI layer):**
```python
# Get or create today's record for an employee. Safe to call multiple times.
record = self.env['dayflow.attendance'].get_or_create_today(employee_id)
# employee_id = integer ID of hr.employee record
```

**Leave → Attendance sync:**
When `leave.action_approve()` is called, `_sync_attendance_for_leave()` marks
all dates in `date_from..date_to` as `status='leave'` in `dayflow.attendance`.
This is automatic — no UI code needed. You can override `_sync_attendance_for_leave()`
without touching `leave.py`.

---

## 3. Leave Request

**Model:** `dayflow.leave.request`
**Owner:** Mani (model + views)

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one `hr.employee` | Required; defaults to logged-in employee |
| `leave_type` | Selection | `paid\|sick\|unpaid` |
| `date_from` | Date | Required |
| `date_to` | Date | Required; must be ≥ `date_from` |
| `number_of_days` | Integer (computed, stored) | Auto-calculated |
| `remarks` | Text | Employee fills on creation |
| `state` | Selection | `draft\|pending\|approved\|rejected` |
| `hr_comment` | Text | HR fills on approve/reject decision |
| `approved_by` | Many2one `res.users` | Auto-set on approve/reject |
| `approved_date` | Datetime | Auto-set on approve/reject |

**`state` values (stable — do not rename):**
```
draft     Draft
pending   Pending (submitted, awaiting HR)
approved  Approved
rejected  Rejected
```

**`leave_type` values (stable):**
```
paid      Paid Leave
sick      Sick Leave
unpaid    Unpaid Leave
```

**Workflow — Python (type="object"):**
```python
action_submit()          # Employee: draft → pending   (uses sudo internally)
action_approve()         # HR Admin: pending → approved (syncs attendance)
action_reject()          # HR Admin: pending → rejected
action_reset_to_draft()  # HR Admin: rejected/pending → draft
```

**Security enforced at model level:**
- Employees cannot directly write `state`, `hr_comment`, `approved_by`, `approved_date`
- Employees cannot approve/reject (UserError raised in action methods)
- Employees cannot submit another employee's leave

**Overlap validation:** Active (approved/pending) leaves for the same employee
on overlapping dates are blocked by `@api.constrains`.

---

## 4. Payroll

**Model:** `dayflow.payroll`
**Owner:** Mani

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one `hr.employee` | Required |
| `pay_period` | Char | e.g. `"August 2026"` |
| `currency_id` | Many2one `res.currency` | Defaults to company currency |
| `basic_salary` | Monetary | Required |
| `house_rent_allowance` | Monetary | Default 0 |
| `transport_allowance` | Monetary | Default 0 |
| `other_allowances` | Monetary | Default 0 |
| `gross_salary` | Monetary (computed) | Sum of earnings |
| `provident_fund` | Monetary | Default 0 |
| `tax_deduction` | Monetary | Default 0 |
| `other_deductions` | Monetary | Default 0 |
| `total_deductions` | Monetary (computed) | Sum of deductions |
| `net_salary` | Monetary (computed) | gross − total_deductions |
| `state` | Selection | `draft\|confirmed\|paid` |
| `notes` | Text | HR internal only |

**Permissions:**
- Employee: read own records only (ACL + `write()` guard)
- HR Admin: full CRUD

**Workflow methods (HR Admin only):**
```python
action_confirm()      # draft → confirmed
action_mark_paid()    # confirmed → paid
action_reset_draft()  # any → draft
```

**All salary changes are audited automatically via `dayflow.audit.log`.**

---

## 5. Audit Log

**Model:** `dayflow.audit.log`
**Owner:** Mani — append-only, HR Admin read-only via UI

| Field | Type |
|-------|------|
| `user_id` | Many2one `res.users` |
| `timestamp` | Datetime (auto) |
| `model_name` | Char |
| `record_id` | Integer |
| `record_name` | Char |
| `record_ref` | Char (computed, not stored) |
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
    'action':      'approve',      # from selection above
    'field_name':  'state',
    'old_value':   'pending',
    'new_value':   'approved',
})
```

---

## Authentication APIs (Suraj owns — do not modify)

```python
# Server-side helper (called during registration flow)
env['res.users'].sudo().register_dayflow_user(employee_id, email, password, role, name=None)
# employee_id = employee_code value e.g. "DF-001"
```

HTTP JSON endpoints:
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/dayflow/signup` | POST | none | Register new user |
| `/api/dayflow/login` | POST | none | Login, returns session |
| `/dayflow/auth/logout` | POST | user | Logout |
| `/api/dayflow/session` | GET/POST | user | Get current session info |

---

## Module Setup

```bash
# 1. Start Docker environment
docker compose up -d

# 2. Wait for Odoo to be ready (check logs)
docker compose logs -f web

# 3. Create the database if first run:
#    Open http://localhost:8069 → "Manage Databases" → Create new DB
#    DB name: dayflow_db  (matches odoo.conf)
#    Password: admin

# 4. Install the module:
#    Apps → Update Apps List → search "Dayflow HRMS" → Install
#    OR via CLI:
docker compose exec web odoo -d dayflow_db -i dayflow_hr --stop-after-init

# 5. Upgrade after code changes:
docker compose exec web odoo -d dayflow_db -u dayflow_hr --stop-after-init
```

---

## Demo Credentials (password: `Dayflow@123`)

| Name | Login | Role | employee_code |
|------|-------|------|---------------|
| Priya Sharma | priya.sharma@dayflow.demo | HR Admin | DF-001 |
| Ravi Kumar | ravi.kumar@dayflow.demo | Employee | DF-002 |
| Anita Reddy | anita.reddy@dayflow.demo | Employee | DF-003 |
| Kiran Patel | kiran.patel@dayflow.demo | Employee | DF-004 |

**Pre-loaded demo states for live demo flow:**
- **Kiran:** sick leave **APPROVED** — attendance 20–21 Aug marked as `leave`
- **Ravi:** paid leave **DRAFT** — submit live → HR approves in demo
- **Anita:** unpaid leave **REJECTED**
- **Ravi + Anita:** payroll **CONFIRMED**
- **Kiran:** payroll **DRAFT** — confirm live in demo

---

## Runtime Test Checklist (Harshith / Suraj)

### Attendance
- [ ] Employee check-in button creates check_in timestamp, sets status=present
- [ ] Employee check-out sets check_out, worked_hours computed correctly
- [ ] Half-day status auto-set when worked_hours < 7
- [ ] Duplicate same-day attendance record rejected (SQL constraint)
- [ ] check_out before check_in rejected (api.constrains)
- [ ] Future date rejected (api.constrains)
- [ ] Employee cannot see another employee's attendance (record rule)
- [ ] HR Admin sees all attendance records

### Leave
- [ ] Employee creates leave request (state = draft)
- [ ] Employee submits leave (draft → pending)
- [ ] Employee cannot approve own leave (UserError)
- [ ] Employee cannot directly write `state` field (UserError)
- [ ] HR Admin sees all leave requests
- [ ] HR Admin approves → state = approved, approved_by set, attendance synced
- [ ] HR Admin rejects → state = rejected, hr_comment saved
- [ ] Overlapping approved/pending leaves blocked for same employee
- [ ] date_to < date_from rejected

### Payroll
- [ ] Employee reads own payroll (read-only)
- [ ] Employee write on payroll raises UserError
- [ ] HR Admin confirms payroll (draft → confirmed)
- [ ] HR Admin marks paid (confirmed → paid)
- [ ] Salary change creates audit log entry

### Security
- [ ] Employee record rule: employee sees only own hr.employee record
- [ ] Attendance record rule: employee sees only own attendance
- [ ] Leave record rule: employee sees only own leave
- [ ] Payroll ACL: employee has perm_read=1, perm_write=0

### Demo Data
- [ ] 4 users, 4 employees loaded
- [ ] 6 attendance rows (present, half_day, absent, leave ×2 for Kiran)
- [ ] 3 leave requests (approved, draft, rejected)
- [ ] 3 payroll records (confirmed ×2, draft ×1)

---

## Files in this Branch

```
dayflow_hr/
├── __init__.py
├── __manifest__.py          depends: base, mail, hr
├── controllers/
│   ├── __init__.py
│   └── main.py              Suraj: auth endpoints
├── models/
│   ├── __init__.py
│   ├── hr_employee.py       extend hr.employee (Suraj: employee_code; Mani: df_* fields)
│   ├── res_users.py         Suraj: registration helper
│   ├── attendance.py        dayflow.attendance
│   ├── leave.py             dayflow.leave.request
│   ├── payroll.py           dayflow.payroll
│   └── audit_log.py         dayflow.audit.log
├── security/
│   ├── hr_security.xml      groups + all record rules
│   └── ir.model.access.csv  ACL table
├── views/
│   ├── employee_views.xml   extends hr.employee (Odoo 17)
│   ├── attendance_views.xml (Odoo 17)
│   ├── leave_views.xml      (Odoo 17)
│   ├── payroll_views.xml    (Odoo 17)
│   ├── audit_log_views.xml
│   └── menu_views.xml
├── data/
│   └── demo_data.xml        4 users, 4 employees, 6 attendance, 3 leave, 3 payroll
└── INTEGRATION_CONTRACT.md  this file
```
