import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date, timedelta
from config import Config
from extensions import db
from models import Seller, Customer, Product, Invoice, InvoiceItem, Activity
from decimal import Decimal
import decimal
import ai_service

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Helper utilities

def migrate_database():
    """Add missing columns to existing database tables"""
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import OperationalError, ProgrammingError
    
    try:
        with app.app_context():
            # Check if invoices table exists
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'invoices' in tables:
                # Get existing columns
                columns = [col['name'] for col in inspector.get_columns('invoices')]
                
                # Add due_date column if it doesn't exist
                if 'due_date' not in columns:
                    print("Adding due_date column to invoices table...")
                    try:
                        db.session.execute(text("ALTER TABLE invoices ADD COLUMN due_date DATE NULL"))
                        db.session.commit()
                        print("Migration completed: due_date column added successfully!")
                    except (OperationalError, ProgrammingError) as e:
                        error_msg = str(e).lower()
                        if 'duplicate column name' in error_msg or 'already exists' in error_msg:
                            print("due_date column already exists, skipping migration.")
                        else:
                            print(f"Error adding due_date column: {e}")
                            db.session.rollback()
                else:
                    print("due_date column already exists, no migration needed.")
            else:
                print("Invoices table does not exist yet. It will be created by db.create_all()")
            
            # Check if customers table exists and add s_id column if needed
            if 'customers' in tables:
                customer_columns = [col['name'] for col in inspector.get_columns('customers')]
                if 's_id' not in customer_columns:
                    print("Adding s_id column to customers table...")
                    try:
                        db.session.execute(text("ALTER TABLE customers ADD COLUMN s_id VARCHAR(10) NULL"))
                        db.session.execute(text("ALTER TABLE customers ADD CONSTRAINT fk_customers_seller FOREIGN KEY (s_id) REFERENCES sellers(s_id)"))
                        db.session.commit()
                        print("Migration completed: s_id column added to customers table successfully!")
                    except (OperationalError, ProgrammingError) as e:
                        error_msg = str(e).lower()
                        if 'duplicate column name' in error_msg or 'already exists' in error_msg:
                            print("s_id column already exists, skipping migration.")
                        else:
                            print(f"Error adding s_id column: {e}")
                            db.session.rollback()
                else:
                    print("s_id column already exists in customers table, no migration needed.")
            
            # Check if sellers table exists and add s_logo column if needed
            if 'sellers' in tables:
                seller_columns = [col['name'] for col in inspector.get_columns('sellers')]
                if 's_logo' not in seller_columns:
                    print("Adding s_logo column to sellers table...")
                    try:
                        db.session.execute(text("ALTER TABLE sellers ADD COLUMN s_logo VARCHAR(255) NULL"))
                        db.session.commit()
                        print("Migration completed: s_logo column added to sellers table successfully!")
                    except (OperationalError, ProgrammingError) as e:
                        error_msg = str(e).lower()
                        if 'duplicate column name' in error_msg or 'already exists' in error_msg:
                            print("s_logo column already exists, skipping migration.")
                        else:
                            print(f"Error adding s_logo column: {e}")
                            db.session.rollback()
                else:
                    print("s_logo column already exists in sellers table, no migration needed.")
                
                if 's_theme' not in seller_columns:
                    print("Adding s_theme column to sellers table...")
                    try:
                        db.session.execute(text("ALTER TABLE sellers ADD COLUMN s_theme VARCHAR(20) DEFAULT 'system' NULL"))
                        db.session.commit()
                        print("Migration completed: s_theme column added to sellers table successfully!")
                    except (OperationalError, ProgrammingError) as e:
                        error_msg = str(e).lower()
                        if 'duplicate column name' in error_msg or 'already exists' in error_msg:
                            print("s_theme column already exists, skipping migration.")
                        else:
                            print(f"Error adding s_theme column: {e}")
                            db.session.rollback()
                else:
                    print("s_theme column already exists in sellers table, no migration needed.")
    except Exception as e:
        print(f"Migration check error: {e}")
        try:
            db.session.rollback()
        except:
            pass

def generate_next_product_id():
    """Generate next product ID using dictionary-based approach"""
    existing_ids = {pid for (pid,) in db.session.query(Product.p_id).all()}
    max_num = 0
    
    # Extract numbers from existing P### format IDs
    for pid in existing_ids:
        if pid.startswith('P') and len(pid) == 4:
            try:
                num = int(pid[1:])
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
    
    # Find next available ID
    while True:
        max_num += 1
        candidate = f"P{max_num:03d}"
        if candidate not in existing_ids:
            return candidate

def generate_next_customer_id():
    """Generate next customer ID safely to avoid duplicates"""
    existing_ids = {cid for (cid,) in db.session.query(Customer.c_id).all()}
    max_num = 0
    
    # Extract numbers from existing C### format IDs
    for cid in existing_ids:
        if cid and cid.startswith('C') and len(cid) == 4:
            try:
                num = int(cid[1:])
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
    
    # Find next available ID
    while True:
        max_num += 1
        candidate = f"C{max_num:03d}"
        if candidate not in existing_ids:
            return candidate

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] != role:
                flash('Access denied. Insufficient permissions.', 'error')
                user_role = session.get('user_role')
                if user_role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user_role == 'seller':
                    return redirect(url_for('seller_dashboard'))
                elif user_role == 'customer':
                    return redirect(url_for('customer_dashboard'))
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_activity(action_type, description):
    """Log an activity for the current user"""
    if 'user_id' in session and 'user_role' in session:
        activity = Activity(
            user_id=session['user_id'],
            user_role=session['user_role'],
            action_type=action_type,
            description=description
        )
        db.session.add(activity)
        db.session.commit()

def update_overdue_invoices():
    """Update invoice status to overdue if current date > due_date"""
    today = date.today()
    overdue_invoices = Invoice.query.filter(
        Invoice.status.in_(['pending', 'overdue']),
        Invoice.due_date.isnot(None),
        Invoice.due_date < today
    ).all()
    
    for invoice in overdue_invoices:
        if invoice.status != 'overdue':
            invoice.status = 'overdue'
    
    if overdue_invoices:
        db.session.commit()

def restore_stock_on_cancellation(invoice):
    """Restore product stock when invoice is cancelled"""
    for item in invoice.items:
        product = item.product
        if product:
            product.p_stock = product.p_stock + item.item_quantity

_git_commit_cache = None

def get_git_commit_info():
    global _git_commit_cache
    if _git_commit_cache is not None:
        return _git_commit_cache
        
    import subprocess
    try:
        commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip()
        commit_message = subprocess.check_output(['git', 'log', '-1', '--format=%s', 'HEAD'], text=True).strip()
        commit_date = subprocess.check_output(['git', 'log', '-1', '--format=%cd', '--date=format:%Y-%m-%d %H:%M:%S', 'HEAD'], text=True).strip()
        _git_commit_cache = {
            'hash': commit_hash,
            'message': commit_message,
            'date': commit_date,
            'url': f"https://github.com/Kush11318/Invoice-Management-System-with-AI-Assistant/commit/{commit_hash}"
        }
    except Exception as e:
        print(f"Error getting git commit info: {e}")
        _git_commit_cache = {
            'hash': 'Unknown',
            'message': 'No commit info available',
            'date': 'N/A',
            'url': '#'
        }
    return _git_commit_cache

@app.context_processor
def inject_git_commit():
    return {'git_commit': get_git_commit_info()}

@app.route('/')
def index():
    if 'user_id' in session:
        user_role = session.get('user_role')
        if user_role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user_role == 'customer':
            return redirect(url_for('customer_dashboard'))
        return redirect(url_for('seller_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check if user is admin
        if email == 'admin@admin.com' and password == 'admin':
            session['user_id'] = 'ADMIN'
            session['user_name'] = 'Admin'
            session['user_email'] = 'admin@admin.com'
            session['user_role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        
        # Check if user is a seller
        seller = Seller.query.filter_by(s_email=email).first()
        if seller and seller.check_password(password):
            session['user_id'] = seller.s_id
            session['user_name'] = seller.s_name
            session['user_email'] = seller.s_email
            session['user_role'] = 'seller'
            session['user_theme'] = seller.s_theme or 'system'
            return redirect(url_for('seller_dashboard'))
        
        # Check if user is a customer
        customer = Customer.query.filter_by(c_email=email).first()
        if customer and customer.check_password(password):
            session['user_id'] = customer.c_id
            session['user_name'] = customer.c_name
            session['user_email'] = customer.c_email
            session['user_role'] = 'customer'
            return redirect(url_for('customer_dashboard'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        password = request.form['password']
        role = request.form['role']
        
        try:
            if role == 'seller':
                # Check if seller email already exists
                existing_seller = Seller.query.filter_by(s_email=email).first()
                if existing_seller:
                    flash('Seller email already exists', 'error')
                    return render_template('auth/register.html')
                
                # Generate unique seller ID
                seller_count = Seller.query.count()
                seller_id = f"S{seller_count + 1:03d}"
                
                # Create new seller
                seller = Seller(
                    s_id=seller_id,
                    s_name=name,
                    s_email=email,
                    s_address=address,
                    s_phone=phone
                )
                seller.set_password(password)
                db.session.add(seller)
                db.session.commit()
                
                # Auto-login
                session['user_id'] = seller.s_id
                session['user_name'] = seller.s_name
                session['user_email'] = seller.s_email
                session['user_role'] = 'seller'
                
            
            flash('Registration successful!', 'success')
            return redirect(url_for('seller_dashboard'))
                
        except Exception:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/customer')
@login_required
@role_required('customer')
def customer_dashboard():
    # Fetch customer invoices
    invoices = Invoice.query.filter_by(c_id=session['user_id']).order_by(Invoice.invoice_datetime.desc()).all()
    
    # Calculate customer statistics
    total_invoices = len(invoices)
    total_amount = sum(float(inv.amount) for inv in invoices)
    pending_invoices = sum(1 for inv in invoices if inv.status in ['pending', 'overdue'])
    paid_invoices = sum(1 for inv in invoices if inv.status == 'paid')
    
    stats = {
        'total_invoices': total_invoices,
        'total_amount': total_amount,
        'pending_invoices': pending_invoices,
        'paid_invoices': paid_invoices
    }
    
    return render_template('customer/dashboard.html', stats=stats, invoices=invoices)

def refresh_demo_data_dates():
    """Dynamically shift the mock data invoice dates so they are always fresh,
    allowing the demo dashboard to show logical growth and overdue days."""
    try:
        from datetime import datetime, date, timedelta
        from extensions import db
        from models import Invoice
        
        # Define offsets for the seeded invoices to show stable, beautiful dashboard figures.
        offsets = {
            # Paid Invoices:
            "INV-2024-001": (90, "paid"),
            "INV-2024-002": (85, "paid"),
            "INV-2024-003": (80, "paid"),
            "INV-2024-004": (75, "paid"),
            "INV-2024-005": (70, "paid"),
            "INV-2024-006": (65, "paid"),
            "INV-2024-007": (10, "paid"),      # 10 days ago (this month)
            "INV-2024-008": (55, "paid"),
            "INV-2024-009": (45, "paid"),
            "INV-2024-010": (25, "paid"),      # 25 days ago (this month)
            "INV-2024-011": (15, "paid"),      # 15 days ago (this month)
            "INV-2024-012": (5, "paid"),       # 5 days ago (this month)
            
            # Pending Invoices:
            "INV-2025-001": (20, "pending"),
            "INV-2025-002": (15, "pending"),
            "INV-2025-003": (10, "pending"),
            "INV-2025-004": (5, "pending"),
            "INV-2025-005": (3, "pending"),
            
            # Overdue Invoices:
            "INV-OD-001": (50, "overdue"),
            "INV-OD-002": (45, "overdue"),
            "INV-OD-003": (38, "overdue"),
        }
        
        today = date.today()
        now = datetime.now()
        
        invoices = Invoice.query.filter_by(s_id="DEMO01").all()
        for inv in invoices:
            if inv.invoice_no in offsets:
                days_ago, status = offsets[inv.invoice_no]
                inv.status = status
                inv.invoice_datetime = now - timedelta(days=days_ago)
                
                if status == 'overdue':
                    inv.due_date = today - timedelta(days=days_ago - 30) if days_ago > 30 else today - timedelta(days=5)
                elif status == 'pending':
                    inv.due_date = today + timedelta(days=30 - days_ago) if days_ago < 30 else today + timedelta(days=5)
                else:
                    inv.due_date = today - timedelta(days=inv_date_diff if (inv_date_diff := days_ago - 15) > 0 else 5)
                    
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error refreshing demo dates: {e}")

@app.route('/seller')
@login_required
@role_required('seller')
def seller_dashboard():
    # Dynamically refresh demo invoices' dates to prevent stale data metrics over time
    if session.get('user_id') == 'DEMO01':
        refresh_demo_data_dates()
        
    # Calculate stats from database
    total_products = Product.query.filter_by(s_id=session['user_id']).count()
    # Count customers created by this seller
    total_customers = Customer.query.filter_by(s_id=session['user_id']).count()
    total_invoices = Invoice.query.filter_by(s_id=session['user_id']).count()
    paid_invoices_qs = Invoice.query.filter_by(s_id=session['user_id'], status='paid')
    pending_invoices_qs = Invoice.query.filter_by(s_id=session['user_id'], status='pending')
    overdue_invoices_qs = Invoice.query.filter_by(s_id=session['user_id'], status='overdue')
    paid_invoices_count = paid_invoices_qs.count()
    unpaid_invoices_count = pending_invoices_qs.count()
    overdue_invoices_count = overdue_invoices_qs.count()
    revenue_collected = sum(float(inv.amount) for inv in paid_invoices_qs.all())
    revenue_due = sum(float(inv.amount) for inv in pending_invoices_qs.all()) + sum(float(inv.amount) for inv in overdue_invoices_qs.all())
    
    # Calculate real dynamic revenue growth (last 30 days vs 30 to 60 days ago)
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    
    this_month_paid_val = db.session.query(db.func.sum(Invoice.amount)).filter(
        Invoice.s_id == session['user_id'],
        Invoice.status == 'paid',
        Invoice.invoice_datetime >= thirty_days_ago
    ).scalar() or 0.0
    
    last_month_paid_val = db.session.query(db.func.sum(Invoice.amount)).filter(
        Invoice.s_id == session['user_id'],
        Invoice.status == 'paid',
        Invoice.invoice_datetime >= sixty_days_ago,
        Invoice.invoice_datetime < thirty_days_ago
    ).scalar() or 0.0
    
    this_month_paid_revenue = float(this_month_paid_val)
    last_month_paid_revenue = float(last_month_paid_val)
    
    if last_month_paid_revenue > 0:
        revenue_growth_pct = ((this_month_paid_revenue - last_month_paid_revenue) / last_month_paid_revenue) * 100
    else:
        revenue_growth_pct = 100.0 if this_month_paid_revenue > 0 else 0.0
        
    # Calculate real average due days for pending/overdue invoices
    today = date.today()
    due_invoices = pending_invoices_qs.all() + overdue_invoices_qs.all()
    
    if due_invoices:
        days_diffs = []
        for inv in due_invoices:
            if inv.due_date:
                diff = (inv.due_date - today).days
                days_diffs.append(diff)
        if days_diffs:
            avg_days = sum(days_diffs) / len(days_diffs)
            if avg_days >= 0:
                revenue_due_note = f"Average due in {int(round(avg_days))} days"
            else:
                revenue_due_note = f"Average overdue by {int(round(abs(avg_days)))} days"
        else:
            revenue_due_note = "No due dates set"
    else:
        revenue_due_note = "No pending invoices"
    
    # Get recent activities for this seller
    recent_activities = Activity.query.filter_by(user_id=session['user_id']).order_by(Activity.timestamp.desc()).limit(5).all()
    
    stats = {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices_count,
        'unpaid_invoices': unpaid_invoices_count,
        'overdue_invoices': overdue_invoices_count,
        'revenue_collected': revenue_collected,
        'revenue_due': revenue_due,
        'revenue_growth_pct': revenue_growth_pct,
        'revenue_due_note': revenue_due_note
    }
    
    return render_template('seller/dashboard.html', stats=stats, activities=recent_activities)

@app.route('/seller/settings', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def seller_settings():
    seller = db.session.get(Seller, session['user_id'])
    if not seller:
        flash('Seller not found.', 'error')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        # Handlers for text fields
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        theme = request.form.get('theme', 'system').strip().lower()
        remove_logo = request.form.get('remove_logo') == 'true'
        
        if theme not in {'light', 'dark', 'system'}:
            theme = 'system'
        
        # Validation
        if not name or not email:
            flash('Name and Email are required.', 'error')
            return render_template('seller/settings.html', seller=seller)
            
        # Check if email is already in use by another seller
        existing_seller = Seller.query.filter(Seller.s_email == email, Seller.s_id != seller.s_id).first()
        if existing_seller:
            flash('Email is already in use by another seller.', 'error')
            return render_template('seller/settings.html', seller=seller)
            
        # Handle Logo File Upload
        logo_file = request.files.get('logo')
        
        # Create uploads folder if not exists
        upload_folder = os.path.join(app.static_folder, 'uploads', 'logos')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        # Remove logo if requested
        if remove_logo:
            if seller.s_logo:
                old_logo_path = os.path.join(app.static_folder, seller.s_logo)
                if os.path.exists(old_logo_path):
                    try:
                        os.remove(old_logo_path)
                    except Exception as e:
                        print(f"Error removing old logo: {e}")
                seller.s_logo = None
                
        elif logo_file and logo_file.filename != '':
            # Validate extension
            ext = logo_file.filename.rsplit('.', 1)[1].lower() if '.' in logo_file.filename else ''
            if ext not in {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}:
                flash('Invalid image format. Allowed formats: PNG, JPG, JPEG, GIF, WEBP, SVG.', 'error')
                return render_template('seller/settings.html', seller=seller)
                
            # Read file length to check size (limit 2MB)
            logo_file.seek(0, os.SEEK_END)
            file_length = logo_file.tell()
            logo_file.seek(0) # reset pointer
            if file_length > 2 * 1024 * 1024:
                flash('File size exceeds 2MB limit.', 'error')
                return render_template('seller/settings.html', seller=seller)
                
            # Remove old logo if it exists
            if seller.s_logo:
                old_logo_path = os.path.join(app.static_folder, seller.s_logo)
                if os.path.exists(old_logo_path):
                    try:
                        os.remove(old_logo_path)
                    except Exception as e:
                        print(f"Error removing old logo: {e}")
            
            # Secure new filename
            import time
            from werkzeug.utils import secure_filename
            safe_filename = f"logo_{seller.s_id}_{int(time.time())}.{ext}"
            logo_file.save(os.path.join(upload_folder, safe_filename))
            
            # Save relative path (relative to static/)
            seller.s_logo = f"uploads/logos/{safe_filename}"
            
        # Update database fields
        seller.s_name = name
        seller.s_email = email
        seller.s_phone = phone
        seller.s_address = address
        seller.s_theme = theme
        
        db.session.commit()
        
        # Sync session variables
        session['user_name'] = name
        session['user_email'] = email
        session['user_theme'] = theme
        
        log_activity('profile_update', 'Updated organization settings and profile details.')
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('seller_settings'))
        
    return render_template('seller/settings.html', seller=seller)

@app.route('/seller/academy')
@login_required
@role_required('seller')
def seller_academy():
    return render_template('seller/academy.html')

@app.route('/seller/products')
@login_required
@role_required('seller')
def seller_products():
    q = request.args.get('q', '').strip()
    base_query = Product.query.filter_by(s_id=session['user_id'])
    if q:
        products = base_query.filter(Product.p_name.ilike(f"%{q}%")).all()
    else:
        products = base_query.all()
    return render_template('seller/products.html', products=products, q=q)

@app.route('/seller/products/add', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def add_product():
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = Decimal(request.form['price'])
            description = request.form['description']
            stock = int(request.form['stock'])
            
            # Generate product ID safely (avoid duplicates)
            product_id = generate_next_product_id()
            
            new_product = Product(
                p_id=product_id,
                p_name=name,
                p_price=price,
                p_description=description,
                p_stock=stock,
                s_id=session['user_id']
            )
            
            db.session.add(new_product)
            db.session.commit()
            
            # Log activity
            log_activity('product_added', f'Added new product "{name}"')
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('seller_products'))
            
        except Exception:
            db.session.rollback()
            flash('Failed to add product', 'error')
    
    return render_template('seller/add_product.html')

@app.route('/seller/products/edit/<product_id>', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def edit_product(product_id):
    product = Product.query.filter_by(p_id=product_id, s_id=session['user_id']).first()
    
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('seller_products'))
    
    if request.method == 'POST':
        try:
            product.p_name = request.form['name']
            product.p_price = Decimal(request.form['price'])
            product.p_description = request.form['description']
            product.p_stock = int(request.form['stock'])
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('seller_products'))
            
        except Exception:
            db.session.rollback()
            flash('Failed to update product', 'error')
    
    return render_template('seller/edit_product.html', product=product)

@app.route('/seller/products/delete/<product_id>')
@login_required
@role_required('seller')
def delete_product(product_id):
    try:
        product = Product.query.filter_by(p_id=product_id, s_id=session['user_id']).first()
        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('seller_products'))
        
        # Check if product is referenced in any invoice items
        invoice_items = InvoiceItem.query.filter_by(p_id=product_id).all()
        if invoice_items:
            flash(f'Cannot delete product "{product.p_name}" because it is referenced in {len(invoice_items)} invoice(s). Please delete the invoices first.', 'error')
            return redirect(url_for('seller_products'))
        
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete product: {str(e)}', 'error')
    
    return redirect(url_for('seller_products'))

@app.route('/api/products/add', methods=['POST'])
@login_required
@role_required('seller')
def api_add_product():
    """API endpoint to add a product from invoice creation page"""
    try:
        data = request.json
        name = data.get('name')
        price = Decimal(data.get('price', 0))
        description = data.get('description', '')
        stock = int(data.get('stock', 0))
        
        if not name or price <= 0:
            return jsonify({'success': False, 'error': 'Invalid product data'}), 400
        
        # Generate product ID safely
        product_id = generate_next_product_id()
        
        new_product = Product(
            p_id=product_id,
            p_name=name,
            p_price=price,
            p_description=description,
            p_stock=stock,
            s_id=session['user_id']
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        # Log activity
        log_activity('product_added', f'Added new product "{name}" from invoice creation')
        
        return jsonify({
            'success': True,
            'product': new_product.to_dict()
        })
        
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/seller/customers')
@login_required
@role_required('seller')
def seller_customers():
    try:
        # Show only customers created by this seller
        q = request.args.get('q', '').strip()
        
        # Verify session has user_id
        if 'user_id' not in session:
            flash('Session expired. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        # Get customers created by this seller only (s_id must match)
        base = Customer.query.filter(Customer.s_id == session['user_id'])
        
        if q:
            base = base.filter(Customer.c_name.ilike(f"%{q}%"))
        
        customers = base.order_by(Customer.c_name.asc()).all()
        return render_template('seller/customers.html', customers=customers, q=q)
    except Exception as e:
        # Log error but don't break the page
        print(f"Error in seller_customers route: {e}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while loading customers. Please try again.', 'error')
        return render_template('seller/customers.html', customers=[], q='')

@app.route('/seller/customers/<customer_id>/invoices')
@login_required
@role_required('seller')
def view_customer_invoices(customer_id):
    # Verify customer belongs to this seller
    customer = Customer.query.filter_by(c_id=customer_id, s_id=session['user_id']).first()
    
    if not customer:
        flash('Customer not found or access denied', 'error')
        return redirect(url_for('seller_customers'))
    
    invoices = Invoice.query.filter_by(c_id=customer_id, s_id=session['user_id']).all()
    return render_template('seller/customer_invoices.html', customer=customer, invoices=invoices)

@app.route('/seller/customers/add', methods=['POST'])
@login_required
@role_required('seller')
def add_customer():
    try:
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        
        # Check if customer email already exists
        existing_customer = Customer.query.filter_by(c_email=email).first()
        if existing_customer:
            flash('Customer with this email already exists', 'error')
            return redirect(url_for('seller_customers'))
        
        # Generate customer ID safely
        customer_id = generate_next_customer_id()
        
        # Create new customer
        customer = Customer(
            c_id=customer_id,
            c_name=name,
            c_email=email,
            c_phone_no=phone,
            c_address=address,
            password='',  # Avoid DB default issues
            s_id=session['user_id']  # Track which seller created this customer
        )
        db.session.add(customer)
        db.session.commit()
        
        # Log activity
        log_activity('customer_created', f'Created new customer "{name}"')
        
        flash('Customer added successfully!', 'success')
        return redirect(url_for('seller_customers'))

    except Exception:
        db.session.rollback()
        flash('Failed to add customer', 'error')
        return redirect(url_for('seller_customers'))

@app.route('/seller/customers/edit/<customer_id>', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def edit_customer(customer_id):
    # Verify customer belongs to this seller
    customer = Customer.query.filter_by(c_id=customer_id, s_id=session['user_id']).first()
    
    if not customer:
        flash('Customer not found or access denied', 'error')
        return redirect(url_for('seller_customers'))
    
    if request.method == 'POST':
        try:
            # Check if email changed and if new email already exists
            new_email = request.form['email']
            if new_email != customer.c_email:
                existing_customer = Customer.query.filter_by(c_email=new_email).first()
                if existing_customer:
                    flash('Customer with this email already exists', 'error')
                    return redirect(url_for('edit_customer', customer_id=customer_id))
            
            customer.c_name = request.form['name']
            customer.c_email = new_email
            customer.c_phone_no = request.form['phone']
            customer.c_address = request.form['address']
            
            db.session.commit()
            
            # Log activity
            log_activity('customer_updated', f'Updated customer "{customer.c_name}"')
            
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('seller_customers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update customer: {str(e)}', 'error')
    
    return render_template('seller/edit_customer.html', customer=customer)

@app.route('/seller/customers/delete/<customer_id>')
@login_required
@role_required('seller')
def delete_customer(customer_id):
    try:
        # Verify customer belongs to this seller
        customer = Customer.query.filter_by(c_id=customer_id, s_id=session['user_id']).first()
        
        if not customer:
            flash('Customer not found or access denied', 'error')
            return redirect(url_for('seller_customers'))
        
        # Check if customer has invoices
        invoices = Invoice.query.filter_by(c_id=customer_id, s_id=session['user_id']).all()
        if invoices:
            flash(f'Cannot delete customer "{customer.c_name}" because they have {len(invoices)} invoice(s). Please delete or update the invoices first.', 'error')
            return redirect(url_for('seller_customers'))
        
        # Log activity before deletion
        log_activity('customer_deleted', f'Deleted customer "{customer.c_name}"')
        
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete customer: {str(e)}', 'error')
    
    return redirect(url_for('seller_customers'))

@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    """Admin dashboard to manage all sellers"""
    sellers = Seller.query.order_by(Seller.s_name.asc()).all()
    
    # Get statistics
    total_sellers = Seller.query.count()
    total_customers = Customer.query.count()
    total_products = Product.query.count()
    total_invoices = Invoice.query.count()
    
    stats = {
        'total_sellers': total_sellers,
        'total_customers': total_customers,
        'total_products': total_products,
        'total_invoices': total_invoices
    }
    
    return render_template('admin/dashboard.html', sellers=sellers, stats=stats)

@app.route('/admin/sellers')
@login_required
@role_required('admin')
def admin_sellers():
    """List all sellers"""
    sellers = Seller.query.order_by(Seller.s_name.asc()).all()
    return render_template('admin/sellers.html', sellers=sellers)

@app.route('/admin/sellers/<seller_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_seller(seller_id):
    """Edit seller details"""
    seller = db.session.get(Seller, seller_id)
    if not seller:
        flash('Seller not found', 'error')
        return redirect(url_for('admin_sellers'))
    
    if request.method == 'POST':
        try:
            seller.s_name = request.form.get('name', seller.s_name)
            seller.s_email = request.form.get('email', seller.s_email)
            seller.s_phone = request.form.get('phone', seller.s_phone)
            seller.s_address = request.form.get('address', seller.s_address)
            
            # Update password if provided
            new_password = request.form.get('password', '').strip()
            if new_password:
                seller.set_password(new_password)
            
            db.session.commit()
            flash('Seller updated successfully', 'success')
            return redirect(url_for('admin_sellers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update seller: {str(e)}', 'error')
    
    return render_template('admin/edit_seller.html', seller=seller)

@app.route('/admin/sellers/<seller_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_seller(seller_id):
    """Delete a seller"""
    try:
        seller = db.session.get(Seller, seller_id)
        if not seller:
            flash('Seller not found', 'error')
            return redirect(url_for('admin_sellers'))
        
        db.session.delete(seller)
        db.session.commit()
        flash('Seller deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete seller: {str(e)}', 'error')
    
    return redirect(url_for('admin_sellers'))

@app.route('/seller/customer-analytics')
@login_required
@role_required('seller')
def customer_analytics():
    """Customer analytics: most/least invoices and purchases between dates"""
    from sqlalchemy import func, desc, asc, case, and_, or_
    
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    
    # Build base filter for paid invoices
    paid_filters = [
        Invoice.s_id == session['user_id'],
        Invoice.status == 'paid'
    ]
    
    if start_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            paid_filters.append(Invoice.invoice_datetime >= start_dt)
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_dt_inclusive = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            paid_filters.append(Invoice.invoice_datetime <= end_dt_inclusive)
        except ValueError:
            pass
    
    # Query for customers with paid invoices (for most categories)
    paid_invoices_query = db.session.query(
        Customer.c_id,
        Customer.c_name,
        Customer.c_email,
        func.count(Invoice.invoice_no).label('invoice_count'),
        func.sum(Invoice.amount).label('total_purchased')
    ).join(
        Invoice, Customer.c_id == Invoice.c_id
    ).filter(
        and_(*paid_filters)
    ).group_by(
        Customer.c_id, Customer.c_name, Customer.c_email
    )
    
    # Get customer with most paid invoices
    most_invoices = paid_invoices_query.order_by(desc('invoice_count')).first()
    
    # Get customer who purchased most (from paid invoices)
    most_purchased = paid_invoices_query.order_by(desc('total_purchased')).first()
    
    # For least categories, include all customers (even with 0 invoices)
    # Use LEFT JOIN to include customers with no invoices
    all_customers_query = db.session.query(
        Customer.c_id,
        Customer.c_name,
        Customer.c_email,
        func.count(Invoice.invoice_no).label('invoice_count'),
        func.sum(case((Invoice.status == 'paid', Invoice.amount), else_=0)).label('total_purchased')
    ).outerjoin(
        Invoice, 
        and_(
            Customer.c_id == Invoice.c_id,
            Invoice.s_id == session['user_id']
        )
    ).filter(
        Customer.s_id == session['user_id']
    )
    
    # Apply date filters to the LEFT JOIN query
    if start_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            all_customers_query = all_customers_query.filter(
                or_(Invoice.invoice_datetime >= start_dt, Invoice.invoice_no.is_(None))
            )
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_dt_inclusive = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            all_customers_query = all_customers_query.filter(
                or_(Invoice.invoice_datetime <= end_dt_inclusive, Invoice.invoice_no.is_(None))
            )
        except ValueError:
            pass
    
    all_customers_query = all_customers_query.group_by(
        Customer.c_id, Customer.c_name, Customer.c_email
    )
    
    # Get customer with least invoices (includes 0 invoices)
    least_invoices = all_customers_query.order_by(asc('invoice_count')).first()
    
    # Get customer who purchased least (includes 0 rupees for no paid invoices)
    least_purchased = all_customers_query.order_by(asc('total_purchased')).first()
    
    return render_template(
        'seller/customer_analytics.html',
        most_invoices=most_invoices,
        least_invoices=least_invoices,
        most_purchased=most_purchased,
        least_purchased=least_purchased,
        start_date=start_date_str,
        end_date=end_date_str
    )

@app.route('/seller/invoices')
@login_required
@role_required('seller')
def seller_invoices():
    # Update overdue invoices before displaying
    update_overdue_invoices()
    
    q = request.args.get('q', '').strip()
    customer_q = request.args.get('customer', '').strip()
    status = request.args.get('status', '').strip()
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    min_amount_str = request.args.get('min_amount', '').strip()
    max_amount_str = request.args.get('max_amount', '').strip()

    query = Invoice.query.filter_by(s_id=session['user_id'])

    if q:
        query = query.filter(Invoice.invoice_no.ilike(f"%{q}%"))

    if customer_q:
        query = query.join(Customer).filter(
            (Customer.c_name.ilike(f"%{customer_q}%")) | (Customer.c_email.ilike(f"%{customer_q}%"))
        )

    if status:
        query = query.filter(Invoice.status == status)

    # Date range filter (expects YYYY-MM-DD)
    try:
        if start_date_str:
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(Invoice.invoice_datetime >= start_dt)
    except ValueError:
        pass

    try:
        if end_date_str:
            # include entire end day by adding one day and using < next day
            end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_dt_inclusive = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Invoice.invoice_datetime <= end_dt_inclusive)
    except ValueError:
        pass

    # Amount range filter
    try:
        if min_amount_str:
            query = query.filter(Invoice.amount >= Decimal(min_amount_str))
    except Exception:
        pass
    try:
        if max_amount_str:
            query = query.filter(Invoice.amount <= Decimal(max_amount_str))
    except Exception:
        pass

    invoices = query.order_by(Invoice.invoice_datetime.desc()).all()
    return render_template(
        'seller/invoices.html',
        invoices=invoices,
        q=q,
        customer_q=customer_q,
        status=status,
        start_date=start_date_str,
        end_date=end_date_str,
        min_amount=min_amount_str,
        max_amount=max_amount_str,
    )

@app.route('/seller/invoices/create', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def create_invoice():
    if request.method == 'POST':
        try:
            customer_id = request.form.get('customer_id', '').strip()
            if not customer_id:
                flash('Please select a customer', 'error')
                return redirect(url_for('create_invoice'))
            
            tax = Decimal(request.form.get('tax', 10))
            due_date_str = request.form.get('due_date', '').strip()
            
            # Parse due date
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Check if this is a new customer being created
            if customer_id.startswith('temp_'):
                # Create new customer
                customer_name = request.form['temp_customer_name']
                customer_email = request.form['temp_customer_email']
                customer_phone = request.form['temp_customer_phone']
                customer_address = request.form['temp_customer_address']
                
                # Check if customer email already exists
                existing_customer = Customer.query.filter_by(c_email=customer_email).first()
                if existing_customer:
                    flash('Customer with this email already exists', 'error')
                    return redirect(url_for('create_invoice'))
                
                # Generate customer ID safely
                customer_id = generate_next_customer_id()
                
                # Create new customer
                customer = Customer(
                    c_id=customer_id,
                    c_name=customer_name,
                    c_email=customer_email,
                    c_phone_no=customer_phone,
                    c_address=customer_address,
                    password='',  # Avoid DB default issues
                    s_id=session['user_id']  # Track which seller created this customer
                )
                db.session.add(customer)
                db.session.flush()  # Get the customer ID
                
                # Log activity
                log_activity('customer_created', f'Created new customer "{customer_name}" during invoice creation')
            else:
                # Get existing customer info and verify it belongs to this seller
                customer = db.session.get(Customer, customer_id)
                if not customer:
                    flash('Customer not found', 'error')
                    return redirect(url_for('create_invoice'))
                if customer.s_id != session['user_id']:
                    flash('Access denied: This customer does not belong to you', 'error')
                    return redirect(url_for('create_invoice'))
            
            # Process items
            items = []
            subtotal = Decimal('0')
            
            item_indices = sorted(list(set([
                key.split('_')[1] for key in request.form 
                if key.startswith('product_') and key.endswith('_id')
            ])))

            for item_index in item_indices:
                product_id = request.form.get(f'product_{item_index}_id')
                quantity = int(request.form.get(f'quantity_{item_index}', 1))
                discount = Decimal(request.form.get(f'discount_{item_index}', 0))

                # If a temp product was added inline, create it now
                if product_id and product_id.startswith('temp_'):
                    temp_name = request.form.get(f'temp_product_name_{item_index}')
                    temp_price = Decimal(request.form.get(f'temp_product_price_{item_index}', 0))
                    temp_stock = int(request.form.get(f'temp_product_stock_{item_index}', 0))
                    temp_desc = request.form.get(f'temp_product_desc_{item_index}', '')

                    new_product_id = generate_next_product_id()
                    product = Product(
                        p_id=new_product_id,
                        p_name=temp_name,
                        p_price=temp_price,
                        p_description=temp_desc,
                        p_stock=temp_stock,
                        s_id=session['user_id']
                    )
                    db.session.add(product)
                    db.session.flush()
                    # Log activity for product creation
                    log_activity('product_added', f'Added new product "{temp_name}" during invoice creation')
                else:
                    product = db.session.get(Product, product_id)

                if product:
                    # Ensure sufficient stock is available
                    if product.p_stock < quantity:
                        db.session.rollback()
                        flash(f'Insufficient stock for product \"{product.p_name}\". Available: {product.p_stock}', 'error')
                        return redirect(url_for('create_invoice'))
                    item_total = (product.p_price * quantity) - discount
                    subtotal += item_total
                    items.append({
                        'product': product,
                        'quantity': quantity,
                        'discount': discount,
                        'total': item_total
                    })
                else:
                    db.session.rollback()
                    flash('Selected product not found.', 'error')
                    return redirect(url_for('create_invoice'))
            
            if not items:
                flash('Please add at least one item', 'error')
                return redirect(url_for('create_invoice'))
            
            total = subtotal + tax
            
            # Create invoice with unique ID
            # Generate unique invoice ID by checking existing ones
            existing_invoice_nos = [inv.invoice_no for inv in Invoice.query.all()]
            invoice_num = 1
            while True:
                invoice_id = f"INV-{invoice_num:03d}"
                if invoice_id not in existing_invoice_nos:
                    break
                invoice_num += 1
            
            new_invoice = Invoice(
                invoice_no=invoice_id,
                invoice_datetime=datetime.utcnow(),
                due_date=due_date,
                status='pending',
                tax=tax,
                amount=total,
                s_id=session['user_id'],
                c_id=customer_id
            )
            
            # Check if invoice is already overdue
            if due_date and due_date < date.today():
                new_invoice.status = 'overdue'
            
            db.session.add(new_invoice)
            db.session.flush()  # Get the invoice ID
            
            # Create invoice items
            for item in items:
                invoice_item = InvoiceItem(
                    invoice_no=new_invoice.invoice_no,
                    p_id=item['product'].p_id,
                    item_quantity=item['quantity'],
                    discount=item['discount']
                )
                db.session.add(invoice_item)
            
            # Adjust product stock levels immediately
            for item in items:
                product = item['product']
                if product:
                    product.p_stock = product.p_stock - item['quantity']
            
            db.session.commit()
            
            # Log activity
            log_activity('invoice_created', f'Created invoice {invoice_id} for {customer.c_name}')
            
            flash(f'Invoice {invoice_id} created successfully!', 'success')
            return redirect(url_for('view_invoice', invoice_id=invoice_id))
            
        except Exception:
            db.session.rollback()
            flash('Failed to create invoice', 'error')
    
    products = Product.query.filter_by(s_id=session['user_id']).all()
    # Show only customers created by this seller
    customers = Customer.query.filter_by(s_id=session['user_id']).order_by(Customer.c_name.asc()).all()
    # Convert products to dictionaries for JSON serialization
    products_data = [product.to_dict() for product in products]
    return render_template('seller/create_invoice.html', products=products_data, customers=customers)


@app.route('/seller/invoices/upload_bill', methods=['POST'])
@login_required
@role_required('seller')
def upload_bill():
    if 'bill_file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('seller_invoices'))
        
    file = request.files['bill_file']
    if not file or file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('seller_invoices'))
        
    filename = file.filename.lower()
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.pdf'}
    ext = os.path.splitext(filename)[1]
    if ext not in allowed_extensions:
        flash('Invalid file type. Only PDF and images (PNG, JPG) are allowed.', 'error')
        return redirect(url_for('seller_invoices'))
        
    file_bytes = file.read()
    if not file_bytes:
        flash('Uploaded file is empty', 'error')
        return redirect(url_for('seller_invoices'))
        
    mime_type = 'application/pdf' if ext == '.pdf' else f'image/{ext.lstrip(".")}'
    if mime_type == 'image/jpg':
        mime_type = 'image/jpeg'
        
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not gemini_key:
        flash('Gemini API key is not configured. Please add GEMINI_API_KEY to your environment.', 'error')
        return redirect(url_for('seller_invoices'))
        
    try:
        from google import genai
        from google.genai import types
        import json
        from pydantic import BaseModel, Field
        from typing import List, Optional
        
        class BillItem(BaseModel):
            product_name: str = Field(description="Name of the item/product")
            quantity: int = Field(description="Quantity of the item")
            price: float = Field(description="Unit price of the item")
            discount: float = Field(default=0.0, description="Discount amount for this item")

        class BillData(BaseModel):
            vendor_name: str = Field(description="Name of the vendor or merchant or shop")
            invoice_no: Optional[str] = Field(None, description="Invoice or bill number if present")
            billing_date: Optional[str] = Field(None, description="Billing date in YYYY-MM-DD format")
            due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format")
            subtotal: float = Field(description="Subtotal amount before tax and discount")
            tax: float = Field(description="Tax amount")
            total_amount: float = Field(description="Total amount including tax")
            items: List[BillItem] = Field(default=[], description="List of items on the bill")
            is_paid: bool = Field(default=False, description="True if the bill is marked as Paid, Cash, Receipt or has zero balance due")

        client = genai.Client(api_key=gemini_key)
        
        print("Calling Gemini 2.5 Flash to digitalize bill...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(
                    data=file_bytes,
                    mime_type=mime_type
                ),
                "Extract all details from this receipt or bill. If any value is missing or hard to read, estimate it reasonably based on other fields."
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=BillData,
                temperature=0.1
            )
        )
        
        bill_info = json.loads(response.text)
        print(f"Gemini response: {bill_info}")
        
        vendor_name = bill_info.get('vendor_name', 'Unknown Vendor').strip()
        subtotal = Decimal(str(bill_info.get('subtotal', 0.0)))
        tax = Decimal(str(bill_info.get('tax', 0.0)))
        total_amount = Decimal(str(bill_info.get('total_amount', 0.0)))
        extracted_invoice_no = bill_info.get('invoice_no')
        
        s_id = session['user_id']
        customer = Customer.query.filter_by(s_id=s_id, c_name=vendor_name).first()
        if not customer:
            customer = Customer.query.filter(Customer.s_id == s_id, Customer.c_name.like(f"%{vendor_name}%")).first()
            
        if not customer:
            c_id = generate_next_customer_id()
            customer = Customer(
                c_id=c_id,
                c_name=vendor_name,
                c_email=f"{vendor_name.lower().replace(' ', '_')}@example.com",
                c_phone_no="0000000000",
                c_address="Extracted from digitized bill",
                password='',
                s_id=s_id
            )
            db.session.add(customer)
            db.session.flush()
            log_activity('customer_created', f'Created customer/vendor "{vendor_name}" automatically from digitized bill')
        else:
            c_id = customer.c_id
            
        existing_invoice_nos = {inv.invoice_no for inv in Invoice.query.all()}
        if extracted_invoice_no and extracted_invoice_no.strip() and extracted_invoice_no.strip() not in existing_invoice_nos:
            invoice_no = extracted_invoice_no.strip()
        else:
            invoice_num = 1
            while True:
                invoice_no = f"INV-{invoice_num:03d}"
                if invoice_no not in existing_invoice_nos:
                    break
                invoice_num += 1
                
        billing_date_str = bill_info.get('billing_date')
        invoice_datetime = datetime.utcnow()
        if billing_date_str:
            try:
                invoice_datetime = datetime.strptime(billing_date_str, '%Y-%m-%d')
            except ValueError:
                pass
                
        due_date_str = bill_info.get('due_date')
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if not due_date:
            due_date = (invoice_datetime + timedelta(days=30)).date()
            
        status = 'paid' if bill_info.get('is_paid') else 'pending'
        if status == 'pending' and due_date < date.today():
            status = 'overdue'
            
        new_invoice = Invoice(
            invoice_no=invoice_no,
            invoice_datetime=invoice_datetime,
            due_date=due_date,
            status=status,
            tax=tax,
            amount=total_amount,
            s_id=s_id,
            c_id=c_id
        )
        db.session.add(new_invoice)
        db.session.flush()
        
        items_list = bill_info.get('items', [])
        for item in items_list:
            item_name = item.get('product_name', 'Unnamed Item').strip()
            item_qty = int(item.get('quantity', 1))
            item_price = Decimal(str(item.get('price', 0.0)))
            item_discount = Decimal(str(item.get('discount', 0.0)))
            
            product = Product.query.filter_by(s_id=s_id, p_name=item_name).first()
            if not product:
                product = Product.query.filter(Product.s_id == s_id, Product.p_name.like(f"%{item_name}%")).first()
                
            if not product:
                p_id = generate_next_product_id()
                product = Product(
                    p_id=p_id,
                    p_name=item_name,
                    p_price=item_price,
                    p_description="Digitized product from bill",
                    p_stock=item_qty + 10,
                    s_id=s_id
                )
                db.session.add(product)
                db.session.flush()
                log_activity('product_added', f'Added product "{item_name}" automatically from digitized bill')
            else:
                if product.p_stock < item_qty:
                    product.p_stock = item_qty + 10
                    
            invoice_item = InvoiceItem(
                invoice_no=invoice_no,
                p_id=product.p_id,
                item_quantity=item_qty,
                discount=item_discount
            )
            db.session.add(invoice_item)
            product.p_stock = product.p_stock - item_qty
            
        db.session.commit()
        log_activity('invoice_created', f'Digitized bill and created invoice {invoice_no} for vendor "{vendor_name}"')
        
        flash(f'Successfully digitized bill! Created invoice {invoice_no} for vendor "{vendor_name}".', 'success')
        return redirect(url_for('view_invoice', invoice_id=invoice_no))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error digitalizing bill: {e}")
        flash(f"Error digitalizing bill: {str(e)}", 'error')
        return redirect(url_for('seller_invoices'))


@app.route('/seller/invoices/edit/<invoice_id>', methods=['GET', 'POST'])
@login_required
@role_required('seller')
def edit_invoice(invoice_id):
    invoice = Invoice.query.filter_by(invoice_no=invoice_id, s_id=session['user_id']).first()
    
    if not invoice:
        flash('Invoice not found', 'error')
        return redirect(url_for('seller_invoices'))
    
    # Check if invoice is cancelled - make it uneditable
    if invoice.status == 'cancelled':
        flash('Cannot edit a cancelled invoice', 'error')
        return redirect(url_for('seller_invoices'))
    
    if request.method == 'POST':
        try:
            # Update invoice status
            new_status = request.form.get('status', invoice.status)
            old_status = invoice.status
            
            # Handle cancellation - restore stock
            if new_status == 'cancelled' and old_status != 'cancelled':
                restore_stock_on_cancellation(invoice)
            
            invoice.status = new_status
            
            # Update tax
            tax_value = request.form.get('tax', '').strip()
            if tax_value:
                try:
                    invoice.tax = Decimal(tax_value)
                except (ValueError, decimal.InvalidOperation):
                    invoice.tax = Decimal('0')
            else:
                invoice.tax = Decimal('0')
            
            # Update due date
            due_date_str = request.form.get('due_date', '').strip()
            if due_date_str:
                try:
                    invoice.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Check if invoice should be overdue
            if invoice.due_date and invoice.due_date < date.today() and new_status in ['pending', 'overdue']:
                invoice.status = 'overdue'
                new_status = 'overdue'
            
            # Handle item updates, additions, and deletions
            existing_item_ids = set()
            subtotal = Decimal('0')
            
            # Process existing items
            for item in invoice.items:
                item_id = item.item_id
                existing_item_ids.add(item_id)
                
                # Check if item should be deleted
                delete_key = f'delete_{item_id}'
                if delete_key in request.form:
                    product = item.product
                    if product:
                        product.p_stock = product.p_stock + item.item_quantity
                    db.session.delete(item)
                    continue
                
                # Update quantity
                quantity_key = f'quantity_{item_id}'
                if quantity_key in request.form:
                    new_quantity = int(request.form[quantity_key])
                    product = item.product
                    if product:
                        stock_diff = item.item_quantity - new_quantity
                        if stock_diff < 0 and product.p_stock < abs(stock_diff):
                            db.session.rollback()
                            flash(f'Insufficient stock for product \"{product.p_name}\" while updating invoice.', 'error')
                            return redirect(url_for('edit_invoice', invoice_id=invoice_id))
                        product.p_stock = product.p_stock + stock_diff
                    item.item_quantity = new_quantity
                
                # Update discount
                discount_key = f'discount_{item_id}'
                if discount_key in request.form:
                    discount_value = request.form[discount_key].strip()
                    try:
                        item.discount = Decimal(discount_value) if discount_value else Decimal('0')
                    except (ValueError, decimal.InvalidOperation):
                        item.discount = Decimal('0')
                
                # Update price (if product changed)
                product_key = f'product_{item_id}'
                if product_key in request.form:
                    new_product_id = request.form[product_key]
                    if new_product_id and new_product_id != item.p_id:
                        old_product = item.product
                        if old_product:
                            old_product.p_stock = old_product.p_stock + item.item_quantity
                        new_product = db.session.get(Product, new_product_id)
                        if not new_product:
                            db.session.rollback()
                            flash('Selected product not found.', 'error')
                            return redirect(url_for('edit_invoice', invoice_id=invoice_id))
                        if new_product.p_stock < item.item_quantity:
                            db.session.rollback()
                            flash(f'Insufficient stock for product \"{new_product.p_name}\".', 'error')
                            return redirect(url_for('edit_invoice', invoice_id=invoice_id))
                        new_product.p_stock = new_product.p_stock - item.item_quantity
                        item.p_id = new_product_id
                        item.product = new_product
                
                subtotal += (item.product.p_price * item.item_quantity) - item.discount
            
            # Add new items
            new_item_indices = sorted(list(set([key.split('_')[1] for key in request.form if key.startswith('new_product_') and key.endswith('_id')])))
            
            for item_index in new_item_indices:
                product_id = request.form.get(f'new_product_{item_index}_id')
                if product_id:
                    quantity = int(request.form.get(f'new_quantity_{item_index}', 1))
                    discount_value = request.form.get(f'new_discount_{item_index}', '0').strip()
                    try:
                        discount = Decimal(discount_value) if discount_value else Decimal('0')
                    except (ValueError, decimal.InvalidOperation):
                        discount = Decimal('0')
                    
                    product = db.session.get(Product, product_id)
                    if product:
                        if product.p_stock < quantity:
                            db.session.rollback()
                            flash(f'Insufficient stock for product \"{product.p_name}\".', 'error')
                            return redirect(url_for('edit_invoice', invoice_id=invoice_id))
                        new_item = InvoiceItem(
                            invoice_no=invoice.invoice_no,
                            p_id=product_id,
                            item_quantity=quantity,
                            discount=discount
                        )
                        db.session.add(new_item)
                        product.p_stock = product.p_stock - quantity
                        subtotal += (product.p_price * quantity) - discount
                    else:
                        db.session.rollback()
                        flash('Selected product not found.', 'error')
                        return redirect(url_for('edit_invoice', invoice_id=invoice_id))
            
            # Recalculate total
            invoice.amount = subtotal + invoice.tax
            
            db.session.commit()
            
            # Log activity
            log_activity('invoice_updated', f'Updated invoice {invoice_id} - Status: {new_status}')
            
            flash('Invoice updated successfully!', 'success')
            return redirect(url_for('seller_invoices'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update invoice: {str(e)}', 'error')
    
    products = Product.query.filter_by(s_id=session['user_id']).all()
    # Show only customers created by this seller (for reference, but invoice customer is already set)
    customers = Customer.query.filter_by(s_id=session['user_id']).all()
    products_data = [product.to_dict() for product in products]
    
    return render_template('seller/edit_invoice.html', invoice=invoice, products=products_data, customers=customers)


@app.route('/invoice/<invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    
    if not invoice:
        flash('Invoice not found', 'error')
        if session.get('user_role') == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('seller_dashboard'))
    
    # Check permission based on role
    role = session.get('user_role')
    if role == 'seller' and invoice.s_id != session['user_id']:
        flash('Access denied', 'error')
        return redirect(url_for('seller_dashboard'))
    elif role == 'customer' and invoice.c_id != session['user_id']:
        flash('Access denied', 'error')
        return redirect(url_for('customer_dashboard'))
    elif role not in ['seller', 'customer', 'admin']:
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    return render_template('invoice/view.html', invoice=invoice)

@app.route('/seller/invoices/delete/<invoice_id>')
@login_required
@role_required('seller')
def delete_invoice(invoice_id):
    try:
        # Verify invoice belongs to this seller
        invoice = Invoice.query.filter_by(invoice_no=invoice_id, s_id=session['user_id']).first()
        if not invoice:
            flash('Invoice not found or access denied', 'error')
            return redirect(url_for('seller_invoices'))
        
        # Only allow deletion of cancelled invoices
        if invoice.status != 'cancelled':
            flash('Only cancelled invoices can be deleted', 'error')
            return redirect(url_for('seller_invoices'))
        
        # Log activity before deletion
        log_activity('invoice_deleted', f'Deleted cancelled invoice {invoice_id} for {invoice.customer.c_name}')
        
        # Delete invoice (invoice_items will be cascade deleted due to relationship)
        db.session.delete(invoice)
        db.session.commit()
        flash('Invoice deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete invoice: {str(e)}', 'error')
    
    return redirect(url_for('seller_invoices'))



@app.route('/api/ai/process', methods=['POST'])
@login_required
def process_ai_command():
    try:
        # Validate session first
        if 'user_id' not in session or 'user_role' not in session:
            return jsonify({'error': 'Session expired. Please log in again.', 'success': False}), 401
        
        if session.get('user_role') != 'seller':
            return jsonify({'error': 'Access denied. This feature is only available for sellers.', 'success': False}), 403
        
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid request data', 'success': False}), 400
        
        user_text = data.get('text', '').strip()
        history = data.get('history', [])
        language = data.get('language', 'en-IN')
        
        if not user_text:
            return jsonify({'error': 'No text provided', 'success': False}), 400
        
        # Get context (products and customers) - only for current seller
        products = Product.query.filter_by(s_id=session['user_id']).all()
        customers = Customer.query.filter_by(s_id=session['user_id']).all()
        
        # Aggregate Business Stats
        stats = {
            'revenue': 0.0,
            'invoices_count': 0,
            'customers_count': 0,
            'products_count': len(products),
            'low_stock': [],
            'top_selling': [],
            'recent_invoices': []
        }
        try:
            revenue_val = db.session.query(db.func.sum(Invoice.amount)).filter(Invoice.s_id == session['user_id']).scalar() or 0.0
            stats['revenue'] = float(revenue_val)
            stats['invoices_count'] = Invoice.query.filter_by(s_id=session['user_id']).count()
            stats['customers_count'] = Customer.query.filter_by(s_id=session['user_id']).count()
            
            low_stock_products = Product.query.filter(Product.s_id == session['user_id'], Product.p_stock < 10).all()
            stats['low_stock'] = [{'name': p.p_name, 'stock': p.p_stock} for p in low_stock_products]
            
            top_selling = db.session.query(
                Product.p_name,
                db.func.sum(InvoiceItem.item_quantity).label('qty')
            ).join(
                InvoiceItem, Product.p_id == InvoiceItem.p_id
            ).join(
                Invoice, InvoiceItem.invoice_no == Invoice.invoice_no
            ).filter(
                Invoice.s_id == session['user_id']
            ).group_by(
                Product.p_name
            ).order_by(
                db.text('qty DESC')
            ).limit(3).all()
            stats['top_selling'] = [{'name': name, 'quantity': int(qty)} for name, qty in top_selling]
            
            recent_invoices = Invoice.query.filter_by(s_id=session['user_id']).order_by(Invoice.invoice_datetime.desc()).limit(3).all()
            stats['recent_invoices'] = [{
                'invoice_no': inv.invoice_no,
                'customer_name': inv.customer.c_name if inv.customer else 'Unknown',
                'amount': float(inv.amount),
                'status': inv.status
            } for inv in recent_invoices]
        except Exception as e:
            print(f"Error compiling business stats context: {e}")
            
        # Get all invoices for this seller to allow AI to query the database
        invoices = Invoice.query.filter_by(s_id=session['user_id']).all()
        invoices_data = []
        for inv in invoices:
            invoices_data.append({
                'invoice_no': inv.invoice_no,
                'customer_name': inv.customer.c_name if inv.customer else 'Unknown',
                'amount': float(inv.amount),
                'status': inv.status,
                'date': inv.invoice_datetime.strftime('%Y-%m-%d') if inv.invoice_datetime else 'N/A',
                'due_date': inv.due_date.strftime('%Y-%m-%d') if inv.due_date else 'N/A',
                'items': [{'name': item.product.p_name if item.product else 'Unknown', 'quantity': item.item_quantity} for item in inv.items]
            })

        context = {
            'products': [p.to_dict() for p in products],
            'customers': [c.to_dict() for c in customers],
            'invoices': invoices_data,
            'stats': stats
        }
        
        result = ai_service.parse_command(user_text, context, history, language=language)
        
        # Inject live statistics context if the user requested business insights
        if result.get('intent') == 'business_insights':
            result['data'] = stats
            result['success'] = True
        
        # Handle add_product intent - actually add to database
        if result.get('intent') == 'add_product':
            product_data = result.get('data', {})
            print(f"DEBUG: Product data from AI: {product_data}")  # Debug logging
            try:
                # Validate required fields
                product_name = product_data.get('name')
                print(f"DEBUG: Product name extracted: {product_name}, type: {type(product_name)}")  # Debug logging
                # Handle None or empty string
                if not product_name or (isinstance(product_name, str) and product_name.strip() == ''):
                    result['response_text'] = "❌ Product name is required. Please specify a product name. For example: 'Add product Milk price 50'"
                    result['success'] = False
                else:
                    # Verify seller exists using query (more reliable than db.session.get)
                    seller = Seller.query.filter_by(s_id=session['user_id']).first()
                    if not seller:
                        result['response_text'] = f"❌ Seller with ID '{session['user_id']}' not found. Please log in again."
                        result['success'] = False
                    else:
                        # Generate product ID
                        new_product_id = generate_next_product_id()
                        
                        # Get and validate price
                        price = product_data.get('price', 0)
                        try:
                            price_decimal = Decimal(str(price)) if price else Decimal('0')
                        except (ValueError, TypeError):
                            price_decimal = Decimal('0')
                        
                        # Get and validate stock
                        stock = product_data.get('stock', 0)
                        try:
                            stock_int = int(stock) if stock else 0
                        except (ValueError, TypeError):
                            stock_int = 0
                        
                        # Create product - ensure product_name is a valid string
                        product_name_str = product_name.strip() if isinstance(product_name, str) else (str(product_name) if product_name else '')
                        if not product_name_str:
                            result['response_text'] = "❌ Product name is required. Please specify a product name. For example: 'Add product Milk price 50'"
                            result['success'] = False
                        else:
                            description = product_data.get('description', '')
                            description_str = description.strip() if description and isinstance(description, str) else ''
                            
                            new_product = Product(
                                p_id=new_product_id,
                                p_name=product_name_str,
                                p_price=price_decimal,
                                p_description=description_str,
                                p_stock=stock_int,
                                s_id=session['user_id']
                            )
                            db.session.add(new_product)
                            db.session.commit()
                            
                            # Log activity
                            log_activity('product_added', f'Added product "{product_name_str}" via AI assistant')
                            
                            # Update response
                            result['response_text'] = f"✅ Product '{product_name_str}' has been added successfully! You can view it in the Products tab."
                            result['success'] = True
                            result['product_id'] = new_product_id
                
            except Exception as e:
                db.session.rollback()
                error_msg = str(e)
                # Provide more user-friendly error messages
                if 'foreign key constraint' in error_msg.lower():
                    result['response_text'] = f"❌ Failed to add product: Seller account issue. Please try logging in again."
                elif "'NoneType' object has no attribute" in error_msg:
                    result['response_text'] = f"❌ Failed to add product: Missing product information. Please provide product name, price, and other details. Example: 'Add product Milk price 50 stock 100'"
                else:
                    result['response_text'] = f"❌ Failed to add product: {error_msg}"
                result['success'] = False
                print(f"Product addition error: {e}")  # Debug logging
                import traceback
                traceback.print_exc()  # Print full traceback for debugging
        
        # Handle add_customer intent - actually add to database
        elif result.get('intent') == 'add_customer':
            customer_data = result.get('data', {})
            try:
                # Validate session
                if 'user_id' not in session:
                    result['response_text'] = "❌ Session expired. Please log in again."
                    result['success'] = False
                    return jsonify(result)
                
                # Validate required fields - safely handle None values
                name_raw = customer_data.get('name')
                email_raw = customer_data.get('email')
                
                customer_name = (name_raw or '').strip() if name_raw else ''
                customer_email = (email_raw or '').strip() if email_raw else ''
                
                if not customer_name:
                    result['response_text'] = "❌ Customer name is required. Please specify a customer name. Example: 'Add customer John Doe email john@example.com'"
                    result['success'] = False
                elif not customer_email:
                    result['response_text'] = "❌ Customer email is required. Please specify an email address. Example: 'Add customer John Doe email john@example.com'"
                    result['success'] = False
                else:
                    # Check if customer email already exists
                    existing = Customer.query.filter_by(c_email=customer_email).first()
                    if existing:
                        result['response_text'] = f"❌ Customer with email '{customer_email}' already exists!"
                        result['success'] = False
                    else:
                        # Verify seller exists
                        seller = Seller.query.filter_by(s_id=session['user_id']).first()
                        if not seller:
                            result['response_text'] = f"❌ Seller account not found. Please log in again."
                            result['success'] = False
                        else:
                            # Generate customer ID safely
                            customer_id = generate_next_customer_id()
                            
                            # Safely handle optional fields (phone and address)
                            phone_raw = customer_data.get('phone')
                            address_raw = customer_data.get('address')
                            
                            phone_value = (phone_raw or '').strip() if phone_raw else ''
                            address_value = (address_raw or '').strip() if address_raw else ''
                            
                            # Create customer with all required fields
                            new_customer = Customer(
                                c_id=customer_id,
                                c_name=customer_name,
                                c_email=customer_email,
                                c_phone_no=phone_value,
                                c_address=address_value,
                                password='',
                                s_id=session['user_id']  # Always set s_id
                            )
                            db.session.add(new_customer)
                            db.session.commit()
                            
                            # Log activity
                            log_activity('customer_created', f'Added customer "{customer_name}" via AI assistant')
                            
                            # Update response
                            result['response_text'] = f"✅ Customer '{customer_name}' has been added successfully! You can view them in the Customers tab."
                            result['success'] = True
                            result['customer_id'] = customer_id
                    
            except Exception as e:
                db.session.rollback()
                error_msg = str(e)
                if 'foreign key constraint' in error_msg.lower():
                    result['response_text'] = "❌ Failed to add customer: Seller account issue. Please try logging in again."
                elif 'unique constraint' in error_msg.lower() or 'duplicate' in error_msg.lower():
                    result['response_text'] = f"❌ Failed to add customer: Email already exists."
                else:
                    result['response_text'] = f"❌ Failed to add customer: {error_msg}"
                result['success'] = False
                print(f"Customer addition error: {e}")
                import traceback
                traceback.print_exc()
        
        return jsonify(result)
    except Exception as e:
        print(f"AI Processing Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500

@app.errorhandler(500)
def handle_internal_error(error):
    flash('An unexpected error occurred. Please try again later.', 'error')
    return redirect(url_for('seller_dashboard'))


def auto_seed():
    """Auto-seed demo data. Checks by specific demo email so it re-seeds if missing."""
    try:
        # Check specifically if our demo seller exists
        demo_seller = Seller.query.filter_by(s_email='demo@invoiceai.com').first()
        if demo_seller:
            print("Demo data already exists, skipping auto-seed.")
            return

        from decimal import Decimal
        from datetime import datetime, date, timedelta

        print("Seeding rich demo data...")

        # ── Seller ──────────────────────────────────────────────
        seller = Seller(
            s_id="DEMO01",
            s_name="TechVault Pvt Ltd",
            s_email="demo@invoiceai.com",
            s_address="42 Sector 18, Cyber City, Gurgaon, Haryana 122002",
            s_phone="9876543210"
        )
        seller.set_password("demo123")
        db.session.add(seller)
        db.session.commit()
        print("  ✓ Seller created: demo@invoiceai.com / demo123")

        # ── Products ─────────────────────────────────────────────
        products_data = [
            ("DP001", "Wireless Mouse Pro",       1299.00, "Ergonomic 2.4GHz wireless mouse with 7 buttons and DPI switcher.", 60),
            ("DP002", "Mechanical Keyboard RGB",  3499.00, "TKL mechanical keyboard with Cherry MX switches and per-key RGB.", 20),
            ("DP003", "4K Monitor 27\"",          24999.00, "27-inch 4K UHD IPS panel, 144Hz, HDR400, USB-C.",                 8),
            ("DP004", "USB-C Docking Station",    5999.00, "12-in-1 USB-C hub with dual HDMI, Ethernet, SD card reader.",     15),
            ("DP005", "Noise Cancelling Headphones", 8999.00, "Over-ear ANC headphones, 30h battery, Bluetooth 5.2.",          30),
            ("DP006", "Webcam 1080p HD",          2199.00, "Full HD webcam with built-in ring light and privacy cover.",      45),
            ("DP007", "Laptop Stand Aluminium",    999.00, "Adjustable 6-angle aluminium laptop riser, foldable.",            50),
            ("DP008", "External SSD 1TB",         6499.00, "Portable NVMe SSD, 1050MB/s read, USB 3.2 Gen2.",                25),
        ]
        for p_id, name, price, desc, stock in products_data:
            db.session.add(Product(p_id=p_id, p_name=name, p_price=Decimal(str(price)),
                                   p_description=desc, p_stock=stock, s_id="DEMO01"))
        db.session.commit()
        print("  ✓ 8 products created")

        # ── Customers ─────────────────────────────────────────────
        customers_data = [
            ("DC001", "Arjun Mehta",     "arjun.mehta@gmail.com",    "9911223344", "New Delhi"),
            ("DC002", "Priya Sharma",    "priya.sharma@hotmail.com", "9922334455", "Mumbai"),
            ("DC003", "Rahul Gupta",     "rahul.gupta@yahoo.com",    "9933445566", "Bangalore"),
            ("DC004", "Sneha Reddy",     "sneha.reddy@outlook.com",  "9944556677", "Hyderabad"),
            ("DC005", "Vikram Singh",    "vikram.singh@gmail.com",   "9955667788", "Pune"),
            ("DC006", "Anjali Patel",    "anjali.patel@gmail.com",   "9966778899", "Ahmedabad"),
            ("DC007", "Karan Joshi",     "karan.joshi@gmail.com",    "9977889900", "Kolkata"),
            ("DC008", "Demo Customer",   "customer@example.com",     "9999999999", "Chennai"),
        ]
        for c_id, name, email, phone, addr in customers_data:
            c = Customer(c_id=c_id, c_name=name, c_email=email, c_phone_no=phone,
                         c_address=addr, s_id="DEMO01")
            c.set_password("pass123")
            db.session.add(c)
        db.session.commit()
        print("  ✓ 8 customers created")

        # ── Invoices with Items ────────────────────────────────────
        today = date.today()

        def make_invoice(inv_no, cust_id, status, days_ago, items_list, tax_pct=18):
            inv_date = datetime.utcnow() - timedelta(days=days_ago)
            if status == 'overdue':
                due = today - timedelta(days=days_ago - 30) if days_ago > 30 else today - timedelta(days=5)
            elif status == 'pending':
                due = today + timedelta(days=30 - days_ago) if days_ago < 30 else today + timedelta(days=5)
            else:
                due = today - timedelta(days=days_ago - 15)
            subtotal = sum(Decimal(str(price)) * qty - Decimal(str(disc)) for price, qty, disc in items_list)
            tax_amt  = (subtotal * Decimal(str(tax_pct))) / Decimal('100')
            total    = subtotal + tax_amt
            inv = Invoice(invoice_no=inv_no, invoice_datetime=inv_date, due_date=due,
                          status=status, tax=tax_amt.quantize(Decimal('0.01')),
                          amount=total.quantize(Decimal('0.01')), s_id="DEMO01", c_id=cust_id)
            db.session.add(inv)
            db.session.flush()
            for price, qty, disc in items_list:
                # find matching product
                prod = Product.query.filter_by(p_price=Decimal(str(price)), s_id="DEMO01").first()
                if prod:
                    db.session.add(InvoiceItem(invoice_no=inv_no, p_id=prod.p_id,
                                               item_quantity=qty, discount=Decimal(str(disc))))

        # Paid invoices (revenue already collected)
        make_invoice("INV-2024-001", "DC001", "paid",    90, [(1299, 2, 0),   (999, 1, 0)])
        make_invoice("INV-2024-002", "DC002", "paid",    85, [(3499, 1, 200), (2199, 1, 0)])
        make_invoice("INV-2024-003", "DC003", "paid",    80, [(24999, 1, 0)])
        make_invoice("INV-2024-004", "DC004", "paid",    75, [(1299, 3, 150), (5999, 1, 0)])
        make_invoice("INV-2024-005", "DC005", "paid",    70, [(6499, 2, 500)])
        make_invoice("INV-2024-006", "DC001", "paid",    65, [(8999, 1, 0),   (999, 2, 0)])
        make_invoice("INV-2024-007", "DC006", "paid",    10, [(3499, 2, 0),   (2199, 1, 0)])  # 10 days ago (this month)
        make_invoice("INV-2024-008", "DC002", "paid",    55, [(5999, 1, 0),   (1299, 2, 0)])
        make_invoice("INV-2024-009", "DC007", "paid",    45, [(24999, 1, 2000)])
        make_invoice("INV-2024-010", "DC003", "paid",    25, [(6499, 1, 0),   (999, 3, 0)])   # 25 days ago (this month)
        make_invoice("INV-2024-011", "DC004", "paid",    15, [(8999, 1, 500), (2199, 2, 0)])  # 15 days ago (this month)
        make_invoice("INV-2024-012", "DC005", "paid",    5, [(3499, 1, 0),   (1299, 1, 0)])   # 5 days ago (this month)

        # Pending invoices (awaiting payment)
        make_invoice("INV-2025-001", "DC001", "pending", 20, [(5999, 1, 0),   (999, 2, 0)])
        make_invoice("INV-2025-002", "DC006", "pending", 15, [(24999, 1, 0)])
        make_invoice("INV-2025-003", "DC007", "pending", 10, [(3499, 2, 300)])
        make_invoice("INV-2025-004", "DC008", "pending",  5, [(8999, 1, 0),   (1299, 3, 0)])
        make_invoice("INV-2025-005", "DC002", "pending",  3, [(6499, 1, 0)])

        # Overdue invoices
        make_invoice("INV-OD-001", "DC003", "overdue", 50, [(24999, 1, 0)])
        make_invoice("INV-OD-002", "DC004", "overdue", 45, [(8999, 1, 0), (5999, 1, 0)])
        make_invoice("INV-OD-003", "DC005", "overdue", 38, [(3499, 2, 0)])

        db.session.commit()
        print("  ✓ 20 invoices created (12 paid, 5 pending, 3 overdue)")

        # ── Activities ───────────────────────────────────────────
        activities = [
            ("invoice_created",  'Created invoice INV-2025-004 for Demo Customer'),
            ("invoice_created",  'Created invoice INV-2025-003 for Karan Joshi'),
            ("customer_created", 'Added new customer "Demo Customer"'),
            ("product_added",    'Added product "External SSD 1TB"'),
            ("invoice_paid",     'Invoice INV-2024-012 marked as paid'),
            ("invoice_paid",     'Invoice INV-2024-011 marked as paid'),
        ]
        for act_type, desc in activities:
            db.session.add(Activity(user_id="DEMO01", user_role="seller",
                                    action_type=act_type, description=desc))
        db.session.commit()

        print("Auto-seed complete! 🎉")
        print("  Login → demo@invoiceai.com / demo123")
        print("  Customer login → customer@example.com / pass123")
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        print(f"Auto-seed failed: {e}")


# Create database tables on startup (runs with both gunicorn and python app.py)
with app.app_context():
    migrate_database()
    db.create_all()
    auto_seed()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)


