import matplotlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import seaborn as sns
import io


def load_data_set():
    encodings = ['windows-1251','cp-1251','iso-8859-1','utf-8']

    for encoding in encodings:
        try:
            df = pd.read_csv('DataSet.csv',sep= ';', encoding=encoding)
            print(f"Кодировка : {encoding}")
            break
        except Exception as e:
            print(f"Кодировка : {encoding} не подошла")

    df.columns = ['Nick','Game','Genre','Playtime','Achievements']

    df['Achievements'] = df['Achievements'].astype(str).str.replace(',','.').astype(float)

    return df

def get_basic_stats(df):
    """Базовая статистика для подписей"""
    stats = {
        'total_players': df['Nick'].nunique(),
        'total_games': df['Game'].nunique(),
        'total_genres': df['Genre'].nunique(),
        'total_hours': df['Playtime'].sum(),
        'avg_playtime': df['Playtime'].mean(),
        'max_playtime': df['Playtime'].max()
    }
    return stats

#Работа с графиками
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'DejaVu Sans'

def create_top_games_plot(df):
    plt.figure(figsize = (12, 8))
    top_games = df['Game'].value_counts().head(10) #число меняет количество игр в топ-е
    ax = sns.barplot(x = top_games.values , y = top_games.index,
                     palette = 'viridis', hue = top_games.index,
                     legend = False, dodge = False)

    plt.title('ТОП 10 игр, в которые играют мои друзья')
    plt.xlabel('Количество игроков', fontsize = 12)
    plt.ylabel('')

    # Добавляем значения на столбцы
    for i, value in enumerate(top_games.values):
        ax.text(value + 0.1, i, f'{value}', va='center', fontweight='bold')

    plt.tight_layout()

    # Сохраняем в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def create_playtime_distribution(df):
    """Распределение времени игры"""
    plt.figure(figsize=(12, 8))

    # Гистограмма с KDE
    sns.histplot(data=df, x='Playtime', bins=20, kde=True, color='skyblue')
    plt.title('Распределение времени игры', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Часы в игре', fontsize=12)
    plt.ylabel('Количество записей', fontsize=12)

    plt.tight_layout()

    buf = io.BytesIO() #временный буфер, чтобы не сохранять график на пк
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def create_genre_analysis(df):
    """Анализ по жанрам"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # График 1: Круговой график жанров
    genre_counts = df['Genre'].value_counts()
    colors = sns.color_palette("pastel")[:len(genre_counts)]
    ax1.pie(genre_counts.values, labels=genre_counts.index, autopct='%1.1f%%',
            colors=colors, startangle=90)
    ax1.set_title('Распределение по жанрам', fontsize=14, fontweight='bold')

    # График 2: Boxplot времени по жанрам
    # Убираем emoji из заголовков и исправляем синтаксис
    sns.boxplot(data=df, x='Genre', y='Playtime', ax=ax2,
                hue='Genre', palette="Set2", legend=False, dodge=False)

    ax2.set_title('Время игры по жанрам', fontsize=14, fontweight='bold')

    # способ поворота подписей
    ax2.tick_params(axis='x', rotation=45)
    ax2.set_ylabel('Часы в игре')

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def create_playtime_distribution(df):
    """Распределение времени игры"""
    plt.figure(figsize=(12, 8))

    # Гистограмма с KDE
    sns.histplot(data=df, x='Playtime', bins=20, kde=True, color='skyblue')
    plt.title('Распределение времени игры', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Часы в игре', fontsize=12)
    plt.ylabel('Количество записей', fontsize=12)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def test_playtime_achievements_correlation(df):
    """Проверяем корреляцию между временем игры и достижениями"""

    # Корреляция через pandas
    correlation = df['Playtime'].corr(df['Achievements'])

    # Интерпретация корреляции
    if abs(correlation) > 0.7:
        strength = "сильная"
    elif abs(correlation) > 0.5:
        strength = "умеренная"
    elif abs(correlation) > 0.3:
        strength = "слабая"
    else:
        strength = "очень слабая"

    direction = "положительная" if correlation > 0 else "отрицательная"

    # Дополнительная проверка через группировку
    df['Playtime_Group'] = pd.cut(df['Playtime'], bins=5)
    group_stats = df.groupby('Playtime_Group',observed= False)['Achievements'].agg(['mean', 'count'])
    return correlation, strength, direction, group_stats

def test_playtime_is_assymetryc(df):
    playtime = df['Playtime'].skew()
    return playtime