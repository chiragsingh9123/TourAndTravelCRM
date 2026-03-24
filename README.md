# 🧳 TourAndTravelCRM

> 🚀 A modern **Travel Agency CRM** built with **Flask · MySQL · Vanilla JS**
> Manage leads, bookings, payments & WhatsApp communication — all in one powerful dashboard.

---

## 🌟 Overview

TourAndTravelCRM is a **complete business solution for travel agencies** to manage their sales pipeline, customer interactions, and bookings efficiently.

It replaces messy Excel sheets, manual follow-ups, and scattered communication with a **centralized automation system**.

---

## ✨ Features

### 🧑‍💼 Lead Management

* Capture leads from multiple sources
* Assign leads to staff
* Track lead status (New → Contacted → Converted)

### 📞 Smart Conversation Timeline

* Log call details (duration, outcome)
* Maintain full communication history
* Auto-create follow-ups

### 📦 Tour Package Builder

* Create custom travel packages
* Add itinerary, hotel, transport & pricing
* Flexible pricing structure

### 🏨 Tour Categories

* Organize packages into categories
* Sub-category support
* Set starting prices for quick filtering

### 🎫 Bookings & Payments

* Convert leads into bookings
* Record partial/full payments
* Track pending balances

### 💬 WhatsApp Integration

* Pre-built message templates (Hindi + English)
* One-click send to customers
* Perfect for follow-ups & confirmations

### 📊 Dashboard & Reports

* Revenue analytics
* Staff performance tracking
* Lead conversion insights

### 🔐 Role-Based Access (JWT)

* Admin → Full control
* Manager → Operations + reports
* Staff → Assigned leads only

### 📌 Smart Notes System

* Add color-tagged notes
* Pin important information
* Quick access during calls

### 📤 Export System

* Export leads & bookings to CSV
* Useful for reporting & backups

---

## 🖼️ Screenshots (Add your images here)

```
/screenshots/dashboard.png
/screenshots/leads.png
/screenshots/booking.png
```

> 💡 Tip: Add screenshots to make your repo look 10x more professional

---

## 🗂️ Project Structure

```
TourAndTravelCRM/
│
├── backend/
│   └── app.py
│
├── db/
│   ├── travel_crm_leads.sql
│   ├── travel_crm_bookings.sql
│   ├── travel_crm_conversations.sql
│   ├── travel_crm_followups.sql
│   ├── travel_crm_packages.sql
│   ├── travel_crm_payments.sql
│   ├── travel_crm_users.sql
│   └── travel_crm_activity_logs.sql
│
└── frontend/
    ├── app.py
    └── templates/
        ├── base.html
        ├── login.html
        ├── dashboard.html
        ├── leads.html
        ├── lead_detail.html
        ├── lead_form.html
        ├── bookings.html
        ├── followups.html
        ├── tour_categories.html
        ├── reports.html
        ├── staff.html
        └── activity.html
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/chiragsingh9123/TourAndTravelCRM.git
cd TourAndTravelCRM
```

---

### 2️⃣ Install Dependencies

```bash
pip install flask flask-cors flask-jwt-extended mysql-connector-python bcrypt
```

---

### 3️⃣ Setup MySQL Database

Create database:

```sql
CREATE DATABASE travel_crm;
```

Import tables:

```bash
mysql -u root -p travel_crm < db/travel_crm_users.sql
mysql -u root -p travel_crm < db/travel_crm_leads.sql
mysql -u root -p travel_crm < db/travel_crm_bookings.sql
mysql -u root -p travel_crm < db/travel_crm_conversations.sql
mysql -u root -p travel_crm < db/travel_crm_followups.sql
mysql -u root -p travel_crm < db/travel_crm_packages.sql
mysql -u root -p travel_crm < db/travel_crm_payments.sql
mysql -u root -p travel_crm < db/travel_crm_activity_logs.sql
```

---

### 4️⃣ Configure Database

Edit `backend/app.py`:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "travel_crm"
}
```

---

### 5️⃣ Run Application

```bash
# Start Backend API
python backend/app.py
```

```bash
# Start Frontend
python frontend/app.py
```

---

### 🌐 Access App

👉 http://localhost:5000

---

## 🧠 Architecture

```
Frontend (HTML + JS)
        ↓
Flask API (Backend)
        ↓
MySQL Database
```

---

## 🚀 Future Improvements

* 🔄 Real-time notifications (WebSockets)
* 📱 Mobile app version
* 🌍 Multi-agency SaaS support
* 🤖 AI-based lead scoring
* 📊 Advanced analytics dashboard
* 💳 Payment gateway integration

---

## 🤝 Contributing

Contributions are welcome!

```bash
fork → clone → create branch → commit → push → PR
```

---

## 📄 License

MIT License — free to use, modify & distribute.

---

## ❤️ Support

If you like this project:

⭐ Star the repo
🍴 Fork it
📢 Share with others

---

<div align="center">

🔥 Built for Travel Businesses to Scale Faster 🚀

</div>
