# Dayflow — Backend Integration Contract

> Owner: **Mani** (HR Core / Data Layer)  
> Branch: `feature/mani-hr-core`  
> Last updated: 2026-08-22

This document is the stable API contract for the Dayflow Odoo module.  
**Do not change model names, field names, or selection values without notifying Suraj and the affected teammate first.**

---

## Security Groups

| XML ID | Display Name | Inherits |
|--------|-------------|----------|
| `dayflow.group_dayflow_employee` | Employee | — |
| `dayflow.group_dayflow_hr_admin` | HR / Admin | Employee |

Use these in your views with `groups="dayflow.group_dayflow_hr_admin"`.

---

## Model 1 — Employee

**Base model:** `hr.employee` (extended, not replaced)  
**Additional fields added by Dayflow:**

| Field | Type | Notes |
|-------|------|-------|
| `dayflow_employee_id` | Char | Unique ID, e.g. DF-001 |
| `phone_number` | Char | Employee can edit |
| `address_line1` | Char | Employee can edit |
| `address_line2` | Char | Employee can edit |
| `city` | Char | Employee can edit |
| `state_region` | Char | Employee can edit |
| `postal_code` | Char | Employee can edit |
| `country_name` | Char | Employee can edit |
| `date_of_joining` | Date | HR/Admin managed |
| `employment_type` | Selection | full_time / part_time / contract / intern |
| `attendance_ids` | One2many → dayflow.attendance | |
| `leave_request_ids` | One2many → dayflow.leave.request | |
| `payroll_id` | One2many → dayflow.payroll | |

**Inherited fields used:**  
`name`, `work_email`, `user_id`, `job_title`, `image_1920` (profile photo), `active`

---

## Model 2 — Attendance

**Model name:** `dayflow.attendance`

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → hr.employee | Required |
| `date` | Date | Required, no future dates |
| `check_in` | Datetime | |
| `check_out` | Datetime | Must be after check_in |
| `status` | Selection | See values below |
| `worked_hours` | Float (computed) | Hours between check_in and check_out |
| `notes` | Text | |

**Status values:**

| Value | Label |
|-------|-------|
| `present` | Present |
| `absent` | Absent |
| `half_day` | Half-Day |
| `leave` | On Leave |

**Business methods (callable from UI/Kunam):**
- `record.action_check_in()` — sets check_in, status=present
- `record.action_check_out()` — sets check_out

**Constraints:**
- `UNIQUE(employee_id, date)` — one record per employee per day
- check_out > check_in enforced at ORM level
- No future dates

---

## Model 3 — Leave Request

**Model name:** `dayflow.leave.request`  
**Inherits:** `mail.thread`, `mail.activity.mixin` (chatter enabled)

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → hr.employee | Required |
| `leave_type` | Selection | See values below |
| `date_from` | Date | Required |
| `date_to` | Date | Required, must be >= date_from |
| `remarks` | Text | Employee fills in |
| `status` | Selection | See values below |
| `hr_comment` | Text | HR/Admin fills in |
| `approved_by` | Many2one → res.users | Auto-set on approve/reject |
| `action_date` | Datetime | Auto-set on approve/reject |
| `number_of_days` | Integer (computed) | date_to - date_from + 1 |

**Leave type values:**

| Value | Label |
|-------|-------|
| `paid` | Paid Leave |
| `sick` | Sick Leave |
| `unpaid` | Unpaid Leave |

**Status values:**

| Value | Label |
|-------|-------|
| `pending` | Pending |
| `approved` | Approved |
| `rejected` | Rejected |

**Workflow methods (HR/Admin only):**
- `record.action_approve()` — sets status=approved
- `record.action_reject()` — sets status=rejected
- `record.action_reset_to_pending()` — resets rejected → pending

**Guards:**
- Employees cannot approve their own leave
- Employees cannot edit approved/rejected requests
- Only `group_dayflow_hr_admin` can call approve/reject

---

## Model 4 — Payroll

**Model name:** `dayflow.payroll`

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → hr.employee | Required |
| `effective_date` | Date | Required |
| `basic_salary` | Float | HR/Admin editable |
| `house_rent_allowance` | Float | |
| `transport_allowance` | Float | |
| `other_allowances` | Float | |
| `gross_salary` | Float (computed) | sum of earnings |
| `tax_deduction` | Float | |
| `provident_fund` | Float | |
| `other_deductions` | Float | |
| `total_deductions` | Float (computed) | sum of deductions |
| `net_salary` | Float (computed) | gross - deductions |
| `currency_id` | Many2one → res.currency | defaults to INR |

**Access:**
- Employees: **read-only** (ACL enforced, not just UI)
- HR/Admin: full read/write

---

## Model 5 — Audit Log

**Model name:** `dayflow.audit.log`

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | Many2one → res.users | Who made the change |
| `timestamp` | Datetime | Auto-set |
| `model_name` | Char | e.g. `dayflow.payroll` |
| `record_id` | Integer | DB id of changed record |
| `record_name` | Char | Human label at time of change |
| `action` | Selection | create / write / salary_update / leave_approved / etc. |
| `field_name` | Char | Which field changed |
| `old_value` | Text | Previous value |
| `new_value` | Text | New value |

**Access:** HR/Admin read-only. No write/delete for anyone.

---

## Demo Accounts

| Login | Password | Role |
|-------|----------|------|
| `hr.admin@dayflow.com` | (set via Odoo UI or reset) | HR / Admin |
| `alice@dayflow.com` | (set via Odoo UI or reset) | Employee (DF-001) |
| `bob@dayflow.com` | (set via Odoo UI or reset) | Employee (DF-002) |
| `carol@dayflow.com` | (set via Odoo UI or reset) | Employee (DF-003) |

---

## How to Install

1. Copy the `dayflow/` folder into your Odoo `addons` directory.
2. Restart Odoo server.
3. Go to **Settings → Apps → Update App List**.
4. Search for **Dayflow** and click **Install**.
5. Enable demo data on install for seed records.

```bash
# With demo data
./odoo-bin -d dayflow_db -i dayflow --demo
```

---

## Consuming Models from Other Modules

```python
# Read all employees (Harshith / Dashboard)
employees = request.env['hr.employee'].search([('active', '=', True)])

# Read attendance for current user's employee (Kunam / Attendance UI)
employee = request.env['hr.employee'].search([('user_id', '=', request.env.uid)], limit=1)
records = request.env['dayflow.attendance'].search([('employee_id', '=', employee.id)])

# Read leave requests pending approval (Kunam / Leave UI)
pending = request.env['dayflow.leave.request'].search([('status', '=', 'pending')])

# Read own salary (Employee dashboard)
salary = request.env['dayflow.payroll'].search([('employee_id.user_id', '=', request.env.uid)])
```

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-08-22 | Mani | Initial models: employee, attendance, leave, payroll, audit_log |
| 2026-08-22 | Mani | Security groups, ACL, views, demo data |
