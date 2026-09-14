import uuid
import json
from datetime import datetime
from flask import Blueprint, jsonify, request
from app.models import db, FraudAlert, Order, Customer, Product, FraudLabel, FraudRuleConfig
from app.fraud.detector import fraud_detector

fraud_bp = Blueprint('fraud', __name__)

@fraud_bp.route('/alerts', methods=['GET'])
def get_alerts():
    decision_filter = request.args.get('decision') # PENDING_REVIEW, BLOCKED, APPROVED
    query = FraudAlert.query

    if decision_filter:
        query = query.filter_by(decision=decision_filter)

    alerts = query.order_by(FraudAlert.created_at.desc()).limit(100).all()
    return jsonify({
        'success': True,
        'count': len(alerts),
        'alerts': [a.to_dict() for a in alerts]
    })

@fraud_bp.route('/decision/<alert_id>', methods=['POST'])
def handle_decision(alert_id):
    alert = FraudAlert.query.get_or_404(alert_id)
    data = request.get_json() or {}
    decision = data.get('decision') # 'APPROVED' or 'BLOCKED'

    if decision not in ['APPROVED', 'BLOCKED']:
        return jsonify({'success': False, 'message': 'Decision must be APPROVED or BLOCKED'}), 400

    alert.decision = decision

    # Update associated order
    if alert.order:
        alert.order.status = decision
        if alert.order.fraud_label:
            alert.order.fraud_label.is_fraud = (decision == 'BLOCKED')

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Alert {alert.id[:8]} marked as {decision}",
        'alert': alert.to_dict()
    })

@fraud_bp.route('/rules', methods=['GET'])
def get_rules():
    rules = FraudRuleConfig.query.all()
    return jsonify({
        'success': True,
        'rules': [r.to_dict() for r in rules]
    })

@fraud_bp.route('/rules/update', methods=['POST'])
def update_rules():
    data = request.get_json() or {}
    updated = []

    for rule_name, val in data.items():
        rule_obj = FraudRuleConfig.query.filter_by(rule_name=rule_name).first()
        if rule_obj:
            rule_obj.rule_value = float(val)
            updated.append(rule_name)

    db.session.commit()
    return jsonify({
        'success': True,
        'message': f"Updated rules: {', '.join(updated)}"
    })

@fraud_bp.route('/simulate-attack', methods=['POST'])
def simulate_attack():
    """
    Live interactive attack simulator for demo purposes:
    Generates a burst of 6 rapid transactions with bot characteristics,
    screens them via FraudDetector, and returns the intercepted results.
    """
    data = request.get_json() or {}
    attack_type = data.get('attack_type', 'bot_burst') # bot_burst, coupon_spam, fake_account

    # Find or pick a target customer and product
    target_cust = Customer.query.first()
    target_prod = Product.query.first()

    results = []

    if attack_type == 'bot_burst':
        # Simulate 6 orders within 30 seconds
        for i in range(6):
            eval_res = fraud_detector.evaluate_order(
                customer=target_cust,
                order_data={
                    'quantity': 3,
                    'price_paid': target_prod.current_price * 3,
                    'discount_applied': 0.0,
                    'coupon_code': None,
                    'payment_method': 'UPI',
                    'is_flash_sale': True,
                    'simulated_burst_count': i + 4 # simulates > 5/min
                }
            )
            
            order_id = str(uuid.uuid4())
            new_order = Order(
                id=order_id,
                customer_id=target_cust.id,
                product_id=target_prod.id,
                quantity=3,
                price_paid=target_prod.current_price * 3,
                discount_applied=0.0,
                coupon_code=None,
                order_timestamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000000'),
                payment_method='UPI',
                is_flash_sale=True,
                status=eval_res['decision']
            )
            db.session.add(new_order)

            alert = FraudAlert(
                id=str(uuid.uuid4()),
                order_id=order_id,
                risk_score=eval_res['risk_score'],
                fraud_type=eval_res['fraud_type'],
                signals_json=json.dumps(eval_res['signals']),
                decision=eval_res['decision'],
                created_at=datetime.utcnow()
            )
            db.session.add(alert)
            results.append({
                'order_id': order_id,
                'decision': eval_res['decision'],
                'risk_score': eval_res['risk_score'],
                'signals': eval_res['signals']
            })

    elif attack_type == 'coupon_spam':
        # Simulate coupon cycling brute-force
        for i in range(4):
            eval_res = fraud_detector.evaluate_order(
                customer=target_cust,
                order_data={
                    'quantity': 1,
                    'price_paid': target_prod.current_price * 0.5,
                    'discount_applied': target_prod.current_price * 0.5,
                    'coupon_code': f'SPAM_EXPLOIT_{i+1}',
                    'payment_method': 'Card',
                    'is_flash_sale': True,
                    'simulated_burst_count': 2
                }
            )
            order_id = str(uuid.uuid4())
            new_order = Order(
                id=order_id,
                customer_id=target_cust.id,
                product_id=target_prod.id,
                quantity=1,
                price_paid=target_prod.current_price * 0.5,
                discount_applied=target_prod.current_price * 0.5,
                coupon_code=f'SPAM_EXPLOIT_{i+1}',
                order_timestamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000000'),
                payment_method='Card',
                is_flash_sale=True,
                status=eval_res['decision']
            )
            db.session.add(new_order)
            alert = FraudAlert(
                id=str(uuid.uuid4()),
                order_id=order_id,
                risk_score=eval_res['risk_score'],
                fraud_type=eval_res['fraud_type'],
                signals_json=json.dumps(eval_res['signals']),
                decision=eval_res['decision'],
                created_at=datetime.utcnow()
            )
            db.session.add(alert)
            results.append({
                'order_id': order_id,
                'decision': eval_res['decision'],
                'risk_score': eval_res['risk_score'],
                'signals': eval_res['signals']
            })

    db.session.commit()

    return jsonify({
        'success': True,
        'attack_type': attack_type,
        'simulated_attempts': len(results),
        'intercepted_results': results
    })
