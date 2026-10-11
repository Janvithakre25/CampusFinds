from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.db import query_db, execute_db, log_activity, create_notification
from app.auth_utils import login_required
from app.storage import save_uploaded_file, get_image_url
from app.matching import find_similar_items

items_bp = Blueprint('items', __name__)

CATEGORIES = [
    'Electronics',
    'ID Cards & Documents',
    'Keys',
    'Wallets & Purses',
    'Books & Study Material',
    'Clothing & Wearables',
    'Bags & Backpacks',
    'Bottles & Lunchboxes',
    'Personal Accessories',
    'Other'
]

@items_bp.route('/')
def list_items():
    """Browse lost and found items with search and filters."""
    item_type = request.args.get('type', '') # 'lost', 'found', or ''
    category = request.args.get('category', '')
    status = request.args.get('status', 'open') # default to open items
    keyword = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()

    sql = """
        SELECT i.*, u.full_name as reporter_name, u.email as reporter_email
        FROM items i
        JOIN users u ON i.user_id = u.id
        WHERE 1=1
    """
    params = []

    if item_type in ('lost', 'found'):
        sql += " AND i.item_type = %s"
        params.append(item_type)

    if category:
        sql += " AND i.category = %s"
        params.append(category)

    if status and status != 'all':
        sql += " AND i.status = %s"
        params.append(status)

    if keyword:
        sql += " AND (i.title LIKE %s OR i.description LIKE %s)"
        kw_param = f"%{keyword}%"
        params.extend([kw_param, kw_param])

    if location:
        sql += " AND i.location LIKE %s"
        params.append(f"%{location}%")

    sql += " ORDER BY i.created_at DESC LIMIT 60"
    items = query_db(sql, tuple(params))

    # Enrich with accessible image urls
    for it in items:
        it['display_image_url'] = get_image_url(it['image_url'])

    return render_template(
        'items/list.html',
        items=items,
        categories=CATEGORIES,
        current_type=item_type,
        current_category=category,
        current_status=status,
        current_keyword=keyword,
        current_location=location
    )

@items_bp.route('/report/lost', methods=['GET', 'POST'])
@login_required
def report_lost():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        item_date = request.form.get('item_date', '').strip()
        private_details = request.form.get('private_verification_details', '').strip()

        if not title or not category or not description or not location or not item_date:
            flash("Please fill in all required fields marked with *.", "danger")
            return render_template('items/report_lost.html', categories=CATEGORIES, form=request.form)

        # Handle image file upload
        image_filename = None
        file = request.files.get('image')
        if file and file.filename != '':
            try:
                image_filename = save_uploaded_file(file)
            except Exception as e:
                flash(f"Image upload error: {str(e)}", "danger")
                return render_template('items/report_lost.html', categories=CATEGORIES, form=request.form)

        try:
            res = execute_db(
                """
                INSERT INTO items (user_id, item_type, title, category, description, location, item_date, image_url, private_verification_details, status)
                VALUES (%s, 'lost', %s, %s, %s, %s, %s, %s, %s, 'open')
                """,
                (session['user_id'], title, category, description, location, item_date, image_filename, private_details)
            )
            item_id = res['lastrowid']
            log_activity(session['user_id'], 'REPORT_LOST', f"Reported lost item #{item_id}: {title}", request.remote_addr)

            flash("Lost item report submitted successfully!", "success")
            return redirect(url_for('items.item_detail', item_id=item_id))
        except Exception as e:
            flash(f"Database error saving item: {str(e)}", "danger")

    return render_template('items/report_lost.html', categories=CATEGORIES)

@items_bp.route('/report/found', methods=['GET', 'POST'])
@login_required
def report_found():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        item_date = request.form.get('item_date', '').strip()
        private_details = request.form.get('private_verification_details', '').strip()

        if not title or not category or not description or not location or not item_date:
            flash("Please fill in all required fields marked with *.", "danger")
            return render_template('items/report_found.html', categories=CATEGORIES, form=request.form)

        # Handle image file upload
        image_filename = None
        file = request.files.get('image')
        if file and file.filename != '':
            try:
                image_filename = save_uploaded_file(file)
            except Exception as e:
                flash(f"Image upload error: {str(e)}", "danger")
                return render_template('items/report_found.html', categories=CATEGORIES, form=request.form)

        try:
            res = execute_db(
                """
                INSERT INTO items (user_id, item_type, title, category, description, location, item_date, image_url, private_verification_details, status)
                VALUES (%s, 'found', %s, %s, %s, %s, %s, %s, %s, 'open')
                """,
                (session['user_id'], title, category, description, location, item_date, image_filename, private_details)
            )
            item_id = res['lastrowid']
            log_activity(session['user_id'], 'REPORT_FOUND', f"Reported found item #{item_id}: {title}", request.remote_addr)

            flash("Found item report submitted successfully! Thank you for your honesty.", "success")
            return redirect(url_for('items.item_detail', item_id=item_id))
        except Exception as e:
            flash(f"Database error saving item: {str(e)}", "danger")

    return render_template('items/report_found.html', categories=CATEGORIES)

@items_bp.route('/<int:item_id>')
def item_detail(item_id):
    """View item details. Private verification details are strictly restricted."""
    item = query_db(
        """
        SELECT i.*, u.full_name as reporter_name, u.email as reporter_email, u.phone as reporter_phone
        FROM items i
        JOIN users u ON i.user_id = u.id
        WHERE i.id = %s
        """,
        (item_id,),
        one=True
    )

    if not item:
        abort(404)

    item['display_image_url'] = get_image_url(item['image_url'])

    # Determine whether current user is allowed to view private verification details
    current_uid = session.get('user_id')
    is_owner = (current_uid == item['user_id'])
    is_admin = (session.get('user_role') == 'admin')
    can_see_private = is_owner or is_admin

    # Fetch claims if current user is the reporter or admin
    claims = []
    if can_see_private:
        claims = query_db(
            """
            SELECT c.*, u.full_name as claimant_name, u.email as claimant_email, u.student_id as claimant_student_id, u.phone as claimant_phone
            FROM claims c
            JOIN users u ON c.claimant_id = u.id
            WHERE c.item_id = %s
            ORDER BY c.created_at DESC
            """,
            (item_id,)
        )
        for c in claims:
            c['display_proof_image'] = get_image_url(c['proof_image_url'])

    # Check if logged-in student has already submitted a claim on this item
    user_claim = None
    if current_uid:
        user_claim = query_db(
            "SELECT * FROM claims WHERE item_id = %s AND claimant_id = %s",
            (item_id, current_uid),
            one=True
        )

    # Fetch handover record if returned
    handover = None
    if item['status'] == 'returned':
        handover = query_db(
            """
            SELECT h.*, u1.full_name as handed_name, u2.full_name as received_name
            FROM handovers h
            JOIN users u1 ON h.handed_by = u1.id
            JOIN users u2 ON h.received_by = u2.id
            WHERE h.item_id = %s
            """,
            (item_id,),
            one=True
        )

    # Similar items suggestions (free keyword + category heuristic)
    similar_items = find_similar_items(
        item['id'],
        item['item_type'],
        item['category'],
        item['title'],
        item['description']
    )
    for sim in similar_items:
        sim['display_image_url'] = get_image_url(sim['image_url'])

    return render_template(
        'items/detail.html',
        item=item,
        can_see_private=can_see_private,
        is_owner=is_owner,
        is_admin=is_admin,
        claims=claims,
        user_claim=user_claim,
        handover=handover,
        similar_items=similar_items
    )
