# CCTV Face Attendance (cctv_face_attendance) - Odoo 17 Community

Bridge between **Smart CCTV Management** (`cctv_management`) and **HR Attendances** (`hr_attendance`).
Mark a camera as an attendance camera; employees recognised by the face service are checked in / out
automatically in the standard `hr.attendance` model.

## Install
1. Put `cctv_management` and `cctv_face_attendance` in the addons path, update the Apps list.
2. Install **CCTV Face Attendance** (depends on `cctv_management`, `hr_attendance`, `hr`).
3. Make sure the system parameter `cctv_management.api_key` is set (same key the AI service uses).
4. Install and start `face_attendance_service` (separate folder, see its README).

## Setup in Odoo (10 minutes)
1. **Employees**: each employee needs a clear photo on the employee form. Select employees in the
   list > Action > *Enrol for Face Attendance* (or Settings > Smart CCTV > Face Attendance > *Enrol all employees*).
2. **Cameras**: Smart CCTV > Configuration > Cameras > open camera > tick **Face Attendance Camera** and pick the role:
   * **Entry** - only checks in (camera at the entrance)
   * **Exit** - only checks out
   * **Single door** - toggles, with a minimum gap
   Cameras that merely see people walking past should not be attendance cameras.
3. **Check**: Smart CCTV > Face Attendance > *Enrolment Status* shows who is ready; the service reports
   employees whose photo it cannot use (no face, too small, several faces).
4. Settings > Smart CCTV > *Face Attendance* holds every threshold with explanations.

## How a punch is decided
`face service` -> several frames agree + quality gates + lead over the next person ->
`/cctv/api/attendance/punch` -> confidence band -> role/state rules -> `hr.attendance`.

| Match % | Result |
|---|---|
| >= 55 (default) | punch is made automatically |
| 45 - 55 | goes to *Needs Review*; HR approves or dismisses |
| < 45 | nothing happens |

Also: late punches (service was offline > 30 min) go to review; a forgotten check-out is closed at the last
time the person was seen (never "now") and flagged *Closed Automatically*; the first check-in of the day is
compared with the Monitoring Assignment shift for *Minutes After Shift Start* / *Late*.

## Sync with other HR modules
Everything is written to standard `hr.attendance` (`in_mode` / `out_mode` = *CCTV Face*), so Odoo overtime,
Time Off, attendance reports and any payroll that reads attendances (Enterprise `hr_payroll` with
work entries, OCA payroll, custom) see face punches exactly like manual ones. Community Odoo has no
built-in payroll; nothing here changes payslips by itself.

## Audit & privacy
Every punch keeps camera, match %, frames, and an evidence snapshot (Punch Log). Snapshots are purged after
`Keep punch snapshots (days)` (default 90). Optional *Require biometric consent*. Face photos are biometric
personal data: check local law and employment contracts.

## Tests
`odoo-bin -d <db> -u cctv_face_attendance --test-tags /cctv_face_attendance --stop-after-init` (31 tests).
