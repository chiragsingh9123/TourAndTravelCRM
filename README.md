# 🧳 TourAndTravelCRM

> A production-ready **Travel Agency CRM** built with **Flask · MySQL · Vanilla JS**  
> Manage leads, packages, bookings, payments & WhatsApp messaging — all in one place.

---

## ✨ Features

| Module | Description |
|--------|-------------|
| 🧑‍💼 **Lead Management** | Capture, assign & track leads through the full sales pipeline |
| 📞 **Conversation Timeline** | Log calls with result, duration & auto follow-up scheduling |
| 📦 **Package Builder** | Build custom tour packages with itinerary, hotels, transport & pricing |
| 🏨 **Tour Categories** | Organize leads by tour type with sub-categories & starting prices |
| 🎫 **Bookings & Payments** | Convert leads to bookings, record partial payments, track balance |
| 💬 **WhatsApp Integration** | Pre-built Hindi/English message templates with one-click send |
| 📊 **Dashboard & Reports** | Revenue stats, staff performance & lead status breakdown |
| 🔐 **Role-based Access** | Admin, Manager & Staff roles with JWT authentication |
| 📌 **Pinned Notes** | Attach color-tagged notes to any lead |
| 📤 **CSV Export** | Export leads and bookings data anytime |

---

## 🗂️ Project Structure
```
TourAndTravelCRM/
│
├── 🐍 backend/
│   └── app.py                        # Flask REST API — all routes & DB logic
│
├── 🗄️ db/
│   ├── travel_crm_leads.sql          # Leads table
│   ├── travel_crm_bookings.sql       # Bookings table
│   ├── travel_crm_conversations.sql  # Call logs & timeline
│   ├── travel_crm_followups.sql      # Follow-up scheduler
│   ├── travel_crm_packages.sql       # Tour package builder
│   ├── travel_crm_payments.sql       # Payment records
│   ├── travel_crm_users.sql          # Staff & roles
│   └── travel_crm_activity_logs.sql  # Audit trail
│
└── 🎨 frontend/
    ├── app.py                        # Flask template server
    └── templates/
        ├── base.html                 # Shared layout & navigation
        ├── login.html                # JWT auth login page
        ├── dashboard.html            # Stats, charts & overview
        ├── leads.html                # Lead list with filters
        ├── lead_detail.html          # Full lead CRM view
        ├── lead_form.html            # Add new lead
        ├── bookings.html             # All bookings
        ├── followups.html            # Today's follow-ups
        ├── tour_categories.html      # Category & sub-category manager
        ├── reports.html              # Revenue & performance reports
        ├── staff.html                # Staff management
        └── activity.html             # Activity & audit logs
```

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/TourAndTravelCRM.git
cd TourAndTravelCRM
```

### 2. Install dependencies
```bash
pip install flask flask-cors flask-jwt-extended mysql-connector-python bcrypt
```

### 3. Set up the database
```bash
# Import all tables into MySQL
mysql -u root -p travel_crm < db/travel_crm_users.sql
mysql -u root -p travel_crm < db/travel_crm_leads.sql
# ... repeat for all files in /db
```

### 4. Configure DB credentials
Open `backend/app.py` and update:
```python
DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': '',
    'database': 'travel_crm'
}
```

### 5. Run the app
```bash
# Terminal 1 — API server
python backend/app.py

# Terminal 2 — Frontend server
python frontend/app.py
```

Then open **http://localhost:5000** in your browser 🎉

---

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)

---

## 🔐 Default Roles

| Role | Access |
|------|--------|
| **Admin** | Full access — users, reports, all leads |
| **Manager** | Leads, bookings, reports, staff view |
| **Staff** | Own assigned leads only |

---


## 📄 License

MIT License — feel free to use, modify & distribute.

---

<div align="center">
  Made with ❤️ for Travel Agencies
</div>