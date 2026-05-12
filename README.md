# CITS (JXON)

## Overview
CITS is an employee-first ticketing system designed to improve support team efficiency through automated context gathering, expertise-based routing, and proactive SLA risk detection.

## Key Features
- Auto-context gathering: attaches logs, client history, and related incidents to tickets
- Expertise-based routing: assigns tickets using weighted scoring (skill, recency, efficiency, load)
- Tiered collaboration: enables coordinated workflows between T1 and T2 support
- SLA breach prediction: identifies and flags high-risk tickets before deadlines
- Auto-resolution: handles routine requests such as password resets
- Skill tracking: builds agent skill profiles based on resolution patterns
- Privacy-first design: no individual monitoring; metrics are team-focused

## Tech Stack
- Backend: Python, FastAPI, SQLAlchemy
- Database: SQLite (designed for PostgreSQL migration)
- Frontend: Vanilla JavaScript (SPA)

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Seed database
python seed.py

# Run application
python -m app.main
