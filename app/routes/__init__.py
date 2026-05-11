from .auth import auth_bp
from .orders import orders_bp
from .portfolio import portfolio_bp
from .main import main_bp

def register_blueprints(app):
    """Registers all route blueprints with the Flask application"""
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(portfolio_bp)
    