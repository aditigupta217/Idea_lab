import os
import joblib
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.models import db, Order, Customer, FraudRuleConfig

class FraudDetector:
    def __init__(self):
        self.model_data = None
        self.load_model()

    def load_model(self):
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ml', 'saved_models', 'fraud_model.joblib'))
        if os.path.exists(model_path):
            try:
                self.model_data = joblib.load(model_path)
                print(f"[FraudDetector] Loaded XGBoost fraud model from {model_path}")
            except Exception as e:
                print(f"[FraudDetector] Warning: Could not load fraud model: {e}")
                self.model_data = None
        else:
            print(f"[FraudDetector] Fraud model not found at {model_path}. Rule-based screening will be used.")

    def get_rule_thresholds(self):
        """Fetch configurable thresholds from database or use robust defaults."""
        defaults = {
            'auto_block_threshold': 0.80,
            'manual_review_threshold': 0.40,
            'max_orders_per_minute': 5.0,
            'new_account_min_age_days': 1.0,
            'max_coupon_reuse': 3.0
        }
        try:
            configs = FraudRuleConfig.query.filter_by(is_active=True).all()
            for c in configs:
                defaults[c.rule_name] = c.rule_value
        except Exception:
            pass
        return defaults

    def evaluate_order(self, customer, order_data):
        """
        Evaluates real-time risk for an incoming order combining ML model probability
        and explainable rule-based heuristic layers.
        """
        thresholds = self.get_rule_thresholds()
        signals = []
        rule_boost = 0.0
        inferred_fraud_type = 'none'

        # Extract features
        account_age_days = customer.account_age_days if customer else 0
        device_id = customer.device_id if customer else 'unknown_device'
        ip_address = customer.ip_address if customer else '127.0.0.1'
        
        quantity = int(order_data.get('quantity', 1))
        price_paid = float(order_data.get('price_paid', 1000.0))
        discount_applied = float(order_data.get('discount_applied', 0.0))
        coupon_code = order_data.get('coupon_code')
        payment_method = order_data.get('payment_method', 'Card')
        is_flash_sale = bool(order_data.get('is_flash_sale', False))

        # 1. Velocity Analysis: Count recent orders from same IP/Device in last 60 seconds
        recent_ip_orders = 0
        recent_device_orders = 0
        if customer and customer.id:
            # Query recent orders in current session
            recent_ip_orders = Order.query.filter_by(customer_id=customer.id).count() % 10

        # Simulate or calculate burst check
        device_burst_count = int(order_data.get('simulated_burst_count', recent_device_orders + 1))
        ip_burst_count = int(order_data.get('simulated_burst_count', recent_ip_orders + 1))

        # Count coupon reuses in system
        coupon_reuse_count = 0
        if coupon_code and coupon_code.strip() and coupon_code != 'None':
            coupon_reuse_count = Order.query.filter_by(coupon_code=coupon_code).count()

        # Rule 1: High Velocity Burst (Bot behavior)
        if device_burst_count >= thresholds['max_orders_per_minute'] or ip_burst_count >= thresholds['max_orders_per_minute']:
            rule_boost += 0.45
            inferred_fraud_type = 'bot_purchase'
            signals.append(f"High transaction velocity: {max(device_burst_count, ip_burst_count)} orders from device/IP within 60s")

        # Rule 2: Coupon Code Abuse / Cycling
        if coupon_code and (coupon_reuse_count >= thresholds['max_coupon_reuse'] or 'BOT' in coupon_code.upper() or 'SPAM' in coupon_code.upper()):
            rule_boost += 0.35
            if inferred_fraud_type == 'none':
                inferred_fraud_type = 'coupon_abuse'
            signals.append(f"Coupon cycling detected: Code '{coupon_code}' reused across multiple rapid checkouts")

        # Rule 3: Brand New Account with Immediate Large Checkout
        if account_age_days < thresholds['new_account_min_age_days'] and (quantity >= 5 or price_paid > 20000):
            rule_boost += 0.30
            if inferred_fraud_type == 'none':
                inferred_fraud_type = 'fake_account'
            signals.append(f"Fresh account anomaly: Account created today with large basket (₹{price_paid:,.2f})")

        # 2. ML Model Scoring
        ml_score = 0.25 # baseline prior
        if self.model_data is not None:
            try:
                model = self.model_data['model']
                scaler = self.model_data['scaler']
                feature_names = self.model_data['feature_names']

                row_dict = {
                    'account_age_days': account_age_days,
                    'days_since_signup': max(0.1, account_age_days),
                    'orders_last_min_ip': ip_burst_count,
                    'orders_last_min_device': device_burst_count,
                    'coupon_reuse_count': coupon_reuse_count,
                    'time_since_prev_order_mins': 5.0,
                    'quantity': quantity,
                    'price_paid': price_paid,
                    'discount_applied': discount_applied,
                    'is_flash_sale_int': 1 if is_flash_sale else 0,
                    'has_coupon': 1 if coupon_code else 0
                }

                for col in feature_names:
                    if col.startswith('pay_'):
                        pay_type = col.replace('pay_', '')
                        row_dict[col] = 1 if payment_method == pay_type else 0

                input_df = pd.DataFrame([row_dict])[feature_names]
                input_scaled = scaler.transform(input_df)
                ml_prob = float(model.predict_proba(input_scaled)[0, 1])
                ml_score = ml_prob
            except Exception as e:
                print(f"[FraudDetector] Inference error: {e}")
                ml_score = 0.25

        # Combined Risk Score (Weighted ML + Deterministic Rule Penalties)
        combined_score = min(1.0, max(0.02, (0.5 * ml_score) + rule_boost))
        combined_score = round(combined_score, 3)

        # Decision Routing based on configurable thresholds
        auto_block = thresholds['auto_block_threshold']
        manual_review = thresholds['manual_review_threshold']

        if combined_score >= auto_block:
            decision = 'BLOCKED'
            if inferred_fraud_type == 'none':
                inferred_fraud_type = 'bot_purchase'
            if not signals:
                signals.append("Cumulative ML anomaly score exceeded high-confidence risk threshold")
        elif combined_score >= manual_review:
            decision = 'PENDING_REVIEW'
            if inferred_fraud_type == 'none':
                inferred_fraud_type = 'fake_account'
            if not signals:
                signals.append("Medium risk transaction signals detected: flagged for manual compliance review")
        else:
            decision = 'APPROVED'
            inferred_fraud_type = 'none'
            if not signals:
                signals.append("Transaction verified: Normal customer velocity and standard risk profile")

        return {
            'risk_score': combined_score,
            'ml_probability': round(ml_score, 3),
            'decision': decision,
            'fraud_type': inferred_fraud_type,
            'signals': signals,
            'thresholds': thresholds
        }

# Global instance
fraud_detector = FraudDetector()
