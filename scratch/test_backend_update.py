import sys
sys.path.append(r'c:\Projects\Invoice-Management-System-with-AI-Assistant')

from app import app
from models import Invoice

with app.test_client() as client:
    # Log in
    login_res = client.post('/login', data={
        'email': 'demo@invoiceai.com',
        'password': 'demo123'
    }, follow_redirects=True)
    
    # Process AI command
    res = client.post('/api/ai/process', json={
        'text': 'update invoice 002 to paid status',
        'history': [],
        'language': 'en-IN'
    })
    print("AI Process API Status Code:", res.status_code)
    print("AI Process API JSON Response:")
    import pprint
    pprint.pprint(res.get_json())
    
    # Verify invoice statuses in DB
    with app.app_context():
        inv_2025_002 = Invoice.query.filter_by(invoice_no='INV-2025-002').first()
        inv_2024_002 = Invoice.query.filter_by(invoice_no='INV-2024-002').first()
        inv_od_002 = Invoice.query.filter_by(invoice_no='INV-OD-002').first()
        print("INV-2025-002 (pending) status:", inv_2025_002.status if inv_2025_002 else "None")
        print("INV-2024-002 (paid) status:", inv_2024_002.status if inv_2024_002 else "None")
        print("INV-OD-002 (overdue) status:", inv_od_002.status if inv_od_002 else "None")
