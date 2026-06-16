"""
data_loader.py - Загрузка реальных данных из Excel

Отвечает за импорт исторических данных о продажах.
Пользователь скачивает шаблон, заполняет, загружает - программа читает.
"""

import pandas as pd
import os
from datetime import datetime
from typing import Dict, Optional, List


class DemandDataLoader:
    """Загрузчик реальных данных о спросе из Excel"""
    
    @staticmethod
    def load_from_excel(file_path: str) -> Dict[datetime.date, float]:
        """
        Загружает данные из Excel-файла.
        
        Ожидаемая структура:
        - Колонка 'Дата' (или 'Date') с датами
        - Колонка 'Спрос' (или 'Demand') со значениями спроса
        
        Returns:
            Словарь {дата: спрос}
        """
        df = pd.read_excel(file_path)
        
        # Ищем колонку с датами (пользователь мог назвать по-разному)
        date_col = None
        for col in ['Дата', 'Date', 'ДАТА', 'date']:
            if col in df.columns:
                date_col = col
                break
        
        # Ищем колонку со спросом
        demand_col = None
        for col in ['Спрос', 'Demand', 'demand', 'СПРОС']:
            if col in df.columns:
                demand_col = col
                break
        
        if date_col is None or demand_col is None:
            raise ValueError("Excel должен содержать колонки 'Дата' и 'Спрос'")
        
        # Приводим даты к единому формату
        df[date_col] = pd.to_datetime(df[date_col])
        
        # Собираем словарь для быстрого доступа по дате
        demand_dict = {}
        for _, row in df.iterrows():
            date = row[date_col].date()
            demand = float(row[demand_col])
            demand_dict[date] = demand
        
        return demand_dict
    
    
    @staticmethod
    def create_template(file_path: str = "demand_template.xlsx"):
        """Создаёт шаблон Excel для заполнения пользователем"""
        template = pd.DataFrame({
            'Дата': [datetime.now().date()],
            'Спрос': [100]
        })
        template.to_excel(file_path, index=False)
        return file_path
