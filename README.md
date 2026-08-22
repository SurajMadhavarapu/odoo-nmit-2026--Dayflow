# Dayflow — Human Resource Management System (HRMS)

Team repository for the Odoo × NMIT Bangalore Hackathon 2026 — collaborative development, documentation, and implementation of our hackathon HRMS solution.

---

## 🛠️ Shared Development Environment

The project is configured as a custom Odoo 17 module (`dayflow_hr`) running on PostgreSQL 15 via Docker Compose.

### Quick Start

1. **Start the environment:**
   ```bash
   docker compose up -d
   ```
2. **Access Odoo Web Client:**
   Open [http://localhost:8069](http://localhost:8069) in your browser.
3. **Module Installation / Upgrade:**
   ```bash
   docker exec dayflow_odoo odoo -u dayflow_hr -d dayflow_db --stop-after-init -c /etc/odoo/odoo.conf
   ```

---

## ⚠️ Security Notice (Development Credentials Only)

The credentials configured in `odoo.conf` (`db_password = odoo`, `admin_passwd = admin`) are strictly **development-only defaults** for local hackathon testing. **Do not use or reuse these credentials in a production environment.**

---

## 📁 Repository Structure

```text
odoo-nmit-2026--Dayflow/
├── docker-compose.yml          # Local Odoo 17 + PostgreSQL 15 orchestration
├── odoo.conf                   # Odoo server development configuration
├── README.md
└── dayflow_hr/                 # Dayflow HRMS Custom Odoo Module
    ├── __init__.py
    ├── __manifest__.py
    ├── INTEGRATION_CONTRACT.md # Shared team architecture contract
    ├── README.md
    ├── data/
    ├── models/
    ├── security/
    │   └── hr_security.xml     # Dayflow Employee & HR/Admin security groups
    └── views/
```
