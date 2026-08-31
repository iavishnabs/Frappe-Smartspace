# SmartSpace — Installation & Setup Guide

Smart Co-working Management System built on the Frappe Framework (v15).

---

## 1. System Requirements

### Operating System
- Ubuntu 22.04 LTS (recommended) or any Linux distribution
- macOS (development only)
- Windows via WSL2 (Ubuntu)

### Python
- Python 3.10+ (required by Frappe v15)

### Node.js
- Node.js 18.x or 20.x

### Redis
- Redis 6.x+ (for queue, cache, and socketio)

### MariaDB
- MariaDB 10.6+ (recommended for production)
- MySQL 8.0 (alternative)

### Other System Packages
- `libmysqlclient-dev` (for Python MySQL driver)
- `libxslt1.1`, `libxslt-dev`, `libxml2-dev` (for XML processing)
- `build-essential`, `python3-dev`, `wget`, `curl`, `git`
- `pipx` (for installing Frappe CLI tools)
- `cron` (for scheduler)
- `nginx` (for production)
- `supervisor` (for production process management)

---

## 2. Install Prerequisites (Ubuntu 22.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3 python3-pip python3-dev \
    nodejs npm \
    redis-server \
    mariadb-server mariadb-client \
    libmysqlclient-dev \
    libxslt1.1 libxslt-dev libxml2-dev \
    build-essential wget curl git \
    cron nginx supervisor \
    pipx

# Install Yarn (for asset building)
sudo npm install -g yarn

# Configure pipx
pipx ensurepath
source ~/.bashrc
```

### Configure MariaDB

```bash
# Start MariaDB
sudo systemctl start mariadb
sudo systemctl enable mariadb

# Secure installation
sudo mysql_secure_installation

# Ensure Frappe-compatible settings
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

Add/verify these settings under `[mysqld]`:

```ini
[mysqld]
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
innodb-buffer-pool-size = 1G  # adjust based on available RAM
```

```bash
sudo systemctl restart mariadb
```

### Create Database User

```bash
sudo mysql -u root -p
```

```sql
CREATE USER 'smartspace'@'localhost' IDENTIFIED BY 'your_password';
CREATE DATABASE smartspace;
GRANT ALL PRIVILEGES ON smartspace.* TO 'smartspace'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## 3. Install Frappe Bench

```bash
# Install Frappe CLI via pipx
pipx install frappe-bench

# Verify installation
bench --version
```

---

## 4. Create a New Bench (or use existing)

### Option A: New Bench

```bash
# Create bench with Frappe v15
bench init --frappe-branch version-15 smartspace-bench

cd smartspace-bench
```

### Option B: Existing Bench

If you already have a v15 bench, skip to step 5.

---

## 5. Get the SmartSpace App

### From Git Repository

```bash
# From within your bench directory
bench get-app https://github.com/avishnabs/Frappe-Smartspace.git
```

### From Local Path

If you have the app source locally:

```bash
bench get-app /path/to/smartspace
```

---

## 6. Create a Site & Install the App

```bash
# Create a new site
bench new-site smartspace.local

# Install the SmartSpace app on the site
bench --site smartspace.local install-app smartspace
```

---

## 7. Build Assets & Start the Server

```bash
# Build frontend assets (JS, CSS, etc.)
bench build

# Start the development server
bench start
bench migrate
```

The app will be available at `http://localhost:8000`.

---

## 8. Access the Application

### Frappe Desk (Admin Backend)
- URL: `http://localhost:8000/app`
- Login with the Administrator credentials set during `bench new-site`.

### Portal Pages
- **Member Portal:** `http://localhost:8000/member/dashboard`
- **Technician Portal:** `http://localhost:8000/technician/dashboard`
- **Security Portal:** `http://localhost:8000/security/dashboard`
- **Supervisor Portal:** `http://localhost:8000/supervisor/dashboard`

### Admin Portal Pages
- **Analytics:** `http://localhost:8000/admin-portal/analytics`
- **Event Suggestions:** `http://localhost:8000/admin-portal/event-suggestions`
- **Chat Support:** `http://localhost:8000/admin-portal/chat`

---

## 9. PWA (Progressive Web App) Setup

SmartSpace portal pages (member, technician, security, supervisor) are PWA-enabled.

### PWA Files
- **Manifest:** `/assets/smartspace/manifest.json`
- **Service Worker:** `/assets/smartspace/sw.js`

### Testing PWA Locally

#### Option 1: Local Network (Same WiFi)
```bash
# Find your local IP
ip addr show | grep inet

# Start bench on a specific port
bench start --port 8001
```
Access from mobile at `http://<your-local-ip>:8001`

#### Option 2: ngrok (Public HTTPS Tunnel)
```bash
# Install ngrok
snap install ngrok

# Authenticate (get token from https://ngrok.com)
ngrok config add-authtoken YOUR_TOKEN

# Tunnel to your bench
ngrok http 127.0.0.1:8001
```
Access the ngrok HTTPS URL on your mobile browser and install as PWA.

### PWA Cache Version
The service worker uses a cache version string (`CACHE_VERSION`) in `sw.js`.
Bump this version whenever you deploy changes to force PWA clients to update:

```javascript
// smartspace/public/sw.js
const CACHE_VERSION = "v4";  // increment to push updates
```

---

## 10. App Structure

```
smartspace/
├── smartspace/
│   ├── hooks.py              # Frappe app configuration
│   ├── modules.txt           # Module list
│   ├── patches.txt           # Database patches
│   ├── notification.py       # Realtime notification system
│   ├── frontend_api/         # REST API endpoints for portals
│   │   ├── auth.py           # Authentication & role checks
│   │   ├── member.py         # Member portal APIs
│   │   ├── technician.py     # Technician portal APIs
│   │   ├── security.py       # Security portal APIs
│   │   ├── supervisor.py     # Supervisor portal APIs
│   │   ├── chat.py           # Chat support APIs
│   │   ├── analytics.py      # Analytics dashboard APIs
│   │   └── ai_insights.py    # AI-powered insights & suggestions
│   ├── space_booking/        # Space reservation & booking module
│   ├── space_finance/        # Financial transactions & expenses
│   ├── space_event/          # Event management module
│   ├── space_complaint/      # Complaint management module
│   ├── space_parking/        # Parking slot management
│   ├── space_asset/          # Asset tracking & allocation
│   ├── space_ai/             # AI chatbot & recommendations
│   ├── www/                  # Web pages (portals, admin pages)
│   │   ├── member/           # Member portal pages
│   │   ├── technician/       # Technician portal pages
│   │   ├── security/         # Security portal pages
│   │   ├── supervisor/       # Supervisor portal pages
│   │   ├── admin-portal/     # Admin portal pages
│   │   └── nav_footer/       # Shared header & footer includes
│   └── public/               # Static assets (JS, CSS, icons, PWA)
│       ├── manifest.json     # PWA manifest
│       ├── sw.js             # Service worker
│       └── js/               # Tailwind, Vue, Chart.js, Socket.io
├── pyproject.toml            # Python project config
└── INSTALLATION.md           # This file
```

---

## 11. Key Dependencies

| Dependency        | Purpose                          |
|-------------------|----------------------------------|
| Frappe Framework  | Core framework (v15)             |
| Tailwind CSS      | UI styling (CDN + local build)   |
| Vue.js 3          | Reactive frontend for admin pages|
| Chart.js          | Analytics charts & graphs        |
| Socket.io         | Realtime notifications           |
| Redis             | Caching, queue, and socketio     |
| MariaDB           | Database                         |

---

## 12. Scheduled Tasks

The app registers the following scheduled jobs (defined in `hooks.py`):

| Frequency | Task                                      |
|-----------|-------------------------------------------|
| Daily     | Expire pending bookings                   |
| Daily     | Close expired events                      |

---

## 13. Fixtures

The app includes fixtures for:
- Expense Categories (enabled records)
- Custom HTML Block: "Portal Link Button"

Run `bench --site <site> migrate` after installation to sync fixtures.

---

## 14. Production Deployment

### Using Frappe Cloud (Easiest)
1. Push your app to a Git repository
2. Create a new site on [Frappe Cloud](https://frappecloud.com)
3. Add your app repository and install

### Manual Production Setup

```bash
# Setup production config
sudo bench setup production smartspace

# Setup SSL (Let's Encrypt)
sudo bench setup lets-encrypt smartspace.local

# Setup supervisor & nginx
sudo bench setup supervisor
sudo bench setup nginx

# Reload services
sudo supervisorctl restart all
sudo systemctl reload nginx
```

---

## 15. Troubleshooting

### Bench commands not found
```bash
# Ensure pipx path is loaded
source ~/.bashrc
# Or use full path
~/.local/bin/bench --version
```

### Database connection error
```bash
# Verify MariaDB is running
sudo systemctl status mariadb

# Test connection
mysql -u smartspace -p -e "SELECT 1"
```

### Assets not loading
```bash
# Rebuild assets
bench build

# Clear cache
bench --site smartspace.local clear-cache
bench --site smartspace.local clear-website-cache
```

### Service worker not updating (PWA)
1. Close the installed PWA app completely
2. Reopen — the new service worker will activate
3. Or in Chrome DevTools: Application → Service Workers → Update/Unregister

### Port already in use
```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use a different port
bench start --port 8001
```

---

## 16. Useful Bench Commands

| Command | Description |
|---------|-------------|
| `bench start` | Start development server |
| `bench build` | Build frontend assets |
| `bench migrate` | Run database migrations |
| `bench --site <site> install-app smartspace` | Install app on site |
| `bench --site <site> clear-cache` | Clear site cache |
| `bench --site <site> backup` | Create database backup |
| `bench --site <site> doctor` | Check site health |
| `bench update` | Update all apps & migrate |
| `bench --site <site> console` | Open Python console |

---

## 17. License

MIT License — see `hooks.py` (`app_license = "mit"`)

---

## 18. Author

**avishna**  
Email: avishnazenha333@gmail.com

---

*Built with Frappe Framework v15*
