from flask import Flask


def create_app():
    app = Flask(__name__)

    # Import and register blueprints or routes here
    from .app import bp as app_bp
    app.register_blueprint(app_bp)

    return app