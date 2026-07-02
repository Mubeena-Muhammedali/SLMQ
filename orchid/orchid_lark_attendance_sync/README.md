# Lark Attendance Sync (Odoo 19)

Pulls punch/check-in records from the **Lark / Feishu Open Platform Attendance API**
and creates matching `hr.attendance` records in Odoo.

## Install

1. Copy the `lark_attendance_sync` folder into your Odoo `addons` path.
2. Update Apps list, search for **Lark Attendance Sync**, install.
   (Depends only on `hr_attendance`, which is included in Community.)

## Setup

### 1. Create a Lark/Feishu custom app
In the Lark or Feishu Developer Console, create a **custom app** and enable the
Attendance scopes needed to read punch records (e.g. `attendance:user_flow`,
plus whatever contact scopes are needed to resolve `employee_id`). Publish/
enable the app for your tenant so the "tenant_access_token" flow works.

**Two extra steps specific to Attendance (easy to miss):**
- On the Developer Console **Permissions & Scopes** page, grant both **read
  and write** scopes to the attendance app (write is required even if you
  only read data, per Lark's own guide).
- Separately, open the **Attendance Admin** console (not the Developer
  Console) and click **API Integration** in the upper-right corner to link
  your app to the Attendance module. Without this step the API calls will
  fail even if scopes look correct in the Developer Console.
- If your organization has "post review" enabled, a company administrator
  must approve the app before its credentials become active — check with
  your Lark tenant admin if calls keep failing with a permission error.

### 2. Configure Odoo
Settings ‣ General Settings ‣ **Lark Attendance Sync** section:
- Platform: Feishu (China) or Lark (International)
- App ID / App Secret from step 1
- Days to look back per sync run (keep small, e.g. 1-3, if the cron runs every
  few hours)

### 3. Map employees
On each `hr.employee` form, fill in **Lark User ID** (the `employee_id` of that
person from Lark's admin console: Organization ‣ Members). Employees without
this field are skipped by the sync.

### 4. Sync
- **Manual**: open an employee with a Lark User ID set and click
  **Sync Lark Attendance**.
- **Automatic**: Settings ‣ Technical ‣ Automation ‣ Scheduled Actions ‣
  "Lark Attendance: Sync Check-in/out" — it is created **inactive**; enable
  it and set your preferred interval once credentials are configured.

### 5. Review
Attendance ‣ (manager menu) ‣ **Lark Sync Logs** shows the result of every
sync run (success/error, counts, error messages) for troubleshooting.

## How matching works

For each employee/day, the module fetches all punch timestamps in the
window, takes the **earliest** as `check_in` and the **latest** (if more than
one punch that day) as `check_out`. If an `hr.attendance` record already
exists for that employee/day it is updated (check-out filled in, or check-in
corrected if an earlier punch is found) instead of creating a duplicate.

## Notes / things to verify for your tenant

- The exact Lark Attendance API path and payload shape can differ slightly
  between the China (Feishu) and International (Lark) platforms and between
  API versions — the module targets the documented
  `POST /open-apis/attendance/v1/user_flow/query` (Batch Query of Attendance
  Flow Record) endpoint with `employee_type=employee_id`. If your app uses
  `open_id` instead, change the `employee_type` param in
  `models/lark_attendance_sync.py` and store `open_id` values in
  `lark_user_id` instead.
- This is intentionally a **simple**, single-direction (Lark → Odoo) sync.
  It does not push Odoo attendance back to Lark, and it does not handle
  leave/overtime/shift data — only raw check-in/check-out punches.
