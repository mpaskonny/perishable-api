import random
import pandas as pd
import os
import sys

# Диапазон значений для первой группы: от 100 до 50 с шагом -5
# Вторая группа = 100 - первая группа
exp = 100  # количество экспериментов

filename = "rezultaty_fifo_lifo.xlsx"

with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    for p1_percent in range(100, 49, -5):  # 100, 95, 90, ..., 50
        p2_percent = 100 - p1_percent  # 0, 5, 10, ..., 50
        
        # Преобразуем в вероятности (доли)
        p1 = p1_percent / 100
        p2 = p2_percent / 100
        
        data = []
        
        for j in range(1, exp + 1):
            kol1 = 0
            kol2 = 0
            
            for i in range(1000):
                r = random.random()
                if r <= p1:
                    kol1 = kol1 + 1
                else:
                    kol2 = kol2 + 1
            
            # Добавляем запись
            data.append({
                '№ эксперимента': j,
                'Ожидаемое FIFO/LIFO': f"{p1_percent}/{p2_percent}",
                'FIFO фактическая': round(kol1 / 10, 1),
                'LIFO фактическая': round(kol2 / 10, 1)
            })
        
        df = pd.DataFrame(data)
        sheet_name = f"{p1_percent}_{p2_percent}"
        df.to_excel(writer, sheet_name=sheet_name, index=False)

# Открываем файл
if sys.platform.startswith('win'):
    os.startfile(filename)
elif sys.platform.startswith('darwin'):
    os.system(f'open {filename}')
else:
    os.system(f'xdg-open {filename}')
