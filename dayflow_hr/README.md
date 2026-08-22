# Dayflow HRMS Custom Odoo Module

Minimal Odoo custom module skeleton for Dayflow Human Resource Management System.

## Module Structure

- `__init__.py`: Module entry point
- `__manifest__.py`: Odoo module manifest and dependencies
- `models/`: Odoo ORM model definitions
- `security/`: Security categories and group definitions (`hr_security.xml`)
- `views/`: View XML files (Form, Tree, Kanban, Dashboards)
- `data/`: Initial XML/CSV seed data



Dayflow is a modern Human Resource Management System (HRMS) built on **Odoo 17**, designed to provide employees and HR/Admin teams with a unified platform for authentication, employee management, attendance, leave management, payroll, and audit tracking.

The project uses a **Neo-Brutalist UI** to provide a bold, high-contrast, fast, and distinctive user experience.

---

## Team

### Suraj
**Authentication + Architecture + Integration + UI/UX**

- Odoo authentication
- User ↔ employee integration
- Security architecture
- Frontend/UI
- Backend/API integration
- Final system integration

### Mani
**Employee + Payroll + Attendance + Leave + Backend HR Core**

- Employee management
- Audit logging
- Backend security and business logic

### Vardhan
** Attendance + Leave**
- Attendance
- Leave management
- Payroll

### Harshith
**Testing / QA**

- End-to-end testing
- Role and permission testing
- Integration verification
- Bug identification and validation

---

# Features

## Authentication

- Employee and HR/Admin registration
- Secure login using native Odoo authentication
- Session management
- Logout
- Session restoration
- Role-based access

## Employee Management

- Employee profiles
- Employee ID
- Contact and job information
- Employee directory
- Employee-specific data isolation

## Attendance

- Check-in
- Check-out
- Attendance status
- Worked hours
- Daily attendance records
- Employee-specific attendance visibility
- HR/Admin attendance visibility

## Leave Management

Supported leave types:

- Paid
- Sick
- Unpaid

Leave workflow:

```text
Draft
  ↓
Pending
  ↓
Approved / Rejected
