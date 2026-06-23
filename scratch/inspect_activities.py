import sys
sys.path.append(r'c:\Projects\Invoice-Management-System-with-AI-Assistant')

from app import app
from models import Activity

with app.app_context():
    activities = Activity.query.order_by(Activity.timestamp.desc()).limit(10).all()
    print("Recent Activities:")
    for act in activities:
        print(f"Time: {act.timestamp}, Type: {act.action_type}, Desc: {act.description}")
