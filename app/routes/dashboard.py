from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import query_db, execute_db
from app.auth_utils import login_required
from app.storage import get_image_url

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def home():
    """CampusFind landing page."""
    # Summary counters
    stats = {
        'total_lost': query_db("SELECT COUNT(*) as c FROM items WHERE item_type = 'lost'", one=True)['c'],
        'total_found': query_db("SELECT COUNT(*) as c FROM items WHERE item_type = 'found'", one=True)['c'],
        'total_returned': query_db("SELECT COUNT(*) as c FROM items WHERE status = 'returned'", one=True)['c'],
        'active_students': query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student'", one=True)['c'],
    }

    # Recent items
    recent_items = query_db(
        """
        SELECT i.*, u.full_name as reporter_name
        FROM items i
        JOIN users u ON i.user_id = u.id
        WHERE i.status = 'open'
        ORDER BY i.created_at DESC
        LIMIT 6
        """
    )
    for it in recent_items:
        it['display_image_url'] = get_image_url(it['image_url'])

    return render_template('home.html', stats=stats, recent_items=recent_items)

@dashboard_bp.route('/dashboard')
@login_required
def student_dashboard():
    """Main student dashboard showing their reports, claims, returns, and notifications."""
    user_id = session['user_id']

    # Reported Lost Items
    my_lost_items = query_db(
        "SELECT * FROM items WHERE user_id = %s AND item_type = 'lost' ORDER BY created_at DESC",
        (user_id,)
    )

    # Reported Found Items
    my_found_items = query_db(
        "SELECT * FROM items WHERE user_id = %s AND item_type = 'found' ORDER BY created_at DESC",
        (user_id,)
    )

    # My Claims on Found Items
    my_claims = query_db(
        """
        SELECT c.*, i.title as item_title, i.status as item_status
        FROM claims c
        JOIN items i ON c.item_id = i.id
        WHERE c.claimant_id = %s
        ORDER BY c.created_at DESC
        """,
        (user_id,)
    )

    # Incoming claims on my found items
    incoming_claims = query_db(
        """
        SELECT c.*, i.title as item_title, u.full_name as claimant_name
        FROM claims c
        JOIN items i ON c.item_id = i.id
        JOIN users u ON c.claimant_id = u.id
        WHERE i.user_id = %s AND c.status = 'pending'
        ORDER BY c.created_at DESC
        """,
        (user_id,)
    )

    # Handover records involved
    handovers = query_db(
        """
        SELECT h.*, i.title as item_title, u1.full_name as handed_name, u2.full_name as received_name
        FROM handovers h
        JOIN items i ON h.item_id = i.id
        JOIN users u1 ON h.handed_by = u1.id
        JOIN users u2 ON h.received_by = u2.id
        WHERE h.handed_by = %s OR h.received_by = %s
        ORDER BY h.handover_date DESC
        """,
        (user_id, user_id)
    )

    # Unread notifications count and list
    notifications = query_db(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 10",
        (user_id,)
    )

    return render_template(
        'dashboard/student.html',
        my_lost_items=my_lost_items,
        my_found_items=my_found_items,
        my_claims=my_claims,
        incoming_claims=incoming_claims,
        handovers=handovers,
        notifications=notifications
    )

@dashboard_bp.route('/notifications')
@login_required
def notifications_view():
    """List all notifications with option to mark all as read."""
    user_id = session['user_id']
    notifs = query_db(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,)
    )
    # Mark as read
    execute_db("UPDATE notifications SET is_read = TRUE WHERE user_id = %s", (user_id,))

    return render_template('dashboard/notifications.html', notifications=notifs)
