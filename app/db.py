import pymysql
from pymysql.cursors import DictCursor
from flask import g, current_app
import logging

logger = logging.getLogger(__name__)

def get_db():
    """
    Returns a MySQL database connection stored in Flask application context 'g'.
    Automatically works for local MySQL or AWS RDS MySQL based on config.
    """
    if 'db' not in g:
        config = current_app.config
        try:
            g.db = pymysql.connect(
                host=config['DB_HOST'],
                port=config['DB_PORT'],
                user=config['DB_USER'],
                password=config['DB_PASSWORD'],
                database=config['DB_NAME'],
                cursorclass=DictCursor,
                autocommit=True,
                charset='utf8mb4',
                connect_timeout=config.get('DB_CONNECT_TIMEOUT', 10)
            )
        except pymysql.MySQLError as e:
            logger.error(f"Database connection error: {e}")
            raise e
    return g.db

def close_db(e=None):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass

def init_db_app(app):
    """Registers teardown handlers with the Flask app."""
    app.teardown_appcontext(close_db)

# Helper query execution functions
def query_db(query, args=(), one=False):
    """Executes a SELECT query and returns dictionary rows."""
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute(query, args)
        rv = cursor.fetchall()
        return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Executes an INSERT/UPDATE/DELETE query and returns lastrowid and rowcount."""
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute(query, args)
        return {
            'lastrowid': cursor.lastrowid,
            'rowcount': cursor.rowcount
        }

def log_activity(user_id, action, details=None, ip_address=None):
    """Records an activity log in the database."""
    try:
        execute_db(
            "INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES (%s, %s, %s, %s)",
            (user_id, action, details, ip_address)
        )
    except Exception as e:
        logger.warning(f"Failed to record activity log: {e}")

def create_notification(user_id, title, message, link=None):
    """Creates an in-app notification for a user."""
    try:
        execute_db(
            "INSERT INTO notifications (user_id, title, message, link, is_read) VALUES (%s, %s, %s, %s, FALSE)",
            (user_id, title, message, link)
        )
    except Exception as e:
        logger.warning(f"Failed to create notification: {e}")
