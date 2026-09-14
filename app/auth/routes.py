import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, Customer, AdminUser

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and not getattr(current_user, 'is_admin', False):
        return redirect(url_for('products.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        customer = Customer.query.filter_by(email=email).first()
        if customer and customer.check_password(password):
            session['is_admin'] = False
            login_user(customer)
            flash(f"Welcome back, {customer.name}!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('products.index'))
        else:
            flash("Invalid email or password. (Demo: customer@idealab.com / customer123)", "error")

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated and not getattr(current_user, 'is_admin', False):
        return redirect(url_for('products.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not name or not email or not password:
            flash("Please fill in all required fields.", "error")
            return render_template('auth/register.html')

        if Customer.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return render_template('auth/register.html')

        new_customer = Customer(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            signup_date=datetime.utcnow().strftime('%Y-%m-%d'),
            device_id=f"device-{uuid.uuid4().hex[:12]}",
            ip_address=request.remote_addr or "127.0.0.1",
            account_age_days=0
        )
        new_customer.set_password(password)
        db.session.add(new_customer)
        db.session.commit()

        session['is_admin'] = False
        login_user(new_customer)
        flash("Account created successfully! Welcome to FlashDeals.", "success")
        return redirect(url_for('products.index'))

    return render_template('auth/register.html')

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and getattr(current_user, 'is_admin', False):
        return redirect(url_for('dashboard.overview'))

    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        admin = AdminUser.query.filter(
            (AdminUser.username == username_or_email) | (AdminUser.email == username_or_email)
        ).first()

        if admin and admin.check_password(password):
            session['is_admin'] = True
            login_user(admin)
            flash("Logged into Admin Command Center.", "success")
            return redirect(url_for('dashboard.overview'))
        else:
            flash("Invalid admin credentials. (Demo: admin@idealab.com / admin123)", "error")

    return render_template('auth/admin_login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    was_admin = session.get('is_admin', False)
    logout_user()
    session.pop('is_admin', None)
    flash("You have been signed out.", "info")
    if was_admin:
        return redirect(url_for('auth.admin_login'))
    return redirect(url_for('products.index'))
