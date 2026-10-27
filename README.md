# Library Book Management System

A web-based library book management system built with Flask and SQLite.

## Features

- Book catalog with search by title or author
- Book registration with unique ISBN verification
- Member registration and listing
- Book issue tracking with a 14-day borrowing duration
- Borrowing limit enforcement of maximum 3 books per member
- Book return processing with overdue fine calculation at Rs. 5 per day

## Requirements

- Python 3.10 or higher
- Dependencies listed in requirements.txt

## Installation

1. Create and activate a Python virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Start the Flask application:

```bash
python app.py
```

The database tables are initialized automatically on startup. Open your browser and navigate to:

```text
http://127.0.0.1:5000
```

## Running Tests and Linting

Run automated unit and integration tests:

```bash
python -m pytest -v
```

Check code style and compliance with Flake8:

```bash
python -m flake8 app.py database.py tests
```
