import os
import re

try:
    import MySQLdb
except Exception:
    MySQLdb = None

try:
    from config import MYSQL_CONFIG
except Exception:
    MYSQL_CONFIG = {
        "host": os.environ.get("SMARTSERVE_DB_HOST", "localhost"),
        "user": os.environ.get("SMARTSERVE_DB_USER", "root"),
        "password": os.environ.get("SMARTSERVE_DB_PASSWORD", ""),
        "database": os.environ.get("SMARTSERVE_DB_NAME", "smartserve_db"),
    }

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def _server_config():
    cfg = dict(MYSQL_CONFIG)
    cfg.pop("database", None)
    return cfg


def _database_name():
    return MYSQL_CONFIG.get("database", "smartserve_db")


def ensure_database():
    """Create the configured database and required tables if MySQL is available."""
    if MySQLdb is None:
        return False, "mysqlclient/MySQLdb is not installed."

    db_name = _database_name()
    if not re.match(r"^[A-Za-z0-9_$]+$", db_name):
        return False, "Invalid database name in SMARTSERVE_DB_NAME."

    try:
        conn = MySQLdb.connect(**_server_config())
        cur = conn.cursor()
        cur.execute(
            "CREATE DATABASE IF NOT EXISTS `{}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(db_name)
        )
        conn.commit()
        cur.close()
        conn.close()

        conn = MySQLdb.connect(**MYSQL_CONFIG)
        cur = conn.cursor()

        # Keep table creation explicit and idempotent so an existing installation
        # is never destroyed.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS forecasts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                forecast_date DATE NOT NULL,
                item VARCHAR(100) NOT NULL,
                predicted_demand DECIMAL(10,2) NOT NULL,
                recommended_production INT NOT NULL,
                weather VARCHAR(50),
                event VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_forecast_date (forecast_date),
                INDEX idx_forecast_item (item)
            ) ENGINE=InnoDB
        """)

        # Add the optional risk field to databases created by older builds.
        try:
            cur.execute("ALTER TABLE forecasts ADD COLUMN waste_risk VARCHAR(20) NULL")
        except Exception:
            pass

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sale_date DATE NOT NULL,
                item VARCHAR(100) NOT NULL,
                quantity_sold INT NOT NULL,
                prepared_quantity INT DEFAULT 0,
                weather VARCHAR(50),
                event VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_sales_date (sale_date),
                INDEX idx_sales_item (item)
            ) ENGINE=InnoDB
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ingredient_inventory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ingredient VARCHAR(100) NOT NULL UNIQUE,
                stock_quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
                unit VARCHAR(20) NOT NULL,
                unit_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS procurement_alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                alert_date DATE NOT NULL,
                ingredient VARCHAR(100) NOT NULL,
                required_quantity DECIMAL(12,3) NOT NULL,
                available_quantity DECIMAL(12,3) NOT NULL,
                shortage_quantity DECIMAL(12,3) NOT NULL,
                recommended_order DECIMAL(12,3) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_procurement_date (alert_date),
                INDEX idx_procurement_status (status)
            ) ENGINE=InnoDB
        """)

        conn.commit()
        cur.close()
        conn.close()
        return True, f"Database '{db_name}' and required tables are ready."
    except Exception as exc:
        return False, str(exc)


def get_connection(auto_initialize=True):
    """Return a MySQL connection, optionally initializing the DB first."""
    if MySQLdb is None:
        return None

    if auto_initialize:
        ok, _ = ensure_database()
        if not ok:
            return None

    try:
        return MySQLdb.connect(**MYSQL_CONFIG)
    except Exception:
        return None

def save_forecast(item, forecast_date, predicted_demand, recommended_production, waste_risk):
    """
    Save a single demand forecast to the forecasts table.
    Returns True if saved successfully, otherwise False.
    """
    conn = None
    cursor = None

    try:
        conn = get_connection()

        if conn is None:
            return False

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO forecasts
            (
                item,
                forecast_date,
                predicted_demand,
                recommended_production,
                waste_risk
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                item,
                forecast_date,
                predicted_demand,
                recommended_production,
                waste_risk
            )
        )

        conn.commit()
        return True

    except Exception as e:
        print(f"[SmartServe] Could not save forecast: {e}")
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()