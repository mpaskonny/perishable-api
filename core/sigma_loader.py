"""
sigma_loader.py - Загрузка эмпирических сигм для нормального спроса

Файл: constants/demand_sigma.xlsx
Листы: названия = спрос (10, 20, 30...)
Ячейка с сигмой: F7 (фиксированная)

Сигмы рассчитаны по реальным данным (100 экспериментов по 1000 попыток)
"""

import os
import pandas as pd
from pathlib import Path


class SigmaLoader:
    """
    Загрузчик сигм из Excel-файла.
    При первом обращении читает файл и сохраняет все сигмы в словарь.
    Далее работает только с кэшем (ленивая загрузка + синглтон).
    """
    
    # Фиксированная ячейка для сигмы (F7)
    SIGMA_ROW = 6  # 0-индексация: строка 7 = индекс 6
    SIGMA_COL = 5  # 0-индексация: колонка F = индекс 5
    
    def __init__(self, excel_path="constants/demand_sigma.xlsx"):
        self.excel_path = excel_path
        self.sigma_cache = {}       # {спрос: сигма}
        self.available_demands = [] # список спросов для поиска ближайшего
        self._loaded = False        # флаг загрузки
    
    def _load_from_excel(self):
        """Загружает сигмы из Excel (выполняется 1 раз)"""
        
        if not os.path.exists(self.excel_path):
            # Файла нет - будем использовать теоретическую сигму
            self._loaded = True
            return
        
        try:
            excel_file = pd.ExcelFile(self.excel_path)
            
            for sheet_name in excel_file.sheet_names:
                try:
                    # Название листа = спрос (должно быть числом)
                    demand = int(sheet_name)
                    
                    df = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)
                    sigma = df.iloc[self.SIGMA_ROW, self.SIGMA_COL]
                    
                    self.sigma_cache[demand] = float(sigma)
                    self.available_demands.append(demand)
                    
                except ValueError:
                    # Лист с нечисловым названием — пропускаем
                    continue
                except Exception:
                    continue
            
            self.available_demands.sort()
            
        except Exception:
            pass
        
        self._loaded = True
    
    def _ensure_loaded(self):
        """Гарантирует, что данные загружены (ленивая загрузка)"""
        if not self._loaded:
            self._load_from_excel()
    
    def get_sigma(self, base_demand: float) -> float:
        """
        Возвращает сигму для заданного базового спроса.
        - Если данные из Excel есть → берёт из кэша (ближайшее значение)
        - Если нет файла → теоретическая сигма (15% от спроса)
        """
        self._ensure_loaded()
        
        # Если кэш пуст (нет файла или ошибка) → теоретическая сигма
        if not self.sigma_cache:
            return base_demand * 0.15
        
        # Округляем спрос до целого (так как листы с целыми числами)
        demand_int = int(round(base_demand))
        
        # Точное совпадение
        if demand_int in self.sigma_cache:
            return self.sigma_cache[demand_int]
        
        # Поиск ближайшего
        closest = min(self.available_demands, key=lambda x: abs(x - demand_int))
        return self.sigma_cache[closest]
    
    def get_stats(self):
        """Возвращает статистику загруженных сигм (для отладки)"""
        self._ensure_loaded()
        return {
            'loaded': len(self.sigma_cache),
            'demands': self.available_demands,
            'sigmas': self.sigma_cache
        }


# ========== ГЛОБАЛЬНЫЙ ОДИНОЧКА ==========
_sigma_loader = None

def get_sigma_loader() -> SigmaLoader:
    """Возвращает глобальный экземпляр SigmaLoader (ленивая инициализация)"""
    global _sigma_loader
    if _sigma_loader is None:
        _sigma_loader = SigmaLoader()
    return _sigma_loader
