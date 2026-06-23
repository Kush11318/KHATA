import sys
sys.path.append(r'c:\Projects\Invoice-Management-System-with-AI-Assistant')

from app import app
from models import Invoice

with app.app_context():
    invoices = Invoice.query.all()
    for inv in invoices:
        if "002" in inv.invoice_no or "002" in str(inv.invoice_no):
            print(f"Invoice No: {inv.invoice_no}, Seller ID: {inv.s_id}, Customer: {inv.customer_name}, Status: {inv.status}")
