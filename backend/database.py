import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id           INTEGER PRIMARY KEY,
            name         TEXT NOT NULL,
            city         TEXT,
            segment      TEXT,
            since_date   TEXT
        );

        CREATE TABLE IF NOT EXISTS products (
            id        INTEGER PRIMARY KEY,
            name      TEXT NOT NULL,
            category  TEXT,
            price     REAL,
            stock     INTEGER
        );

        CREATE TABLE IF NOT EXISTS orders (
            id          INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(id),
            product_id  INTEGER REFERENCES products(id),
            quantity    INTEGER,
            order_date  TEXT,
            status      TEXT,
            total       REAL
        );
    """)

    if cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
        _seed(cur)

    conn.commit()
    conn.close()


def _seed(cur):
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", [
        (1, "Apex Manufacturing",   "Chicago",  "Enterprise",  "2021-03-15"),
        (2, "BlueRidge Logistics",  "Atlanta",  "Mid-Market",  "2022-01-08"),
        (3, "Crest Industrial",     "Dallas",   "Enterprise",  "2020-11-20"),
        (4, "Delta Fabricators",    "Phoenix",  "SMB",         "2023-04-01"),
        (5, "Eastern Supply Co",    "Boston",   "Mid-Market",  "2021-07-14"),
        (6, "Frontier Equipment",   "Denver",   "SMB",         "2022-09-30"),
        (7, "Global Parts Inc",     "Seattle",  "Enterprise",  "2019-05-22"),
        (8, "Harbor Industries",    "Miami",    "Mid-Market",  "2023-01-15"),
    ])

    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?)", [
        (1,  "Industrial Sensor Array",      "Sensors",     2499.00, 45),
        (2,  "Gateway Controller Unit",      "Hardware",    1899.00, 23),
        (3,  "RFID Reader Pro",              "Hardware",    3200.00, 12),
        (4,  "Data Logger Module",           "Sensors",      899.00, 67),
        (5,  "Network Switch 24-Port",       "Networking",  1250.00,  8),
        (6,  "Power Supply 48V",             "Components",   349.00,150),
        (7,  "Antenna Array UHF",            "Hardware",     750.00, 34),
        (8,  "Integration Software License", "Software",    4500.00,999),
        (9,  "Mounting Hardware Kit",        "Components",   125.00,210),
        (10, "Calibration Service Pack",     "Services",    2000.00,999),
    ])

    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", [
        (1,  1, 3,  2, "2026-01-10", "completed",  6400.00),
        (2,  2, 1,  5, "2026-01-15", "completed", 12495.00),
        (3,  3, 8,  3, "2026-01-18", "completed", 13500.00),
        (4,  1, 2,  1, "2026-02-02", "completed",  1899.00),
        (5,  5, 4, 10, "2026-02-05", "completed",  8990.00),
        (6,  4, 6, 20, "2026-02-10", "completed",  6980.00),
        (7,  7, 3,  4, "2026-02-14", "completed", 12800.00),
        (8,  2, 5,  2, "2026-02-20", "completed",  2500.00),
        (9,  6, 7,  6, "2026-03-01", "completed",  4500.00),
        (10, 3, 1,  3, "2026-03-05", "completed",  7497.00),
        (11, 8, 8,  1, "2026-03-10", "completed",  4500.00),
        (12, 1, 9, 15, "2026-03-12", "completed",  1875.00),
        (13, 5, 2,  2, "2026-03-18", "completed",  3798.00),
        (14, 7, 10, 2, "2026-04-01", "completed",  4000.00),
        (15, 3, 4,  8, "2026-04-05", "completed",  7192.00),
        (16, 2, 3,  1, "2026-04-10", "pending",    3200.00),
        (17, 4, 1,  3, "2026-04-15", "pending",    7497.00),
        (18, 6, 8,  2, "2026-04-18", "pending",    9000.00),
        (19, 8, 5,  1, "2026-04-20", "processing", 1250.00),
        (20, 1, 2,  2, "2026-04-22", "processing", 3798.00),
    ])
