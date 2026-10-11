import os
from flask import Flask, render_template, session
from app.config import Config
from app.db import init_db_app, query_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize database teardown hooks
    init_db_app(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.items import items_bp
    from app.routes.claims import claims_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(items_bp, url_prefix='/items')
    app.register_blueprint(claims_bp, url_prefix='/claims')
    app.register_blueprint(admin_bp)

    # Global context processor to make notification count and user details available in templates
    @app.context_processor
    def inject_global_data():
        unread_notifs = 0
        if session.get('user_id'):
            try:
                res = query_db(
                    "SELECT COUNT(*) as c FROM notifications WHERE user_id = %s AND is_read = FALSE",
                    (session['user_id'],),
                    one=True
                )
                unread_notifs = res['c'] if res else 0
            except Exception:
                unread_notifs = 0
        return dict(unread_notifications_count=unread_notifs)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    return app
