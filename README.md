# Uniform Management System

> A simple system to manage and verify student/staff uniforms — checks items such as blazer ("blesser" typo handled), white shirt, tie, belt, ID card and shoes. Built to be easy to run, extend and integrate with school/college attendance or disciplinary tooling.

---

## Table of contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Tech stack](#tech-stack)
4. [Prerequisites](#prerequisites)
5. [Usage / UI flow](#installation)
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

