import os
import sys
sys.path.append(os.getcwd())

from app import app
from extensions import db
from models import Product, Customer

def cleanup():
    with app.app_context():
        # Inspect products with description 'Digitized product from bill'
        digitized_products = Product.query.filter(Product.p_description == 'Digitized product from bill').all()
        print(f"Found {len(digitized_products)} digitized products.")
        
        updated_count = 0
        for p in digitized_products:
            p.is_synced = False
            updated_count += 1
            print(f"Updated product: {p.p_name} (is_synced -> False)")
            
        # Inspect customers with address 'Extracted from digitized bill'
        digitized_customers = Customer.query.filter(Customer.c_address == 'Extracted from digitized bill').all()
        print(f"Found {len(digitized_customers)} digitized customers.")
        
        for c in digitized_customers:
            c.is_synced = False
            updated_count += 1
            print(f"Updated customer: {c.c_name} (is_synced -> False)")
            
        db.session.commit()
        print(f"Successfully updated {updated_count} records in database.")

if __name__ == '__main__':
    cleanup()
