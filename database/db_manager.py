import sqlite3
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path="database/perishable.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Инициализация БД с новой схемой"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, существует ли старая таблица experiments с неправильной структурой
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='experiments'")
            old_table_exists = cursor.fetchone()
            
            if old_table_exists:
                # Проверяем структуру старой таблицы
                cursor.execute("PRAGMA table_info(experiments)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Если нет колонки id_setting, значит старая структура
                if 'id_setting' not in columns:
                    print("⚠️ Обнаружена старая структура БД. Пересоздание таблиц...")
                    
                    # Удаляем старые таблицы
                    cursor.execute("DROP TABLE IF EXISTS experiment_daily_history")
                    cursor.execute("DROP TABLE IF EXISTS experiments")
                    cursor.execute("DROP TABLE IF EXISTS experiment_settings")
                    
                    # Сбрасываем последовательности
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name='experiments'")
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name='experiment_settings'")
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name='experiment_daily_history'")
                    
                    print("✅ Старые таблицы удалены. Создаются новые...")

            # 1. Категории товаров
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_category (
                    id_category INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                )
            """)

            # 2. Товары
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id_product INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    purchase_price REAL NOT NULL,
                    sale_price REAL NOT NULL,
                    shelf_life_days INTEGER NOT NULL,
                    base_demand REAL NOT NULL,
                    id_category INTEGER NOT NULL,
                    FOREIGN KEY (id_category) REFERENCES product_category(id_category)
                )
            """)

            # 3. Настройки эксперимента
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_settings (
                    id_setting INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_product INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    purchase_price REAL NOT NULL,
                    sale_price REAL NOT NULL,
                    shelf_life_days INTEGER NOT NULL,
                    base_demand REAL NOT NULL,
                    product_category TEXT NOT NULL,
                    distribution TEXT NOT NULL,
                    demand_min REAL,
                    demand_max REAL,
                    demand_sigma REAL,
                    weekday_factors TEXT,
                    spoilage_type TEXT NOT NULL,
                    power_p REAL,
                    logistic_k REAL,
                    strategy_type TEXT NOT NULL,
                    delivery_type TEXT NOT NULL,
                    box_size INTEGER DEFAULT 0,
                    fixed_quantity REAL,
                    schedule_type TEXT,
                    delivery_frequency INTEGER,
                    delivery_days TEXT,
                    reorder_point REAL,
                    max_stock REAL,
                    min_stock REAL,
                    delivery_cost_type TEXT,
                    delivery_fixed_cost REAL DEFAULT 0,
                    delivery_rate_cost REAL DEFAULT 0,
                    fifo_percent REAL,
                    utilization_price REAL DEFAULT 0,
                    days INTEGER NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    num_simulations INTEGER DEFAULT 1,
                    random_seed INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_product) REFERENCES products(id_product) ON DELETE RESTRICT
                )
            """)

            # 4. Результаты экспериментов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id_experiment INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_setting INTEGER NOT NULL,
                    total_revenue REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    total_purchase_cost REAL,
                    total_delivery_cost REAL,
                    total_utilization_cost REAL,
                    total_spoilage_kg REAL NOT NULL,
                    total_spoilage_money REAL NOT NULL,
                    profit REAL NOT NULL,
                    avg_stock REAL DEFAULT 0,
                    total_unmet_demand REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_setting) REFERENCES experiment_settings(id_setting) ON DELETE CASCADE
                )
            """)

            # 5. Детальная история по дням
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiment_daily_history (
                    id_daily INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_experiment INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    demand REAL NOT NULL,
                    start_stock REAL NOT NULL,
                    sales REAL NOT NULL,
                    spoilage_kg REAL NOT NULL,
                    order_qty REAL NOT NULL,
                    revenue REAL NOT NULL,
                    purchase_cost REAL NOT NULL,
                    end_stock REAL NOT NULL,
                    unmet_demand REAL DEFAULT 0,
                    fifo_percent REAL,
                    lifo_percent REAL,
                    fifo_sales REAL,
                    lifo_sales REAL,
                    stock_week1 REAL,
                    stock_week2 REAL,
                    stock_week3 REAL,
                    utilization_cost REAL DEFAULT 0,
                    batch_1_stock REAL,
                    batch_2_stock REAL,
                    batch_3_stock REAL,
                    batch_4_stock REAL,
                    batch_5_stock REAL,
                    FOREIGN KEY (id_experiment) REFERENCES experiments(id_experiment) ON DELETE CASCADE
                )
            """)

            # Индексы (проверяем существование таблиц перед созданием)
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_experiments_id_setting ON experiments(id_setting)")
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_id_experiment ON experiment_daily_history(id_experiment)")
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_day ON experiment_daily_history(id_experiment, day)")
            except sqlite3.OperationalError:
                pass

            # Начальные данные (категории)
            cursor.execute("SELECT COUNT(*) FROM product_category")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO product_category (id_category, name) VALUES (1, 'strict')")
                cursor.execute("INSERT INTO product_category (id_category, name) VALUES (2, 'gradual')")

            conn.commit()

    # ========== ТОВАРЫ ==========
    def get_all_products(self) -> pd.DataFrame:
        query = """
            SELECT p.id_product, p.name, pc.name as category,
                   p.purchase_price, p.sale_price, p.shelf_life_days,
                   p.base_demand
            FROM products p
            JOIN product_category pc ON p.id_category = pc.id_category
        """
        return pd.read_sql_query(query, self._get_connection())

    def add_product(self, name: str, category_id: int, purchase_price: float,
                    sale_price: float, shelf_life_days: int, base_demand: float) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (name, id_category, purchase_price, sale_price, 
                                     shelf_life_days, base_demand)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, category_id, purchase_price, sale_price, 
                  shelf_life_days, base_demand))
            return cursor.lastrowid

    def update_product(self, product_id: int, **kwargs):
        allowed = ['name', 'id_category', 'purchase_price', 'sale_price', 
                   'shelf_life_days', 'base_demand']
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
            # Проверяем, есть ли эксперименты
            cursor.execute("""
                SELECT COUNT(*) FROM experiment_settings 
                WHERE id_product = ?
            """, (product_id,))
            count = cursor.fetchone()[0]
            if count > 0:
                raise Exception(f"Невозможно удалить товар: есть {count} сохранённых экспериментов")
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

    # ========== НАСТРОЙКИ ЭКСПЕРИМЕНТА ==========
    def save_settings(self, settings: Dict[str, Any]) -> int:
        """Сохраняет настройки эксперимента, возвращает id_setting"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Преобразуем JSON-поля
            weekday_factors = json.dumps(settings.get('weekday_factors', [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]))
            delivery_days = json.dumps(settings.get('delivery_days', []))
            
            cursor.execute("""
                INSERT INTO experiment_settings (
                    id_product, product_name, purchase_price, sale_price,
                    shelf_life_days, base_demand, product_category,
                    distribution, demand_min, demand_max, demand_sigma,
                    weekday_factors, spoilage_type, power_p, logistic_k,
                    strategy_type, delivery_type, box_size, fixed_quantity,
                    schedule_type, delivery_frequency, delivery_days,
                    reorder_point, max_stock, min_stock,
                    delivery_cost_type, delivery_fixed_cost, delivery_rate_cost,
                    fifo_percent, utilization_price,
                    days, start_date, end_date,
                    num_simulations, random_seed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                settings.get('id_product'),
                settings.get('product_name'),
                settings.get('purchase_price'),
                settings.get('sale_price'),
                settings.get('shelf_life_days'),
                settings.get('base_demand'),
                settings.get('product_category'),
                settings.get('distribution'),
                settings.get('demand_min'),
                settings.get('demand_max'),
                settings.get('demand_sigma'),
                weekday_factors,
                settings.get('spoilage_type'),
                settings.get('power_p'),
                settings.get('logistic_k'),
                settings.get('strategy_type'),
                settings.get('delivery_type'),
                settings.get('box_size', 0),
                settings.get('fixed_quantity'),
                settings.get('schedule_type'),
                settings.get('delivery_frequency'),
                delivery_days,
                settings.get('reorder_point'),
                settings.get('max_stock'),
                settings.get('min_stock'),
                settings.get('delivery_cost_type'),
                settings.get('delivery_fixed_cost', 0),
                settings.get('delivery_rate_cost', 0),
                settings.get('fifo_percent'),
                settings.get('utilization_price', 0),
                settings.get('days'),
                settings.get('start_date'),
                settings.get('end_date'),
                settings.get('num_simulations', 1),
                settings.get('random_seed')
            ))
            return cursor.lastrowid

    def get_settings_by_id(self, id_setting: int) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiment_settings WHERE id_setting = ?", (id_setting,))
            row = cursor.fetchone()
            if row:
                cols = [desc[0] for desc in cursor.description]
                settings = dict(zip(cols, row))
                # Восстанавливаем JSON
                if settings.get('weekday_factors'):
                    try:
                        settings['weekday_factors'] = json.loads(settings['weekday_factors'])
                    except:
                        settings['weekday_factors'] = [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]
                if settings.get('delivery_days'):
                    try:
                        settings['delivery_days'] = json.loads(settings['delivery_days'])
                    except:
                        settings['delivery_days'] = []
                return settings
            return None

    # ========== ЭКСПЕРИМЕНТЫ (МЕТРИКИ) ==========
    def save_experiment(self, experiment: Dict[str, Any]) -> int:
        """Сохраняет метрики эксперимента, возвращает id_experiment"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiments (
                    id_setting, total_revenue, total_cost, total_purchase_cost,
                    total_delivery_cost, total_utilization_cost, total_spoilage_kg,
                    total_spoilage_money, profit, avg_stock, total_unmet_demand
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment.get('id_setting'),
                experiment.get('total_revenue'),
                experiment.get('total_cost'),
                experiment.get('total_purchase_cost'),
                experiment.get('total_delivery_cost'),
                experiment.get('total_utilization_cost'),
                experiment.get('total_spoilage_kg'),
                experiment.get('total_spoilage_money'),
                experiment.get('profit'),
                experiment.get('avg_stock', 0),
                experiment.get('total_unmet_demand', 0)
            ))
            return cursor.lastrowid

    def get_experiment_by_id(self, id_experiment: int) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiments WHERE id_experiment = ?", (id_experiment,))
            row = cursor.fetchone()
            if row:
                cols = [desc[0] for desc in cursor.description]
                return dict(zip(cols, row))
            return None

    def get_all_experiments(self) -> pd.DataFrame:
        """Получает все эксперименты с нужными колонками для отображения"""
        query = """
            SELECT 
                e.id_experiment,
                s.product_name,
                s.strategy_type,
                e.profit,
                e.total_revenue,
                e.total_cost,
                e.total_spoilage_kg,
                e.total_unmet_demand,
                e.avg_stock,
                e.created_at
            FROM experiments e
            JOIN experiment_settings s ON e.id_setting = s.id_setting
            ORDER BY e.id_experiment DESC
        """
        return pd.read_sql_query(query, self._get_connection())

    # ========== ДЕТАЛЬНАЯ ИСТОРИЯ ПО ДНЯМ ==========
    def save_daily_history_batch(self, id_experiment: int, daily_history: List[Dict]):
        """Пакетное сохранение истории по дням"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for day in daily_history:
                cursor.execute("""
                    INSERT INTO experiment_daily_history (
                        id_experiment, day, date, demand, start_stock, sales,
                        spoilage_kg, order_qty, revenue, purchase_cost, end_stock,
                        unmet_demand, fifo_percent, lifo_percent, fifo_sales, lifo_sales,
                        stock_week1, stock_week2, stock_week3, utilization_cost,
                        batch_1_stock, batch_2_stock, batch_3_stock, batch_4_stock, batch_5_stock
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    id_experiment,
                    day.get('day'),
                    day.get('date'),
                    day.get('demand'),
                    day.get('start_stock'),
                    day.get('sales'),
                    day.get('spoilage_kg', 0),
                    day.get('order', 0),
                    day.get('revenue'),
                    day.get('purchase_cost'),
                    day.get('end_stock'),
                    day.get('unmet_demand', 0),
                    day.get('fifo_percent'),
                    day.get('lifo_percent'),
                    day.get('fifo_sales'),
                    day.get('lifo_sales'),
                    day.get('stock_week1'),
                    day.get('stock_week2'),
                    day.get('stock_week3'),
                    day.get('utilization_cost', 0),
                    day.get('batch_1_stock'),
                    day.get('batch_2_stock'),
                    day.get('batch_3_stock'),
                    day.get('batch_4_stock'),
                    day.get('batch_5_stock')
                ))
            conn.commit()

    def get_daily_history(self, id_experiment: int) -> pd.DataFrame:
        query = """
            SELECT day, date, demand, start_stock, sales, spoilage_kg,
                   order_qty, revenue, purchase_cost, end_stock, unmet_demand,
                   fifo_percent, lifo_percent, stock_week1, stock_week2, stock_week3
            FROM experiment_daily_history
            WHERE id_experiment = ?
            ORDER BY day
        """
        return pd.read_sql_query(query, self._get_connection(), params=(id_experiment,))

    # ========== ПОЛНАЯ ВЫГРУЗКА ЭКСПЕРИМЕНТА ==========
    def get_full_experiment_data(self, id_experiment: int) -> Optional[Dict]:
        """Возвращает все данные эксперимента для выгрузки в Excel"""
        experiment = self.get_experiment_by_id(id_experiment)
        if not experiment:
            return None
        
        settings = self.get_settings_by_id(experiment['id_setting'])
        daily_history = self.get_daily_history(id_experiment)
        
        return {
            'experiment': experiment,
            'settings': settings,
            'daily_history': daily_history
        }

    def clear_all_experiments(self):
        """Удаляет ВСЕ эксперименты (для администрирования)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM experiment_daily_history")
            cursor.execute("DELETE FROM experiments")
            cursor.execute("DELETE FROM experiment_settings")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='experiments'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='experiment_settings'")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='experiment_daily_history'")
            conn.commit()

    def delete_experiment(self, id_experiment: int):
        """Удаляет эксперимент и все связанные данные"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Получаем id_setting
            cursor.execute("SELECT id_setting FROM experiments WHERE id_experiment = ?", (id_experiment,))
            row = cursor.fetchone()
            if row:
                id_setting = row[0]
                # Удаляем историю дней
                cursor.execute("DELETE FROM experiment_daily_history WHERE id_experiment = ?", (id_experiment,))
                # Удаляем эксперимент
                cursor.execute("DELETE FROM experiments WHERE id_experiment = ?", (id_experiment,))
                # Проверяем, остались ли эксперименты с этими настройками
                cursor.execute("SELECT COUNT(*) FROM experiments WHERE id_setting = ?", (id_setting,))
                count = cursor.fetchone()[0]
                if count == 0:
                    cursor.execute("DELETE FROM experiment_settings WHERE id_setting = ?", (id_setting,))
            conn.commit()
