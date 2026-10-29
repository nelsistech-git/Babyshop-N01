# Face Recognition Attendance (sot_face_attendance) - Odoo 17 Community

Check in / check out with face recognition (face-api.js) on top of the standard
Odoo **Attendances** app.

## What it provides

- **Public kiosk page** `/face/attendance`: type an employee ID, look at the camera,
  the face is compared in the browser with the employee photo and the attendance
  is toggled (check in / check out).
- **Backend screen** *Face Attendance* (top menu): the logged-in employee checks
  in / out with their face (uses the standard attendance check in / out of Odoo).
- **HTTP endpoint** `GET /attendance/face/get_employees/<employee_id>`: toggles the
  attendance of the employee. Used by the external Flask app (`odoo_face_attendance`).
- **Photo endpoint** `GET /sot_face_attendance/employee_image/<employee_id>`: employee
  photo used as the reference face (replaces the `base_64_to_url` route).

## Installation

1. Copy the `sot_face_attendance` folder into your Odoo 17 addons path.
2. Restart Odoo, enable developer mode, *Apps > Update Apps List*.
3. Install **sot_face_attendance** (depends on `hr_attendance` and `website`).

## Usage

1. Every employee needs a clear front-facing photo on the employee form.
2. Backend: open the **Face Attendance** menu and click the face icon.
3. Kiosk: open `https://<your-odoo>/face/attendance`, enter the employee ID and
   click the face icon. The browser needs camera access (HTTPS or localhost).

## Security note

`/attendance/face/get_employees/<id>` and `/sot_face_attendance/employee_image/<id>`
are public (the face is matched in the browser / by the Flask app), so anyone who
knows an employee ID can call them. Restrict them (reverse proxy, VPN, IP allow
list) or add a shared token before using this in production.

## License

LGPL-3
