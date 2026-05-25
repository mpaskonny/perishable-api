import os
import pandas as pd


class SpoilageSigmaLoader:
    """Загрузчик сигм для вариативности срока годности"""
    
    SIGMA_ROW = 6  # строка 7 = индекс 6
    SIGMA_COL = 5  # колонка F = индекс 5
    
    def __init__(self, excel_path="constants/spoilage_sigma.xlsx"):
        self.excel_path = excel_path
        self.sigma_cache = {}   # {shelf_life_days: sigma}
        self.available_days = []
        self._loaded = False
    
    def _load_from_excel(self):
        """Загружает сигмы из Excel (выполняется 1 раз)"""
        
        if not os.path.exists(self.excel_path):
            self._loaded = True
            return
        
        try:
            excel_file = pd.ExcelFile(self.excel_path)
            
            for sheet_name in excel_file.sheet_names:
                try:
                    shelf_life = int(sheet_name)
                    df = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)
                    sigma = df.iloc[self.SIGMA_ROW, self.SIGMA_COL]
                    
                    self.sigma_cache[shelf_life] = float(sigma)
                    self.available_days.append(shelf_life)
                    
                except ValueError:
                    continue
                except Exception:
                    continue
            
            self.available_days.sort()
            
        except Exception:
            pass
        
        self._loaded = True
    
    def _ensure_loaded(self):
        if not self._loaded:
            self._load_from_excel()
    
    def get_sigma(self, shelf_life_days: int) -> float:
        """
        Возвращает сигму для заданного срока годности.
        Если точного значения нет, берёт ближайшее.
        """
        self._ensure_loaded()
        
        if not self.sigma_cache:
            return shelf_life_days * 0.1  # теоретическая сигма (10% от срока)
        
        # Точное совпадение
        if shelf_life_days in self.sigma_cache:
            return self.sigma_cache[shelf_life_days]
        
        # Ближайшее значение
        closest = min(self.available_days, key=lambda x: abs(x - shelf_life_days))
        return self.sigma_cache[closest]
    
    def get_stats(self):
        """Возвращает статистику загруженных сигм (для отладки)"""
        self._ensure_loaded()
        return {
            'loaded': len(self.sigma_cache),
            'available_days': self.available_days,
            'sigmas': self.sigma_cache
        }


# ========== ГЛОБАЛЬНЫЙ ОДИНОЧКА ==========
_spoilage_sigma_loader = None

def get_spoilage_sigma_loader() -> SpoilageSigmaLoader:
    """Возвращает глобальный экземпляр SpoilageSigmaLoader"""
    global _spoilage_sigma_loader
    if _spoilage_sigma_loader is None:
        _spoilage_sigma_loader = SpoilageSigmaLoader()
    return _spoilage_sigma_loader
