import os
import re
import sqlite3
import json
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
import sys
import io
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
DB = "database.db"

# ── Database setup ────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS challenges (
            id           INTEGER PRIMARY KEY,
            title        TEXT,
            topic        TEXT,
            difficulty   TEXT,
            description  TEXT,
            starter_code TEXT,
            done         INTEGER DEFAULT 0,
            bookmarked   INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS notes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER UNIQUE,
            content      TEXT,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS news_cache (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            content    TEXT,
            fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS user_solutions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER UNIQUE,
            code         TEXT,
            done         INTEGER DEFAULT 0,
            bookmarked   INTEGER DEFAULT 0,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS hint_cache (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER UNIQUE,
            content      TEXT,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY, name TEXT, department TEXT,
            dept_id INTEGER, salary REAL, age INTEGER
        );
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY, dept_name TEXT, location TEXT
        );
    """)

    existing = conn.execute("SELECT COUNT(*) FROM challenges").fetchone()[0]
    if existing == 0:
        challenges = [
            (1, "Pandas Basics", "Data Wrangling", "Easy",
             "Given a DataFrame with columns: name, age, score.\n\nTasks:\n1. Filter rows where age > 25\n2. Fill missing scores with the mean\n3. Sort by score descending\n4. Print the result",
             "import pandas as pd\n\ndf = pd.DataFrame({\n    'name':  ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],\n    'age':   [22, 30, 35, 28, 24],\n    'score': [88, 92, None, 76, None]\n})\n\n# Your code below\n"),
            (2, "Linear Regression from Scratch", "ML Fundamentals", "Easy",
             "Implement simple linear regression using only NumPy.\n\nGiven X and y values, calculate:\n1. Slope (m)\n2. Intercept (b)\n3. Predict y for X=10\n4. Print all results",
             "import numpy as np\n\nX = np.array([1, 2, 3, 4, 5, 6, 7])\ny = np.array([1.5, 3.2, 4.8, 6.1, 7.9, 9.2, 10.8])\n\n# Your code below\n"),
            (3, "Data Cleaning", "Data Wrangling", "Easy",
             "Clean this messy dataset:\n\n1. Drop duplicate rows\n2. Fill missing salary with median\n3. Strip whitespace from name\n4. Print cleaned DataFrame info",
             "import pandas as pd\n\ndf = pd.DataFrame({\n    'name':   ['Alice ', ' Bob', 'Charlie', 'Alice ', 'David'],\n    'salary': [50000, None, 70000, 50000, None],\n    'dept':   ['HR', 'IT', 'IT', 'HR', 'Finance']\n})\n\n# Your code below\n"),
            (4, "K-Means Clustering", "ML Fundamentals", "Medium",
             "Apply K-Means clustering on the given data.\n\n1. Use KMeans with 3 clusters\n2. Fit the model\n3. Print cluster labels\n4. Print cluster centers",
             "from sklearn.cluster import KMeans\nimport numpy as np\n\nX = np.array([\n    [1, 2], [1.5, 1.8], [5, 8],\n    [8, 8], [1, 0.6], [9, 11],\n    [8, 2], [10, 2], [9, 3]\n])\n\n# Your code below\n"),
            (5, "Feature Engineering", "Data Wrangling", "Medium",
             "Engineer new features from this sales dataset:\n\n1. Create revenue = price * quantity\n2. Create is_expensive = True if price > 100\n3. One-hot encode the category column\n4. Print final DataFrame",
             "import pandas as pd\n\ndf = pd.DataFrame({\n    'product':  ['A', 'B', 'C', 'D', 'E'],\n    'price':    [120, 45, 200, 80, 150],\n    'quantity': [3, 10, 2, 7, 4],\n    'category': ['Electronics', 'Food', 'Electronics', 'Food', 'Clothing']\n})\n\n# Your code below\n"),
            (6, "SQL - Basic SELECT", "SQL", "Easy",
             "You have a table called employees with columns:\nid, name, department, salary, age\n\nWrite a SQL query to:\n1. Select name and salary\n2. Only employees in Engineering\n3. Order by salary descending",
             "SELECT name, salary\nFROM employees\n-- Add WHERE and ORDER BY below\n"),
            (7, "SQL - GROUP BY & Aggregates", "SQL", "Easy",
             "Using the employees table:\nid, name, department, salary, age\n\nWrite a SQL query to:\n1. Count employees per department\n2. Show average salary per department\n3. Only include departments with more than 1 employee",
             "SELECT department, COUNT(*) as emp_count, AVG(salary) as avg_salary\nFROM employees\n-- Add GROUP BY and HAVING below\n"),
            (8, "SQL - JOIN", "SQL", "Medium",
             "You have two tables:\n- employees: id, name, dept_id, salary\n- departments: id, dept_name, location\n\nWrite a SQL query to:\n1. Join both tables\n2. Show employee name, dept_name, salary\n3. Only employees with salary > 60000",
             "SELECT e.name, d.dept_name, e.salary\nFROM employees e\n-- Add JOIN and WHERE below\n"),
            (9, "Decision Tree Classifier", "ML Fundamentals", "Medium",
             "Build a decision tree classifier:\n\n1. Use the iris dataset from sklearn\n2. Split into train/test (80/20)\n3. Train a DecisionTreeClassifier\n4. Print accuracy score",
             "from sklearn.datasets import load_iris\nfrom sklearn.tree import DecisionTreeClassifier\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.metrics import accuracy_score\n\niris = load_iris()\nX, y = iris.data, iris.target\n\n# Your code below\n"),
            (10, "Time Series Basics", "ML Fundamentals", "Medium",
             "Analyse this time series data:\n\n1. Calculate rolling mean with window=3\n2. Find the month with highest sales\n3. Calculate % change month over month\n4. Print all results",
             "import pandas as pd\n\ndata = {\n    'month': ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug'],\n    'sales': [150, 180, 165, 210, 195, 230, 245, 220]\n}\ndf = pd.DataFrame(data)\n\n# Your code below\n"),
        ]
        conn.executemany(
            "INSERT INTO challenges(id,title,topic,difficulty,description,starter_code) VALUES(?,?,?,?,?,?)",
            challenges
        )

    if conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
        conn.executemany("INSERT INTO employees VALUES(?,?,?,?,?,?)", [
            (1,'Alice','Engineering',1,95000,30),
            (2,'Bob','Marketing',2,62000,25),
            (3,'Charlie','Engineering',1,88000,35),
            (4,'Diana','HR',3,55000,28),
            (5,'Eve','Engineering',1,102000,32),
            (6,'Frank','Marketing',2,58000,27),
            (7,'Grace','HR',3,51000,24),
            (8,'Henry','Engineering',1,78000,29),
        ])
        conn.executemany("INSERT INTO departments VALUES(?,?,?)", [
            (1,'Engineering','New York'),
            (2,'Marketing','Chicago'),
            (3,'HR','Austin'),
        ])

    conn.commit()
    conn.close()


# ── Routes ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return "OK", 200

@app.route("/api/challenges")
def get_challenges():
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, n.content as note, s.code as saved_code,
               COALESCE(s.done,0) as done,
               COALESCE(s.bookmarked,0) as bookmarked,
               h.content as cached_hint
        FROM challenges c
        LEFT JOIN notes n ON c.id = n.challenge_id
        LEFT JOIN user_solutions s ON c.id = s.challenge_id
        LEFT JOIN hint_cache h ON c.id = h.challenge_id
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/challenges/<int:cid>/done", methods=["POST"])
def toggle_done(cid):
    conn = get_db()
    conn.execute("""
        INSERT INTO user_solutions(challenge_id, done) VALUES(?,1)
        ON CONFLICT(challenge_id) DO UPDATE SET done = NOT done
    """, (cid,))
    conn.commit()
    row = conn.execute("SELECT done FROM user_solutions WHERE challenge_id=?", (cid,)).fetchone()
    conn.close()
    return jsonify({"done": bool(row["done"]) if row else False})

@app.route("/api/challenges/<int:cid>/bookmark", methods=["POST"])
def toggle_bookmark(cid):
    conn = get_db()
    conn.execute("""
        INSERT INTO user_solutions(challenge_id, bookmarked) VALUES(?,1)
        ON CONFLICT(challenge_id) DO UPDATE SET bookmarked = NOT bookmarked
    """, (cid,))
    conn.commit()
    row = conn.execute("SELECT bookmarked FROM user_solutions WHERE challenge_id=?", (cid,)).fetchone()
    conn.close()
    return jsonify({"bookmarked": bool(row["bookmarked"]) if row else False})

@app.route("/api/challenges/<int:cid>/note", methods=["POST"])
def save_note(cid):
    content = request.json.get("content", "")
    conn    = get_db()
    conn.execute("""
        INSERT INTO notes(challenge_id, content) VALUES(?,?)
        ON CONFLICT(challenge_id) DO UPDATE SET content=excluded.content, updated_at=CURRENT_TIMESTAMP
    """, (cid, content))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/challenges/<int:cid>/solution", methods=["POST"])
def save_solution(cid):
    code = request.json.get("code", "")
    conn = get_db()
    conn.execute("""
        INSERT INTO user_solutions(challenge_id, code, done) VALUES(?,?,1)
        ON CONFLICT(challenge_id) DO UPDATE SET code=excluded.code, done=1, updated_at=CURRENT_TIMESTAMP
    """, (cid, code))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

# ── Python runner ──────────────────────────────────────────────────
@app.route("/api/run", methods=["POST"])
def run_code():
    code = request.json.get("code", "")
    if not code.strip():
        return jsonify({"output": "No code to run."})
    try:
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        exec(compile(code, "<string>", "exec"), {})
        sys.stdout = old_stdout
        return jsonify({"output": buffer.getvalue() or "Code ran with no output."})
    except Exception as e:
        sys.stdout = old_stdout
        return jsonify({"error": str(e)})

# ── SQL runner ─────────────────────────────────────────────────────
@app.route("/api/sql", methods=["POST"])
def run_sql():
    query = request.json.get("code", "").strip()
    if not query:
        return jsonify({"error": "No query provided."})
    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        cur  = conn.execute(query)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        return jsonify({"columns": cols, "rows": [list(r) for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)})

# ── Built-in hints ─────────────────────────────────────────────────
def builtin_hint(ch):
    hints = {
        "Data Wrangling": [
            "Use df.fillna(df['col'].mean()) to fill missing numeric values.",
            "Use df.drop_duplicates() to remove duplicate rows.",
            "Use df['col'].str.strip() to remove whitespace from strings.",
        ],
        "ML Fundamentals": [
            "Always split your data with train_test_split() before fitting.",
            "Use .fit() on training data only — never on the full dataset.",
            "Use accuracy_score(y_test, y_pred) to evaluate your model.",
        ],
        "SQL": [
            "Use WHERE to filter rows — it runs before GROUP BY.",