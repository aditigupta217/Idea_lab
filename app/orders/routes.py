import uuid
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.models import db, Order, Product, Customer, FraudAlert, FraudLabel
from app.fraud.detector import fraud_detector

orders_bp = Blueprint('orders', __name__)

# --- Cart Helpers ---
def get_cart():
    return session.get('cart', {})

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

@orders_bp.route('/cart')
def cart():
    cart_dict = get_cart()
    cart_items = []
    subtotal = 0.0

    for prod_id, item_data in cart_dict.items():
        product = Product.query.get(prod_id)
        if product:
            qty = item_data.get('quantity', 1)
            item_total = product.current_price * qty
            subtotal += item_total
            cart_items.append({
                'product': product,
                'quantity': qty,
                'item_total': item_total
            })

    return render_template('storefront/cart.html', cart_items=cart_items, subtotal=subtotal)

@orders_bp.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    data = request.get_json() or request.form
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))

    product = Product.query.get_or_404(product_id)
    cart = get_cart()

    if product_id in cart:
        cart[product_id]['quantity'] += quantity
    else:
        cart[product_id] = {
            'product_id': product_id,
            'name': product.name,
            'price': product.current_price,
            'quantity': quantity
        }

    save_cart(cart)
    total_count = sum(item['quantity'] for item in cart.values())

    return jsonify({
        'success': True,
        'message': f"Added '{product.name}' to cart",
        'cart_count': total_count
    })

@orders_bp.route('/api/cart/update', methods=['POST'])
def update_cart():
    data = request.get_json() or request.form
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))

    cart = get_cart()
    if product_id in cart:
        if quantity > 0:
            cart[product_id]['quantity'] = quantity
        else:
            cart.pop(product_id, None)
        save_cart(cart)

    return jsonify({'success': True, 'cart_count': sum(item['quantity'] for item in cart.values())})

@orders_bp.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    data = request.get_json() or request.form
    product_id = data.get('product_id')

    cart = get_cart()
    if product_id in cart:
        cart.pop(product_id, None)
        save_cart(cart)

    return jsonify({'success': True, 'cart_count': sum(item['quantity'] for item in cart.values())})

@orders_bp.route('/checkout', methods=['GET'])
@login_required
def checkout():
    cart_dict = get_cart()
    if not cart_dict:
        flash("Your cart is empty.", "info")
        return redirect(url_for('products.index'))

    cart_items = []
    subtotal = 0.0
    for prod_id, item_data in cart_dict.items():
        product = Product.query.get(prod_id)
        if product:
            qty = item_data.get('quantity', 1)
            item_total = product.current_price * qty
            subtotal += item_total
            cart_items.append({
                'product': product,
                'quantity': qty,
                'item_total': item_total
            })

    return render_template(
        'storefront/checkout.html',
        cart_items=cart_items,
        subtotal=subtotal,
        customer=current_user
    )

@orders_bp.route('/api/checkout', methods=['POST'])
@login_required
def process_checkout():
    cart_dict = get_cart()
    if not cart_dict:
        return jsonify({'success': False, 'message': 'Cart is empty.'}), 400

    data = request.get_json() or request.form
    coupon_code = data.get('coupon_code', '').strip()
    payment_method = data.get('payment_method', 'Card')
    simulated_burst = int(data.get('simulated_burst', 1)) # Demo trigger parameter

    # Calculate discount
    discount_pct = 0.0
    if coupon_code:
        code_upper = coupon_code.upper()
        if 'FLASH20' in code_upper:
            discount_pct = 0.20
        elif 'SAVE10' in code_upper:
            discount_pct = 0.10
        elif 'VIP50' in code_upper or 'SPAM' in code_upper or 'BOT' in code_upper:
            discount_pct = 0.50
        else:
            discount_pct = 0.05

    created_orders = []
    highest_risk = 0.0
    final_decision = 'APPROVED'
    detected_fraud_type = 'none'
    all_signals = []

    for prod_id, item_data in cart_dict.items():
        product = Product.query.get(prod_id)
        if not product:
            continue

        quantity = item_data.get('quantity', 1)
        raw_price = product.current_price * quantity
        discount_amount = raw_price * discount_pct
        final_price = max(1.0, raw_price - discount_amount)

        # Real-time AI Fraud Screening
        fraud_eval = fraud_detector.evaluate_order(
            customer=current_user,
            order_data={
                'quantity': quantity,
                'price_paid': final_price,
                'discount_applied': discount_amount,
                'coupon_code': coupon_code or None,
                'payment_method': payment_method,
                'is_flash_sale': (product.current_price < product.base_price),
                'simulated_burst_count': simulated_burst
            }
        )

        risk_score = fraud_eval['risk_score']
        order_status = fraud_eval['decision']
        fraud_type = fraud_eval['fraud_type']
        signals = fraud_eval['signals']

        if risk_score > highest_risk:
            highest_risk = risk_score
            final_decision = order_status
            detected_fraud_type = fraud_type
            all_signals = signals

        # Create Order Record
        order_id = str(uuid.uuid4())
        new_order = Order(
            id=order_id,
            customer_id=current_user.id,
            product_id=product.id,
            quantity=quantity,
            price_paid=final_price,
            discount_applied=discount_amount,
            coupon_code=coupon_code or None,
            order_timestamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000000'),
            payment_method=payment_method,
            is_flash_sale=(product.current_price < product.base_price),
            status=order_status
        )
        db.session.add(new_order)

        # If approved, decrement inventory
        if order_status == 'APPROVED':
            product.stock_quantity = max(0, product.stock_quantity - quantity)

        # If flagged for review or blocked, log FraudAlert for Admin Dashboard
        if order_status in ['BLOCKED', 'PENDING_REVIEW']:
            alert = FraudAlert(
                id=str(uuid.uuid4()),
                order_id=order_id,
                risk_score=risk_score,
                fraud_type=fraud_type,
                signals_json=json.dumps(signals),
                decision=order_status,
                created_at=datetime.utcnow()
            )
            db.session.add(alert)

            fraud_lbl = FraudLabel(
                id=str(uuid.uuid4()),
                order_id=order_id,
                is_fraud=True,
                fraud_type=fraud_type
            )
            db.session.add(fraud_lbl)
        else:
            fraud_lbl = FraudLabel(
                id=str(uuid.uuid4()),
                order_id=order_id,
                is_fraud=False,
                fraud_type='none'
            )
            db.session.add(fraud_lbl)

        created_orders.append(new_order)

    db.session.commit()
    # Clear cart
    save_cart({})

    return jsonify({
        'success': True,
        'decision': final_decision,
        'risk_score': highest_risk,
        'fraud_type': detected_fraud_type,
        'signals': all_signals,
        'order_count': len(created_orders),
        'message': "Order placed successfully!" if final_decision == 'APPROVED' else (
            "Order flagged for security compliance review." if final_decision == 'PENDING_REVIEW' else
            "Order blocked by automated AI fraud detection shield."
        )
    })

@orders_bp.route('/my-orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.order_timestamp.desc()).all()
    return render_template('storefront/my_orders.html', orders=orders)
