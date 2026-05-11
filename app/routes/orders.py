from flask import Blueprint, request, jsonify
from app.middleware.auth import require_broker_connection
import logging

logger = logging.getLogger(__name__)
orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/placeOrder', methods=['GET', 'POST'])
@require_broker_connection
def place_order(adapter):
    try:
        result = adapter.placeOrder(request.args.to_dict())
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return jsonify({"Error": str(e)}), 500

@orders_bp.route('/squareoff', methods=['GET', 'POST'])
@require_broker_connection
def squareoff(adapter):
    result = adapter.squareOffOrder(request.args.to_dict())
    return jsonify(result), 200

@orders_bp.route('/modifyOrder', methods=['GET', 'POST'])
@require_broker_connection
def modify_order(adapter):
    result = adapter.modifyOrder(request.args.to_dict())
    return jsonify(result), 200

@orders_bp.route('/cancelOrder', methods=['GET', 'POST'])
@require_broker_connection
def cancel_order(adapter):
    order_ref = request.args.get("orderId")
    result = adapter.cancelOrder(order_ref)
    return jsonify(result), 200

@orders_bp.route('/getOrderList', methods=['GET', 'POST'])
@require_broker_connection
def get_order_list(adapter):
    result = adapter.getOrdersList(request.args.to_dict())
    return jsonify(result), 200

@orders_bp.route('/getOrderDetails', methods=['GET', 'POST'])
@require_broker_connection
def get_order_details(adapter):
    order_id = request.args.get("orderId")
    result = adapter.getOrderDetails(order_id)
    return jsonify(result), 200