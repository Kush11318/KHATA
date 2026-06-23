import sys
sys.path.append(r'c:\Projects\Invoice-Management-System-with-AI-Assistant')

from app import app, find_invoice_by_no

with app.app_context():
    inv = find_invoice_by_no('INV-2024-002', 'DEMO01', 'update invoice 002 to paid status')
    if inv:
        print("Matched Invoice No:", inv.invoice_no, "Status:", inv.status)
    else:
        print("No invoice matched!")
