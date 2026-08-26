# JRF — Job Request Form

Odoo 17 Community module for traceable cross-department work requests at KodingYuk.

## Scope

- Automatic number at submission: `JRF/IT/2026/0001`
- Requester, target department, priority reason, purpose, scope, and expected output
- Assignment, waiting-for-requester status, review, requester acceptance, and completion
- Chatter, activities, and standard Odoo attachments
- Change requests with a child number such as `JRF-IT-2026-0001-CR01`
- Printable A4 QWeb PDF from the **Print** menu

## Roles

- **JRF User**: create and see requests related to them.
- **JRF Department Head**: approves and assigns requests for their department.
- **JRF Management**: access to all requests and acceptance override.

## Installation

Place `jrf_odoo_ops` in the Odoo addons path, update the Apps List, assign JRF roles, then install **JRF - Job Request Form**. Set the **JRF Code** on every department that receives jobs (for example `IT`, `MKT`, or `ACD`).

## Workflow

`Draft → Submitted → Approved → Assigned → In Progress → Review → Completed`

Alternative operational state: `Waiting for Requester`. A request may also be cancelled.
