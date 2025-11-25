# Uniform Management System

> A simple system to manage and verify student/staff uniforms — checks items such as blazer ("blesser" typo handled), white shirt, tie, belt, ID card and shoes. Built to be easy to run, extend and integrate with school/college attendance or disciplinary tooling.

---

## Table of contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Tech stack](#tech-stack)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Database schema (example)](#database-schema-example)
8. [Running the app](#running-the-app)
9. [Usage / UI flow](#usage--ui-flow)
10. [API endpoints](#api-endpoints)
11. [Testing](#testing)
12. [Deployment](#deployment)
13. [Troubleshooting](#troubleshooting)
14. [Contributing](#contributing)
15. [License](#license)

---

## Project overview

This repository contains a Uniform Management System (UMS) that helps school/college staff verify and record uniform compliance. The app supports:

* Quick manual verification (checkboxes) for each student.
* Store verification history with timestamp and inspector name.
* Generate daily/weekly reports and export CSVs.
* Optional rules (e.g., "tie optional on Fridays") and custom item lists.

> **Note:** You wrote *"blesser"* in your request — I checked common usage and it appears you meant **"blazer"** (a jacket used in school uniforms). The README uses **blazer** as the standard item name but preserves your original spelling in notes where helpful.

## Features

* Check items: blazer, white shirt, tie, belt, ID card, shoes (customizable list).
* Store per-student verification records.
* Search students and view last verification state.
* Bulk import/export (CSV).
* Role-based access: `inspector`, `admin`.
* Simple web UI and REST API for integrations.

## Tech stack

* Backend: Python (Flask or Django — swap-in easily).
* Database: MySQL / PostgreSQL (configurable via env).
* Frontend: HTML/CSS/JS (Bootstrap or Tailwind optional).
* Optional: Docker for local dev and deployment.

## Prerequisites

* Python 3.10+ (if using Python stack)
* pip
* MySQL or PostgreSQL server (or SQLite for quick testing)
* (Optional) Docker & Docker Compose

## Installation

1. Clone the repo:

```bash
git clone <your-repo-url>
cd uniform-management-system
```

2. Create a venv and install deps:

```bash
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

3. Create `.env` (see Configuration) and set DB credentials.


FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=mysql+pymysql://user:pass@localhost/uniform_db
PORT=5000
```

Or set `DATABASE_URL` for Postgres:`postgresql://user:pass@host/dbname`.

## Database schema (example)

Below are suggested tables and fields. Adjust to your app.

```sql
-- students
CREATE TABLE students (
  id INT PRIMARY KEY AUTO_INCREMENT,
  roll_no VARCHAR(50) NOT NULL,
  name VARCHAR(150) NOT NULL,
  class VARCHAR(50),
  section VARCHAR(10),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- uniform_items (customizable list)
CREATE TABLE uniform_items (
  id INT PRIMARY KEY AUTO_INCREMENT,
  key_name VARCHAR(50) NOT NULL, -- e.g. blazer, white_shirt, tie
  display_name VARCHAR(100) NOT NULL,
  required BOOLEAN DEFAULT TRUE
);

-- verifications
CREATE TABLE verifications (
  id INT PRIMARY KEY AUTO_INCREMENT,
  student_id INT NOT NULL,
  inspector VARCHAR(150),
  verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  blazer BOOLEAN,    -- example items
  white_shirt BOOLEAN,
  tie BOOLEAN,
  belt BOOLEAN,
  id_card BOOLEAN,
  shoes BOOLEAN,
  notes TEXT,
  FOREIGN KEY (student_id) REFERENCES students(id)
);
```

## Running the app

### Local (without Docker)

```bash
# activate venv
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --port 5000
```

Visit `http://localhost:5000`.

### Using Docker

Provide a `Dockerfile` and `docker-compose.yml` that builds the app and links to a database container. Example quick commands:

```bash
docker compose up --build
```

## Usage / UI flow

1. Login as `inspector`.
2. Search student by roll number or name.
3. Open verification form and check items (blazer, white shirt, tie...).
4. Save — the record is stored with timestamp and inspector name.
5. Admins can view reports, export CSV, and change required item rules.

## API endpoints (example)

```
GET  /api/students               -> list students (query params: q, class, section)
GET  /api/students/:id           -> student details + last verification
POST /api/verifications         -> create verification record
GET  /api/verifications?date=... -> list verifications by date
POST /api/import/students       -> bulk import CSV
GET  /api/reports/daily?date=...-> export CSV report
```

Adjust routes to your implementation.

## Testing

* Unit tests for core logic (attendance rules, imports).
* Integration tests for API endpoints (use pytest + requests or Django test client).

Example:

```bash
pytest tests/
```

## Deployment

* Use Docker + managed database for production.
* Ensure `SECRET_KEY` and DB credentials are set via env vars.
* Configure HTTPS and a reverse proxy (nginx) for production.

## Troubleshooting

* DB connection errors: check `DATABASE_URL` and network access.
* Missing migrations: run `python manage.py migrate` or `flask db upgrade`.
* Timezone issues: ensure DB and app share expected timezone or store UTC.
