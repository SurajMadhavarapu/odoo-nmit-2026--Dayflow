# Dayflow HRMS — Team Integration Contract

**Version:** 1.1.0 (Runtime Verified - Odoo 17.0)  
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
| **Authentication & Architecture** | Suraj | `res.users`, `security/hr_security.xml`, `security/ir.model.access.csv`, `controllers/main.py` | User auth contract, Security Groups, Record Rules integration, Registration & Session APIs |
| **Employee & Payroll** | Mani | `hr.employee`, `hr.payslip`, `hr.contract` | Employee profile extensions, Employee ID generation, Payroll computation & payslips |
| **Attendance & Leave** | Kunam | `hr.attendance`, `hr.leave` | Check-in/out logic, work hour calculation, Leave request state transitions & balances |
| **Dashboards & UI/UX** | Harshith | `ir.ui.view`, QWeb templates, Kanban/Form/Tree views | Front-end Odoo views, Dashboard widgets, styling, and user experience |

---

## 3. Verified User ↔ Employee Identity Mapping

```text
res.users (Authentication Identity - Odoo Core)
    │  (1-to-1 link via user_id)
    ▼
hr.employee (HR Profile Entity - Odoo Core + Dayflow Extensions)
    │
    ├── hr.attendance (Attendance Logs - Owned by Kunam)
    ├── hr.leave (Leave Requests - Owned by Kunam)
    └── hr.payslip (Payroll / Salary Statements - Owned by Mani)
```

* **Authentication Fields (`res.users`):**
  * `login`: User email / login string (Unique)
  * `password`: Native password hash (Managed by `res.users`)
  * `dayflow_role`: Computed selection (`'employee'` vs `'hr_admin'`)
* **Employee Identity Fields (`hr.employee`):**
  * `user_id`: Many2one reference to `res.users`
  * `employee_code`: Char field for Dayflow Employee ID (Unique, `index=True`)
  * `work_email`: Work Email address string

---

## 4. Registration & Authentication APIs

* **Server-side Helper (Python):**
  ```python
  env['res.users'].register_dayflow_user(employee_id, email, password, role, name=None)
  ```
* **JSON HTTP Endpoints:**
  * `POST /api/dayflow/signup`: `{ "employee_id": "EMP001", "email": "user@example.com", "password": "Pass", "role": "Employee", "name": "Name" }`
  * `POST /api/dayflow/login`: `{ "login": "user@example.com", "password": "Pass" }`
  * `GET/POST /api/dayflow/session`: Returns current session user status, Dayflow role, and linked employee ID.

---

## 5. Security Groups & Record Rules

* **Security Group XML IDs:**
  * `dayflow_hr.group_dayflow_employee` (**Employee Role**)
  * `dayflow_hr.group_dayflow_hr_admin` (**HR / Admin Role**)
* **Record Rules (`ir.rule`):**
  * `dayflow_hr.hr_employee_rule_dayflow_employee`: Restricts Employee profile access domain to `[('user_id', '=', user.id)]`.
  * `dayflow_hr.hr_employee_rule_dayflow_hr_admin`: Grants HR/Admin unrestricted profile access domain `[(1, '=', 1)]`.

---

## 6. Development Guidelines (DOs and DO NOTs)

### ✅ DO:
* **Reference `hr.employee` directly:**
  ```python
  employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
  ```
* **Reference Dayflow Security Groups:**
  Use `dayflow_hr.group_dayflow_employee` or `dayflow_hr.group_dayflow_hr_admin` in view files and access definitions.

### ❌ DO NOT:
* **DO NOT** create a custom `User` table or custom `Employee` table.
* **DO NOT** store employee IDs as plain unindexed text strings (`custom_id = fields.Char(...)`) in Attendance, Leave, or Payroll.
* **DO NOT** create separate login/signup databases or JWT authentication controllers.
