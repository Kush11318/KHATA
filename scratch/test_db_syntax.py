import sys
sys.path.append(r'c:\Projects\Invoice-Management-System-with-AI-Assistant')

from app import app
from extensions import db
from sqlalchemy import text

with app.app_context():
    try:
        # Check if we can execute a dummy migration statement with TRUE/FALSE in SQLite
        db.session.execute(text("CREATE TABLE IF NOT EXISTS test_bool (id INTEGER PRIMARY KEY, val BOOLEAN NOT NULL DEFAULT FALSE, val2 BOOLEAN NOT NULL DEFAULT TRUE)"))
        db.session.commit()
        print("SQLite successfully created table with DEFAULT FALSE and DEFAULT TRUE!")
        # Clean up
        db.session.execute(text("DROP TABLE test_bool"))
        db.session.commit()
    except Exception as e:
        print(f"Error: {e}")
