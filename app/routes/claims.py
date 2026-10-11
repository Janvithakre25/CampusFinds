from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.db import query_db, execute_db, log_activity, create_notification
from app.auth_utils import login_required
from app.storage import save_uploaded_file, get_image_url

claims_bp = Blueprint('claims', __name__)

@claims_bp.route('/')
@login_required
def my_claims():
    """Displays claims created by the logged-in student, as well as claims received on their items."""
    user_id = session['user_id']

    # Claims made by this user
    made_claims = query_db(
        """
        SELECT c.*, i.title as item_title, i.item_type, i.category, i.status as item_status,
               u.full_name as reporter_name
        FROM claims c
        JOIN items i ON c.item_id = i.id
        JOIN users u ON i.user_id = u.id
        WHERE c.claimant_id = %s
        ORDER BY c.created_at DESC
        """,
        (user_id,)
    )

    # Claims received on items reported by this user
    received_claims = query_db(
        """
        SELECT c.*, i.title as item_title, i.item_type, i.category, i.status as item_status,
               u.full_name as claimant_name, u.email as claimant_email, u.phone as claimant_phone, u.student_id as claimant_student_id
        FROM claims c
        JOIN items i ON c.item_id = i.id
        JOIN users u ON c.claimant_id = u.id
        WHERE i.user_id = %s
        ORDER BY c.created_at DESC
        """,
        (user_id,)
    )

    for c in made_claims + received_claims:
        c['display_proof_image'] = get_image_url(c.get('proof_image_url'))

    return render_template('claims/index.html', made_claims=made_claims, received_claims=received_claims)

@claims_bp.route('/submit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def submit_claim(item_id):
    """Submit an ownership claim on a found item."""
    item = query_db("SELECT * FROM items WHERE id = %s", (item_id,), one=True)
    if not item:
        abort(404)

    if item['item_type'] != 'found':
        flash("Ownership claims can only be submitted on 'found' items.", "warning")
        return redirect(url_for('items.item_detail', item_id=item_id))

    if item['user_id'] == session['user_id']:
        flash("You cannot claim an item that you reported finding.", "warning")
        return redirect(url_for('items.item_detail', item_id=item_id))

    # Check for existing claim
    existing = query_db(
        "SELECT id FROM claims WHERE item_id = %s AND claimant_id = %s",
        (item_id, session['user_id']),
        one=True
    )
    if existing:
        flash("You have already submitted a claim for this item.", "info")
        return redirect(url_for('items.item_detail', item_id=item_id))

    if request.method == 'POST':
        claim_description = request.form.get('claim_description', '').strip()
        proof_details = request.form.get('proof_details', '').strip()

        if not claim_description or not proof_details:
            flash("Please provide both a claim description and proof of ownership.", "danger")
            return render_template('claims/submit.html', item=item)

        proof_image = None
        file = request.files.get('proof_image')
        if file and file.filename != '':
            try:
                proof_image = save_uploaded_file(file)
            except Exception as e:
                flash(f"Proof image upload error: {str(e)}", "danger")
                return render_template('claims/submit.html', item=item)

        try:
            res = execute_db(
                """
                INSERT INTO claims (item_id, claimant_id, claim_description, proof_details, proof_image_url, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
                """,
                (item_id, session['user_id'], claim_description, proof_details, proof_image)
            )
            claim_id = res['lastrowid']

            # Notify the finder
            create_notification(
                item['user_id'],
                "New Claim Submitted",
                f"A new ownership claim was submitted for '{item['title']}'.",
                url_for('items.item_detail', item_id=item_id)
            )

            log_activity(session['user_id'], 'CLAIM_SUBMITTED', f"Submitted claim #{claim_id} for item #{item_id}", request.remote_addr)

            flash("Your ownership claim has been submitted! The finder or administrator will review it.", "success")
            return redirect(url_for('items.item_detail', item_id=item_id))
        except Exception as e:
            flash(f"Database error submitting claim: {str(e)}", "danger")

    return render_template('claims/submit.html', item=item)

@claims_bp.route('/<int:claim_id>/review', methods=['POST'])
@login_required
def review_claim(claim_id):
    """Finder or Admin approves or rejects a claim."""
    claim = query_db(
        """
        SELECT c.*, i.user_id as item_owner_id, i.title as item_title, i.status as item_status
        FROM claims c
        JOIN items i ON c.item_id = i.id
        WHERE c.id = %s
        """,
        (claim_id,),
        one=True
    )

    if not claim:
        abort(404)

    is_finder = (claim['item_owner_id'] == session['user_id'])
    is_admin = (session.get('user_role') == 'admin')

    if not (is_finder or is_admin):
        flash("You are not authorized to review this claim.", "danger")
        return redirect(url_for('claims.my_claims'))

    decision = request.form.get('decision') # 'approved' or 'rejected'
    remarks = request.form.get('remarks', '').strip()

    if decision not in ('approved', 'rejected'):
        flash("Invalid decision.", "danger")
        return redirect(url_for('items.item_detail', item_id=claim['item_id']))

    try:
        execute_db(
            """
            UPDATE claims
            SET status = %s, admin_or_finder_remarks = %s, reviewed_by = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (decision, remarks, session['user_id'], claim_id)
        )

        if decision == 'approved':
            # Mark item as claimed
            execute_db("UPDATE items SET status = 'claimed' WHERE id = %s", (claim['item_id'],))
            create_notification(
                claim['claimant_id'],
                "Claim Approved!",
                f"Your claim for '{claim['item_title']}' was approved! Please coordinate the handover.",
                url_for('items.item_detail', item_id=claim['item_id'])
            )
            flash("Claim approved successfully! The item is now marked as 'Claimed'. Proceed with Handover when returning.", "success")
        else:
            create_notification(
                claim['claimant_id'],
                "Claim Rejected",
                f"Your claim for '{claim['item_title']}' was rejected. Reason: {remarks or 'Details did not match'}.",
                url_for('items.item_detail', item_id=claim['item_id'])
            )
            flash("Claim marked as rejected.", "info")

        log_activity(session['user_id'], f"CLAIM_{decision.upper()}", f"Claim #{claim_id} set to {decision}", request.remote_addr)

    except Exception as e:
        flash(f"Error updating claim: {str(e)}", "danger")

    return redirect(url_for('items.item_detail', item_id=claim['item_id']))

@claims_bp.route('/<int:claim_id>/handover', methods=['GET', 'POST'])
@login_required
def record_handover(claim_id):
    """
    Record physical return/handover of the item.
    Only permitted after claim is approved. Prevents duplicate handovers.
    Marks the item status as 'returned'.
    """
    claim = query_db(
        """
        SELECT c.*, i.id as item_id, i.title as item_title, i.user_id as item_owner_id, i.status as item_status,
               u1.full_name as claimant_name, u2.full_name as finder_name
        FROM claims c
        JOIN items i ON c.item_id = i.id
        JOIN users u1 ON c.claimant_id = u1.id
        JOIN users u2 ON i.user_id = u2.id
        WHERE c.id = %s
        """,
        (claim_id,),
        one=True
    )

    if not claim:
        abort(404)

    is_finder = (claim['item_owner_id'] == session['user_id'])
    is_admin = (session.get('user_role') == 'admin')

    if not (is_finder or is_admin):
        flash("Only the finder or an administrator can record a physical handover.", "danger")
        return redirect(url_for('items.item_detail', item_id=claim['item_id']))

    if claim['status'] != 'approved':
        flash("You can only record a handover for an approved claim.", "warning")
        return redirect(url_for('items.item_detail', item_id=claim['item_id']))

    # Check if handover already exists
    existing_handover = query_db("SELECT id FROM handovers WHERE item_id = %s", (claim['item_id'],), one=True)
    if existing_handover:
        flash("A handover has already been recorded for this item.", "info")
        return redirect(url_for('items.item_detail', item_id=claim['item_id']))

    if request.method == 'POST':
        location = request.form.get('location', '').strip()
        notes = request.form.get('notes', '').strip()

        if not location:
            flash("Handover meeting location is required.", "danger")
            return render_template('claims/handover.html', claim=claim)

        try:
            execute_db(
                """
                INSERT INTO handovers (item_id, claim_id, handed_by, received_by, location, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (claim['item_id'], claim['id'], session['user_id'], claim['claimant_id'], location, notes)
            )

            # Update item status to returned
            execute_db("UPDATE items SET status = 'returned' WHERE id = %s", (claim['item_id'],))

            # Send notifications
            create_notification(
                claim['claimant_id'],
                "Handover Recorded — Item Returned!",
                f"Handover for '{claim['item_title']}' has been officially confirmed at {location}.",
                url_for('items.item_detail', item_id=claim['item_id'])
            )
            create_notification(
                claim['item_owner_id'],
                "Item Returned Successfully",
                f"Your return of '{claim['item_title']}' was recorded.",
                url_for('items.item_detail', item_id=claim['item_id'])
            )

            log_activity(session['user_id'], 'HANDOVER_COMPLETED', f"Recorded handover for item #{claim['item_id']} to claimant #{claim['claimant_id']}", request.remote_addr)

            flash("Handover successfully completed! The item is now marked as Returned.", "success")
            return redirect(url_for('items.item_detail', item_id=claim['item_id']))
        except Exception as e:
            flash(f"Error saving handover record: {str(e)}", "danger")

    return render_template('claims/handover.html', claim=claim)
