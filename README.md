# Beauto — Service Booking Platform (Django)

An Urban-Company-style booking platform connecting **customers**, **beauticians**,
and **admins**, built in Django with real role-based access control, email
verification, two-factor admin login, and automatic nearest-beautician matching.


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



---

## 2. Run it locally 

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

---

## 4. Role-based access control (RBAC) — how it's actually enforced

There's one `User` model (`accounts/models.py`) with a `role` field
(`customer` / `beautician` / `admin`) instead of three separate tables.
Every foreign key elsewhere (`Booking.customer`, `Booking.beautician`)
points at the same table — this is the standard pattern for small-to-mid
RBAC systems.


### Why three login pages, not one

Real platforms like this (Urban Company, Uber, Swiggy) never show a
"customer or partner?" toggle on one page — the partner/admin experience
is a different product with different trust requirements. 

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


Customers and beauticians don't get TOTP in this project — email
verification is the appropriate bar for them. Admin accounts guard
platform-wide actions (approvals, revenue, service pricing), which is why
they get the stronger control.

---

## 6. Email notifications

All outgoing email is centralized in **`notifications/emails.py`** — Emails
fire for: signup verification, beautician application received,
beautician approved/rejected, booking received, booking assigned (both
customer and beautician get a copy), and any status change (reschedule,
cancel, completion).


## 7. In-app admin notifications ("every action is notified to admin")

Separate from email: — one function,
imported wherever something admin-relevant happens (new signup, new
booking, auto-assignment, completion, cancellation, reschedule).


---

## 8. Project structure

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
└── static/css/        theme 

```
