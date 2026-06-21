# Context Bridge — Week 1

## Folder Structure
```
context-bridge-week1/
│
├── experiments/               ← Run these first, no server needed
│   ├── day1_call_claude_api.py    Monday   — Call Claude API
│   └── day2_python_concepts.py   Tuesday  — Python fundamentals
│
├── backend/                   ← These need uvicorn to run
│   ├── day3_fastapi_basics.py    Wednesday — Build API routes
│   ├── day4_database.py          Thursday  — SQLite database
│   └── day5_fastapi_plus_db.py   Weekend   — Connect both together
│
└── requirements.txt           ← Install everything with one command
```

## Setup (do this first)
```bash
pip install -r requirements.txt
```

## How to run each day

### Day 1 & 2 (plain Python scripts)
```bash
cd experiments
python day1_call_claude_api.py
python day2_python_concepts.py
```

### Day 3 (FastAPI server)
```bash
cd backend
uvicorn day3_fastapi_basics:app --reload
# Open http://localhost:8000/docs
```

### Day 4 (plain Python script)
```bash
cd backend
python day4_database.py
```

### Day 5 (FastAPI + DB combined)
```bash
cd backend
uvicorn day5_fastapi_plus_db:app --reload
# Open http://localhost:8000/docs
```

## What you will know by end of Week 1
- How to call any AI API from Python
- How FastAPI routes work (GET, POST)
- How to store and retrieve data from SQLite
- How token tracking works
- The complete skeleton of our backend
