import sys
sys.path.append(r'c:\Projects\Invoice-Management-System-with-AI-Assistant')

from app import app
import ai_service
from models import Product, Customer, Invoice

with app.app_context():
    products = Product.query.filter_by(s_id='demo_seller', is_synced=True).all()
    customers = Customer.query.filter_by(s_id='demo_seller', is_synced=True).all()
    invoices = Invoice.query.filter_by(s_id='demo_seller').all()
    
    invoices_data = []
    for inv in invoices:
        invoices_data.append({
            'invoice_no': inv.invoice_no,
            'customer_name': inv.customer.c_name if inv.customer else 'Unknown',
            'amount': float(inv.amount),
            'status': inv.status,
            'date': inv.invoice_datetime.strftime('%Y-%m-%d') if inv.invoice_datetime else 'N/A',
            'due_date': inv.due_date.strftime('%Y-%m-%d') if inv.due_date else 'N/A',
            'is_bill': inv.is_bill,
            'accommodate_in_metrics': inv.accommodate_in_metrics,
            'items': [{'name': item.product.p_name if item.product else 'Unknown', 'quantity': item.item_quantity} for item in inv.items]
        })

    context = {
        'products': [p.to_dict() for p in products],
        'customers': [c.to_dict() for c in customers],
        'invoices': invoices_data
    }
    
    user_text = "update invoice 002 to paid status"
    print("User Text:", user_text)
    
    result = ai_service.parse_command(user_text, context, [], 'en-IN')
    print("AI Parsing Result:")
    import pprint
    pprint.pprint(result)
