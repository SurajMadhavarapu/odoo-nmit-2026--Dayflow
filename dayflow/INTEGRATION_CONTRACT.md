# Dayflow – Backend Integration Contract

> **Owner:** Mani (HR Core / Data Layer)
> **Last updated:** 2026-08-22
> **Branch:** `feature/mani-hr-core`

This document is the stable interface contract for the Dayflow backend models.
**Do not rename models, fields, or selection values without telling Suraj and the affected teammate first.**

---

## Security Groups

| XML ID | Technical Name | Who |
|--------|---------------|-----|
| `dayflow.group_dayflow_employee` | Dayflow Employee | Regular employees |
| `dayflow.group_dayflow_hr`       | Dayflow HR/Admin  | HR officers & admins |

Use these in your views to show/hide buttons:
```xml
groups="dayflow.group_dayflow_hr"
groups="dayflow.group_dayflow_employee"
```

---

## 1. Employee

**Base model extended:** `hr.employee`

| Field | Type | Notes |
|-------|------|-------|
| `df_employee_id` | Char | Unique employee code, e.g. `DF-001` |
| `df_phone` | Char | Editable by employee |
| `df_address` | Text | Editable by employee |
| `df_document_ids` | One2many → `dayflow.employee.document` | Employee docs |
| `df_attendance_ids` | One2many → `dayflow.attendance` | Reverse relation |
| `df_leave_ids` | One2many → `dayflow.leave.request` | Reverse relation |
| `df_payroll_id` | One2many → `dayflow.payroll` | Reverse relation |

**Standard hr.employee fields still usable:**
`name`, `work_email`, `job_title`, `job_id`, `department_id`, `image_1920` (profile pic), `active`

---

## 2. Attendance

**Model:** `dayflow.attendance`

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → `hr.employee` | Required |
| `date` | Date | Required, unique per employee |
| `check_in` | Datetime | Optional |
| `check_out` | Datetime | Optional, must be ≥ check_in |
| `working_hours` | Float (computed) | Hours between check-in/out |
| `status` | Selection | See values below |
| `notes` | Text | Optional |

**Status values:**
```
present   → Present
absent    → Absent
half_day  → Half Day
leave     → On Leave
```

**Programmatic check-in (for Kunam's workflow):**
```python
# Check in current employee
attendance = env['dayflow.attendance'].action_check_in(employee_id)

# Check out (call on the record)
attendance.action_check_out()
```

---

## 3. Leave Request

**Model:** `dayflow.leave.request`

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → `hr.employee` | Required; defaults to logged-in employee |
| `leave_type` | Selection | See values below |
| `date_from` | Date | Required |
| `date_to` | Date | Required, must be ≥ date_from |
| `number_of_days` | Integer (computed) | Auto-calculated |
| `remarks` | Text | Employee fills this |
| `status` | Selection | See values below |
| `hr_comment` | Text | HR fills this on approval/rejection |
| `approved_by` | Many2one → `res.users` | Set automatically on approve/reject |
| `approved_date` | Datetime | Set automatically on approve/reject |

**Leave type values:**
```
paid    → Paid Leave
sick    → Sick Leave
unpaid  → Unpaid Leave
```

**Status values:**
```
draft    → Pending
approved → Approved
rejected → Rejected
```

**Workflow methods (call on record, HR group required):**
```python
leave.action_approve()        # Approves + marks attendance as 'leave'
leave.action_reject()         # Rejects request
leave.action_reset_to_draft() # Resets rejected → pending (HR only)
```

---

## 4. Payroll

**Model:** `dayflow.payroll`

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → `hr.employee` | Required |
| `currency_id` | Many2one → `res.currency` | Defaults to company currency |
| `basic_salary` | Monetary | Required |
| `allowances` | Monetary | Default 0 |
| `deductions` | Monetary | Default 0 |
| `net_salary` | Monetary (computed) | basic + allowances - deductions |
| `effective_date` | Date | Required |
| `notes` | Text | HR-only notes |

**Permissions:**
- Employees: **read own only** (enforced at model + ACL level)
- HR/Admin: **full CRUD**

---

## 5. Audit Log

**Model:** `dayflow.audit.log`

Read-only. Written to automatically by the system on:
- Salary changes (`dayflow.payroll` write)
- Leave approval / rejection (`dayflow.leave.request` actions)

**To log a custom event from your code:**
```python
self.env['dayflow.audit.log'].sudo().log(
    model='dayflow.leave.request',
    res_id=record.id,
    action='approve',        # create|update|approve|reject|archive|other
    field_name='status',
    old_value='draft',
    new_value='approved',
)
```

---

## Demo Users (password: `Dayflow@123`)

| Name | Login | Role |
|------|-------|------|
| Priya Sharma | priya.sharma@dayflow.demo | HR Admin |
| Ravi Kumar | ravi.kumar@dayflow.demo | Employee |
| Anita Reddy | anita.reddy@dayflow.demo | Employee |
| Kiran Patel | kiran.patel@dayflow.demo | Employee |

---

## How to Install

1. Place the `dayflow/` folder in your Odoo `addons` path.
2. Restart Odoo server.
3. Go to **Settings → Apps**, search `Dayflow`, click **Install**.
4. For demo data: enable **Technical → Activate Developer Mode**, then install with demo data OR run:
   ```bash
   odoo-bin -d your_db --init dayflow --load-demo-data
   ```

---

## Questions / Changes

Ping **Suraj** (architecture lead) before renaming anything in this contract.
