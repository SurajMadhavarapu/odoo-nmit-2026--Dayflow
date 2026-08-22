# -*- coding: utf-8 -*-
# Mani owns: employee, payroll, audit_log
# Kunam owns: attendance, leave (stubs provided here for integration)
from . import employee      # hr.employee extension + dayflow.employee.document
from . import attendance    # dayflow.attendance  — KUNAM
from . import leave         # dayflow.leave.request — KUNAM
from . import payroll       # dayflow.payroll
from . import audit_log     # dayflow.audit.log
