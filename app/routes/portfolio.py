from flask import Blueprint, request, jsonify
from app.middleware.auth import require_broker_connection

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/getOpenPositions', methods=['GET', 'POST'])
@require_broker_connection
def get_open_positions(adapter):
    result = adapter.getOpenPositionsList()
    return jsonify(result), 200

@portfolio_bp.route('/getRealisedPnL', methods=['GET', 'POST'])
@require_broker_connection
def get_realised_pnl(adapter):
    result = adapter.getPnl(request.args.to_dict())
    return jsonify(result), 200

@portfolio_bp.route('/getFunds', methods=['GET', 'POST'])
@require_broker_connection
def get_funds(adapter):
    result = adapter.getFunds()
    return jsonify(result), 200

@portfolio_bp.route('/getMargin', methods=['GET', 'POST'])
@require_broker_connection
def get_margin(adapter):
    result = adapter.getMargin(request.args.to_dict())
    return jsonify(result), 200

@portfolio_bp.route('/marginCalculator', methods=['GET', 'POST'])
@require_broker_connection
def margin_calculator(adapter):
    result = adapter.marginCalculator(request.args.to_dict())
    return jsonify(result), 200

@portfolio_bp.route('/getBrokerages', methods=['GET', 'POST'])
@require_broker_connection
def get_brokerages(adapter):
    result = adapter.getBrokerages(request.args.to_dict())
    return jsonify(result), 200