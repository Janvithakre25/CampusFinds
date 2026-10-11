from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import query_db, execute_db, log_activity
from app.auth_utils import admin_required
from app.storage import get_image_url

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    """Main administrator control center with metrics and quick links."""
    stats = {
        'total_users': query_db("SELECT COUNT(*) as c FROM users", one=True)['c'],
        'total_items': query_db("SELECT COUNT(*) as c FROM items", one=True)['c'],
        'open_lost': query_db("SELECT COUNT(*) as c FROM items WHERE item_type = 'lost' AND status = 'open'", one=True)['c'],
        'open_found': query_db("SELECT COUNT(*) as c FROM items WHERE item_type = 'found' AND status = 'open'", one=True)['c'],
        'pending_claims': query_db("SELECT COUNT(*) as c FROM claims WHERE status = 'pending'", one=True)['c'],
        'total_returned': query_db("SELECT COUNT(*) as c FROM handovers", one=True)['c'],
    }

    recent_items = query_db(
        """
        SELECT i.*, u.full_name as reporter_name
        FROM items i
        JOIN users u ON i.user_id = u.id
        ORDER BY i.created_at DESC LIMIT 5
        """
    )
    for it in recent_items:
        it['display_image_url'] = get_image_url(it['image_url'])

    recent_claims = query_db(
        """
        SELECT c.*, i.title as item_title, u.full_name as claimant_name
        FROM claims c
        JOIN items i ON c.item_id = i.id
        JOIN users u ON c.claimant_id = u.id
        ORDER BY c.created_at DESC LIMIT 5
        """
    )

    recent_logs = query_db(
        """
        SELECT l.*, u.full_name as user_name, u.email as user_email
        FROM activity_logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC LIMIT 8
        """
    )

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_items=recent_items,
        recent_claims=recent_claims,
        recent_logs=recent_logs
    )

@admin_bp.route('/items')
@admin_required
def manage_items():
    """Admin view to moderate all items."""
    item_type = request.args.get('type')
    status = request.args.get('status')

    sql = """
        SELECT i.*, u.full_name as reporter_name, u.email as reporter_email
        FROM items i
        JOIN users u ON i.user_id = u.id
        WHERE 1=1
    """
    params = []
    if item_type:
        sql += " AND i.item_type = %s"
        params.append(item_type)
    if status:
        sql += " AND i.status = %s"
        params.append(status)

    sql += " ORDER BY i.created_at DESC"
    items = query_db(sql, tuple(params))

    return render_template('admin/items.html', items=items, item_type=item_type, status=status)

@admin_bp.route('/items/<int:item_id>/delete', methods=['POST'])
@admin_required
def delete_item(item_id):
    """Delete an item listing if inappropriate or spam."""
    try:
        execute_db("DELETE FROM items WHERE id = %s", (item_id,))
        log_activity(session['user_id'], 'ADMIN_DELETE_ITEM', f"Admin deleted item #{item_id}", request.remote_addr)
        flash(f"Item #{item_id} has been permanently deleted.", "success")
    except Exception as e:
        flash(f"Error deleting item: {str(e)}", "danger")

    return redirect(url_for('admin.manage_items'))

@admin_bp.route('/items/<int:item_id>/status', methods=['POST'])
@admin_required
def update_item_status(item_id):
    """Manually update an item's status (open, claimed, returned, closed)."""
    new_status = request.form.get('status')
    if new_status in ('open', 'claimed', 'returned', 'closed'):
        execute_db("UPDATE items SET status = %s WHERE id = %s", (new_status, item_id))
        log_activity(session['user_id'], 'ADMIN_STATUS_UPDATE', f"Updated item #{item_id} status to {new_status}", request.remote_addr)
        flash(f"Item #{item_id} status updated to {new_status}.", "success")
    return redirect(url_for('admin.manage_items'))

@admin_bp.route('/claims')
@admin_required
def manage_claims():
    """Admin claim moderation panel."""
    claims = query_db(
        """
        SELECT c.*, i.title as item_title, i.item_type,
               u1.full_name as claimant_name, u1.email as claimant_email,
               u2.full_name as reporter_name
        FROM claims c
        JOIN items i ON c.item_id = i.id
        JOIN users u1 ON c.claimant_id = u1.id
        JOIN users u2 ON i.user_id = u2.id
        ORDER BY c.created_at DESC
        """
    )
    for c in claims:
        c['display_proof_image'] = get_image_url(c['proof_image_url'])

    return render_template('admin/claims.html', claims=claims)

@admin_bp.route('/users')
@admin_required
def manage_users():
    """Admin user directory and role management."""
    users = query_db("SELECT * FROM users ORDER BY created_at DESC")
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/toggle-role', methods=['POST'])
@admin_required
def toggle_user_role(user_id):
    """Promote or demote user between student and admin."""
    if user_id == session['user_id']:
        flash("You cannot change your own administrator role.", "warning")
        return redirect(url_for('admin.manage_users'))

    user = query_db("SELECT role FROM users WHERE id = %s", (user_id,), one=True)
    if user:
        new_role = 'admin' if user['role'] == 'student' else 'student'
        execute_db("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        log_activity(session['user_id'], 'ADMIN_ROLE_CHANGE', f"Changed user #{user_id} role to {new_role}", request.remote_addr)
        flash(f"User role updated to {new_role}.", "success")

    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/logs')
@admin_required
def view_logs():
    """View system audit trails and security activity logs."""
    logs = query_db(
        """
        SELECT l.*, u.full_name as user_name, u.email as user_email
        FROM activity_logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC
        LIMIT 100
        """
    )
    return render_template('admin/logs.html', logs=logs)
