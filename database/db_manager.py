import sqlite3
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path="database/perishable.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Категория товара
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_category (
                    id_category INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)

            # Товары (без min_stock)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id_product INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    purchase_price REAL NOT NULL,
                    sale_price REAL NOT NULL,
                    shelf_life_days INTEGER,
                    id_category INTEGER NOT NULL,
                    FOREIGN KEY (id_category) REFERENCES product_category(id_category)
                )
            """)

            # Параметры порчи по неделям
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_spoilage_rates (
                    id_product INTEGER NOT NULL,
                    week_number INTEGER NOT NULL,
                    rate REAL NOT NULL,
                    PRIMARY KEY (id_product, week_number),
                    FOREIGN KEY (id_product) REFERENCES products(id_product) ON DELETE CASCADE
                )
            """)

            # Эксперименты (история симуляций)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id_experiment INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    distribution TEXT NOT NULL,
                    days INTEGER NOT NULL,
                    fifo_percent REAL,
                    min_stock REAL NOT NULL,
                    purchase_price REAL NOT NULL,
                    sale_price REAL NOT NULL,
                    delivery_type TEXT NOT NULL,
                    delivery_frequency INTEGER,
                    delivery_days TEXT,
                    packing_type TEXT NOT NULL,
                    box_size INTEGER DEFAULT 1,
                    total_revenue REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    total_spoilage_kg REAL NOT NULL,
                    total_spoilage_money REAL NOT NULL,
                    profit REAL NOT NULL,
                    total_unmet_demand REAL DEFAULT 0
                )
            """)

            self._init_default_data(cursor)
            conn.commit()

    def _init_default_data(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM product_category")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO product_category (id_category, name) VALUES (1, 'strict')")
            cursor.execute("INSERT INTO product_category (id_category, name) VALUES (2, 'gradual')")

    # ---------- ТОВАРЫ ----------
    def get_all_products(self) -> pd.DataFrame:
        query = """
            SELECT p.id_product, p.name, pc.name as category,
                   p.purchase_price, p.sale_price, p.shelf_life_days
            FROM products p
            JOIN product_category pc ON p.id_category = pc.id_category
        """
        return pd.read_sql_query(query, self._get_connection())

    def add_product(self, name: str, category_id: int, purchase_price: float,
                    sale_price: float, shelf_life_days: int = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (name, id_category, purchase_price, sale_price, shelf_life_days)
                VALUES (?, ?, ?, ?, ?)
            """, (name, category_id, purchase_price, sale_price, shelf_life_days))
            return cursor.lastrowid

    def update_product(self, product_id: int, **kwargs):
        allowed = ['name', 'id_category', 'purchase_price', 'sale_price', 'shelf_life_days']
        updates = []
        values = []
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                updates.append(f"{k} = ?")
                values.append(v)
        if not updates:
            return
        values.append(product_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE products SET {', '.join(updates)} WHERE id_product = ?", values)
            conn.commit()

    def delete_product(self, product_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id_product = ?", (product_id,))
            conn.commit()

    def get_product_by_name(self, name: str) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                cols = [desc[0] for desc in cursor.description]
                return dict(zip(cols, row))
            return None

    def get_product_id_by_name(self, name: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_product FROM products WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None

    # ---------- ПОРЧА ----------
    def get_spoilage_rates(self, product_id: int) -> pd.DataFrame:
        return pd.read_sql_query(
            f"SELECT week_number, rate FROM product_spoilage_rates WHERE id_product = {product_id} ORDER BY week_number",
            self._get_connection()
        )

    def add_spoilage_rate(self, product_id: int, week_number: int, rate: float):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO product_spoilage_rates (id_product, week_number, rate)
                VALUES (?, ?, ?)
            """, (product_id, week_number, rate))
            conn.commit()

    def delete_spoilage_rate(self, product_id: int, week_number: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM product_spoilage_rates WHERE id_product = ? AND week_number = ?",
                         (product_id, week_number))
            conn.commit()

    # ---------- ЭКСПЕРИМЕНТЫ ----------
    def save_experiment(self, data: dict) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiments (
                    product_name, distribution, days, fifo_percent,
                    min_stock, purchase_price, sale_price,
                    delivery_type, delivery_frequency, delivery_days,
                    packing_type, box_size,
                    total_revenue, total_cost, total_spoilage_kg,
                    total_spoilage_money, profit, total_unmet_demand
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['product_name'], data['distribution'], data['days'],
                data.get('fifo_percent'),
                data['min_stock'], data['purchase_price'], data['sale_price'],
                data['delivery_type'], data.get('delivery_frequency'), data.get('delivery_days'),
                data['packing_type'], data.get('box_size', 1),
                data['total_revenue'], data['total_cost'], data['total_spoilage_kg'],
                data['total_spoilage_money'], data['profit'], data['total_unmet_demand']
            ))
            return cursor.lastrowid

    def get_all_experiments(self) -> pd.DataFrame:
        return pd.read_sql_query("SELECT * FROM experiments ORDER BY id_experiment DESC", self._get_connection())

    def experiment_exists(self, data: dict) -> bool:
        """Проверяет, существует ли эксперимент с такими же параметрами"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM experiments 
                WHERE product_name = ? AND distribution = ? AND days = ? 
                AND min_stock = ? AND purchase_price = ? AND sale_price = ?
            """, (
                data['product_name'], data['distribution'], data['days'],
                data['min_stock'], data['purchase_price'], data['sale_price']
            ))
            count = cursor.fetchone()[0]
            return count > 0
    