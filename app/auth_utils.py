from functools import wraps
from flask import session, flash, redirect, url_for, request, abort

def login_required(f):
    """Ensures user is logged in before accessing the view."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Ensures user is logged in and possesses the admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash("Please log in as an administrator.", "warning")
            return redirect(url_for('auth.login', next=request.path))
        if session.get('user_role') != 'admin':
            flash("Administrator privileges are required for this action.", "danger")
            return redirect(url_for('dashboard.student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function
