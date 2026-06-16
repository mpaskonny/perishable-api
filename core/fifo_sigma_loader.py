"""
fifo_sigma_loader.py - Загрузка эмпирических сигм для FIFO/LIFO

Сигмы рассчитаны экспериментально (100 экспериментов по 1000 попыток)
и сохранены в Excel. Файл: constants/fifo_lifo_sigma.xlsx
Листы имеют вид "90_10" (FIFO 90%, LIFO 10%)
"""

import os
import pandas as pd
import re


class FIFOSigmaLoader:
    """Загрузчик сигм для FIFO/LIFO из Excel-файла"""
    
    # Фиксированные ячейки в Excel, где лежат сигмы
    SIGMA_FIFO_ROW = 6  # строка 7 (0-индексация)
    SIGMA_FIFO_COL = 5  # колонка F
    SIGMA_LIFO_ROW = 6
    SIGMA_LIFO_COL = 6  # колонка G
    
    def __init__(self, excel_path="constants/fifo_lifo_sigma.xlsx"):
        self.excel_path = excel_path
        self.sigma_fifo_cache = {}   # {fifo_percent: sigma_fifo}
        self.sigma_lifo_cache = {}   # {fifo_percent: sigma_lifo}
        self.available_fifos = []
        self._loaded = False
    
    def _parse_sheet_name(self, sheet_name: str) -> int:
        """Извлекает процент FIFO из названия листа (например '90_10' → 90)"""
        match = re.match(r"(\d+)_\d+", sheet_name)
        if match:
            return int(match.group(1))
        return None
    
    def _load_from_excel(self):
        """Загружает сигмы из Excel (выполняется 1 раз, результат кэшируется)"""
        
        if not os.path.exists(self.excel_path):
            print(f"⚠️ Файл {self.excel_path} не найден")
            self._loaded = True
            return
        
        try:
            excel_file = pd.ExcelFile(self.excel_path)
            
            for sheet_name in excel_file.sheet_names:
                fifo_percent = self._parse_sheet_name(sheet_name)
                
                if fifo_percent is None:
                    continue
                
                try:
                    df = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)
                    
                    sigma_fifo = df.iloc[self.SIGMA_FIFO_ROW, self.SIGMA_FIFO_COL]
                    sigma_lifo = df.iloc[self.SIGMA_LIFO_ROW, self.SIGMA_LIFO_COL]
                    
                    self.sigma_fifo_cache[fifo_percent] = float(sigma_fifo)
                    self.sigma_lifo_cache[fifo_percent] = float(sigma_lifo)
                    self.available_fifos.append(fifo_percent)
                    
                except Exception as e:
                    print(f"⚠️ Ошибка чтения листа {sheet_name}: {e}")
                    continue
            
            self.available_fifos.sort()
            
        except Exception as e:
            print(f"❌ Ошибка загрузки Excel: {e}")
        
        self._loaded = True
    
    def _ensure_loaded(self):
        if not self._loaded:
            self._load_from_excel()
    
    def get_sigmas(self, fifo_percent: int) -> tuple:
        """
        Возвращает (sigma_fifo, sigma_lifo) для заданного процента FIFO.
        Если точного нет - ищем симметричный или ближайший.
        """
        self._ensure_loaded()
        
        # Если кэш пуст (нет файла) - возвращаем теоретическое значение
        if not self.sigma_fifo_cache:
            return 1.51, 1.51
        
        # 1. Точное совпадение
        if fifo_percent in self.sigma_fifo_cache:
            return self.sigma_fifo_cache[fifo_percent], self.sigma_lifo_cache[fifo_percent]
        
        # 2. Симметричный поиск (90% FIFO → берём сигмы от 10% FIFO, меняя местами)
        symmetric = 100 - fifo_percent
        if symmetric in self.sigma_fifo_cache:
            return self.sigma_lifo_cache[symmetric], self.sigma_fifo_cache[symmetric]
        
        # 3. Ближайшее значение
        closest = min(self.available_fifos, key=lambda x: abs(x - fifo_percent))
        return self.sigma_fifo_cache[closest], self.sigma_lifo_cache[closest]
    
    def get_stats(self):
        """Для отладки - возвращает статистику загруженных сигм"""
        self._ensure_loaded()
        return {
            'loaded': len(self.sigma_fifo_cache),
            'fifos': self.available_fifos,
            'sigma_fifo': self.sigma_fifo_cache,
            'sigma_lifo': self.sigma_lifo_cache
        }


# ========== ГЛОБАЛЬНЫЙ ОДИНОЧКА ==========
# Чтобы не читать Excel при каждом вызове, используем синглтон
_fifo_sigma_loader = None

def get_fifo_sigma_loader() -> FIFOSigmaLoader:
    """Возвращает глобальный экземпляр (ленивая инициализация)"""
    global _fifo_sigma_loader
    if _fifo_sigma_loader is None:
        _fifo_sigma_loader = FIFOSigmaLoader()
    return _fifo_sigma_loader
