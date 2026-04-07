# Student Performance Analytics Web Application (Python)

A full-stack Flask application to manage student records, run performance analytics, upload CSV data, and export PDF reports.

## Features
- Authentication with role support (`Admin`, `Teacher`, `Student`)
- Student CRUD + marks entry
- Analytics dashboard with Chart.js visualizations
- CSV upload with pandas ingestion
- PDF report export per student
- Search/filter by class, name, and roll number

## Project Structure
```
app.py
models/
utils/
templates/
static/
uploads/
```

## Local Setup
1. **Python version:** Python 3.10+ recommended
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python app.py
   ```
4. Open `http://127.0.0.1:5000`

## Key Routes
- `/login`
- `/register`
- `/students`
- `/analytics`
- `/upload`

## CSV Format
Expected headers:
- `name`
- `roll_number`
- `class`
- `section`
- `subject`
- `marks`

## Notes
- Default database: SQLite (`student_analytics.db`)
- For PostgreSQL, set `DATABASE_URL` environment variable.
