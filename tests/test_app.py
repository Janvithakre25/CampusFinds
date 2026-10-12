import pytest
import io
from app import create_app
from app.db import execute_db, query_db

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_home_page(client):
    """Test that landing page renders with status 200."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"CampusFind" in response.data

def test_browse_items(client):
    """Test listing items and filter search."""
    response = client.get('/items/')
    assert response.status_code == 200
    assert b"Browse Campus Items" in response.data

    # Test filtering by keyword
    search_resp = client.get('/items/?q=AirPods')
    assert search_resp.status_code == 200
    assert b"AirPods" in search_resp.data

def test_user_registration_and_login(client):
    """Test user registration, domain restriction (@rbunagpur.in), and login authentication."""
    import uuid
    rand_id = uuid.uuid4().hex[:6]
    valid_email = f"student_{rand_id}@rbunagpur.in"
    invalid_email = f"intruder_{rand_id}@gmail.com"

    # Test rejection of unauthorized domain
    bad_resp = client.post('/auth/register', data={
        'full_name': 'External User',
        'email': invalid_email,
        'phone': '9876543210',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)
    assert b"Registration restricted: Only official college email addresses" in bad_resp.data

    # Valid registration with @rbunagpur.in
    reg_resp = client.post('/auth/register', data={
        'full_name': 'RBU Student',
        'email': valid_email,
        'phone': '9876543210',
        'student_id': f'RBU-{rand_id}',
        'department': 'Computer Science',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)
    assert reg_resp.status_code == 200
    assert b"Registration successful" in reg_resp.data

    # Attempt duplicate registration
    dup_resp = client.post('/auth/register', data={
        'full_name': 'RBU Student',
        'email': valid_email,
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)
    assert b"already exists" in dup_resp.data

    # Login
    login_resp = client.post('/auth/login', data={
        'email': valid_email,
        'password': 'Password123!'
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    assert b"Welcome back" in login_resp.data

def test_report_item_flow(client):
    """Test logged-in student reporting lost and found items."""
    # Login as student alex@rbunagpur.in
    client.post('/auth/login', data={
        'email': 'alex@rbunagpur.in',
        'password': 'Password123!'
    }, follow_redirects=True)

    # Report lost item with private verification details
    report_resp = client.post('/items/report/lost', data={
        'title': 'Blue Hydro Flask Bottle',
        'category': 'Bottles & Lunchboxes',
        'description': '32oz blue bottle left near basketball court.',
        'location': 'Basketball Court',
        'item_date': '2026-10-11',
        'private_verification_details': 'Scratch shaped like an X on the bottom'
    }, follow_redirects=True)
    assert report_resp.status_code == 200
    assert b"Blue Hydro Flask Bottle" in report_resp.data
    # Verify confidential notes are visible to author
    assert b"Confidential Verification Details" in report_resp.data

def test_claim_and_handover_flow(client):
    """Test claim submission, approval, and handover record creation."""
    # Login as student alex
    client.post('/auth/login', data={
        'email': 'alex@rbunagpur.in',
        'password': 'Password123!'
    }, follow_redirects=True)

    # Item #4 is found by David Chen (user 4). Alex claims item #4
    claim_resp = client.post('/claims/submit/4', data={
        'claim_description': 'Those are my dorm keys!',
        'proof_details': 'Guitar keychain has initials D.K.'
    }, follow_redirects=True)
    assert claim_resp.status_code == 200
    assert b"ownership claim has been submitted" in claim_resp.data

    # Log out alex, log in as David (finder) to review claim
    client.get('/auth/logout')
    client.post('/auth/login', data={
        'email': 'david@rbunagpur.in',
        'password': 'Password123!'
    }, follow_redirects=True)

    # Find the created claim ID
    with client.application.app_context():
        claim = query_db("SELECT id FROM claims WHERE item_id = 4 AND claimant_id = 2", one=True)
        assert claim is not None
        claim_id = claim['id']

    # David approves claim
    review_resp = client.post(f'/claims/{claim_id}/review', data={
        'decision': 'approved',
        'remarks': 'Initials match. Meet at campus security.'
    }, follow_redirects=True)
    assert review_resp.status_code == 200
    assert b"Claim approved successfully" in review_resp.data

    # David records handover
    handover_resp = client.post(f'/claims/{claim_id}/handover', data={
        'location': 'Campus Security Office Room 102',
        'notes': 'Handed over in person with ID verification.'
    }, follow_redirects=True)
    assert handover_resp.status_code == 200
    assert b"Handover successfully completed" in handover_resp.data

    # Verify item status updated to 'returned'
    with client.application.app_context():
        item = query_db("SELECT status FROM items WHERE id = 4", one=True)
        assert item['status'] == 'returned'

def test_admin_authorization_protection(client):
    """Test that unauthorized students cannot access administrator panel."""
    # Login as student
    client.post('/auth/login', data={
        'email': 'samantha@rbunagpur.in',
        'password': 'Password123!'
    }, follow_redirects=True)

    admin_resp = client.get('/admin/', follow_redirects=True)
    assert b"Administrator privileges are required" in admin_resp.data

    # Logout and login as admin
    client.get('/auth/logout')
    client.post('/auth/login', data={
        'email': 'admin@rbunagpur.in',
        'password': 'Password123!'
    }, follow_redirects=True)

    admin_ok_resp = client.get('/admin/')
    assert admin_ok_resp.status_code == 200
    assert b"Campus Overview & Metrics" in admin_ok_resp.data
