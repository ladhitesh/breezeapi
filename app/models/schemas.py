from marshmallow import Schema, fields, validate, ValidationError, post_load
from app.models.orders import OrderRequest, OrderAction, OrderType, Product

class OrderSchema(Schema):
    """Validates incoming JSON/Form data for placing an order"""
    action = fields.Str(
        required=True,
        validate=validate.OneOf([a.value for a in OrderAction]),
        error_messages={"validator_failed": "Invalid action. Must be BUY or SELL."}
    )
    stock_code = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=20)
    )
    quantity = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=100000)
    )
    product = fields.Str(
        required=True,
        validate=validate.OneOf([p.value for p in Product])
    )
    exchange_code = fields.Str(load_default="NFO")
    order_type = fields.Str(
        load_default="LIMIT",
        validate=validate.OneOf([t.value for t in OrderType])
    )
    price = fields.Float(load_default=0.0)
    stoploss = fields.Float(load_default=0.0)
    
    expiry_date = fields.Str(allow_none=True)
    strike_price = fields.Float(allow_none=True)
    right_type = fields.Str(allow_none=True, validate=validate.OneOf(["CE", "PE"]))
    
    @post_load
    def make_order_request(self, data, **kwargs):
        """Converts the validated dictionary into our type-safe OrderRequest object"""
        data['action'] = OrderAction[data['action'].upper()]
        data['product'] = Product[data['product'].upper()]
        data['order_type'] = OrderType[data['order_type'].upper()]
        return OrderRequest(**data)