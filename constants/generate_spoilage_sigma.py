import random
import pandas as pd
import os
import sys

# Диапазон ожидаемой порчи: от 10 до 180 с шагом 2
values = range(10, 181, 2)  # 10, 12, 14, ..., 180
exp = 100  # количество экспериментов
n_trials = 1000  # количество испытаний в эксперименте

filename = "rezultaty.xlsx"

with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    for ozhidaemaya_porcha in values:
        data = []
        
        # Вероятность = ожидаемая порча / 1000
        p = ozhidaemaya_porcha / 1000
        
        for j in range(1, exp + 1):
            kol = 0  # счетчик "успехов"
            
            # Проводим 1000 испытаний
            for i in range(n_trials):
                r = random.random()
                if r <= p:
                    kol = kol + 1
            
            # Фактическая порча (в штуках, не в процентах)
            fakticheskaya_porcha = kol
            
            data.append({
                '№ эксперимента': j,
                'Ожидаемая порча': ozhidaemaya_porcha,
                'Фактическая порча': fakticheskaya_porcha
            })
        
        df = pd.DataFrame(data)
        sheet_name = str(ozhidaemaya_porcha)
        df.to_excel(writer, sheet_name=sheet_name, index=False)

# Открываем файл
if sys.platform.startswith('win'):
    os.startfile(filename)
elif sys.platform.startswith('darwin'):
    os.system(f'open {filename}')
else:
    os.system(f'xdg-open {filename}')
