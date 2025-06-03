import streamlit as st             
import pandas as pd                   
import matplotlib.pyplot as plt       
import seaborn as sns                
import os                            
import datetime                      
import urllib.request                
import requests                       

#Отримуємо шлях до директорії, де розміщено скрипт
script_dir = os.path.dirname(os.path.abspath(__file__))
#Формуємо шлях до папки для збереження файлів з VHI-даними
vhi_folder = os.path.join(script_dir, 'vhi')

area_id_to_name = {
    22: 'Вінницька', 24: 'Волинська', 23: 'Дніпропетровська', 25: 'Донецька', 3: 'Житомирська',
    4: 'Закарпатська', 8: 'Запорізька', 19: 'Івано-Франківська', 20: 'Кіровоградська', 21: 'Київська',
    9: 'Луганська', 10: 'Львівська', 11: 'Миколаївська', 12: 'Одеська', 13: 'Полтавська', 15: 'Рівенська',
    14: 'Сумська', 16: 'Тернопільська', 17: 'Харківська', 18: 'Херсонська', 6: 'Хмельницька',
    1: 'Черкаська', 2: 'Чернівецька', 7: 'Чернігівська', 5: 'Республіка Крим'
}

#Зберігаємо список упорядкованих назв областей
ordered_regions = list(area_id_to_name.values())

df_all_path = os.path.join(vhi_folder, 'df_all.csv')

if os.path.exists(df_all_path):
    df_all = pd.read_csv(df_all_path)
    df_all['Year'] = df_all['Year'].astype(int) 
else:
    os.makedirs(vhi_folder, exist_ok=True)
    df_list = []
    for ids in range(1, 28):  
        url = f"https://www.star.nesdis.noaa.gov/smcd/emb/vci/VH/get_TS_admin.php?country=UKR&provinceID={ids}&year1=1981&year2=2024&type=Mean"
        response = requests.get(url)
        if response.status_code == 200:
            file_name = f'vhi_id_{ids}_{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
            file_path = os.path.join(vhi_folder, file_name)
            with open(file_path, 'wb') as out:
                out.write(response.content)
        else:
            continue  

    # Завантаження всіх CSV-файлів
    for file in os.listdir(vhi_folder):
        if file.endswith(".csv") and file.startswith("vhi_id_"):
            df = pd.read_csv(os.path.join(vhi_folder, file), header=1, skiprows=1,
                             names=['Year', 'Week', 'SMN', 'SMT', 'VCI', 'TCI', 'VHI', 'empty'])
            df.drop(columns=['empty'], inplace=True, errors='ignore')  
            df['VHI'] = pd.to_numeric(df['VHI'], errors='coerce')      
            df = df[df['VHI'] != -1].dropna()                          
            area_code = int(file.split('_')[2]) if file.split('_')[2].isdigit() else None
            df['area_code'] = area_code
            df_list.append(df)

    # Об'єднання всіх даних в один DataFrame
    df_all = pd.concat(df_list, ignore_index=True)
    df_all.dropna(axis=1, how='all', inplace=True)
    df_all.drop_duplicates(inplace=True)

    # Виправляємо відповідність кодів областей
    dict_areas_fix = {1: 22, 2: 24, 3: 23, 4: 25, 5: 3, 6: 4, 7: 8, 8: 19, 9: 20, 10: 21, 11: 9,
                      13: 10, 14: 11, 15: 12, 16: 13, 17: 15, 18: 14, 19: 16, 21: 17, 22: 18,
                      23: 6, 24: 1, 25: 2, 26: 7, 27: 5}
    df_all['area_code'] = df_all['area_code'].replace(dict_areas_fix)
    df_all['area'] = df_all['area_code'].map(area_id_to_name)
    df_all.to_csv(df_all_path, index=False)  
    df_all['Year'] = df_all['Year'].astype(int)

# Ініціалізація фільтрів у сесії
if 'filters' not in st.session_state:
    st.session_state.filters = {
        'time_series': 'VCI',
        'region': ordered_regions[0],
        'week_range': (int(df_all['Week'].min()), int(df_all['Week'].max())),
        'year_range': (int(df_all['Year'].min()), int(df_all['Year'].max())),
        'sort_asc': False,
        'sort_desc': False
    }

# Блок керування фільтрами в бічній панелі
with st.sidebar:
    st.header("Filters")

    if st.button("Reset filters"):
        # Скидаємо всі фільтри до значень за замовчуванням
        st.session_state.filters = {
            'time_series': 'VCI',
            'region': ordered_regions[0],
            'week_range': (int(df_all['Week'].min()), int(df_all['Week'].max())),
            'year_range': (int(df_all['Year'].min()), int(df_all['Year'].max())),
            'sort_asc': False,
            'sort_desc': False
        }
        st.rerun()

    filters = st.session_state.filters
    filters['time_series'] = st.selectbox("Select time series:", ['VCI', 'TCI', 'VHI'], index=['VCI', 'TCI', 'VHI'].index(filters['time_series']))
    filters['region'] = st.selectbox("Select region:", ordered_regions, index=ordered_regions.index(filters['region']))
    filters['week_range'] = st.slider("Select week range:", int(df_all['Week'].min()), int(df_all['Week'].max()), filters['week_range'])
    filters['year_range'] = st.slider("Select year range:", int(df_all['Year'].min()), int(df_all['Year'].max()), filters['year_range'])
    filters['sort_asc'] = st.checkbox("Sort ascending", value=filters['sort_asc'])
    filters['sort_desc'] = st.checkbox("Sort descending", value=filters['sort_desc'])

# Фільтрація основного датафрейму за вибраними параметрами
f = filters
filtered_df = df_all[
    (df_all['area'] == f['region']) &
    (df_all['Week'] >= f['week_range'][0]) & (df_all['Week'] <= f['week_range'][1]) &
    (df_all['Year'] >= f['year_range'][0]) & (df_all['Year'] <= f['year_range'][1])
].copy()

# Сортування фільтрованих даних
if f['sort_asc'] and not f['sort_desc']:
    filtered_df.sort_values(by=f['time_series'], ascending=True, inplace=True)
elif f['sort_desc'] and not f['sort_asc']:
    filtered_df.sort_values(by=f['time_series'], ascending=False, inplace=True)
elif f['sort_asc'] and f['sort_desc']:
    st.warning("Please select only one sort option.")

# Вкладки для відображення результатів
tab1, tab2, tab3 = st.tabs(["Table", "Heatmap", "Comparison"])

# Таблиця
with tab1:
    st.subheader("Table")
    st.dataframe(filtered_df)

# Графік-теплокарта
with tab2:
    st.subheader("Heatmap")
    if not filtered_df.empty:
        heatmap_data = filtered_df.pivot_table(index='Year', columns='Week', values=f['time_series'])
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.heatmap(heatmap_data, cmap='Purples', ax=ax, cbar_kws={'label': f['time_series']})
        ax.set_title(f"Heatmap of {f['time_series']} for {f['region']} (by week and year)")
        st.pyplot(fig)
    else:
        st.info("No data to display.")

# Порівняння по регіонах
with tab3:
    st.subheader("Region comparison")
    filtered_cmp = df_all[
        (df_all['Week'] >= f['week_range'][0]) & (df_all['Week'] <= f['week_range'][1]) &
        (df_all['Year'] >= f['year_range'][0]) & (df_all['Year'] <= f['year_range'][1])
    ]
    if not filtered_cmp.empty:
        grouped_cmp = filtered_cmp.groupby('area')[f['time_series']].mean().reset_index()

        # Сортування при порівнянні
        if f['sort_asc'] and not f['sort_desc']:
            grouped_cmp.sort_values(by=f['time_series'], ascending=True, inplace=True)
        elif f['sort_desc'] and not f['sort_asc']:
            grouped_cmp.sort_values(by=f['time_series'], ascending=False, inplace=True)

        # Підсвічування обраного регіону
        colors = ['orange' if area == f['region'] else 'skyblue' for area in grouped_cmp['area']]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(grouped_cmp['area'], grouped_cmp[f['time_series']], color=colors)
        ax.set_title(f"Average {f['time_series']} by region for selected period")
        ax.set_xlabel("Region")
        ax.set_ylabel(f"Average {f['time_series']}")
        ax.set_xticklabels(grouped_cmp['area'], rotation=45, ha='right')
        ax.grid(axis='y')
        fig.tight_layout()
        st.pyplot(fig)
    else:
        st.info("Not enough data to compare.")