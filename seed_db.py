import os
from datetime import datetime, date
from decimal import Decimal
from app import app
from extensions import db
from models import Seller, Product, Customer, Invoice, InvoiceItem, Activity

def seed():
    print("Starting database seeding...")
    with app.app_context():
        # Recreate tables to guarantee a clean slate
        print("Clearing existing database tables...")
        db.drop_all()
        db.create_all()

        # 1. Create Default Seller
        seller_email = "seller@example.com"
        seller = Seller.query.filter_by(s_email=seller_email).first()
        if not seller:
            seller = Seller(
                s_id="S001",
                s_name="Global Trade Corp",
                s_email=seller_email,
                s_address="123 Innovation Boulevard, Tech Park, New Delhi",
                s_phone="9876543210",
                password="seller"  # Plain text password as per models.py comparison
            )
            db.session.add(seller)
            db.session.commit()
            print("Default seller 'seller@example.com' created successfully (Password: 'seller').")
        else:
            print("Default seller already exists, skipping seller creation.")
            
        # Ensure we use this seller's ID
        s_id = seller.s_id

        # 2. Create Dummy Products
        products_data = [
            ("P001", "Wireless Mouse", 850.00, "Ergonomic 2.4GHz wireless mouse with optical tracker.", 45),
            ("P002", "Mechanical Keyboard", 2499.00, "RGB back-lit mechanical keyboard with brown switches.", 4), # Low stock!
            ("P003", "FullHD Monitor 24\"", 8999.00, "24-inch 1080p IPS display with 75Hz refresh rate.", 15),
            ("P004", "USB-C Docking Station", 3499.00, "Multi-port type-c docking hub with HDMI, USB 3.0, and PD charging.", 8), # Low stock!
            ("P005", "Noise Cancelling Headphones", 5999.00, "Over-ear active noise cancelling bluetooth headphones.", 25)
        ]

        for p_id, name, price, desc, stock in products_data:
            prod = Product.query.filter_by(p_id=p_id).first()
            if not prod:
                prod = Product(
                    p_id=p_id,
                    p_name=name,
                    p_price=Decimal(str(price)),
                    p_description=desc,
                    p_stock=stock,
                    s_id=s_id
                )
                db.session.add(prod)
                print(f"Product '{name}' seeded.")
        db.session.commit()

        # 3. Create Dummy Customers
        customers_data = [
            ("C001", "Alice Smith", "alice@gmail.com", "9988776655", "Flat 4B, Green Park Apartments, New Delhi"),
            ("C002", "Bob Jones", "bob@yahoo.com", "8877665544", "12th Floor, Bandra Heights, Bandra West, Mumbai"),
            ("C003", "Charlie Brown", "charlie@outlook.com", "7766554433", "Sector V, Salt Lake City, Kolkata"),
            ("C004", "Demo Customer", "customer@example.com", "9999999999", "123 Demo Street, Bangalore")
        ]

        for c_id, name, email, phone, addr in customers_data:
            cust = Customer.query.filter_by(c_id=c_id).first()
            if not cust:
                cust = Customer(
                    c_id=c_id,
                    c_name=name,
                    c_email=email,
                    c_phone_no=phone,
                    c_address=addr,
                    password="password",
                    s_id=s_id
                )
                db.session.add(cust)
                print(f"Customer '{name}' seeded.")
        db.session.commit()

        # 4. Create Dummy Invoices & Invoice Items
        # Invoice 1
        inv1 = Invoice.query.filter_by(invoice_no="INV001").first()
        if not inv1:
            inv1 = Invoice(
                invoice_no="INV001",
                invoice_datetime=datetime(2026, 6, 1, 10, 30),
                due_date=date(2026, 6, 15),
                status="paid",
                tax=Decimal("153.00"),
                amount=Decimal("1853.00"),
                s_id=s_id,
                c_id="C001"
            )
            db.session.add(inv1)
            # Items
            db.session.add(InvoiceItem(invoice_no="INV001", p_id="P001", item_quantity=2, discount=Decimal("0.00")))
            print("Invoice INV001 seeded.")

        # Invoice 2
        inv2 = Invoice.query.filter_by(invoice_no="INV002").first()
        if not inv2:
            inv2 = Invoice(
                invoice_no="INV002",
                invoice_datetime=datetime(2026, 6, 3, 14, 15),
                due_date=date(2026, 6, 20),
                status="pending",
                tax=Decimal("301.41"),
                amount=Decimal("3650.41"),
                s_id=s_id,
                c_id="C002"
            )
            db.session.add(inv2)
            # Items
            db.session.add(InvoiceItem(invoice_no="INV002", p_id="P002", item_quantity=1, discount=Decimal("0.00")))
            db.session.add(InvoiceItem(invoice_no="INV002", p_id="P001", item_quantity=1, discount=Decimal("0.00")))
            print("Invoice INV002 seeded.")

        # Invoice 3
        inv3 = Invoice.query.filter_by(invoice_no="INV003").first()
        if not inv3:
            inv3 = Invoice(
                invoice_no="INV003",
                invoice_datetime=datetime(2026, 6, 4, 16, 45),
                due_date=date(2026, 6, 30),
                status="paid",
                tax=Decimal("809.91"),
                amount=Decimal("9808.91"),
                s_id=s_id,
                c_id="C003"
            )
            db.session.add(inv3)
            # Items
            db.session.add(InvoiceItem(invoice_no="INV003", p_id="P003", item_quantity=1, discount=Decimal("0.00")))
            print("Invoice INV003 seeded.")

        # Invoice 4
        inv4 = Invoice.query.filter_by(invoice_no="INV004").first()
        if not inv4:
            inv4 = Invoice(
                invoice_no="INV004",
                invoice_datetime=datetime(2026, 6, 5, 11, 0),
                due_date=date(2026, 7, 5),
                status="pending",
                tax=Decimal("584.82"),
                amount=Decimal("7082.82"),
                s_id=s_id,
                c_id="C001"
            )
            db.session.add(inv4)
            # Items
            db.session.add(InvoiceItem(invoice_no="INV004", p_id="P005", item_quantity=1, discount=Decimal("0.00")))
            db.session.add(InvoiceItem(invoice_no="INV004", p_id="P001", item_quantity=1, discount=Decimal("0.00")))
            print("Invoice INV004 seeded.")

        db.session.commit()

        # Seed initial activities logs
        if Activity.query.count() == 0:
            db.session.add(Activity(user_id="S001", user_role="seller", action_type="product_added", description='Added product "Wireless Mouse"'))
            db.session.add(Activity(user_id="S001", user_role="seller", action_type="customer_created", description='Added customer "Alice Smith"'))
            db.session.add(Activity(user_id="S001", user_role="seller", action_type="invoice_created", description='Created Invoice INV001 for Alice Smith'))
            db.session.commit()
            print("Seeded log activities.")

        print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed()
