## Full Project Flow

### Asset Chain

1. **Asset Item** — Admin creates category (Chair, AC, Desk)
2. **Asset Purchase** — Admin buys in bulk → auto-creates individual **Asset** records with serial numbers
3. **Asset Allocation** — Admin allocates assets to a Space via child table → assets marked "Allocated"
4. **Complaints** — User reports issue on Asset → technician assigned
5. **Asset Maintenance** — Technician fixes → asset back to "Allocated", or decommissioned if unusable

### Space Setup

1. **Location** → **Floor** → **Space** (with `hourly_rate`, `space_type`, `availability_status`)
2. **App Settings** — Admin sets office hours (09:00–18:00)

### Space Booking Flow

1. **User creates Reservation:**
   - Selects Space, Booking Type, Booking From, Count
   - `booking_to`, `rate`, `duration`, `total_amount` auto-calculated
   - **Conference Room** → Hourly only, throws error if Daily/Weekly/Monthly/Yearly selected
   - **Conference Room + existing Regular member** → total = 0 (free perk)
   - **Conference Room + Flex/new user** → paid hourly
   - Save → `booking_status = "Pending"`

2. **User clicks "Confirm":**
   - Member created/upgraded (Flex for Hourly/Daily, Regular for Weekly/Monthly/Yearly)
   - `expiry_date` updated to latest `booking_to`
   - Inactive members reactivated
   - Payment created (linked to Reservation, status "Pending")
   - `booking_status = "Booked"`, Space → "Occupied"
   - If total = 0 → no Payment created, `payment_status = "Paid"`

3. **User clicks "Pay Now":**
   - Payment → "Paid"
   - `booking_status = "Paid"`

4. **Daily scheduler:**
   - Expired bookings → `booking_status = "Completed"`, Space → "Available"


### Member Type Logic

| Booking Type | Member Type |
|---|---|
| Hourly / Daily | Flex |
| Weekly / Monthly / Yearly | Regular |

- Regular members get **Conference Room free** (checked from existing Member record, not current booking)
- Flex members pay for Conference Room hourly
- A user becomes Regular by booking a Desk/Cabin long-term first






Now update the Python controller.

Now update the JS with black buttons and no hover effect.

Now add CSS to remove hover effect on the black buttons.

Now let me also add permissions for App User role so any user can create reports.



----------------------------------------------------------------------------------------------
### Lost & Found Flow

**1. Any user creates report:**
- Selects Report Type (Lost/Found)
- Enters item name, description, image, location
- Save → `status = "Open"`, `reported_date` auto-set

**2. Admin clicks "Mark Returned" (black button, no hover):**
- Dialog opens to select:
  - **Matched Lost Report** — filtered to Open Lost reports only
  - **Returned To** — which App User claimed the item
- Both Found and matched Lost reports → `status = "Returned"`
- `matched_report` and `returned_to` set on both records

**3. Admin clicks "Close" (black button, no hover):**
- Both matched reports → `status = "Closed"`

### Buttons
- Black background (`#000000`), white text
- No hover effect — `mouseenter`/`mouseleave` handlers force same style
- `transition: none` to prevent CSS animation

### Permissions
- **System Manager** — full access (create, delete, read, write, report)
- **App User** — create, read, write, share (no delete, no report export)

### Chat
- Already linked via `related_doctype = "Lost And Found"` + `related_name` in Chat doctype
- Users and admin can chat on any specific Lost and Found report for verification

----------------------------------------------------------------------------------------------

## Parking Module

1. **Admin creates Parking Slots** — per location/floor, type (Bike/Car/Visitor), status = Available
2. **Security parks a car** — selects available slot, enters vehicle number, selects member (or blank for visitor) → slot becomes "Occupied"
3. **Security releases parking** — clicks "Release" → slot back to "Available", allocation marked "Completed"
4. **Security finds a vehicle** — clicks "Find Vehicle", types vehicle number → sees slot, member, parked since

----------------------------------------------------------------------------------------------

## Event Module

1. **Admin creates Event** — name, location, theme, start/end date, description → status = "Draft"
2. **Admin clicks "Publish"** → status = "Published", all members + staff notified
3. **Admin creates Event Fund** — links to event, sets budget
4. **Member contributes** — creates Member Event Fund with any amount → Payment auto-created (Paid) → Event Fund totals auto-update
5. **Admin creates Expense** — selects event, adds expense items → on "Approved", Event Fund + Event summary auto-refresh
6. **Daily scheduler** — events past end_date → "Completed"

### Visible on Event form
- **Total Collected** — sum of all contributions
- **Total Spent** — sum of approved expenses
- **Fund Balance** — collected minus spent

### Visible on Event Fund form
- **Total Collection**, **Total Expense**, **Fund Balance** — same logic, fund-level view

----------------------------------------------------------------------------------------------