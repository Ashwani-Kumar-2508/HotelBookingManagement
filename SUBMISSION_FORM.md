# Candidate Submission Form: Hotel Booking Domain Project

This document provides the exact structured text and values required to complete the internship project submission form.

---

## 1. Candidate Identification
* **Full Name:** Ashwani Kumar
* **Registration / Roll Number:** [Enter your University / College Registration Number, e.g., 2023-CS-XXXX]
* **University Email:** [Enter your official University / College Email, e.g., student@university.edu]

---

## 2. Assignment Confirmation
* **Internship Role:** Software Engineering Intern (Full Stack / Backend)
* **Assigned Project Title:** Responsive, Database-Backed Hotel Booking Application & Property Management System (GrandView Hotel & Resort)

---

## 3. Code and Version
* **Repository URL:** https://github.com/Ashwani-Kumar-2508/HotelBookingManagement
* **Primary Branch:** `main`
* **Final Commit ID:** `7515c65`
* **Reviewer Access:** Public repository (or granted reviewer read access)

---

## 4. Demonstration
* **Video Walkthrough Link:** [Insert your 3–5 minute video walkthrough link, e.g., Loom / YouTube Unlisted / Google Drive link]
* **Live Demo URL:** `Declared: Local-Only Demo` (Zero external hosting required. Complete local setup instructions provided in README.md)

---

## 5. Documentation Links
* **Technical Report Link:** Included in repository as `TECHNICAL_REPORT.md` (and README.md)
* **Database & Schema Architecture Diagram:** Included in `README.md` and `TECHNICAL_REPORT.md` (Mermaid ER diagram)
* **API Documentation Link:** `http://127.0.0.1:8000/api/docs/` (Interactive Swagger UI) and `http://127.0.0.1:8000/api/openapi.json` (OpenAPI 3.0 specification)

---

## 6. Technology Stack & Limitations
* **Technology Stack:**
  * **Frontend & UX:** React 18, Vite, Tailwind CSS, Lucide React, glassmorphism UI system, real-time hold countdown state engine
  * **Backend & Framework:** Python 3.13, Django 5.1 (Modular Monolith architecture)
  * **Database & Concurrency:** SQLite 3 (ACID, `select_for_update` pessimistic row locks, CheckConstraints, compound indices)
  * **API & Documentation:** OpenAPI 3.0.3, Interactive Swagger UI
  * **Testing:** Django TestCase suite (9/9 automated acceptance tests passed)
* **Setup Notes:**
  1. `cd CoServe`
  2. `.\venv\Scripts\Activate.ps1` (or `source venv/bin/activate`)
  3. `python manage.py migrate`
  4. `python manage.py seed_hotel_data`
  5. `python manage.py runserver` -> Visit `http://127.0.0.1:8000/`
* **Known Incomplete Features / Assumptions:**
  * Payment transactions operate in simulated test sandbox mode (dummy card `4242 ...`) in accordance with submission guidelines.
  * Physical RFID door key encoding hardware is abstracted by digital check-in confirmation vouchers.

---

## 7. Role-Specific Form Fields & Demo Accounts

### 1-Click Role Switcher
Reviewers do not need to type passwords. Every page features a top **Reviewer Demo Switcher Bar** and `/accounts/login/` includes **1-Click Quick Sign-In Buttons**:

| Role | Email | Password | Primary Console & Features |
|---|---|---|---|
| **Hotel Administrator** | `admin@grandview.com` | `adminpassword123` | Room & Rate CRUD (`/rooms/types/`), Operations Analytics (`/reports/dashboard/`), Audit Log (`/bookings/admin/audit-trail/`) |
| **Front Desk Staff** | `staff@grandview.com` | `staffpassword123` | Reception Desk (`/bookings/staff/desk/`), Check-In / Check-Out, Housekeeping Board (`/reports/housekeeping/`) |
| **Primary Guest** | `guest@example.com` | `guestpassword123` | Availability Search, 15-Minute Hold, Sandbox Checkout, Confirmation Voucher, My Stays (`/bookings/my-bookings/`), Cancellation |
| **Secondary Guest** | `sarah@example.com` | `guestpassword123` | Multi-user stay isolation and concurrency overlap verification |

---

## 8. AI and Attribution
* **AI Tools Used:** Google Antigravity (Gemini)
* **Purpose of Use:** Code scaffolding, schema design structuring, boilerplate reduction, and automated test scenario generation.
* **Third-Party Libraries & Asset Attribution:**
  * Tailwind CSS & Lucide Icons (CDN)
  * Swagger UI Bundle (CDN)
  * Unsplash Photography (Royalty-free hospitality demo photos)

---

## 9. Declarations
* **Originality & Code Explanation:** I declare that I wrote, understand, and can explain every architectural decision, schema relationship, and concurrency lock in this codebase during the live technical walkthrough and debugging evaluation.
* **Security & Sensitive Data:** I confirm that no real production secrets, passwords, or live payment credentials have been committed. A placeholder `.env.example` is provided.
* **Functional Verification:** I confirm that all internal links, automated tests (`python manage.py test apps.bookings`), and database seed scripts have been tested and verified to work locally.
