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
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS hint_cache (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER UNIQUE,
            content      TEXT,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
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

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY, name TEXT, department TEXT,
            dept_id INTEGER, salary REAL, age INTEGER
        );
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY, dept_name TEXT, location TEXT
        );
    """)

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


@app.route("/api/challenges")
def get_challenges():
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, n.content as note, s.code as saved_code, h.content as cached_hint
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
    conn.execute("UPDATE challenges SET done = NOT done WHERE id=?", (cid,))
    conn.commit()
    row = conn.execute("SELECT done FROM challenges WHERE id=?", (cid,)).fetchone()
    conn.close()
    return jsonify({"done": bool(row["done"])})


@app.route("/api/challenges/<int:cid>/bookmark", methods=["POST"])
def toggle_bookmark(cid):
    conn = get_db()
    conn.execute("UPDATE challenges SET bookmarked = NOT bookmarked WHERE id=?", (cid,))
    conn.commit()
    row = conn.execute("SELECT bookmarked FROM challenges WHERE id=?", (cid,)).fetchone()
    conn.close()
    return jsonify({"bookmarked": bool(row["bookmarked"])})


@app.route("/api/challenges/<int:cid>/note", methods=["POST"])
def save_note(cid):
    content = request.json.get("content", "")
    conn = get_db()
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
        INSERT INTO user_solutions(challenge_id, code) VALUES(?,?)
        ON CONFLICT(challenge_id) DO UPDATE SET code=excluded.code, updated_at=CURRENT_TIMESTAMP
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
        output = buffer.getvalue()
        return jsonify({"output": output or "Code ran successfully with no output."})
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


# ── Built-in hints fallback ────────────────────────────────────────
def builtin_hint(ch):
    hints = {
        "Data Wrangling": [
            "Use df.fillna(df['col'].mean()) to fill missing numeric values with the mean.",
            "Use df.drop_duplicates() to remove duplicate rows from your DataFrame.",
            "Use df['col'].str.strip() to remove leading/trailing whitespace from strings.",
        ],
        "ML Fundamentals": [
            "Always split your data with train_test_split() before fitting any model.",
            "Use .fit() on training data only — never on the full dataset.",
            "Use accuracy_score(y_test, y_pred) to evaluate classification models.",
        ],
        "SQL": [
            "Use WHERE to filter rows — it runs before GROUP BY.",
            "Use HAVING to filter groups after GROUP BY (e.g. HAVING COUNT(*) > 1).",
            "Use JOIN ... ON table1.id = table2.fk_id to connect two tables.",
        ]
    }
    topic_hints = hints.get(ch["topic"], [
        "Break the problem into smaller steps.",
        "Print intermediate results to understand what your code is doing.",
        "Re-read the problem description carefully before writing code.",
    ])
    return "\n".join(f"• {h}" for h in topic_hints)


# ── AI Hint ────────────────────────────────────────────────────────
@app.route("/api/hint/<int:cid>")
def get_hint(cid):
    conn = get_db()
    ch = conn.execute("SELECT * FROM challenges WHERE id=?", (cid,)).fetchone()
    cached = conn.execute(
        "SELECT content FROM hint_cache WHERE challenge_id=?", (cid,)
    ).fetchone()
    conn.close()

    # Return cached hint instantly
    if cached:
        return jsonify({"hint": cached["content"], "source": "cache"})

    # Try HuggingFace API
    key = os.getenv("HF_API_KEY")
    if key:
        try:
            prompt = (
                f"I am a beginner in Data Science working on this challenge:\n"
                f"Title: {ch['title']}\nDescription: {ch['description']}\n\n"
                f"Give me exactly 3 short beginner-friendly hints (not the full solution). "
                f"Format as bullet points starting with •. Be concise."
            )
            data = json.dumps({
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 250,
                    "temperature": 0.5,
                    "return_full_text": False
                }
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
                data=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode())

            if isinstance(result, list) and result:
                hint_text = result[0].get("generated_text", "").strip()
                if hint_text:
                    conn = get_db()
                    conn.execute("""
                        INSERT INTO hint_cache(challenge_id, content) VALUES(?,?)
                        ON CONFLICT(challenge_id) DO UPDATE SET content=excluded.content
                    """, (cid, hint_text))
                    conn.commit()
                    conn.close()
                    return jsonify({"hint": hint_text, "source": "ai"})
        except Exception as e:
            print(f"HuggingFace hint failed: {e}")

    # Fallback to built-in hints
    hint_text = builtin_hint(ch)
    conn = get_db()
    conn.execute("""
        INSERT INTO hint_cache(challenge_id, content) VALUES(?,?)
        ON CONFLICT(challenge_id) DO UPDATE SET content=excluded.content
    """, (cid, hint_text))
    conn.commit()
    conn.close()
    return jsonify({"hint": hint_text, "source": "builtin"})


# ── News — RSS with fallback ───────────────────────────────────────
@app.route("/api/news")
def get_news():
    sources = [
        "https://export.arxiv.org/rss/cs.LG",
        "https://export.arxiv.org/rss/cs.AI",
    ]

    for source_url in sources:
        try:
            req = urllib.request.Request(
                source_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
                    "Accept": "text/html,application/xhtml+xml,application/xml,*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_data = resp.read().decode("utf-8", errors="ignore")

            root  = ET.fromstring(xml_data)
            items = root.findall(".//item")
            news  = []

            for item in items[:8]:
                title_el   = item.find("title")
                link_el    = item.find("link")
                desc_el    = item.find("description")
                pubdate_el = item.find("pubDate")

                if title_el is None:
                    continue

                title   = title_el.text.strip() if title_el.text else "No title"
                link    = link_el.text.strip() if link_el is not None and link_el.text else ""
                summary = ""
                if desc_el is not None and desc_el.text:
                    summary = re.sub(r'<[^>]+>', '', desc_el.text).strip()[:200] + "..."
                date = pubdate_el.text[:16] if pubdate_el is not None and pubdate_el.text else ""

                tl = title.lower()
                if any(w in tl for w in ["language model","llm","gpt","transformer","generative","neural"]):
                    tag = "AI News"
                elif any(w in tl for w in ["survey","review","benchmark","analysis"]):
                    tag = "Research"
                elif any(w in tl for w in ["efficient","framework","tool","library","system"]):
                    tag = "Tools"
                else:
                    tag = "Research"

                news.append({"title": title, "summary": summary, "tag": tag, "date": date, "link": link})

            if news:
                conn = get_db()
                conn.execute("DELETE FROM news_cache")
                conn.execute("INSERT INTO news_cache(content) VALUES(?)", (json.dumps(news),))
                conn.commit()
                conn.close()
                return jsonify(news)

        except Exception as e:
            print(f"RSS source {source_url} failed: {e}")
            continue

    # Try cached news
    try:
        conn = get_db()
        cached = conn.execute(
            "SELECT content FROM news_cache ORDER BY fetched_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if cached:
            return jsonify(json.loads(cached["content"]))
    except Exception:
        pass

    # Hardcoded fallback — always works offline
    fallback = [
        {"title": "Attention Is All You Need — Transformer Architecture", "summary": "The seminal paper introducing the Transformer model which revolutionized NLP and deep learning.", "tag": "Research", "date": "2017-06-12", "link": "https://arxiv.org/abs/1706.03762"},
        {"title": "BERT: Pre-training of Deep Bidirectional Transformers", "summary": "Google's BERT model for language understanding using bidirectional training of Transformers.", "tag": "AI News", "date": "2018-10-11", "link": "https://arxiv.org/abs/1810.04805"},
        {"title": "XGBoost: A Scalable Tree Boosting System", "summary": "XGBoost is a highly efficient gradient boosting framework widely used in data science competitions.", "tag": "Tools", "date": "2016-03-09", "link": "https://arxiv.org/abs/1603.02754"},
        {"title": "Random Forests — Ensemble Learning Method", "summary": "Leo Breiman's random forests algorithm combining multiple decision trees for better accuracy.", "tag": "Research", "date": "2001-10-01", "link": "https://arxiv.org/abs/1106.0257"},
        {"title": "Deep Residual Learning for Image Recognition", "summary": "Microsoft's ResNet paper introducing skip connections to train very deep neural networks.", "tag": "AI News", "date": "2015-12-10", "link": "https://arxiv.org/abs/1512.03385"},
        {"title": "A Survey on Transfer Learning in Deep Learning", "summary": "Comprehensive survey covering transfer learning methods, applications and open research problems.", "tag": "Research", "date": "2019-08-01", "link": "https://arxiv.org/abs/1911.02685"},
    ]
    return jsonify(fallback)


if __name__ == "__main__":
    init_db()
    print("\nApp running at http://127.0.0.1:5000\n")
    app.run(debug=True)