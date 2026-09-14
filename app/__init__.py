import os
from flask import Flask, session
from flask_login import LoginManager
from app.models import db, Customer, AdminUser

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    # Check if user is admin or customer based on session or prefix
    if session.get('is_admin'):
        return AdminUser.query.get(user_id)
    return Customer.query.get(user_id)

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # Configuration
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'ecommerce.db'))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dynamic-pricing-fraud-shield-secret-2026'),
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.from_mapping(test_config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register Blueprints
    from app.auth.routes import auth_bp
    from app.products.routes import products_bp
    from app.orders.routes import orders_bp
    from app.pricing.routes import pricing_bp
    from app.fraud.routes import fraud_bp
    from app.dashboard.routes import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(pricing_bp, url_prefix='/api/pricing')
    app.register_blueprint(fraud_bp, url_prefix='/api/fraud')
    app.register_blueprint(dashboard_bp)

    # Context processors and template filters
    @app.template_filter('currency')
    def currency_filter(value):
        try:
            return f"₹{float(value):,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"

    @app.context_processor
    def inject_cart_count():
        cart = session.get('cart', {})
        count = sum(item.get('quantity', 1) for item in cart.values())
        return {'cart_item_count': count}

    return app
