"""
Tool definitions and handlers.
Claude never touches raw SQL — it calls named, parameterized functions.
"""
import json
from database import get_connection

TOOL_DEFINITIONS = [
    {
        "name": "get_revenue_summary",
        "description": "Get total revenue and order count. Optionally filter by date range or status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"},
                "status":    {"type": "string", "enum": ["completed", "pending", "processing"]},
            },
        },
    },
    {
        "name": "get_top_customers",
        "description": "Rank customers by total spend. Returns name, segment, city, and total revenue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit":    {"type": "integer", "description": "Number of results. Default 5."},
                "segment":  {"type": "string",  "description": "Filter by segment: Enterprise, Mid-Market, SMB"},
                "date_from":{"type": "string",  "description": "Only count orders from this date"},
            },
        },
    },
    {
        "name": "get_orders",
        "description": "Fetch orders with optional filters. Returns order details including customer and product names.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status":      {"type": "string", "enum": ["completed", "pending", "processing"]},
                "customer_id": {"type": "integer"},
                "date_from":   {"type": "string"},
                "date_to":     {"type": "string"},
                "limit":       {"type": "integer"},
            },
        },
    },
    {
        "name": "get_inventory",
        "description": "Get product inventory levels. Filter by category or flag items below a stock threshold.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category":        {"type": "string", "description": "Filter by category"},
                "below_stock":     {"type": "integer", "description": "Only return products with stock below this number"},
            },
        },
    },
    {
        "name": "get_customer_detail",
        "description": "Get full profile for a specific customer including their order history summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "name":        {"type": "string", "description": "Search by partial name if ID not known"},
            },
        },
    },
    {
        "name": "get_revenue_by_category",
        "description": "Break down revenue by product category to see which categories drive the most sales.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string"},
                "date_to":   {"type": "string"},
            },
        },
    },
]


def handle_tool(name: str, inputs: dict) -> str:
    handlers = {
        "get_revenue_summary":    _revenue_summary,
        "get_top_customers":      _top_customers,
        "get_orders":             _orders,
        "get_inventory":          _inventory,
        "get_customer_detail":    _customer_detail,
        "get_revenue_by_category":_revenue_by_category,
    }
    fn = handlers.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return json.dumps(fn(**inputs), default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _revenue_summary(date_from=None, date_to=None, status=None):
    q = "SELECT COUNT(*) as order_count, ROUND(SUM(total), 2) as revenue FROM orders WHERE 1=1"
    p = []
    if date_from: q += " AND order_date >= ?"; p.append(date_from)
    if date_to:   q += " AND order_date <= ?"; p.append(date_to)
    if status:    q += " AND status = ?";      p.append(status)
    row = get_connection().execute(q, p).fetchone()
    return {"order_count": row[0], "revenue": row[1]}


def _top_customers(limit=5, segment=None, date_from=None):
    q = """
        SELECT c.name, c.segment, c.city,
               COUNT(o.id) as orders,
               ROUND(SUM(o.total), 2) as total_spend
        FROM customers c
        JOIN orders o ON o.customer_id = c.id
        WHERE 1=1
    """
    p = []
    if segment:   q += " AND c.segment = ?";    p.append(segment)
    if date_from: q += " AND o.order_date >= ?"; p.append(date_from)
    q += " GROUP BY c.id ORDER BY total_spend DESC LIMIT ?"
    p.append(limit)
    rows = get_connection().execute(q, p).fetchall()
    return [dict(r) for r in rows]


def _orders(status=None, customer_id=None, date_from=None, date_to=None, limit=20):
    q = """
        SELECT o.id, c.name as customer, p.name as product,
               o.quantity, o.order_date, o.status, o.total
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        JOIN products  p ON p.id = o.product_id
        WHERE 1=1
    """
    p = []
    if status:      q += " AND o.status = ?";         p.append(status)
    if customer_id: q += " AND o.customer_id = ?";    p.append(customer_id)
    if date_from:   q += " AND o.order_date >= ?";    p.append(date_from)
    if date_to:     q += " AND o.order_date <= ?";    p.append(date_to)
    q += " ORDER BY o.order_date DESC LIMIT ?"
    p.append(limit)
    rows = get_connection().execute(q, p).fetchall()
    return [dict(r) for r in rows]


def _inventory(category=None, below_stock=None):
    q = "SELECT name, category, price, stock FROM products WHERE 1=1"
    p = []
    if category:    q += " AND category = ?"; p.append(category)
    if below_stock is not None: q += " AND stock < ?"; p.append(below_stock)
    q += " ORDER BY stock ASC"
    rows = get_connection().execute(q, p).fetchall()
    return [dict(r) for r in rows]


def _customer_detail(customer_id=None, name=None):
    conn = get_connection()
    if name:
        row = conn.execute("SELECT * FROM customers WHERE name LIKE ?", (f"%{name}%",)).fetchone()
    else:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not row:
        return {"error": "Customer not found"}
    cust = dict(row)
    summary = conn.execute("""
        SELECT COUNT(*) as orders, ROUND(SUM(total), 2) as total_spend,
               MIN(order_date) as first_order, MAX(order_date) as last_order
        FROM orders WHERE customer_id = ?
    """, (cust["id"],)).fetchone()
    cust.update(dict(summary))
    return cust


def _revenue_by_category(date_from=None, date_to=None):
    q = """
        SELECT p.category,
               COUNT(o.id) as orders,
               ROUND(SUM(o.total), 2) as revenue
        FROM orders o
        JOIN products p ON p.id = o.product_id
        WHERE 1=1
    """
    p = []
    if date_from: q += " AND o.order_date >= ?"; p.append(date_from)
    if date_to:   q += " AND o.order_date <= ?"; p.append(date_to)
    q += " GROUP BY p.category ORDER BY revenue DESC"
    rows = get_connection().execute(q, p).fetchall()
    return [dict(r) for r in rows]
