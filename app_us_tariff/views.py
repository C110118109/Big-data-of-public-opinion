from django.shortcuts import render
import json
from datetime import datetime, timedelta
import pandas as pd
import re
import os
from django.conf import settings
from collections import Counter
import jieba

# Global variable for the dataframe
df = None

def load_df_data():
    global df
    df = pd.read_csv('app_us_tariff/dataset/ttv_news_preprocessed.csv', sep='|')
    print("US Tariff app: Data loaded successfully with", len(df), "records")

load_df_data()

def home(request):
    tariff_data = extract_tariff_data()
    
    freqByDate = calculate_date_frequency(tariff_data)
    freqByRegion = calculate_region_frequency(tariff_data)
    freqByIndustry = calculate_industry_frequency(tariff_data)
    
    regions = [item[0] for item in freqByRegion]
    industries = [item[0] for item in freqByIndustry]
    
    freqByDate_json = json.dumps(freqByDate)
    freqByRegion_json = json.dumps([item[1] for item in freqByRegion])
    freqByIndustry_json = json.dumps([item[1] for item in freqByIndustry])
    regions_json = json.dumps(regions)
    industries_json = json.dumps(industries)
    
    num_occurrence = len(tariff_data)
    num_frequency = count_tariff_mentions(tariff_data)
    
    relatedKeywords = extract_related_keywords(tariff_data)
    
    mayor_responses = [
        {
            'mayor': '蔣萬安',
            'region': '台北市',
            'action': '率隊拜會產業界了解需求，敲定9日召開「基北北桃四首長會議」共商應對策略。'
        },
        {
            'mayor': '張善政',
            'region': '桃園市',
            'action': '聯繫新竹縣、市長和苗栗縣長，要維護「桃竹苗科技廊帶」計畫。'
        },
        {
            'mayor': '藍白七縣市首長',
            'region': '多地區',
            'action': '串聯應對關稅危機，共同面對美國高關稅衝擊。'
        },
        {
            'mayor': '蔣萬安',
            'region': '台北市',
            'action': '喊話中央與美國談判，籲全台灣不分顏色團結應對。'
        }
    ]
    
    news_list = extract_news_list(tariff_data)
    
    context = {
        'freqByDate': freqByDate_json,
        'freqByRegion': freqByRegion_json,
        'freqByIndustry': freqByIndustry_json,
        'regions': regions_json,
        'industries': industries_json,
        'num_occurrence': num_occurrence,
        'num_frequency': num_frequency,
        'relatedKeywords': json.dumps(relatedKeywords),
        'mayor_responses': json.dumps(mayor_responses),
        'news_list': json.dumps(news_list)
    }
    
    return render(request, 'app_us_tariff/home.html', context)

def extract_tariff_data():
    """Extract news items related to tariffs"""
    # Make sure data is loaded
    if df is None:
        load_df_data()
    
    tariff_keywords = ['關稅', '貿易', '川普', '美國', '對等關稅', '高關稅']
    
    tariff_data = df[df.apply(lambda row: 
        any(keyword in str(row['title']) for keyword in tariff_keywords) or 
        any(keyword in str(row['content']) for keyword in tariff_keywords), axis=1)]
    
    tariff_list = []
    for _, row in tariff_data.iterrows():
        tariff_list.append(row.to_dict())
    
    return tariff_list

def calculate_date_frequency(data):
    date_freq = {}
    
    for item in data:
        date = item.get('date', '')
        if date:
            date_freq[date] = date_freq.get(date, 0) + 1
    
    result = []
    for date, count in sorted(date_freq.items()):
        result.append({
            'x': date,  
            'y': count
        })
    
    return result

def calculate_region_frequency(data):
    """Calculate the frequency of tariff news by region"""
    regions = ['台北', '新北', '桃園', '基隆', '新竹', '苗栗', '台中']
    region_freq = {region: 0 for region in regions}
    
    for item in data:
        title = str(item.get('title', ''))
        content = str(item.get('content', ''))
        
        for region in regions:
            if region in title or region in content:
                region_freq[region] += 1
    
    result = [(region, freq) for region, freq in region_freq.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    
    return result

def calculate_industry_frequency(data):
    """Calculate the frequency of tariff news by industry"""
    industries = ['科技', '製造', '半導體', '出口', '電子']
    industry_freq = {industry: 0 for industry in industries}
    
    for item in data:
        title = str(item.get('title', ''))
        content = str(item.get('content', ''))
        
        for industry in industries:
            if industry in title or industry in content:
                industry_freq[industry] += 1
    
    result = [(industry, freq) for industry, freq in industry_freq.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    
    return result

def count_tariff_mentions(data):
    """Count how many times tariff-related keywords are mentioned"""
    tariff_keywords = ['關稅', '貿易', '川普', '美國', '對等關稅', '高關稅']
    count = 0
    
    for item in data:
        title = str(item.get('title', ''))
        content = str(item.get('content', ''))
        
        for keyword in tariff_keywords:
            count += title.count(keyword)
            count += content.count(keyword)
    
    return count

def extract_related_keywords(data):
    """Extract keywords that frequently appear with tariff-related content"""
    jieba.load_userdict(['蔣萬安', '張善政', '桃竹苗', '藍白七', '川普', '基北北桃', '內科發展協會'])
    
    all_text = ' '.join([str(item.get('title', '')) + ' ' + str(item.get('content', '')) for item in data])
    
    words = jieba.cut(all_text)
    
    stopwords = ['的', '是', '了', '在', '和', '與', '有', '因為', '但是', '可能', '暫無', '及', '以', '要', '不', '、', '，', '。', '！', '（', '）', '：']
    word_counts = Counter()
    
    for word in words:
        if word not in stopwords and len(word) > 1 and not word.isdigit() and not any(c.isdigit() for c in word):
            word_counts[word] += 1
    
    tariff_keywords = ['關稅', '貿易', '川普', '美國', '對等關稅', '高關稅']
    for keyword in tariff_keywords:
        if keyword in word_counts:
            del word_counts[keyword]
    
    top_keywords = word_counts.most_common(20)
    
    max_count = top_keywords[0][1] if top_keywords else 1
    min_count = top_keywords[-1][1] if top_keywords else 1
    
    result = []
    for word, count in top_keywords:
        if max_count == min_count:  
            size = 30
        else:
            size = 15 + (count - min_count) * 35 / (max_count - min_count)
            
        result.append({
            'text': word,
            'size': size
        })
    
    return result

def extract_news_list(data):
    """Extract a formatted list of news for display"""
    news_list = []
    
    for item in data:
        news_list.append({
            'title': str(item.get('title', '')),
            'date': str(item.get('date', '')),
            'category': str(item.get('category', '')),
            'link': str(item.get('link', '#'))
        })
    
    return news_list

print("app_us_tariff was loaded!")