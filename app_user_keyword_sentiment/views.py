from django.http import JsonResponse
from django.shortcuts import render
import pandas as pd
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
import requests
import app_user_keyword.views as userkeyword_views

# (1) Load news data--approach 1 直接指定某個csv檔案
def load_df_data_v1():
    global df # global variable
    # df = pd.read_csv('app_user_keyword/dataset/cna_news_200_preprocessed.csv',sep='|')
    df = pd.read_csv('app_user_keyword_sentiment/dataset/ttv_news_preprocessed.csv',sep='|')

# (2) Load news data--approach 2 跟隔壁的app借用df
# import from app_user_keyword.views and use df later
def load_df_data():
    # import and use df from app_user_keyword 
    global df # global variable
    df = userkeyword_views.df

# call load data function when starting server
load_df_data_v1()
#load_df_data()

def home(request):
    return render(request, 'app_user_keyword_sentiment/home.html')

# This is the function from your notebook
def filter_df_via_content(query_keywords, cond, cate, weeks):
    # end date: the date of the latest record of news
    end_date = df.date.max()
    
    # start date
    start_date_delta = (datetime.strptime(end_date, '%Y-%m-%d').date() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
    start_date_min = df.date.min()
    # set start_date as the larger one from the start_date_delta and start_date_min 開始時間選資料最早時間與周數:兩者較晚者
    start_date = max(start_date_delta, start_date_min)

    # (1) proceed filtering: a duration of a period of time
    # 期間條件
    period_condition = (df.date >= start_date) & (df.date <= end_date) 
    
    # (2) proceed filtering: news category
    # 新聞類別條件
    if (cate == "全部"):
        condition = period_condition  # "全部"類別不必過濾新聞種類
    else:
        # 過濾category新聞類別條件
        condition = period_condition & (df.category == cate)

    # (3) proceed filtering: and or
    # and or 條件
    if (cond == 'and'):
        # query keywords condition使用者輸入關鍵字條件and
        condition = condition & df.content.apply(lambda text: all((qk in text) for qk in query_keywords)) #寫法:all()
    elif (cond == 'or'):
        # query keywords condition使用者輸入關鍵字條件
        condition = condition & df.content.apply(lambda text: any((qk in text) for qk in query_keywords)) #寫法:any()
    # condiction is a list of True or False boolean value
    df_query = df[condition]

    return df_query

# GET: csrf_exempt is not necessary
# POST: csrf_exempt should be used
@csrf_exempt
def api_get_userkey_sentiment_from_remote_api_through_backend(request):

    userkey = request.POST['userkey']
    cate = request.POST['cate']
    cond = request.POST['cond']
    weeks = int(request.POST['weeks'])

    try:
        # (可選擇)展示從後端呼叫API: Call internet sentiment API using requests  但是不能自己呼叫自己!
        url_api_get_sentiment = "http://163.18.23.20:8000/userkeyword_senti/api_get_userkey_sentiment/"
        # Setup data for sentiment analysis request
        sentiment_data = {
            'userkey': userkey,
            'cate': cate,
            'cond': cond,
            'weeks': weeks
        }
        # Alternative way to call the sentiment API directly with requests
        sentiment_response = requests.post(url_api_get_sentiment, data=sentiment_data, timeout=5)
        if sentiment_response.status_code == 200:
            print("由後端呼叫他處API，取得情感分析數據成功!")
            # 解析來自API的回應內容。 .json() 方法會將回應的 JSON 格式資料轉換成 Python 的字典(dictionary)或列表(list)。
            # Parse the response content from the API. The .json() method converts the JSON formatted data from the response into a Python dictionary or list.
            response = sentiment_response.json()
            return JsonResponse(response)
        else:
            print(f"回傳有錯誤，進行本地處理資料")
            print(f"Sentiment API error: {sentiment_response.status_code}")
            return JsonResponse({'error': 'Failed to get sentiment analysis.'})
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"An unexpected error occurred while processing sentiment data: {e}")
        print(f"呼叫異常失敗，進行本地處理資料")
        return JsonResponse({'error': 'An internal error occurred while processing sentiment data.'}, status=500) # Internal Server Error
 
# GET: csrf_exempt is not necessary
# POST: csrf_exempt should be used
@csrf_exempt
def api_get_userkey_sentiment(request):

    userkey = request.POST['userkey']
    cate = request.POST['cate']
    cond = request.POST['cond']
    weeks = int(request.POST['weeks'])
    
    print(f"Searching for: {userkey}, cond: {cond}, cate: {cate}, weeks: {weeks}")
 
    # 進行本地處理資料
    query_keywords = userkey.split()
    # Proceed filtering - use our notebook function instead of filter_dataFrame
    df_query = filter_df_via_content(query_keywords, cond, cate, weeks)
    
    print(f"Found {len(df_query)} matching articles")
    
    # if df_query is empty, return an error message
    if len(df_query) == 0:
        return JsonResponse({'error': 'No results found for the given keywords.'})
    
    sentiCount, sentiPercnt = get_article_sentiment(df_query)

    if weeks <= 4:
        freq_type = 'D'
    else:
        freq_type = 'W'

    line_data_pos = get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type=freq_type)
    line_data_neg = get_daily_basis_sentiment_count(df_query, sentiment_type='neg', freq_type=freq_type)

    response = {
        'sentiCount': sentiCount,
        'data_pos': line_data_pos,
        'data_neg': line_data_neg,
    }
    return JsonResponse(response)

def get_article_sentiment(df_query):
    sentiCount = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    sentiPercnt = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    numberOfArticle = len(df_query)
    
    for senti in df_query.sentiment:
        try:
            # Try to convert sentiment to float
            senti_value = float(senti)

            # Determine sentimental polarity
            if senti_value >= 0.6:
                sentiCount['Positive'] += 1
            elif senti_value <= 0.4:
                sentiCount['Negative'] += 1
            else:
                sentiCount['Neutral'] += 1
                
        except (ValueError, TypeError):
            # If conversion fails (e.g., '暫無'), count as Neutral
            sentiCount['Neutral'] += 1
    
    # Calculate percentages
    for polar in sentiCount:
        try:
            sentiPercnt[polar] = int(sentiCount[polar]/numberOfArticle*100)
        except:
            sentiPercnt[polar] = 0  # 若分母 numberOfArticle=0會報錯
            
    return sentiCount, sentiPercnt

def get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type='D'):
    # Define a safe lambda function to handle non-numeric values
    def safe_sentiment_check(senti, threshold, comparison):
        try:
            senti_value = float(senti)
            if comparison == 'greater':
                return 1 if senti_value >= threshold else 0
            elif comparison == 'less':
                return 1 if senti_value <= threshold else 0
            elif comparison == 'between':
                return 1 if threshold[0] < senti_value < threshold[1] else 0
        except (ValueError, TypeError):
            # If conversion fails, return 0 (not counted in the specific sentiment)
            return 0
    
    # Using lambda to determine if an article has positive/negative/neutral sentiment
    if sentiment_type == 'pos':
        lambda_function = lambda senti: safe_sentiment_check(senti, 0.6, 'greater')
    elif sentiment_type == 'neg':
        lambda_function = lambda senti: safe_sentiment_check(senti, 0.4, 'less')
    elif sentiment_type == 'neutral':
        lambda_function = lambda senti: safe_sentiment_check(senti, (0.4, 0.6), 'between')
    else:
        return None
    
    freq_df = pd.DataFrame({
        'date_index': pd.to_datetime(df_query.date),
        'frequency': [lambda_function(senti) for senti in df_query.sentiment]
    })
    
    # Group rows by the date
    freq_df_group = freq_df.groupby(pd.Grouper(key='date_index', freq=freq_type)).sum()
    
    # Reset index
    freq_df_group.reset_index(inplace=True)
    
    # Format for chart
    xy_line_data = [{'x': date.strftime('%Y-%m-%d'), 'y': freq} 
                   for date, freq in zip(freq_df_group.date_index, freq_df_group.frequency)]
    
    return xy_line_data

print("app_userkey_sentiment was loaded!")