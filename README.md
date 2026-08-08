# Beauto — Service Booking Platform (Django)

An Urban-Company-style booking platform connecting **customers**, **beauticians**,
and **admins**, built in Django with real role-based access control, email
verification, two-factor admin login, and automatic nearest-beautician matching.

This README is written so you can run it, demo it, and explain every
decision in an interview — not just paste it into GitHub.

---

## 1. What's actually in this project

| Concern | App | Key files |
|---|---|---|
| Public marketing site (Home/About/Services/Contact) | `pages` | `views.py`, `templates/pages/` |
| Users, roles, signup, email verification, admin 2FA | `accounts` | `models.py`, `views.py`, `totp_utils.py`, `decorators.py` |
| What can be booked (categories → services → packages) | `services` | `models.py` |
| The booking lifecycle + matching engine | `bookings` | `models.py`, `utils.py`, `views.py` |
| Admin-only dashboards (approvals, CRUD, assignment, revenue) | `adminpanel` | `views.py` |
| In-app activity feed for admins | `notifications` | `models.py`, `services.py` |

Read `docs/ARCHITECTURE.md` for the deep dive (RBAC design, the 2FA flow,
the matching algorithm, and why certain decisions were made). This README
just gets you running.

---

## 2. Run it locally (5 minutes)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env              # defaults work out of the box (SQLite, console email)

python manage.py migrate
python manage.py seed_services    # 5 categories, 9 services, 18 packages of demo data
python manage.py create_admin     # interactive — creates your admin account

python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

### Try the three roles

**As a customer:** Sign up → check your terminal for the verification email
(console backend prints it) → click the link → log in at
`/accounts/login/customer/` → go to Services → book a package → check
"My bookings".

**As a beautician:** Sign up with a real-ish latitude/longitude (e.g. use
Google Maps → right-click a spot → "What's here?" to copy coordinates) →
verify email → **you can't log in yet** — you're now sitting in the
admin's approval queue.

**As an admin:** `python manage.py create_admin`, then log in at
`/accounts/login/admin/`. First login walks you through **2FA setup** — a
QR code appears; scan it with Google Authenticator (or enter the text key
manually), then enter the current 6-digit code to confirm. From then on,
every admin login needs password + a fresh code.

Once logged in as admin: go to **Beautician approvals**, approve the
beautician you just registered. Now that beautician can log in and see
bookings assigned to them.

Go back to the customer's booking — if a beautician was in range and free,
it's already `assigned` (auto-matched at booking time). If not, it's
sitting in **Assignment queue**, where you can "Auto-assign nearest" or
pick manually from a ranked list.

---

## 3. The booking lifecycle (the part worth understanding)

```
Customer picks a package → fills in address + lat/lng + slot →
Booking created (status = "pending")
        │
        ▼
System tries find_nearest_available_beautician() immediately
        │
   ┌────┴────┐
   │ found   │ not found
   ▼         ▼
"assigned"  stays "pending" → shows up in admin's Assignment Queue
   │             │
   │        admin clicks "Auto-assign nearest" (same algorithm)
   │        or manually picks from a ranked, distance-sorted list
   │             │
   └─────┬───────┘
         ▼
  Beautician sees it on their dashboard → does the job →
  clicks "Mark completed" → status = "completed" → counts toward revenue
```

Customers can **reschedule** or **cancel** any booking that's still
`pending` or `assigned` (not once it's `completed`).

### The matching algorithm (`bookings/utils.py`)

Three functions do all the work:

- **`haversine_km(lat1, lon1, lat2, lon2)`** — the standard great-circle
  distance formula. This is why lat/lng, not addresses, drive matching —
  comparing address *strings* can't tell you "how far", but two
  coordinates can, cheaply, with no external API.
- **`has_conflict(beautician, start, end)`** — before assigning anyone,
  checks whether they already have an `assigned` booking whose time range
  overlaps the new one. This is what prevents double-booking.
- **`find_nearest_available_beautician(booking)`** — filters to
  *approved* beauticians, *within their stated service radius*, *free at
  that exact slot*, then returns the closest one. Used both at booking
  time (automatic) and by the admin's "Auto-assign" button.



---

## 4. Role-based access control (RBAC) — how it's actually enforced

There's one `User` model (`accounts/models.py`) with a `role` field
(`customer` / `beautician` / `admin`) instead of three separate tables.
Every foreign key elsewhere (`Booking.customer`, `Booking.beautician`)
points at the same table — this is the standard pattern for small-to-mid
RBAC systems.

**Enforcement** happens through `accounts/decorators.py` —
`@role_required("customer")` (or `"beautician"`, `"admin"`). This is a
custom replacement for Django's built-in `@login_required`, needed
because this project has **three separate login pages**, one per role
(see below), so a generic "redirect to LOGIN_URL" doesn't know which page
to send someone to.

Every dashboard view in `bookings/views.py` and `adminpanel/views.py` is
wrapped in one of these decorators — that's the entire access-control
surface. Nothing role-sensitive is gated only in a template (a template
`{% if %}` hides a button, but the decorator is what actually blocks the
request).

### Why three login pages, not one

Real platforms like this (Urban Company, Uber, Swiggy) never show a
"customer or partner?" toggle on one page — the partner/admin experience
is a different product with different trust requirements. Here:

- `/accounts/login/customer/` and `/accounts/login/beautician/` — same
  underlying Django `AuthenticationForm`, but each view checks
  `user.role` after authentication and rejects a mismatched account with
  a clear message ("That account isn't registered for this login page.")
- `/accounts/login/admin/` — deliberately **doesn't** use
  `AuthenticationForm` at all. See below.

### Two independent approval gates for beauticians

A beautician needs **both**:
1. `User.is_active = True` (flipped by clicking the email verification
   link), **and**
2. `BeauticianProfile.is_approved = True` (flipped by an admin).

The login view checks both and gives a specific message for each missing
piece — "verify your email" vs. "still awaiting admin approval" — so a
beautician always knows exactly what's blocking them.

---

## 5. Admin two-factor authentication (Google Authenticator / TOTP)

This is the one part of the project that isn't "just CRUD" — worth
understanding properly since it's a genuinely industry-standard pattern.

**TOTP (Time-based One-Time Password, RFC 6238)** is the algorithm behind
Google Authenticator, Authy, etc. Both your phone app and the server
independently compute a 6-digit code from **a shared secret + the current
time**, in 30-second windows. Neither side ever transmits the secret
after setup — that's why it's phishing-resistant in a way SMS codes
aren't.

The flow (`accounts/views.py`):

1. **`login_admin`** — checks username/password with `authenticate()`,
   but — critically — **does not call `auth_login()`**. It stashes the
   user's id in `request.session["pending_admin_id"]` and redirects to
   step 2. Password alone never logs an admin in.
2. **First time only — `totp_setup`**: generates `pyotp.random_base32()`
   as the secret, saves it to the user, and renders a QR code (via the
   `qrcode` library, returned as a base64 data URI — no media file
   needed). The admin scans it, types the current code, and **only after
   that code checks out** does `totp_enabled` flip to `True` and does
   `auth_login()` finally happen. Requiring one correct code before
   trusting the setup proves the app was actually scanned in — you can't
   accidentally lock yourself out with an unconfirmed secret.
3. **Every login after that — `totp_verify`**: just asks for the current
   code and checks it with `pyotp.TOTP(secret).verify(code, valid_window=1)`.
   `valid_window=1` tolerates ~30 seconds of clock drift between phone and
   server, which is normal and expected.

Customers and beauticians don't get TOTP in this project — email
verification is the appropriate bar for them. Admin accounts guard
platform-wide actions (approvals, revenue, service pricing), which is why
they get the stronger control.

---

## 6. Email notifications

All outgoing email is centralized in **`notifications/emails.py`** — no
view calls `django.core.mail` directly. Every function there renders one
of the plain-text templates in `templates/emails/` and sends it. Emails
fire for: signup verification, beautician application received,
beautician approved/rejected, booking received, booking assigned (both
customer and beautician get a copy), and any status change (reschedule,
cancel, completion).

By default `EMAIL_BACKEND` is Django's **console backend** — every email
just prints to your terminal, which is genuinely the right choice for
local development (no SMTP setup needed to see the verification flow
working). Switch to real SMTP in `.env`:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=your_address@gmail.com
EMAIL_HOST_PASSWORD=your_16_char_app_password   # Gmail "App Password", not your real password
```

## 7. In-app admin notifications ("every action is notified to admin")

Separate from email: `notifications/models.py` has a `Notification` model,
created by calling `notify_admin(message, link, category)` — one function,
imported wherever something admin-relevant happens (new signup, new
booking, auto-assignment, completion, cancellation, reschedule). The
admin navbar bell badge count comes from
`notifications/context_processors.py`, which injects
`unread_notification_count` into every template automatically — that's
why the badge shows up on every admin page without each view passing it
explicitly.

---

## 8. Money model — packages, platform fee, revenue

- A **`Service`** (e.g. "Bridal Makeup") has a **fixed `platform_fee`**.
- A **`ServicePackage`** (e.g. "Classic Bridal" / "Bridal Deluxe") under
  that service has its own **`price`** — this is the "varied amount
  price" per package.
- A customer books a *package*. `Booking.total_amount()` = package price
  + the service's platform fee.
- **Important detail**: `Booking` stores its own `package_price` and
  `platform_fee` at the moment of booking (`bookings/models.py`), rather
  than always looking up the live `ServicePackage`/`Service` values. This
  is deliberate — if an admin changes a package's price next month,
  historical revenue reports shouldn't silently change. This is the same
  reason real invoices snapshot prices instead of joining live product
  tables.
- The admin dashboard's "Gross revenue" and "Platform fee revenue" figures
  are computed only from `completed` bookings — pending/assigned money
  hasn't been earned yet.

---

## 9. Known simplifications (good "what I'd add next" talking points)

- Lat/lng are plain number inputs, not a real map picker — swap for
  Google Places Autocomplete / Leaflet in a real deployment; the matching
  logic itself doesn't change.
- No payment gateway integration.
- Beautician skills aren't yet filtered against service category during
  matching (any approved beautician can be matched to any service).
- No automated reminder emails (e.g. "your appointment is in 1 hour").
- The public Contact page form is a static demo — not wired to send mail.
- `haversine_km` scans every approved beautician in Python. Fine for a
  learning project / small dataset; a production version at scale would
  push this into the database (PostGIS) or a spatial index.

---

## 10. Project structure

```
beauto_platform/
├── config/            settings, urls, wsgi/asgi
├── pages/             public site: home, about, services catalog, contact
├── accounts/          User, BeauticianProfile, signup, RBAC, admin 2FA
├── services/          ServiceCategory, Service, ServicePackage + seed data
├── bookings/          Booking model, matching engine, customer/beautician views
├── adminpanel/        approvals, service/package CRUD, assignment, revenue
├── notifications/     Notification model + email templates/sender
├── templates/         all HTML, organized by app
├── static/css/        theme (matches beauto.in's purple/violet branding)
└── docs/
    └── ARCHITECTURE.md   deeper design notes + diagrams
```
