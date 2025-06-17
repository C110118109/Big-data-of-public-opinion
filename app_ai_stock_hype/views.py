from django.shortcuts import render
import json
import os
import pandas as pd
from datetime import datetime
from collections import Counter
import re

def home(request):
    """AI股票熱潮分析主頁 - 使用預收集的數據"""
    try:
        ai_stock_data = extract_ai_stock_data()
        
        context = {
            'stock_rankings': json.dumps(ai_stock_data['rankings']),
            'sentiment_trends': json.dumps(ai_stock_data['sentiment_trends']),
            'keyword_frequency': json.dumps(ai_stock_data['keyword_freq']),
            'volume_by_company': json.dumps(ai_stock_data['company_volume']),
            'ai_keywords_cloud': json.dumps(ai_stock_data['keywords_cloud']),
            'total_articles': ai_stock_data['total_articles'],
            'total_mentions': ai_stock_data['total_mentions'],
            'last_update': ai_stock_data.get('last_update', '數據載入中'),
            'data_source': ai_stock_data.get('data_source', '台視新聞'),
            'category_stats': json.dumps(ai_stock_data['category_stats'])
        }
        
    except Exception as e:
        print(f"載入數據時發生錯誤: {e}")
        # 如果沒有數據，提供示例數據
        context = create_demo_context()
        
    return render(request, 'app_ai_stock_hype/home.html', context)

def extract_ai_stock_data():
    """從CSV檔案提取AI股票數據"""
    dataset_dir = 'app_ai_stock_hype/dataset'
    
    # 尋找數據檔案
    ai_news_file = find_latest_csv_file(dataset_dir, pattern='*ai_only*')
    all_news_file = find_latest_csv_file(dataset_dir, pattern='ttv_news*')
    
    if not ai_news_file and not all_news_file:
        raise FileNotFoundError("沒有找到數據檔案，請先執行爬蟲收集數據")
    
    # 優先使用AI專用檔案，否則使用全部新聞檔案並篩選
    if ai_news_file:
        df = pd.read_csv(ai_news_file, sep='|')
        df_ai = df[df.get('is_ai_related', True) == True]  # AI專用檔案應該都是AI相關
    else:
        df = pd.read_csv(all_news_file, sep='|')
        df_ai = df[df.get('is_ai_related', False) == True]
    
    if df_ai.empty:
        raise ValueError("沒有找到AI相關新聞數據")
    
    # AI概念股字典
    ai_stocks = {
        '台積電': ['台積電', 'TSMC', '2330'],
        '聯發科': ['聯發科', 'MediaTek', '2454'], 
        '廣達': ['廣達', 'Quanta', '2382'],
        '鴻海': ['鴻海', 'Foxconn', '2317'],
        '緯創': ['緯創', 'Wistron', '3231'],
        '聯電': ['聯電', 'UMC', '2303'],
        '日月光': ['日月光', 'ASE', '2311'],
        '和碩': ['和碩', 'Pegatron', '4938']
    }
    
    # 1. 計算公司聲量排行
    company_mentions = {}
    for company, keywords in ai_stocks.items():
        mentions = 0
        for _, row in df_ai.iterrows():
            text = str(row.get('title', '')) + ' ' + str(row.get('content', ''))
            mentions += sum(text.count(keyword) for keyword in keywords)
        company_mentions[company] = mentions
    
    rankings = sorted(company_mentions.items(), key=lambda x: x[1], reverse=True)
    rankings = [item for item in rankings if item[1] > 0]  # 只保留有提及的公司
    
    # 2. 時間趨勢分析
    sentiment_trends = calculate_sentiment_trends(df_ai)
    
    # 3. 關鍵字頻率統計
    keyword_freq = calculate_keyword_frequency(df_ai)
    
    # 4. 關鍵字雲
    keywords_cloud = prepare_keywords_cloud(df_ai)
    
    # 5. 分類統計
    category_stats = calculate_category_stats(df_ai)
    
    # 6. 檔案更新時間
    file_path = ai_news_file or all_news_file
    last_update = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
    
    return {
        'rankings': rankings,
        'sentiment_trends': sentiment_trends,
        'keyword_freq': keyword_freq,
        'company_volume': [{'company': comp, 'volume': vol} for comp, vol in rankings],
        'keywords_cloud': keywords_cloud,
        'total_articles': len(df_ai),
        'total_mentions': sum(company_mentions.values()),
        'last_update': last_update,
        'data_source': '台視新聞',
        'category_stats': category_stats
    }

def find_latest_csv_file(directory, pattern='*.csv'):
    """尋找最新的CSV檔案"""
    import glob
    
    if not os.path.exists(directory):
        return None
    
    search_pattern = os.path.join(directory, pattern)
    csv_files = glob.glob(search_pattern)
    
    if not csv_files:
        return None
    
    # 按修改時間排序，取最新的
    latest_file = max(csv_files, key=os.path.getmtime)
    return latest_file

def calculate_sentiment_trends(df_ai):
    """計算情緒趨勢"""
    daily_sentiment = {}
    
    # 正負面關鍵字
    positive_words = ['上漲', '成長', '獲利', '突破', '創新', '領先', '優勢', '看好', '樂觀', '強勁']
    negative_words = ['下跌', '虧損', '衰退', '困難', '挑戰', '風險', '警告', '下滑', '疲軟', '悲觀']
    
    for _, row in df_ai.iterrows():
        date = row.get('date', datetime.now().strftime('%Y-%m-%d'))
        text = str(row.get('title', '')) + ' ' + str(row.get('content', ''))
        
        if date not in daily_sentiment:
            daily_sentiment[date] = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        pos_count = sum(text.count(word) for word in positive_words)
        neg_count = sum(text.count(word) for word in negative_words)
        
        if pos_count > neg_count:
            daily_sentiment[date]['positive'] += 1
        elif neg_count > pos_count:
            daily_sentiment[date]['negative'] += 1
        else:
            daily_sentiment[date]['neutral'] += 1
    
    # 轉換為圖表格式
    trends = []
    for date in sorted(daily_sentiment.keys()):
        trends.append({
            'date': date,
            'positive': daily_sentiment[date]['positive'],
            'negative': daily_sentiment[date]['negative'],
            'neutral': daily_sentiment[date]['neutral']
        })
    
    return trends

def calculate_keyword_frequency(df_ai):
    """計算關鍵字頻率"""
    ai_keywords = [
        '人工智慧', 'AI', 'ChatGPT', '輝達', 'NVIDIA', 
        '台積電', '聯發科', '廣達', '機器學習', '半導體',
        '晶片', '自動化', '演算法', '神經網路', '大數據'
    ]
    
    keyword_freq = {}
    all_text = ' '.join([
        str(row.get('title', '')) + ' ' + str(row.get('content', ''))
        for _, row in df_ai.iterrows()
    ])
    
    for keyword in ai_keywords:
        count = all_text.count(keyword)
        if count > 0:
            keyword_freq[keyword] = count
    
    return keyword_freq

def prepare_keywords_cloud(df_ai):
    """準備關鍵字雲數據"""
    ai_concepts = [
        '人工智慧', 'AI', '機器學習', '深度學習', 'ChatGPT', 
        '自動化', '演算法', '神經網路', '大數據', '雲端運算',
        '智慧製造', '工業4.0', '物聯網', 'IoT', '5G',
        '區塊鏈', '元宇宙', '虛擬實境', 'VR', 'AR'
    ]
    
    all_text = ' '.join([
        str(row.get('title', '')) + ' ' + str(row.get('content', ''))
        for _, row in df_ai.iterrows()
    ])
    
    word_freq = {}
    for concept in ai_concepts:
        count = all_text.count(concept)
        if count > 0:
            word_freq[concept] = count
    
    if not word_freq:
        return []
    
    max_freq = max(word_freq.values())
    min_freq = min(word_freq.values())
    
    keywords_cloud = []
    for word, freq in word_freq.items():
        if max_freq == min_freq:
            size = 30
        else:
            size = 15 + (freq - min_freq) * 40 / (max_freq - min_freq)
        keywords_cloud.append({'text': word, 'size': int(size)})
    
    return keywords_cloud

def calculate_category_stats(df_ai):
    """計算分類統計"""
    category_counts = df_ai.groupby('category').size().to_dict()
    return [{'category': cat, 'count': count} for cat, count in category_counts.items()]

def create_demo_context():
    """創建演示數據"""
    return {
        'stock_rankings': json.dumps([
            ['台積電', 45], ['聯發科', 23], ['廣達', 18], ['鴻海', 15]
        ]),
        'sentiment_trends': json.dumps([
            {'date': '2024-01-01', 'positive': 5, 'negative': 2, 'neutral': 3},
            {'date': '2024-01-02', 'positive': 7, 'negative': 1, 'neutral': 2}
        ]),
        'keyword_frequency': json.dumps({
            'AI': 30, '人工智慧': 25, '台積電': 45, '半導體': 20
        }),
        'volume_by_company': json.dumps([
            {'company': '台積電', 'volume': 45},
            {'company': '聯發科', 'volume': 23}
        ]),
        'ai_keywords_cloud': json.dumps([
            {'text': 'AI', 'size': 40}, {'text': '人工智慧', 'size': 35},
            {'text': '機器學習', 'size': 25}, {'text': '半導體', 'size': 30}
        ]),
        'total_articles': 50,
        'total_mentions': 150,
        'last_update': '演示數據',
        'data_source': '演示模式',
        'category_stats': json.dumps([
            {'category': '財經', 'count': 30},
            {'category': '科技', 'count': 20}
        ]),
        'is_demo': True
    }

# app_ai_stock_hype/urls.py
from django.urls import path
from . import views

app_name = 'app_ai_stock_hype'

urlpatterns = [
    path('', views.home, name='home'),
]