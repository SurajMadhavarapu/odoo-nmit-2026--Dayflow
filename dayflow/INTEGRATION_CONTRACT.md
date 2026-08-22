# Dayflow – Backend Integration Contract

> **Branch:** `feature/mani-hr-core`
> **Last updated:** 2026-08-22
> **Owner:** Mani (HR Core / Data Layer)

This is the **stable field contract** for all Dayflow backend models.

> ⚠️ Do NOT rename models, fields, or selection values after teammates start integrating.
> If a change is needed, tell Suraj first, then the affected teammate.

---

## Team Ownership

| Domain | Owner | Branch |
|--------|-------|--------|
| Auth, architecture, integration, final testing | Suraj | main / feature/suraj-* |
| Employee, Payroll, Security, Audit trail | **Mani** | feature/mani-hr-core |
| Attendance + Leave workflow & UI | Kunam | feature/kunam-* |
| Employee dashboard, HR dashboard, demo prep | Harshith | feature/harshith-* |

---

## Security Groups (canonical — do NOT rename)

| XML ID | Name | Purpose |
|--------|------|---------|
| `dayflow.group_dayflow_employee` | Employee | Regular employees |
| `dayflow.group_dayflow_hr_admin` | HR / Admin | HR officers and admins |

**Use in views:**
```xml
groups="dayflow.group_dayflow_hr_admin"
groups="dayflow.group_dayflow_employee"
```

**Use in Python:**
```python
self.env.user.has_group('dayflow.group_dayflow_hr_admin')
self.env.user.has_group('dayflow.group_dayflow_employee')
```

---

## 1. Employee

**Base model:** `hr.employee` (Odoo built-in)
**Extended by:** Mani's `employee.py` via `_inherit = 'hr.employee'`

### Dayflow-added fields on `hr.employee`

| Field | Type | Editable by |
|-------|------|-------------|
| `df_employee_id` | Char (unique, indexed) | HR Admin only |
| `df_employment_type` | Selection: `full_time \| part_time \| contract \| intern` | HR Admin |
| `df_joining_date` | Date | HR Admin |
| `df_role` | Selection: `employee \| hr_admin` | HR Admin |
| `df_phone` | Char | Employee (own) |
| `df_address` | Text | Employee (own) |
| `df_date_of_birth` | Date | HR Admin |
| `df_gender` | Selection | HR Admin |
| `df_emergency_contact` | Char | Employee (own) |
| `df_emergency_phone` | Char | Employee (own) |
| `df_active` | Boolean | HR Admin |
| `df_attendance_ids` | One2many → `dayflow.attendance` | Read in views |
| `df_leave_ids` | One2many → `dayflow.leave.request` | Read in views |
| `df_payroll_ids` | One2many → `dayflow.payroll` | Read in views |

### Key existing `hr.employee` fields (use these — do NOT duplicate)

| Field | Purpose |
|-------|---------|
| `name` | Full name |
| `work_email` | Work email |
| `job_title` | Free-text job title |
| `job_id` | Many2one hr.job |
| `department_id` | Many2one hr.department |
| `image_1920` | Profile picture |
| `active` | Odoo standard archive flag |
| `user_id` | Linked res.users (handles login) |

---

## 2. Attendance

**Model:** `dayflow.attendance`
**UI Owner:** Kunam

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one `hr.employee` | Required |
| `date` | Date | Required; unique per employee (SQL constraint) |
| `check_in` | Datetime | Optional |
| `check_out` | Datetime | Optional; must be after check_in |
| `worked_hours` | Float (computed, stored) | (check_out - check_in) in hours |
| `status` | Selection | see below |
| `notes` | Text | Optional |

**`status` values (stable — do not rename):**
```
present   → Present
absent    → Absent
half_day  → Half Day
leave     → Leave
```

**Button actions (type="object" in form view):**
```
action_check_in()              sets check_in, status = present
action_check_out()             sets check_out, refines status
```

**API helper (for Kunam's programmatic use):**
```python
# Returns today's attendance record, creating it if it doesn't exist
record = self.env['dayflow.attendance'].get_or_create_today(employee_id)
```

**Leave → Attendance integration point:**
When a leave request is approved, `leave.py` calls `_sync_attendance_for_leave()` which
writes `status = 'leave'` for each date in the range. Kunam can override this method
in a new model file without touching `leave.py`.

---

## 3. Leave Request

**Model:** `dayflow.leave.request`
**UI Owner:** Kunam

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one `hr.employee` | Required; defaults to logged-in employee |
| `leave_type` | Selection | `paid \| sick \| unpaid` |
| `date_from` | Date | Required |
| `date_to` | Date | Required; ≥ date_from |
| `number_of_days` | Integer (computed, stored) | Auto-calculated |
| `remarks` | Text | Employee fills this |
| `state` | Selection | `draft \| pending \| approved \| rejected` |
| `hr_comment` | Text | HR/Admin fills on decision |
| `approved_by` | Many2one `res.users` | Set automatically |
| `approved_date` | Datetime | Set automatically |

**`state` values (stable — do not rename):**
```
draft    → Draft (initial state)
pending  → Pending (submitted by employee)
approved → Approved
rejected → Rejected
```

**Workflow methods (type="object" from form buttons):**
```python
action_submit()           # Employee: draft → pending
action_approve()          # HR Admin: pending → approved
action_reject()           # HR Admin: pending → rejected
action_reset_to_draft()   # HR Admin: rejected/pending → draft
```

---

## 4. Payroll

**Model:** `dayflow.payroll`
**Owner:** Mani

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one `hr.employee` | Required |
| `pay_period` | Char | e.g. "August 2026" |
| `currency_id` | Many2one `res.currency` | Defaults to company currency |
| `basic_salary` | Monetary | Required |
| `house_rent_allowance` | Monetary | Default 0 |
| `transport_allowance` | Monetary | Default 0 |
| `other_allowances` | Monetary | Default 0 |
| `gross_salary` | Monetary (computed) | Sum of all earnings |
| `provident_fund` | Monetary | Default 0 |
| `tax_deduction` | Monetary | Default 0 |
| `other_deductions` | Monetary | Default 0 |
| `total_deductions` | Monetary (computed) | Sum of all deductions |
| `net_salary` | Monetary (computed) | gross_salary - total_deductions |
| `state` | Selection | `draft \| confirmed \| paid` |
| `notes` | Text | HR internal — hidden from employees in views |

**`state` values:**
```
draft     → Draft
confirmed → Confirmed
paid      → Paid
```

**Workflow methods (HR Admin only):**
```python
action_confirm()       # draft → confirmed
action_mark_paid()     # confirmed → paid
action_reset_draft()   # any → draft
```

**Permissions:**
- Employees: **read own record only** — enforced at both ACL and Python model `write()`
- HR Admin: **full CRUD**
- All salary field changes are **automatically audited** to `dayflow.audit.log`

---

## 5. Audit Log

**Model:** `dayflow.audit.log`
**Owner:** Mani

Read-only for HR Admin via UI. Append-only — no manual create/edit/delete.
Written automatically by `employee.py`, `payroll.py`, and `leave.py`.

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | Many2one `res.users` | Who made the change |
| `timestamp` | Datetime | When (auto) |
| `model_name` | Char | e.g. `dayflow.payroll` |
| `record_id` | Integer | ID of changed record |
| `record_name` | Char | Human-readable label |
| `record_ref` | Char (computed) | `"model#id (label)"` — shown in list view |
| `action` | Selection | `create\|update\|approve\|reject\|submit\|confirm\|archive\|other` |
| `field_name` | Char | Which field changed |
| `old_value` | Char | Previous value |
| `new_value` | Char | New value |

**To write from your own model:**
```python
self.env['dayflow.audit.log'].sudo().create({
    'user_id':     self.env.uid,
    'model_name':  self._name,
    'record_id':   record.id,
    'record_name': record.display_name,
    'action':      'approve',         # use one of the selection values
    'field_name':  'state',
    'old_value':   'pending',
    'new_value':   'approved',
})
```

---

## Demo Credentials (password: `Dayflow@123`)

| Name | Login | Role |
|------|-------|------|
| Priya Sharma | priya.sharma@dayflow.demo | HR Admin |
| Ravi Kumar | ravi.kumar@dayflow.demo | Employee |
| Anita Reddy | anita.reddy@dayflow.demo | Employee |
| Kiran Patel | kiran.patel@dayflow.demo | Employee |

**Demo states pre-loaded:**
- Kiran: sick leave APPROVED + attendance marked as leave
- Ravi: paid leave in DRAFT (demo: submit + HR approves live)
- Anita: unpaid leave REJECTED
- Ravi & Anita: payroll CONFIRMED; Kiran: payroll DRAFT (demo: HR confirms live)

---

## How to Install

1. Copy `dayflow/` into your Odoo custom addons path, e.g. `/odoo/custom-addons/dayflow`
2. Restart Odoo server
3. Enable Developer Mode: Settings → General Settings → Developer Tools → Activate
4. Go to **Apps → Update Apps List**
5. Search for **Dayflow**, click **Install**

Demo data loads automatically on first install. To reload:
```bash
./odoo-bin -d your_db -u dayflow
```

---

## Static Consistency Checks (done)

- [x] All Python field names match XML view field references
- [x] All security group XML IDs use `group_dayflow_hr_admin` consistently
- [x] `ir.model.access.csv` group IDs prefixed with `dayflow.`
- [x] Demo data uses `df_employee_id`, `df_employment_type`, `df_joining_date`, `state` (not `status`) on leave
- [x] Payroll demo data uses `house_rent_allowance`, `provident_fund` etc. matching model
- [x] Leave model `state` and views `state` consistent
- [x] `number_of_days` used in both leave model and leave view
- [x] Audit log `record_ref` field exists in both model and view
- [x] Payroll actions `action_confirm`, `action_mark_paid`, `action_reset_draft` defined in model and called in view

## Runtime Tests Required (Harshith / Suraj)

- [ ] Module installs without errors on Odoo 16
- [ ] `df_employee_id` unique constraint fires on duplicate
- [ ] Employee cannot access another employee's attendance (record rule isolation)
- [ ] Employee cannot write payroll — `UserError` raised
- [ ] Leave workflow: draft → pending → approved (check attendance auto-marked as leave)
- [ ] Leave workflow: draft → pending → rejected
- [ ] Audit log entries created on salary field change
- [ ] HR Admin can see all employees, all attendance, all leave, all payroll
