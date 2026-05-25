import random
import pandas as pd
import os
import sys

# Диапазон ожидаемого спроса: от 10 до 1000 с шагом 10
values = range(10, 1010, 10)
exp = 100  # количество экспериментов
n_trials = 1000  # количество испытаний в эксперименте

filename = "rezultaty.xlsx"

with pd.ExcelWriter(filename, engine='openpyxl') as writer:
    for ozhidaemyy_spros in values:
        data = []
        
        # Вероятность = ожидаемый спрос / 1000
        p = ozhidaemyy_spros / 1000
        
        for j in range(1, exp + 1):
            kol = 0  # счетчик "успехов"
            
            # Проводим 1000 испытаний
            for i in range(n_trials):
                r = random.random()
                if r <= p:
                    kol = kol + 1
            
            # Фактический спрос (в штуках, не в процентах)
            fakticheskiy_spros = kol
            
            data.append({
                '№ эксперимента': j,
                'Ожидаемый спрос': ozhidaemyy_spros,
                'Фактический спрос': fakticheskiy_spros
            })
        
        df = pd.DataFrame(data)
        sheet_name = str(ozhidaemyy_spros)
        df.to_excel(writer, sheet_name=sheet_name, index=False)

# Открываем файл
if sys.platform.startswith('win'):
    os.startfile(filename)
elif sys.platform.startswith('darwin'):
    os.system(f'open {filename}')
else:
    os.system(f'xdg-open {filename}')
