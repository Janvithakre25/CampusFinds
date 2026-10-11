# CampusFind — Cloud-Based Campus Lost-and-Found Portal

A clean, modern, fully functional web application designed for universities and colleges to reconnect students with their misplaced belongings. Built with Python Flask, MySQL, and responsive Bootstrap 5, and fully prepared for cloud deployment on Amazon Web Services (AWS RDS & S3).

---

## 📌 Project Overview
Belongings such as student ID cards, wallets, keys, headphones, laptops, and water bottles are frequently misplaced across university campuses. WhatsApp groups and physical noticeboards lack organization, privacy, and verification.

**CampusFind** solves this with:
- **Centralized Listings:** Report lost and found belongings with item photos, campus locations, and dates.
- **Privacy & Ownership Protection:** Private identifying marks (such as serial numbers, lock screens, engravings) are stored securely and never visible to the public.
- **Verification & Claims Workflow:** Claimants must provide proof matching private details before an item is approved.
- **Formal Handover Tracking:** In-person returns are logged with location and timestamps, preventing duplicate claims or disputes.
- **Admin Moderation & Security Audit Trail:** Administrative control panel for user moderation, listing oversight, and activity tracking.
- **Smart Matching Suggestions:** Rule-based heuristic that recommends matching lost/found items based on category and title keywords (completely free, no paid APIs).
- **AWS-Ready Architecture:** Switches effortlessly between local MySQL / storage and Amazon RDS / Amazon S3 via environment variables.

---

## 🛠️ Technology Stack
- **Backend:** Python 3.10+ & Flask (Modular Blueprints architecture)
- **Database:** MySQL 8.x / 9.x (Compatible with Amazon RDS for MySQL)
- **Database Driver:** PyMySQL with connection pooling & context teardown
- **Frontend:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5.3, Bootstrap Icons
- **Storage:** Local file system (dev) and Amazon S3 with secure Pre-Signed URLs (production ready)
- **Security:** PBKDF2/scrypt password hashing, session cookies, route authorization guards, SQL parameterization

---

## 📂 Project Structure
```text
CampusFinds/
├── app/
│   ├── __init__.py           # Flask app factory, error handlers & context processors
│   ├── config.py             # Environment configuration (local vs AWS RDS/S3)
│   ├── db.py                 # MySQL database connector and query helpers
│   ├── storage.py            # Image storage handler (Local uploads & Amazon S3)
│   ├── matching.py           # Similar-item suggestion heuristic
│   ├── auth_utils.py         # Route decorators (@login_required, @admin_required)
│   ├── routes/
│   │   ├── auth.py           # Registration, login, logout
│   │   ├── items.py          # Lost & found listings, search, reporting, details
│   │   ├── claims.py         # Ownership claim submission, review, handover
│   │   ├── dashboard.py      # Homepage, student dashboard, notifications
│   │   └── admin.py          # Admin statistics, user directory, moderation, logs
│   ├── static/
│   │   ├── css/style.css     # Custom UI styling and badges
│   │   ├── js/main.js        # Client-side image preview and alerts
│   │   └── uploads/          # Uploaded photos (local mode)
│   └── templates/
│       ├── base.html         # Base layout with navbar & notifications
│       ├── home.html         # Portal landing page
│       ├── auth/             # Login and registration templates
│       ├── items/            # Listing, detail, report lost/found forms
│       ├── claims/           # Claim submission, review & handover forms
│       ├── dashboard/        # Student dashboard & notifications
│       ├── admin/            # Admin control center, user & audit tables
│       └── errors/           # 404 and 500 error pages
├── database/
│   ├── schema.sql            # Clean MySQL schema with tables & constraints
│   └── seed.sql              # Demo data with admin and student accounts
├── tests/
│   └── test_app.py           # Automated pytest test suite
├── .env.example              # Environment variables template
├── .gitignore                # Git exclusions (credentials, uploads, venvs)
├── requirements.txt          # Python dependencies
├── run.py                    # Application launch script
└── README.md                 # Complete documentation
```

---

## 🚀 Quick Local Setup Guide

### 1. Prerequisites
- Python 3.10+ installed
- MySQL Server (v8.0+ or v9.0+) installed and running locally
- Git

### 2. Clone Repository & Install Dependencies
```bash
git clone https://github.com/Janvithakre25/CampusFinds.git
cd CampusFinds

# Create and activate a virtual environment (recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Configure Database & Environment
1. Copy the environment configuration template:
   ```bash
   cp .env.example .env
   ```
2. Update `.env` with your local MySQL password:
   ```env
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=campusfinds
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   STORAGE_BACKEND=local
   ```

### 4. Initialize MySQL Database
Run the schema and seed scripts in MySQL:
```bash
# Using MySQL Command Line Client:
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql
```
*(On Windows PowerShell, you can pipe the contents: `Get-Content database\schema.sql | mysql -u root -p`)*

### 5. Start the Application
```bash
python run.py
```
Open your web browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 🔑 Demo Login Accounts

| Role | Email | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@campusfinds.edu` | `Password123!` | Full control panel, manage listings, users, audit logs, approve claims |
| **Student (Alex)** | `alex@campusfinds.edu` | `Password123!` | Report lost/found items, file ownership claims, receive notifications |
| **Student (Samantha)** | `samantha@campusfinds.edu` | `Password123!` | Student dashboard, item reporting |
| **Student (David)** | `david@campusfinds.edu` | `Password123!` | Student dashboard, item reporting |

---

## 🧪 Running Automated Tests
The application includes automated integration tests covering user registration, login, report flows, claim processing, handover verification, and admin authorization guards.

Run tests using pytest:
```bash
pytest -v
```

All 6 automated test suites will pass.

---

## ☁️ Future AWS Deployment Preparation

CampusFind has been architected to transition to AWS without code rewrites:

### 1. Amazon RDS (MySQL)
- To connect to an Amazon RDS MySQL instance, simply change the variables in your production environment or AWS Elastic Beanstalk / ECS task definition:
  ```env
  DB_HOST=your-rds-endpoint.xxxxxx.region.rds.amazonaws.com
  DB_PORT=3306
  DB_NAME=campusfinds
  DB_USER=admin
  DB_PASSWORD=your_rds_password
  ```
- No code modifications required.

### 2. Amazon S3 (Image Storage)
- Set `STORAGE_BACKEND=s3` in your `.env`:
  ```env
  STORAGE_BACKEND=s3
  AWS_REGION=us-east-1
  AWS_S3_BUCKET_NAME=campusfinds-media-bucket
  ```
- When hosted on an EC2 instance or ECS task with an attached IAM Role (with S3 PutObject and GetObject permissions), AWS credentials are automatically resolved.
- S3 image URLs use secure, temporary **Pre-Signed URLs**, keeping the S3 bucket private from unauthorized public scrapers.

---

## 🛡️ Security Features
- **Password Protection:** Uses secure adaptive hashing algorithms (`scrypt`/`pbkdf2:sha256`) with unique salts.
- **Route Authorization Guards:** Custom decorators `@login_required` and `@admin_required` prevent unauthenticated access.
- **Confidentiality of Identifying Details:** Private fields are stripped from all public item listings and can only be accessed by the creator or an authorized administrator.
- **SQL Injection Prevention:** 100% parameterized SQL queries via PyMySQL.
- **Sanitized Uploads:** Validates file extensions (`png`, `jpg`, `jpeg`, `webp`, `gif`), restricts file sizes, and generates UUID-based filenames to avoid directory traversal.

---

## 📄 License
This project is open-source and developed for university campus communities.
