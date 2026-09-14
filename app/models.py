import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=100)
    popularity_score = db.Column(db.Float, nullable=False, default=0.5)
    created_at = db.Column(db.String(50), nullable=True)

    # Relationships
    orders = db.relationship('Order', backref='product', lazy='dynamic')
    competitor_prices = db.relationship('CompetitorPrice', backref='product', lazy='dynamic')
    price_logs = db.relationship('PriceLog', backref='product', lazy='dynamic', order_by='PriceLog.timestamp.desc()')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'base_price': round(self.base_price, 2),
            'cost_price': round(self.cost_price, 2),
            'current_price': round(self.current_price, 2),
            'stock_quantity': self.stock_quantity,
            'popularity_score': round(self.popularity_score, 2),
            'created_at': self.created_at,
            'discount_pct': round(((self.base_price - self.current_price) / self.base_price) * 100, 1) if self.base_price > self.current_price else 0
        }


class Customer(UserMixin, db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    signup_date = db.Column(db.String(50), nullable=True)
    device_id = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(100), nullable=True)
    account_age_days = db.Column(db.Integer, nullable=False, default=30)

    # Relationships
    orders = db.relationship('Order', backref='customer', lazy='dynamic', order_by='Order.order_timestamp.desc()')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            # Default password fallback for seeded CSV customers: password123
            return password == "password123"
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return False

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'signup_date': self.signup_date,
            'device_id': self.device_id,
            'ip_address': self.ip_address,
            'account_age_days': self.account_age_days,
            'order_count': self.orders.count()
        }


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    customer_id = db.Column(db.String(64), db.ForeignKey('customers.id'), nullable=False)
    product_id = db.Column(db.String(64), db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_paid = db.Column(db.Float, nullable=False)
    discount_applied = db.Column(db.Float, nullable=False, default=0.0)
    coupon_code = db.Column(db.String(100), nullable=True)
    order_timestamp = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False, default='Card')
    is_flash_sale = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(50), nullable=False, default='APPROVED') # APPROVED, REVIEW, BLOCKED

    # Relationships
    fraud_label = db.relationship('FraudLabel', backref='order', uselist=False)
    fraud_alerts = db.relationship('FraudAlert', backref='order', lazy='dynamic', order_by='FraudAlert.created_at.desc()')

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else 'Unknown',
            'customer_email': self.customer.email if self.customer else 'Unknown',
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else 'Unknown',
            'quantity': self.quantity,
            'price_paid': round(self.price_paid, 2),
            'discount_applied': round(self.discount_applied, 2),
            'coupon_code': self.coupon_code or 'None',
            'order_timestamp': self.order_timestamp,
            'payment_method': self.payment_method,
            'is_flash_sale': self.is_flash_sale,
            'status': self.status,
            'is_fraud': self.fraud_label.is_fraud if self.fraud_label else (self.status == 'BLOCKED'),
            'fraud_type': self.fraud_label.fraud_type if self.fraud_label else 'none'
        }


class FraudLabel(db.Model):
    __tablename__ = 'fraud_labels'

    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    order_id = db.Column(db.String(64), db.ForeignKey('orders.id'), nullable=False)
    is_fraud = db.Column(db.Boolean, nullable=False, default=False)
    fraud_type = db.Column(db.String(100), nullable=False, default='none')

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'is_fraud': self.is_fraud,
            'fraud_type': self.fraud_type
        }


class CompetitorPrice(db.Model):
    __tablename__ = 'competitor_prices'

    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    product_id = db.Column(db.String(64), db.ForeignKey('products.id'), nullable=False)
    competitor_name = db.Column(db.String(100), nullable=False)
    competitor_price = db.Column(db.Float, nullable=False)
    scraped_at = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'competitor_name': self.competitor_name,
            'competitor_price': round(self.competitor_price, 2),
            'scraped_at': self.scraped_at
        }


class PriceLog(db.Model):
    __tablename__ = 'price_logs'

    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    product_id = db.Column(db.String(64), db.ForeignKey('products.id'), nullable=False)
    old_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    ai_recommended_price = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else '',
            'old_price': round(self.old_price, 2),
            'new_price': round(self.new_price, 2),
            'ai_recommended_price': round(self.ai_recommended_price, 2),
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat() if self.timestamp else ''
        }


class FraudAlert(db.Model):
    __tablename__ = 'fraud_alerts'

    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    order_id = db.Column(db.String(64), db.ForeignKey('orders.id'), nullable=False)
    risk_score = db.Column(db.Float, nullable=False) # 0.0 to 1.0
    fraud_type = db.Column(db.String(100), nullable=False) # bot_purchase, fake_account, coupon_abuse, none
    signals_json = db.Column(db.Text, nullable=False) # JSON array of explainable signal strings
    decision = db.Column(db.String(50), nullable=False, default='PENDING_REVIEW') # APPROVED, BLOCKED, PENDING_REVIEW
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        signals = []
        try:
            signals = json.loads(self.signals_json)
        except Exception:
            signals = [self.signals_json]

        return {
            'id': self.id,
            'order_id': self.order_id,
            'order': self.order.to_dict() if self.order else None,
            'risk_score': round(self.risk_score, 3),
            'fraud_type': self.fraud_type,
            'signals': signals,
            'decision': self.decision,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }


class AdminUser(UserMixin, db.Model):
    __tablename__ = 'admin_users'

    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return True


class FraudRuleConfig(db.Model):
    __tablename__ = 'fraud_rule_configs'

    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    rule_name = db.Column(db.String(100), unique=True, nullable=False)
    rule_value = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'rule_value': self.rule_value,
            'description': self.description,
            'is_active': self.is_active
        }
