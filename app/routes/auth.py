import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import query_db, execute_db, log_activity

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('dashboard.student_dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        student_id = request.form.get('student_id', '').strip()
        department = request.form.get('department', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic validations
        if not full_name or not email or not password:
            flash("Full name, email, and password are required.", "danger")
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone, student_id=student_id, department=department)

        if not re.match(EMAIL_REGEX, email):
            flash("Please enter a valid email address.", "danger")
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone, student_id=student_id, department=department)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone, student_id=student_id, department=department)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/register.html', full_name=full_name, email=email, phone=phone, student_id=student_id, department=department)

        # Check existing email
        existing = query_db("SELECT id FROM users WHERE email = %s", (email,), one=True)
        if existing:
            flash("An account with this email already exists. Please log in.", "warning")
            return redirect(url_for('auth.login'))

        # Secure password hashing using PBKDF2/scrypt
        password_hash = generate_password_hash(password)

        try:
            res = execute_db(
                """
                INSERT INTO users (full_name, email, phone, student_id, department, password_hash, role)
                VALUES (%s, %s, %s, %s, %s, %s, 'student')
                """,
                (full_name, email, phone, student_id, department, password_hash)
            )
            user_id = res['lastrowid']
            log_activity(user_id, 'USER_REGISTER', f"New student account created: {email}", request.remote_addr)

            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f"Error registering user: {str(e)}", "danger")

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('dashboard.student_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template('auth/login.html')

        user = query_db("SELECT * FROM users WHERE email = %s", (email,), one=True)

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']

            log_activity(user['id'], 'USER_LOGIN', f"User logged in: {user['email']}", request.remote_addr)
            flash(f"Welcome back, {user['full_name']}!", "success")

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)

            if user['role'] == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            return redirect(url_for('dashboard.student_dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_activity(user_id, 'USER_LOGOUT', "User logged out", request.remote_addr)
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('auth.login'))
