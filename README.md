# SmartSpace

Smart Co-working Management System built on Frappe Framework.

## Features

1. Member Portal - Space booking (hourly, daily, weekly, monthly, yearly), parking allocation, complaints, lost and found, events, AI chatbot assistant
2. Supervisor Portal - Manage technicians, asset allocations, assets (set to damage), spaces, maintenance tasks, members, complaints, lost and found, events, dashboard stats
3. Technician Portal - View assigned tasks, start/finish work, flag unusable assets, profile management
4. Security Portal - Manage parking slots, assign/release parking, view members and visitors, dashboard stats
5. App Admin Portal - Analytics overview, location-wise stats, revenue trends, booking trends, AI insights, space and asset distribution
6. Asset Management - Track assets, allocations, maintenance, decommission, damage status with automatic allocation cancellation
7. Reservation System - Booking with auto member creation/upgrade, payment tracking, parking auto-assignment, expiry management
8. Notification System - Real-time notifications for complaints, lost and found, events, task updates, reservation changes
9. Role-based Access - Member, Supervisor, Technician, Security, App Admin with location-based filtering

## Setup

1. Install Frappe Bench (refer to https://frappeframework.com/docs/user/en/install)
2. Create a bench: bench init smartspace-bench
3. Get the app: bench get-app smartspace (from this repo)
4. Install the app: bench install-app smartspace
5. Start the server: bench start
6. Open browser at http://localhost:8000

## Doctypes

1. App User - User accounts with roles and locations
2. Member - Members with type (Flex/Regular) and booking history
3. Space - Workspaces (Desk, Cabin, Conference Room, Meeting Room, Private Office, Event Hall)
4. Reservation - Space bookings with payment and parking
5. Asset - Trackable assets with status and location
6. Asset Allocation - Asset assignments with active/cancelled status
7. Asset Maintenance - Maintenance requests linked to assets and complaints
8. Maintenance Task Allocation - Tasks assigned to technicians
9. Parking Slot - Parking slots with types and categories
10. Parking Allocation - Parking assignments linked to reservations
11. Complaints - Asset-related and general complaints with status tracking
12. Lost And Found - Lost and found item reports
13. Space Event - Events with funding and expenses
14. Staff - Supervisor, Technician, Security staff records
15. Payment - Payment records linked to reservations
16. Notification Log - User notification history

## Tech Stack

1. Backend - Python, Frappe Framework
2. Frontend - HTML, JavaScript, Tailwind CSS, Vue.js
3. Database - MariaDB
4. Framework - Frappe (ERPNext ecosystem)

## License

MIT