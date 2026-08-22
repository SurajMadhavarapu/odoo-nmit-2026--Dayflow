# Dayflow HRMS — Team Integration Contract

**Version:** 1.0.0  
**Owner:** Suraj (Authentication + Architecture + Integration)  
**Target Module:** `dayflow_hr`  

---

## 1. Core Architecture Principles

1. **Native Odoo Integration:** All modules use native Odoo ORM structures (`res.users`, `hr.employee`, `hr.attendance`, `hr.leave`, `hr.payslip`).
2. **Single Source of Truth:** `res.users` is the sole authentication identity; `hr.employee` is the sole HR profile entity.
3. **No Duplicate Identity Models:** Teammates must NOT create custom User, custom Employee, or parallel authentication tables.

---

## 2. Model & Security Ownership Matrix

| Area / Module | Lead | Core Odoo Models / Files | Responsibilities |
| :--- | :--- | :--- | :--- |
| **Authentication & Architecture** | Suraj | `res.users`, `security/hr_security.xml`, `__manifest__.py` | User auth contract, Security Groups, Record Rules integration, Architecture integrity |
| **Employee & Payroll** | Mani | `hr.employee`, `hr.payslip`, `hr.contract` | Employee profile extensions, Employee ID generation, Payroll computation & payslips |
| **Attendance & Leave** | Kunam | `hr.attendance`, `hr.leave` | Check-in/out logic, work hour calculation, Leave request state transitions & balances |
| **Dashboards & UI/UX** | Harshith | `ir.ui.view`, QWeb templates, Kanban/Form/Tree views | Front-end Odoo views, Dashboard widgets, styling, and user experience |

---

## 3. User ↔ Employee Identity Mapping

```text
res.users (Authentication Identity)
    │  (1-to-1 link via user_id)
    ▼
hr.employee (HR Profile Entity)
    │
    ├── hr.attendance (Attendance Logs)
    ├── hr.leave (Leave Requests)
    └── hr.payslip (Payroll / Salary Statements)
```

* **Sign Up Flow (Design):**
  Inputs: `[Employee ID, Work Email, Password, Role]` → Creates Odoo `res.users` record → Links/Instantiates `hr.employee` record.
* **Sign In Flow (Design):**
  Credentials: `[Email/Login, Password]` → Odoo `res.users` authentication → Security Group verification (`group_dayflow_employee` vs `group_dayflow_hr_admin`) → Interface layout.

---

## 4. Canonical Employee Identifier Contract

* **Primary Key Reference:** Every module (Attendance, Leave, Payroll, Dashboards) **MUST** reference the employee using a standard Many2one field pointing to `hr.employee`:
  ```python
  employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
  ```
* **Employee Identifier Field:** Canonical string identifier (`employee_id` field on `hr.employee` model, managed by Mani).
* **Odoo Runtime Verification:** *"To be finalized after Odoo runtime verification."* (Standard Odoo field name `employee_id` / `x_employee_id`).

---

## 5. Security & Role Contract

Defined Security Groups in [`dayflow_hr/security/hr_security.xml`](file:///c:/Users/suraj/Documents/odoo-nmit-2026--Dayflow/dayflow_hr/security/hr_security.xml):

1. **`group_dayflow_employee` (Employee Role):**
   * **Scope:** Access restricted to user's OWN profile, OWN attendance records, OWN leave requests, and OWN payslips.
   * **Record Rule Contract:** `[('employee_id.user_id', '=', user.id)]`
2. **`group_dayflow_hr_admin` (HR / Admin Role):**
   * **Scope:** Administrative access across ALL employees, attendance logs, leave approvals/refusals, and payroll generation.
   * **Inheritance:** Inherits `group_dayflow_employee`.

---

## 6. Development Guidelines (DOs and DO NOTs)

### ✅ DO:
* **Reference `hr.employee` directly:**
  ```python
  # In Attendance / Leave / Payroll models:
  employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
  ```
* **Use existing Security Groups:**
  Reference `dayflow_hr.group_dayflow_employee` or `dayflow_hr.group_dayflow_hr_admin` in view files and access definitions.
* **Filter records by `user_id` / `employee_id`:**
  Enforce record privacy via ORM domain filters and record rules.

### ❌ DO NOT:
* **DO NOT** create a custom `User` table or custom `Employee` table.
* **DO NOT** store employee IDs as plain unindexed text strings (`custom_employee_id = fields.Char(...)`) in Attendance, Leave, or Payroll.
* **DO NOT** create separate login/signup databases or JWT authentication controllers.
* **DO NOT** define new role strings outside `group_dayflow_employee` and `group_dayflow_hr_admin`.
