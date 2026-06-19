from extensions import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, Date, ForeignKey

class Activity(db.Model):
    """Activity log for tracking changes"""
    __tablename__ = 'activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50))
    user_role = db.Column(db.String(20))
    action_type = db.Column(db.String(50))
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id=None, user_role=None, action_type=None, description=None, timestamp=None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.user_role = user_role
        self.action_type = action_type
        self.description = description
        if timestamp is not None:
            self.timestamp = timestamp

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_role': self.user_role,
            'action_type': self.action_type,
            'description': self.description,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
            'time_ago': self.get_time_ago()
        }
    
    def get_time_ago(self):
        """Get human-readable time ago string"""
        if not self.timestamp:
            return ""
        now = datetime.utcnow()
        diff = now - self.timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"

class Seller(db.Model):
    """SELLER (Admin) entity"""
    __tablename__ = 'sellers'
    s_id = db.Column(db.String(50), primary_key=True)
    s_name = db.Column(db.String(100))
    s_email = db.Column(db.String(100), unique=True)
    s_address = db.Column(db.Text)
    s_phone = db.Column(db.String(20))
    password = db.Column(db.String(255))
    s_logo = db.Column(db.String(255), nullable=True)
    s_theme = db.Column(db.String(20), default='system', nullable=True)
    
    def __init__(self, s_id=None, s_name=None, s_email=None, s_address=None, s_phone=None, password=None, s_logo=None, s_theme='system', **kwargs):
        super().__init__(**kwargs)
        self.s_id = s_id
        self.s_name = s_name
        self.s_email = s_email
        self.s_address = s_address
        self.s_phone = s_phone
        self.s_logo = s_logo
        self.s_theme = s_theme
        if password is not None:
            self.password = password
    
    def set_password(self, password):
        """Set password as plain text"""
        self.password = password
    
    def check_password(self, password):
        """Check password (plain text comparison)"""
        return self.password == password
    
    def to_dict(self):
        return {
            'id': self.s_id,
            'name': self.s_name,
            'email': self.s_email,
            'phone': self.s_phone,
            'address': self.s_address,
            'logo': self.s_logo,
            'theme': self.s_theme,
            'role': 'seller'
        }

class Customer(db.Model):
    """CUSTOMER entity"""
    __tablename__ = 'customer'
    c_id = db.Column(db.String(50), primary_key=True)
    c_name = db.Column(db.String(100))
    c_email = db.Column(db.String(100))
    c_phone_no = db.Column(db.String(20))
    c_address = db.Column(db.Text)
    password = db.Column(db.String(255))
    s_id = db.Column(db.String(50), db.ForeignKey('sellers.s_id'))

    def __init__(self, c_id=None, c_name=None, c_email=None, c_phone_no=None, c_address=None, password=None, s_id=None, **kwargs):
        super().__init__(**kwargs)
        self.c_id = c_id
        self.c_name = c_name
        self.c_email = c_email
        self.c_phone_no = c_phone_no
        self.password = password
        self.s_id = s_id
    
    def set_password(self, password):
        """Set password as plain text"""
        self.password = password
    
    def check_password(self, password):
        """Check password (plain text comparison)"""
        return self.password == password
    
    # Properties for template compatibility
    @property
    def id(self): return self.c_id
    @property
    def name(self): return self.c_name
    @property
    def email(self): return self.c_email
    @property
    def phone(self): return self.c_phone_no
    @property
    def address(self): return self.c_address
    
    def to_dict(self):
        return {
            'id': self.c_id,
            'name': self.c_name,
            'email': self.c_email,
            'phone': self.c_phone_no,
            'address': self.c_address,
            'role': 'customer'
        }

class Product(db.Model):
    """PRODUCT entity"""
    __tablename__ = 'product'
    p_id = db.Column(db.String(50), primary_key=True)
    p_name = db.Column(db.String(100))
    p_price = db.Column(db.Numeric(10, 2))
    p_description = db.Column(db.Text)
    p_stock = db.Column(db.Integer, default=0)
    s_id = db.Column(db.String(50), db.ForeignKey('sellers.s_id'))

    def __init__(self, p_id=None, p_name=None, p_price=None, p_description=None, p_stock=0, s_id=None, **kwargs):
        super().__init__(**kwargs)
        self.p_id = p_id
        self.p_name = p_name
        self.p_price = p_price
        self.p_description = p_description
        self.p_stock = p_stock
        self.s_id = s_id
    
    # Properties for template compatibility
    @property
    def id(self): return self.p_id
    @property
    def name(self): return self.p_name
    @property
    def price(self): return self.p_price
    @property
    def description(self): return self.p_description
    @property
    def stock(self): return self.p_stock
    
    def to_dict(self):
        return {
            'id': self.p_id,
            'name': self.p_name,
            'price': float(self.p_price) if self.p_price else 0,
            'description': self.p_description,
            'stock': self.p_stock,
            'seller_id': self.s_id
        }

class Invoice(db.Model):
    __tablename__ = 'invoice'
    invoice_no = db.Column(db.String(50), primary_key=True)
    invoice_datetime = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')
    tax = db.Column(db.Numeric(10, 2), default=0)
    amount = db.Column(db.Numeric(10, 2), default=0)
    s_id = db.Column(db.String(50), db.ForeignKey('sellers.s_id'))
    c_id = db.Column(db.String(50), db.ForeignKey('customer.c_id'))

    def __init__(self, invoice_no=None, invoice_datetime=None, due_date=None, status='pending', tax=0, amount=0, s_id=None, c_id=None, **kwargs):
        super().__init__(**kwargs)
        self.invoice_no = invoice_no
        if invoice_datetime is not None:
            self.invoice_datetime = invoice_datetime
        self.due_date = due_date
        self.status = status
        self.tax = tax
        self.amount = amount
        self.s_id = s_id
        self.c_id = c_id
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)
    customer = db.relationship('Customer', backref='invoices', lazy=True)
    seller = db.relationship('Seller', backref='invoices', lazy=True)
    
    # Properties for template compatibility
    @property
    def id(self): return self.invoice_no
    @property
    def date(self): return self.invoice_datetime.strftime('%Y-%m-%d') if self.invoice_datetime else ''
    @property
    def customer_name(self): return self.customer.c_name if self.customer else ''
    @property
    def customer_email(self): return self.customer.c_email if self.customer else ''
    
    @property
    def due_date_str(self):
        if self.due_date:
            return self.due_date.strftime('%Y-%m-%d')
        return None
    
    def to_dict(self):
        return {
            'id': self.invoice_no,
            'date': self.date,
            'due_date': self.due_date_str,
            'status': self.status,
            'tax': float(self.tax),
            'amount': float(self.amount),
            'seller_id': self.s_id,
            'customer_id': self.c_id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'items': [item.to_dict() for item in self.items]
        }

class InvoiceItem(db.Model):
    """INVOICE_ITEM entity"""
    __tablename__ = 'invoice_item'
    item_id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), db.ForeignKey('invoice.invoice_no'))
    p_id = db.Column(db.String(50), db.ForeignKey('product.p_id'))
    item_quantity = db.Column(db.Integer, default=0)
    discount = db.Column(db.Numeric(10, 2), default=0)

    def __init__(self, item_id=None, invoice_no=None, p_id=None, item_quantity=0, discount=0, **kwargs):
        super().__init__(**kwargs)
        self.item_id = item_id
        self.invoice_no = invoice_no
        self.p_id = p_id
        self.item_quantity = item_quantity
        self.discount = discount
    
    # Relationships
    product = db.relationship('Product', backref='invoice_items', lazy=True)
    
    # Properties for template compatibility
    @property
    def quantity(self): return self.item_quantity
    @property
    def product_name(self): return self.product.p_name if self.product else ''
    @property
    def price(self): return self.product.p_price if self.product else 0
    @property
    def total(self):
        price = self.product.p_price if self.product else 0
        return (price * self.item_quantity) - self.discount
    
    def to_dict(self):
        price = self.product.p_price if self.product else 0
        return {
            'product_name': self.product_name,
            'quantity': self.item_quantity,
            'price': float(price),
            'discount': float(self.discount),
            'total': float((price * self.item_quantity) - self.discount)
        }
