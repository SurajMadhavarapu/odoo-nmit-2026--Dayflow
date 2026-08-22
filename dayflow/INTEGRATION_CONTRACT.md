# Dayflow – Backend Integration Contract

> **Branch:** `feature/mani-hr-core`
> **Last updated:** 2026-08-22
> **Contact:** Mani (HR Core / Data Layer)

This document is the **stable interface contract** for all Dayflow backend models.

> ⚠️ **Do NOT rename models, fields, or selection values without first notifying Suraj (architecture lead) and the affected teammate.**

---

## Team Ownership

| Domain | Owner | Branch |
|--------|-------|--------|
| Authentication, architecture, integration | Suraj | main / feature/suraj-* |
| Employee, Payroll, Security groups, Audit | **Mani** | feature/mani-hr-core |
| Attendance, Leave workflow & UI | Kunam | feature/kunam-* |
| Dashboard, testing, demo prep | Harshith | feature/harshith-* |

---

## Security Groups (canonical — do not rename)

| XML ID | Technical Name | Purpose |
|--------|---------------|---------|
| `dayflow.group_dayflow_employee` | Dayflow Employee | Regular employees |
| `dayflow.group_dayflow_hr_admin` | Dayflow HR / Admin | HR officers & admins |

Use in views:
```xml
groups="dayflow.group_dayflow_hr_admin"
groups="dayflow.group_dayflow_employee"
```

Use in Python:
```python
self.env.user.has_group('dayflow.group_dayflow_hr_admin')
self.env.user.has_group('dayflow.group_dayflow_employee')
```

---

## 1. Employee

**Base model:** `hr.employee` (Odoo built-in, extended by Mani)

### Dayflow-added fields

| Field | Type | Editable by |
|-------|------|-------------|
| `df_employee_id` | Char (unique, indexed) | HR Admin only |
| `df_phone` | Char | Employee (own) |
| `df_address` | Text | Employee (own) |
| `employment_type` | Selection | HR Admin |
| `date_joined` | Date | HR Admin |
| `emergency_contact_name` | Char | HR Admin |
| `emergency_contact_phone` | Char | HR Admin |
| `df_document_ids` | One2many → `dayflow.employee.document` | Employee (own) |
| `df_attendance_ids` | One2many → `dayflow.attendance` | Read-only here; Kunam owns |
| `df_leave_ids` | One2many → `dayflow.leave.request` | Read-only here; Kunam owns |
| `df_payroll_ids` | One2many → `dayflow.payroll` | Read-only here; HR Admin via Payroll module |

### Existing hr.employee fields (use these, don't duplicate)

| Field | Usage |
|-------|-------|
| `name` | Full name |
| `work_email` | Work email |
| `job_title` | Job title (text) |
| `job_id` | Job position (Many2one hr.job) |
| `department_id` | Department |
| `image_1920` | Profile picture |
| `active` | Archive / active state |
| `user_id` | Linked portal/internal user |

---

## 2. Employee Document

**Model:** `dayflow.employee.document`

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → `hr.employee` | Required |
| `name` | Char | Document name |
| `document_type` | Selection | id_proof, address_proof, certificate, contract, other |
| `file` | Binary (attachment) | The uploaded file |
| `file_name` | Char | Original filename |
| `note` | Text | Optional note |
| `active` | Boolean | Archive support |

---

## 3. Attendance

**Model:** `dayflow.attendance`
**Owner:** KUNAM

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → `hr.employee` | Required — use this, not a separate char ID |
| `date` | Date | Required; unique per employee (SQL constraint) |
| `check_in` | Datetime | Optional |
| `check_out` | Datetime | Optional; must be after check_in |
| `working_hours` | Float (computed) | Hours between check_in and check_out |
| `status` | Selection | See below |
| `notes` | Text | Optional |

**Status values (stable):**
```
present   → Present
absent    → Absent
half_day  → Half Day
leave     → Leave
```

**Integration point with Leave (for Kunam):**
When a leave request is approved, attendance records for each day in the leave range should be set to `status = 'leave'`. The leave model (`leave.py`) has a comment marking the exact integration point. Implement `_sync_attendance_for_leave()` in your branch.

---

## 4. Leave Request

**Model:** `dayflow.leave.request`
**Owner:** KUNAM

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → `hr.employee` | Required; defaults to logged-in employee |
| `leave_type` | Selection | paid, sick, unpaid |
| `date_from` | Date | Required |
| `date_to` | Date | Required; must be ≥ date_from |
| `number_of_days` | Integer (computed) | Auto-calculated |
| `remarks` | Text | Employee fills this |
| `status` | Selection | draft, approved, rejected |
| `hr_comment` | Text | HR fills on approve/reject |
| `approved_by` | Many2one → `res.users` | Set automatically |
| `approved_date` | Datetime | Set automatically |

**Status values (stable):**
```
draft    → Pending
approved → Approved
rejected → Rejected
```

**Workflow methods (HR Admin required):**
```python
leave.action_approve()         # Approves; logs to audit
leave.action_reject()          # Rejects; logs to audit
leave.action_reset_to_draft()  # Reset rejected → pending
```

---

## 5. Payroll

**Model:** `dayflow.payroll`
**Owner:** Mani

| Field | Type | Notes |
|-------|------|-------|
| `employee_id` | Many2one → `hr.employee` | Required |
| `currency_id` | Many2one → `res.currency` | Defaults to company currency |
| `basic_salary` | Monetary | Required |
| `allowances` | Monetary | Default 0 |
| `deductions` | Monetary | Default 0 |
| `net_salary` | Monetary (computed) | basic + allowances - deductions |
| `effective_date` | Date | Required |
| `notes` | Text | HR only; not visible to employees |

**Permissions:**
- Employees: **read own record only** — enforced at both ACL and model level
- HR Admin: **full CRUD**

**Salary changes are automatically audited** to `dayflow.audit.log`.

---

## 6. Audit Log

**Model:** `dayflow.audit.log`
**Owner:** Mani

Read-only. HR Admin can view, no one can create/edit/delete records manually.
Written automatically by the system on: salary changes, leave approve/reject.

**To log from your own model code:**
```python
self.env['dayflow.audit.log'].sudo().log(
    model='dayflow.leave.request',   # technical model name
    res_id=record.id,
    action='approve',                # create|update|approve|reject|archive|other
    field_name='status',
    old_value='draft',
    new_value='approved',
)
```

---

## Demo Credentials (password: `Dayflow@123`)

| Name | Login | Role |
|------|-------|------|
| Priya Sharma | priya.sharma@dayflow.demo | HR Admin |
| Ravi Kumar | ravi.kumar@dayflow.demo | Employee |
| Anita Reddy | anita.reddy@dayflow.demo | Employee |
| Kiran Patel | kiran.patel@dayflow.demo | Employee |

---

## How to Install

1. Place `dayflow/` in your Odoo `addons` path (e.g. `/odoo/custom-addons/dayflow`)
2. Restart Odoo: `./odoo-bin -c odoo.conf`
3. Go to **Settings → Apps**, search `Dayflow`, click **Install**
4. For demo data: enable Developer Mode, then install with demo OR:
   ```bash
   ./odoo-bin -d your_db --init dayflow
   ```
   Demo data loads automatically when the DB is created with `--demo=True` or via Settings → Technical → Load Demo Data.

---

## Runtime Test Status

> These models have NOT been tested against a live Odoo runtime.
> Code inspection and static XML validation only.
> Runtime testing is owned by Harshith.

Static checks confirmed:
- [x] Python model syntax valid
- [x] All `_inherit` / `_name` references consistent
- [x] All field names consistent between models, views, and demo data
- [x] Group references use canonical `group_dayflow_hr_admin` throughout
- [x] `df_employee_id` used as canonical employee ID field everywhere
- [x] No cross-branch dependencies (attendance/leave stubs are clean)
- [x] `ir.model.access.csv` group references prefixed with `dayflow.`

Runtime tests required (Harshith / Suraj):
- [ ] Module installs without errors
- [ ] Employee record creation with df_employee_id uniqueness enforcement
- [ ] Payroll create blocked for employee users
- [ ] Leave approve/reject workflow
- [ ] Audit log entries created on salary change
- [ ] Record rule isolation (employee cannot see other employees' data)
