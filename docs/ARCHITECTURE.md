# Architecture Notes

This document is the "why", not the "how" — the README covers running the
project; this covers the reasoning, so you can defend every decision in a
code review or an interview.

---

## 1. Why six small apps instead of one big app

Django's convention is "one app per bounded concern, not per feature
screen." Each app here owns exactly one thing:

- **`pages`** — has zero models. It only renders the public marketing
  site by *reading* from `services`. Kept separate so "what the internet
  sees before logging in" never gets tangled with auth or booking logic.
- **`accounts`** — owns identity. Every other app imports `User` from
  here; `accounts` imports from nowhere else. This one-way dependency is
  intentional — identity is the foundation everything else sits on.
- **`services`** — owns the catalog (what's sellable), with zero
  knowledge of bookings or users.
- **`bookings`** — owns the transaction lifecycle. It imports `services`
  (a booking needs a package) and `accounts` (a booking needs a customer
  and a beautician), but nothing imports *from* bookings except
  `adminpanel`.
- **`adminpanel`** — the only app allowed to import from all the others.
  This is deliberate: it's the "God view" layer, and confining that to
  one app means the domain apps (`accounts`, `services`, `bookings`) stay
  independently testable and reusable.
- **`notifications`** — a cross-cutting utility, imported by everyone,
  imports nothing domain-specific back. This is the same shape as a
  logging library.

If you diagram the imports, the arrows only point one way — nothing
circular. That's the actual test for "did I split this correctly."

---

## 2. The RBAC model, precisely

```
┌─────────────────────────────────────────────┐
│                  User                        │
│  role: customer | beautician | admin         │
│  is_active: bool   (email verification gate) │
│  email_verified: bool                        │
│  totp_secret, totp_enabled  (admin only)      │
└───────────────┬───────────────────────────────┘
                │ OneToOne (beauticians only)
                ▼
┌─────────────────────────────────────────────┐
│            BeauticianProfile                  │
│  latitude, longitude, service_radius_km       │
│  is_approved: bool   (admin approval gate)    │
│  rejected: bool                               │
│  skills: M2M ServiceSkill                     │
└───────────────────────────────────────────────┘
```

Three independent booleans gate a beautician's ability to log in and work:
`is_active` (their doing — click the email link), `is_approved` (an
admin's doing), and `rejected` (also an admin's doing, mutually exclusive
with approval). Keeping these as three separate flags rather than one
`status` enum was a deliberate choice: it lets the login view give a
*specific* message for each blocking reason instead of a single generic
"pending" state.

**Enforcement point:** `accounts/decorators.py::role_required`. This is
the *only* place role checks happen for view access — not scattered
`if request.user.role == ...` checks in every view body. Centralizing it
means you can audit every protected page in one file (search for
`@role_required` usages) instead of hunting through every view.

---

## 3. Why NOT Django's built-in `@login_required` / `LOGIN_URL`

Django assumes one login page for the whole site (`settings.LOGIN_URL`).
This project intentionally has three, because in the real product these
are different trust boundaries with different UX:

- A customer forgetting their password is a UX problem.
- A beautician logging in wrong is a UX problem.
- An admin's session is a **security** boundary — it can approve payouts,
  edit prices, and see revenue. It gets a completely separate login view
  (`login_admin`) that skips Django's `AuthenticationForm` entirely and
  hand-rolls the two-step password → TOTP flow, because
  `AuthenticationForm.get_user()` would call `authenticate()` and the
  *caller* still has to decide whether to trust that alone — here, we
  deliberately never call `django.contrib.auth.login()` until the second
  factor passes.

`role_required` picks the right one of the three login URLs to redirect
an unauthenticated visitor to, based on which role the decorator was
declared for — that's the glue that makes three login pages feel like
one coherent system instead of three disconnected ones.

---

## 4. The TOTP flow, step by step

```
Admin submits username+password
        │
        ▼
authenticate(username, password)  ──fails──▶  "Invalid admin credentials"
        │ succeeds
        ▼
session["pending_admin_id"] = user.id      (user is NOT logged in yet)
        │
        ▼
   totp_enabled?
   ┌────┴────┐
  no         yes
   │           │
   ▼           ▼
totp_setup   totp_verify
(generate      (just ask for
 secret,        current code)
 show QR,
 require 1
 correct code
 to enable)
   │           │
   └─────┬─────┘
         ▼
  code correct? ──no──▶ show error, stay on same page
         │ yes
         ▼
  auth_login(request, user)   ← THE session is only created here
  session.pop("pending_admin_id")
         ▼
  redirect to /panel/
```

**Why store the pending user id in the session instead of, say, a
short-lived signed token in the URL?** Because the session is already
server-side and tied to the browser via a cookie the user can't read or
tamper with — it's simpler and just as secure for this use case, and it's
automatically cleaned up (`session.pop`) the moment the flow completes or
the session expires.

**Why generate the secret in `totp_setup` rather than at signup time?**
Because `pyotp.random_base32()` should only be generated once and then
immutable — regenerating it on every failed setup attempt would
invalidate a QR code the admin already scanned. The check
`if not user.totp_secret:` makes secret generation idempotent — call
`totp_setup` as many times as you want before confirming, and you keep
seeing the *same* QR code.

---

## 5. The matching engine as a small pipeline

`find_nearest_available_beautician(booking)` is intentionally written as
a **filter → filter → rank** pipeline rather than one clever query, so
each rule is independently readable and testable:

```python
for profile in approved_and_not_rejected_beauticians:
    if distance(profile, booking) > profile.service_radius_km:
        continue          # rule 1: must be in range
    if has_conflict(profile.user, booking.slot_start, booking.slot_end):
        continue          # rule 2: must be free at this exact time
    track_as_candidate(profile, distance)  # rule 3 (final): closest wins
```

This same three-rule pipeline is reused in two places:
`find_nearest_available_beautician` (returns just the winner, used for
automatic matching) and `nearby_available_beauticians` (returns the
*whole* ranked list with in-range/available flags, used for the admin's
manual override screen). Both call the identical `haversine_km` and
`has_conflict` helpers — there is exactly one implementation of "how far"
and exactly one of "is this slot free," so they can never silently drift
out of sync with each other.

### Why booking time snapshots price (`package_price`, `platform_fee`)

This is the same reasoning real invoicing systems use: an invoice is a
*fact about a moment in time*, not a live view into current prices. If
`Booking.total_amount()` always joined live `ServicePackage.price`, then
editing a package's price today would silently rewrite the historical
revenue of every past booking of that package — which is both wrong and,
in a real business, a compliance problem. Storing the values at booking
time makes every booking an immutable receipt.

---

## 6. Request lifecycle for one booking (concrete walk-through)

1. `GET /bookings/package/<id>/book/` → `bookings.views.book_package` →
   renders `BookingForm`.
2. `POST` same URL → form validates → `Booking` row created with
   `status="pending"`, `package_price`/`platform_fee` snapshotted.
3. `send_booking_received_email(booking)` — customer gets a receipt-style
   email immediately, regardless of whether matching succeeds.
4. `notify_admin(...)` — an in-app `Notification` row appears on the
   admin bell right away.
5. `find_nearest_available_beautician(booking)` runs **synchronously**,
   in the same request. If it finds someone: `status="assigned"`,
   `send_booking_assigned_email` fires to both parties, and a second
   `notify_admin` call logs the auto-match.
6. Response redirects to `bookings:customer_dashboard`, where the booking
   now shows up with whatever status resulted.

**Note on synchronicity:** matching runs inline, in the request-response
cycle, not in a background task queue (Celery, etc.). For a learning
project and a small beautician pool this is simple and correct. At real
scale you'd move step 5 into an async task so the customer's response
doesn't wait on however long the scan takes — the *shape* of the matching
function wouldn't need to change, only where it's called from.

---

## 7. What to say if asked "how would you scale this"

- Move `haversine_km` scanning into the database: either PostGIS
  (`ST_DWithin`, `ST_Distance`) or an external service (Elasticsearch
  geo-queries) once the beautician count is in the thousands.
  `find_nearest_available_beautician`'s *interface* (booking in,
  beautician+distance out) wouldn't change — only its internals.
- Move email sending and matching off the request thread into Celery
  tasks, so booking creation returns instantly regardless of email
  latency or beautician-pool size.
- Notifications currently target "all admins" — at a bigger org you'd add
  a `recipient` FK and per-admin read state instead of one shared
  `is_read` flag.
- The `Booking.status` field would grow a proper state machine library
  (e.g. `django-fsm`) once there are more transitions (refunds, disputes,
  no-shows) than the current four states comfortably express by hand.
