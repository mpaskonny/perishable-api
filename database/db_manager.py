import sqlite3
import pandas as pd
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path="database/perishable.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Создание таблиц, если их нет"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Тип категории товара
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_category (
                    id_category INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            
            # Тип поставок (справочник)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS delivery_type (
                    id_type INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            
            # Тип упаковки (справочник)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packing_type (
                    id_pack_type INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            
            # Основные товары
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id_product INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_category INTEGER REFERENCES product_category(id_category),
                    name TEXT NOT NULL UNIQUE,
                    purchase_price REAL NOT NULL,
                    sale_price REAL NOT NULL,
                    min_stock REAL NOT NULL DEFAULT 300,
                    shelf_life_days INTEGER
                )
            """)
            
            # Поставщики
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    id_supplier INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    id_type INTEGER REFERENCES delivery_type(id_type),
                    id_pack_type INTEGER REFERENCES packing_type(id_pack_type),
                    box_size INTEGER DEFAULT 1,
                    delivery_interval INTEGER,
                    delivery_days TEXT,
                    description TEXT
                )
            """)
            
            # Связь товаров и поставщиков (многие ко многим)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_suppliers (
                    id_product INTEGER REFERENCES products(id_product) ON DELETE CASCADE,
                    id_supplier INTEGER REFERENCES suppliers(id_supplier) ON DELETE CASCADE,
                    PRIMARY KEY (id_product, id_supplier)
                )
            """)
            
            # Параметры порчи по неделям
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_spoilage_rates (
                    id_product INTEGER REFERENCES products(id_product),
                    week_number INTEGER NOT NULL,
                    rate REAL NOT NULL,
                    PRIMARY KEY (id_product, week_number)
                )
            """)
            
            # Заполнение начальных данных
            self._init_default_data(cursor)
            
            conn.commit()
    
    def _init_default_data(self, cursor):
        """Заполнение справочников начальными данными"""
        
        # Категории товаров
        cursor.execute("SELECT COUNT(*) FROM product_category")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO product_category (id_category, name) VALUES (1, 'strict')")
            cursor.execute("INSERT INTO product_category (id_category, name) VALUES (2, 'gradual')")
        
        # Типы поставок
        cursor.execute("SELECT COUNT(*) FROM delivery_type")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO delivery_type (id_type, name) VALUES (1, 'periodic')")
            cursor.execute("INSERT INTO delivery_type (id_type, name) VALUES (2, 'days_of_week')")
        
        # Типы упаковки
        cursor.execute("SELECT COUNT(*) FROM packing_type")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO packing_type (id_pack_type, name) VALUES (1, 'unit')")
            cursor.execute("INSERT INTO packing_type (id_pack_type, name) VALUES (2, 'box')")
    
    # ========== РАБОТА С ТОВАРАМИ ==========
    
    def get_all_products(self) -> pd.DataFrame:
        query = """
            SELECT p.id_product, p.name, pc.name as category, 
                   p.purchase_price, p.sale_price, p.min_stock, p.shelf_life_days
            FROM products p
            JOIN product_category pc ON p.id_category = pc.id_category
        """
        return pd.read_sql_query(query, self._get_connection())
    
    def get_product_by_id(self, product_id: int) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id_product = ?", (product_id,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def add_product(self, name: str, category_id: int, purchase_price: float, 
                    sale_price: float, min_stock: float, shelf_life_days: int = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (name, id_category, purchase_price, sale_price, 
                                      min_stock, shelf_life_days)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, category_id, purchase_price, sale_price, min_stock, shelf_life_days))
            return cursor.lastrowid
    
    def update_product(self, product_id: int, **kwargs):
        allowed_fields = ['name', 'id_category', 'purchase_price', 'sale_price', 
                          'min_stock', 'shelf_life_days']
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                updates.append(f"{key} = ?")
                values.append(value)
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
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def get_product_id_by_name(self, name: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_product FROM products WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    # ========== РАБОТА С ПОСТАВЩИКАМИ ==========
    
    def get_all_suppliers(self) -> pd.DataFrame:
        query = """
            SELECT s.id_supplier, s.name, dt.name as delivery_type, 
                   pt.name as packing_type, s.box_size,
                   s.delivery_interval, s.delivery_days, s.description
            FROM suppliers s
            JOIN delivery_type dt ON s.id_type = dt.id_type
            JOIN packing_type pt ON s.id_pack_type = pt.id_pack_type
            ORDER BY s.name
        """
        return pd.read_sql_query(query, self._get_connection())
    
    def get_supplier_by_id(self, supplier_id: int) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM suppliers WHERE id_supplier = ?", (supplier_id,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def get_supplier_by_name(self, name: str) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM suppliers WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def get_supplier_id_by_name(self, name: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_supplier FROM suppliers WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def add_supplier(self, name: str, id_type: int, id_pack_type: int, 
                     box_size: int = 1, delivery_interval: int = None, 
                     delivery_days: str = None, description: str = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO suppliers (name, id_type, id_pack_type, box_size, 
                                       delivery_interval, delivery_days, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, id_type, id_pack_type, box_size, 
                  delivery_interval, delivery_days, description))
            return cursor.lastrowid
    
    def update_supplier(self, supplier_id: int, **kwargs):
        allowed_fields = ['name', 'id_type', 'id_pack_type', 'box_size', 
                          'delivery_interval', 'delivery_days', 'description']
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                updates.append(f"{key} = ?")
                values.append(value)
        if not updates:
            return
        values.append(supplier_id)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE suppliers SET {', '.join(updates)} WHERE id_supplier = ?", values)
            conn.commit()
    
    def delete_supplier(self, supplier_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM suppliers WHERE id_supplier = ?", (supplier_id,))
            conn.commit()
    
    # ========== РАБОТА СО СВЯЗЯМИ ТОВАРОВ И ПОСТАВЩИКОВ ==========
    
    def get_product_suppliers(self, product_id: int) -> pd.DataFrame:
        query = f"""
            SELECT s.id_supplier, s.name, dt.name as delivery_type, 
                   pt.name as packing_type, s.box_size,
                   s.delivery_interval, s.delivery_days
            FROM product_suppliers ps
            JOIN suppliers s ON ps.id_supplier = s.id_supplier
            JOIN delivery_type dt ON s.id_type = dt.id_type
            JOIN packing_type pt ON s.id_pack_type = pt.id_pack_type
            WHERE ps.id_product = {product_id}
            ORDER BY s.name
        """
        return pd.read_sql_query(query, self._get_connection())
    
    def add_product_supplier(self, product_id: int, supplier_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO product_suppliers (id_product, id_supplier)
                VALUES (?, ?)
            """, (product_id, supplier_id))
            conn.commit()
    
    def delete_product_supplier(self, product_id: int, supplier_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM product_suppliers 
                WHERE id_product = ? AND id_supplier = ?
            """, (product_id, supplier_id))
            conn.commit()
    
    # ========== РАБОТА С ПАРАМЕТРАМИ ПОРЧИ ==========
    
    def get_spoilage_rates(self, product_id: int) -> pd.DataFrame:
        query = f"""
            SELECT week_number, rate FROM product_spoilage_rates 
            WHERE id_product = {product_id}
            ORDER BY week_number
        """
        return pd.read_sql_query(query, self._get_connection())
    
    def add_spoilage_rate(self, product_id: int, week_number: int, rate: float):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO product_spoilage_rates (id_product, week_number, rate)
                VALUES (?, ?, ?)
            """, (product_id, week_number, rate))
            conn.commit()
    
    def delete_spoilage_rate(self, product_id: int, week_number: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM product_spoilage_rates 
                WHERE id_product = ? AND week_number = ?
            """, (product_id, week_number))
            conn.commit()
