import os
import sys
import json
import pandas as pd
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add parent directory to path to import app models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import db, Product, Customer, Order, FraudLabel, CompetitorPrice, PriceLog, FraudAlert, AdminUser, FraudRuleConfig
from flask import Flask

def create_app_for_import():
    app = Flask(__name__)
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'ecommerce.db'))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def run_import():
    app = create_app_for_import()
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'raw'))

    print(f"=== Starting Database Import into SQLite ===")
    print(f"Reading CSVs from: {raw_dir}")

    with app.app_context():
        # Create all tables cleanly
        db.drop_all()
        db.create_all()

        # 1. Products
        print("Importing Products...")
        df_prod = pd.read_csv(os.path.join(raw_dir, 'products.csv'))
        products = []
        for _, row in df_prod.iterrows():
            prod = Product(
                id=str(row['id']),
                name=str(row['name']),
                category=str(row['category']),
                base_price=float(row['base_price']),
                cost_price=float(row['cost_price']),
                current_price=float(row['current_price']),
                stock_quantity=int(row['stock_quantity']),
                popularity_score=float(row['popularity_score']),
                created_at=str(row['created_at']) if pd.notna(row['created_at']) else None
            )
            products.append(prod)
        db.session.bulk_save_objects(products)
        db.session.commit()
        print(f"✓ Products imported: {len(products)}")

        # 2. Customers
        print("Importing Customers...")
        df_cust = pd.read_csv(os.path.join(raw_dir, 'customers.csv'))
        # Create a default password hash for all imported customers (password123)
        default_pwd_hash = generate_password_hash("password123")
        customers = []
        for _, row in df_cust.iterrows():
            cust = Customer(
                id=str(row['id']),
                name=str(row['name']),
                email=str(row['email']),
                password_hash=default_pwd_hash,
                signup_date=str(row['signup_date']) if pd.notna(row['signup_date']) else None,
                device_id=str(row['device_id']) if pd.notna(row['device_id']) else None,
                ip_address=str(row['ip_address']) if pd.notna(row['ip_address']) else None,
                account_age_days=int(row['account_age_days']) if pd.notna(row['account_age_days']) else 30
            )
            customers.append(cust)
        db.session.bulk_save_objects(customers)
        db.session.commit()
        print(f"✓ Customers imported: {len(customers)}")

        # 3. Orders
        print("Importing Orders...")
        df_orders = pd.read_csv(os.path.join(raw_dir, 'orders.csv'))
        orders = []
        for _, row in df_orders.iterrows():
            order = Order(
                id=str(row['id']),
                customer_id=str(row['customer_id']),
                product_id=str(row['product_id']),
                quantity=int(row['quantity']),
                price_paid=float(row['price_paid']),
                discount_applied=float(row['discount_applied']) if pd.notna(row['discount_applied']) else 0.0,
                coupon_code=str(row['coupon_code']) if pd.notna(row['coupon_code']) else None,
                order_timestamp=str(row['order_timestamp']),
                payment_method=str(row['payment_method']) if pd.notna(row['payment_method']) else 'Card',
                is_flash_sale=bool(row['is_flash_sale']) if pd.notna(row['is_flash_sale']) else False,
                status='APPROVED'
            )
            orders.append(order)
        db.session.bulk_save_objects(orders)
        db.session.commit()
        print(f"✓ Orders imported: {len(orders)}")

        # 4. Fraud Labels
        print("Importing Fraud Labels...")
        df_fraud = pd.read_csv(os.path.join(raw_dir, 'fraud_labels.csv'))
        fraud_labels = []
        for _, row in df_fraud.iterrows():
            fl = FraudLabel(
                id=str(row['id']),
                order_id=str(row['order_id']),
                is_fraud=bool(row['is_fraud']),
                fraud_type=str(row['fraud_type']) if pd.notna(row['fraud_type']) else 'none'
            )
            fraud_labels.append(fl)
        db.session.bulk_save_objects(fraud_labels)
        db.session.commit()
        print(f"✓ Fraud Labels imported: {len(fraud_labels)}")

        # 5. Competitor Prices
        print("Importing Competitor Prices...")
        df_comp = pd.read_csv(os.path.join(raw_dir, 'competitor_prices.csv'))
        competitors = []
        for _, row in df_comp.iterrows():
            cp = CompetitorPrice(
                id=str(row['id']),
                product_id=str(row['product_id']),
                competitor_name=str(row['competitor_name']),
                competitor_price=float(row['competitor_price']),
                scraped_at=str(row['scraped_at'])
            )
            competitors.append(cp)
        db.session.bulk_save_objects(competitors)
        db.session.commit()
        print(f"✓ Competitor Prices imported: {len(competitors)}")

        # 6. Seed Default Admin User
        print("Seeding Admin User...")
        admin = AdminUser(
            username="admin",
            email="admin@idealab.com",
            role="admin"
        )
        admin.set_password("admin123")
        db.session.add(admin)

        # Also add a dedicated demo customer for immediate login testing
        demo_cust = Customer(
            id="demo-customer-001",
            name="Demo Customer",
            email="customer@idealab.com",
            signup_date=datetime.utcnow().strftime('%Y-%m-%d'),
            device_id="demo-browser-chrome-01",
            ip_address="192.168.1.100",
            account_age_days=180
        )
        demo_cust.set_password("customer123")
        db.session.add(demo_cust)

        # 7. Seed Default Fraud Rules Config
        default_rules = [
            FraudRuleConfig(rule_name="auto_block_threshold", rule_value=0.80, description="Fraud probability score above which order is automatically blocked"),
            FraudRuleConfig(rule_name="manual_review_threshold", rule_value=0.40, description="Fraud probability score above which order is flagged for admin review"),
            FraudRuleConfig(rule_name="max_orders_per_minute", rule_value=5.0, description="Max allowed orders per minute from the same device/IP before auto-flagging"),
            FraudRuleConfig(rule_name="new_account_min_age_days", rule_value=1.0, description="Minimum account age in days before high-frequency order risk is elevated"),
            FraudRuleConfig(rule_name="max_coupon_reuse", rule_value=3.0, description="Max coupon reuses across accounts sharing the same device/IP")
        ]
        db.session.add_all(default_rules)

        # 8. Seed Initial Fraud Alerts & Price Logs from existing data
        print("Populating initial Fraud Alerts & Price History Logs...")
        # Get fraudulent orders from fraud_labels to generate initial alerts for Admin Dashboard review
        fraud_orders_query = db.session.query(Order, FraudLabel).join(FraudLabel, Order.id == FraudLabel.order_id).filter(FraudLabel.is_fraud == True).limit(45).all()
        for ord_obj, fl_obj in fraud_orders_query:
            signals = []
            if fl_obj.fraud_type == 'bot_purchase':
                signals = ["High transaction velocity: >6 orders within 45s", "Consistent timestamp micro-intervals", "Headless browser signature detected"]
                score = 0.88
                decision = "BLOCKED"
                ord_obj.status = "BLOCKED"
            elif fl_obj.fraud_type == 'fake_account':
                signals = ["Account created < 10 minutes before checkout", "Disposable domain / proxy IP address", "Device ID shared across multiple usernames"]
                score = 0.74
                decision = "PENDING_REVIEW"
                ord_obj.status = "REVIEW"
            elif fl_obj.fraud_type == 'coupon_abuse':
                signals = ["Coupon code cycled across 4 separate fresh accounts", "Automated discount stacking pattern"]
                score = 0.65
                decision = "PENDING_REVIEW"
                ord_obj.status = "REVIEW"
            else:
                signals = ["Unusual quantity spike compared to historical average"]
                score = 0.48
                decision = "APPROVED"

            alert = FraudAlert(
                order_id=ord_obj.id,
                risk_score=score,
                fraud_type=fl_obj.fraud_type,
                signals_json=json.dumps(signals),
                decision=decision,
                created_at=datetime.utcnow()
            )
            db.session.add(alert)

        # Generate sample Price Logs for the first 25 products
        for prod in Product.query.limit(25).all():
            comp = CompetitorPrice.query.filter_by(product_id=prod.id).first()
            comp_price = comp.competitor_price if comp else prod.base_price * 0.95
            log = PriceLog(
                product_id=prod.id,
                old_price=prod.base_price,
                new_price=prod.current_price,
                ai_recommended_price=round(min(prod.base_price * 0.92, max(prod.cost_price * 1.05, comp_price * 0.98)), 2),
                reason="Initial Dynamic Flash Sale AI Optimization",
                timestamp=datetime.utcnow()
            )
            db.session.add(log)

        db.session.commit()

        # ==========================================
        # VERIFICATION STEP
        # ==========================================
        print("\n================ VERIFICATION REPORT ================")
        prod_count = Product.query.count()
        cust_count = Customer.query.count()
        order_count = Order.query.count()
        fraud_count = FraudLabel.query.count()
        comp_count = CompetitorPrice.query.count()
        alert_count = FraudAlert.query.count()
        admin_count = AdminUser.query.count()

        print(f"Table 'products':          {prod_count} rows")
        print(f"Table 'customers':         {cust_count} rows")
        print(f"Table 'orders':            {order_count} rows")
        print(f"Table 'fraud_labels':      {fraud_count} rows")
        print(f"Table 'competitor_prices': {comp_count} rows")
        print(f"Table 'fraud_alerts':      {alert_count} rows")
        print(f"Table 'admin_users':       {admin_count} rows")

        # Check Foreign Key Referential Integrity
        print("\nChecking Foreign Key Integrity...")
        orphaned_orders_cust = db.session.query(Order).filter(~Order.customer_id.in_(db.session.query(Customer.id))).count()
        orphaned_orders_prod = db.session.query(Order).filter(~Order.product_id.in_(db.session.query(Product.id))).count()
        orphaned_fraud = db.session.query(FraudLabel).filter(~FraudLabel.order_id.in_(db.session.query(Order.id))).count()
        orphaned_comp = db.session.query(CompetitorPrice).filter(~CompetitorPrice.product_id.in_(db.session.query(Product.id))).count()

        print(f"Orphaned Orders -> Customers: {orphaned_orders_cust} (Expected: 0)")
        print(f"Orphaned Orders -> Products:  {orphaned_orders_prod} (Expected: 0)")
        print(f"Orphaned FraudLabels -> Orders:{orphaned_fraud} (Expected: 0)")
        print(f"Orphaned Competitor -> Products: {orphaned_comp} (Expected: 0)")

        if orphaned_orders_cust == 0 and orphaned_orders_prod == 0 and orphaned_fraud == 0 and orphaned_comp == 0:
            print("\n>>> ALL FOREIGN KEY INTEGRITY CHECKS PASSED PERFECTLY! <<<")
        else:
            print("\n>>> WARNING: Foreign key discrepancies detected! <<<")

if __name__ == '__main__':
    run_import()
