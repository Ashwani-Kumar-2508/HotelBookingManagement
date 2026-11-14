# Quick Setup Guide — GrandView Hotel PMS

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| Node.js (optional, for React UI) | 18+ |
| Git | any recent |

---

## 1. Clone & Environment Setup

```bash
git clone https://github.com/Ashwani-Kumar-2508/HotelBookingManagement.git
cd HotelBookingManagement
```

**Create and activate virtual environment:**

```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

**Install Python dependencies:**

```bash
pip install -r requirements.txt
```

---

## 2. Environment Configuration

```bash
# Copy the example config
cp .env.example .env
```

The defaults in `.env.example` work for local development — no changes needed for a first run.

---

## 3. Database Initialisation

```bash
python manage.py migrate
```

---

## 4. Seed Demo Data

```bash
python manage.py seed_hotel_data
```

This creates:
- **4 demo accounts** (Admin, Staff, 2 Guests)
- **3 room types** (Standard, Deluxe, Presidential)
- **12 physical rooms** across 4 floors
- **10 amenities** (Wi-Fi, Ocean View, Minibar, etc.)
- **Sample reservations** in different states for the dashboard

---

## 5. Run the Development Server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

---

## 6. Demo Accounts

| Role | Email | Password | Quick-login |
|---|---|---|---|
| **Admin** | admin@grandview.com | adminpassword123 | 1-click on login page |
| **Staff** | staff@grandview.com | staffpassword123 | 1-click on login page |
| **Guest (David)** | guest@example.com | guestpassword123 | 1-click on login page |
| **Guest (Sarah)** | sarah@example.com | guestpassword123 | 1-click on login page |

---

## 7. Key Application URLs

| URL | Description | Access |
|---|---|---|
| `/` | Hotel homepage & availability search | Public |
| `/bookings/search/` | Room availability search | Public |
| `/accounts/login/` | Login (with 1-click demo buttons) | Public |
| `/accounts/register/` | Guest self-registration | Public |
| `/bookings/my-bookings/` | Guest booking history | Guest |
| `/bookings/staff/desk/` | Front desk arrivals console | Staff/Admin |
| `/reports/dashboard/` | Revenue & occupancy analytics | Admin |
| `/reports/housekeeping/` | Room status & housekeeping board | Staff/Admin |
| `/rooms/types/` | Room type administration | Admin |
| `/rooms/inventory/` | Physical room management | Admin |
| `/bookings/admin/audit-trail/` | Immutable audit log viewer | Admin |
| `/api/docs/` | Interactive Swagger UI | Public |
| `/api/openapi.json` | OpenAPI 3.0 specification | Public |
| `/admin/` | Django admin panel | Admin (superuser) |

---

## 8. Run the Test Suite

```bash
python manage.py test apps.bookings --verbosity=2
```

**Expected output: 9/9 tests PASSED**

```
test_cancellation_releases_inventory ... ok
test_expired_holds_do_not_block_inventory ... ok
test_guest_search_and_successful_booking ... ok
test_invalid_dates_handling ... ok
test_operations_report_matches_reservations ... ok
test_overlapping_booking_rejection ... ok
test_rest_api_availability_and_booking_journey ... ok
test_server_side_rbac_enforcement ... ok
test_staff_check_in_and_check_out_lifecycle ... ok

Ran 9 tests in ~54s

OK
```

---

## 9. Optional: React Frontend Dev Mode

The compiled React SPA is already included in `frontend/dist/` and served automatically by Django. To run the React dev server separately:

```bash
cd frontend
npm install
npm run dev
```

Then visit **http://localhost:5173/** for the React dev server (connects to Django API at `:8000`).

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `No module named 'django'` | Activate your virtualenv first |
| Login page shows "Demo user not found" | Run `python manage.py seed_hotel_data` |
| `PermissionDenied` on staff pages | Log in with the correct role account |
| Port 8000 already in use | `python manage.py runserver 8080` |
