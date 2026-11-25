# Nelsis Field Force - Demo Data (`nelsis_field_demo`)

One module that fills a **test / demo database** with a believable two-week story, so every screen of
`nelsis_field_tracking`, `nelsis_field_expense`, `nelsis_ai_insights` and the Flutter app has something to show.

**Install = demo ready. Uninstall = demo gone.** Never install it on a production database.

## Install
1. Copy the `nelsis_field_demo` folder next to the other Nelsis addons.
2. Apps -> Update Apps List -> install **Nelsis Field Force - Demo Data**
   (or `odoo -d DEMO_DB -i nelsis_field_demo --stop-after-init`).
3. Only `nelsis_field_tracking` is required. TA/DA claims, advances and AI findings are created **only if** their
   modules (`nelsis_field_expense` + your `conveyance_expense` / `employee_advance`, `nelsis_ai_insights`) are installed.
   Installed them later? Open **Field Force > Configuration > Demo Data** and press **Generate / Regenerate**.

## What you get (everything dated relative to "now")
| Area | Content |
|------|---------|
| Users / employees | 12 people in 5 departments (Management, Sales, Field Operations, Collections, Accounts, Warehouse). Sign in with `demo.manager`, `demo.rahim`, `demo.karim`, `demo.nusrat`, `demo.sabbir`, `demo.mahmud`, `demo.farhana`, `demo.jamal`, `demo.shirin`, `demo.imran`, `demo.tasnim`, `demo.mannan` - password **demo1234**. `demo.manager` is a Field Force administrator (map, dashboard, announcements). |
| Work sites | HQ Gulshan, Motijheel, Tejgaon, Uttara, Narayanganj (geofences). |
| Attendance | 14 days, weekends respected, ~8 % random absence, today's punches still open for people "at work". |
| GPS tracks | ~3,900 points along routes between the sites and customer places around Dhaka (distance, speed, heading, battery, accuracy). Live Map shows positions, online/offline, routes, true/false points. |
| Online / offline | login, signal-lost and logout events. |
| TA/DA claims | 12 claims in every state (draft, with Accounts, Line Manager, HoF, approved, posted, paid, refused) with **Travel, Food and Other** lines and generated receipt images. |
| Advances | paid / submitted / approved. |
| Announcements | 3 sent (all / department) + 1 draft. |
| App devices | one device per user (random tokens - cannot be used to sign in). |
| AI Insights | findings produced by the real risk engine from the data below + 2 sample entries. |

### Built-in "problems" to demo the checks
| Who | What to look at |
|-----|-----------------|
| `demo.imran` | **Mock GPS** two days ago and 6 days ago; TA/DA claim of 85 km that the GPS track does not support (**Mismatch / False**). |
| `demo.jamal` | **Phone clock ahead of the server** 3 days ago (clock mismatch); his claim is **refused** with a reason. |
| `demo.farhana` | **GPS jump** (>160 km/h) 4 days ago. |
| `demo.mahmud` | Offline stretch (12:00-13:30) on 3 days -> points "Synced late"; one **offline punch-in** yesterday. |
| `demo.shirin` | Office worker who punched in **~650 m outside** the HQ geofence 5 days ago. |
| `demo.tasnim` | Arrives after 10:00 almost every day (late pattern); her claim re-uses one **duplicate bill** image. |
| `demo.sabbir` | Punched in today but **signal lost** ~40 minutes ago (shows offline on the map). |
| `demo.karim` | Absent today. `demo.rahim` / `demo.karim` have a far trip (Savar / Gazipur). |

## Re-run / refresh
**Field Force > Configuration > Demo Data** (administrators):
* **Generate / Regenerate** - deletes the old demo records and builds a fresh story ending today. Do this before a
  presentation: "online" status and today's punches are relative to the time of generation.
* **Remove demo data** - deletes only the records this module created (tracked by external id `nelsis_field_demo.demo_rec_*`).
  Real departments / job positions that already existed are re-used and never deleted.

## Notes / limits
* Not compiled or run in the build environment (no Odoo SDK). Python, XML and the simulation were checked in isolation;
  test on a staging database first. The TA/DA part writes to `conveyance.sheet*` / `employee.advance`, which were not in
  the upload, using only the fields that `nelsis_field_expense` itself uses. If your versions differ, that step is skipped
  and reported in the "Last run" box - everything else still loads.
* Demo claims are written directly (state set by the generator, no approval emails / accounting entries).
* The random generator uses a fixed seed: the same story every time, only shifted to today.
