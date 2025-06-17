# ttv_ai_news_crawler.py - 修正版爬蟲程式
"""
台視新聞AI股票相關新聞爬蟲 - 修正版
使用方式：python ttv_ai_news_crawler.py
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time
import random
import logging
import os
from fake_useragent import UserAgent
from urllib.parse import quote

# 設置日誌
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TTVAINewsCrawler:
    def __init__(self):
        self.base_url = "https://news.ttv.com.tw"
        self.ua = UserAgent()
        self.session = requests.Session()
        
        # AI相關關鍵字（可自行調整）
        self.ai_keywords = [
            '人工智慧', 'AI', '台積電', '聯發科', '廣達', '鴻海', '緯創', '聯電',
            'ChatGPT', '輝達', 'NVIDIA', '半導體', '晶片', '機器學習', '深度學習',
            'TSMC', 'MediaTek', 'Foxconn', 'Quanta', 'Wistron', 'UMC', '自動化',
            '演算法', '神經網路', '大數據', '雲端運算', '智慧製造', '工業4.0'
        ]
        
        # 修正後的新聞分類映射 - 使用正確的中文分類名稱
        self.categories = {
            '財經': '財經',
            '政治': '政治', 
            '社會': '社會',
            '國際': '國際',
            '運動': '運動',
            '娛樂': '娛樂'
        }
        
        # 存儲數據的容器
        self.all_news_data = []

    def get_random_headers(self):
        """獲取隨機請求頭"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def scrape_category_page(self, category_name, page_num):
        """爬取單個分類頁面 - 修正版"""
        # 修正URL格式 - 使用正確的中文分類URL
        encoded_category = quote(category_name)
        if page_num == 1:
            url = f"{self.base_url}/category/{encoded_category}"
        else:
            url = f"{self.base_url}/category/{encoded_category}?page={page_num}"
        
        logger.info(f"正在爬取: {url}")
        
        try:
            response = requests.get(url, headers=self.get_random_headers(), timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 嘗試多種可能的新聞列表選擇器
            news_items = []
            
            # 方法1: 尋找包含新聞項目的容器
            selectors = [
                'div.news-list li',
                'ul.news-list li', 
                'div[class*="news-list"] li',
                'div[class*="list"] li',
                '.news-item',
                'article',
                'div[class*="item"]'
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    logger.info(f"使用選擇器找到 {len(items)} 個新聞項目: {selector}")
                    news_items = items
                    break
            
            if not news_items:
                # 如果上述方法都找不到，嘗試查找所有包含標題和連結的項目
                potential_items = soup.find_all('li')
                news_items = []
                for item in potential_items:
                    if item.find('a') and (item.find('div', class_='title') or item.find(string=re.compile(r'.{10,}'))):
                        news_items.append(item)
                
                if news_items:
                    logger.info(f"通過啟發式方法找到 {len(news_items)} 個潛在新聞項目")
            
            if not news_items:
                logger.warning(f"頁面 {url} 沒有找到新聞列表")
                return 0
            
            processed_count = 0
            
            # 計算序號
            serial_no = len([n for n in self.all_news_data if n['category'] == category_name]) + 1
            
            for item in news_items:
                try:
                    # 提取標題 - 嘗試多種方法
                    title = self._extract_title(item)
                    if not title or len(title) < 5:  # 過濾太短的標題
                        continue
                    
                    # 提取連結
                    link_tag = item.find('a')
                    if not link_tag:
                        continue
                    link = link_tag.get('href')
                    if not link:
                        continue
                    
                    full_link = link if link.startswith("http") else f"{self.base_url}{link}"
                    
                    # 提取圖片
                    photo_link = self._extract_photo_link(item)
                    
                    # 提取日期
                    news_date_str = self._extract_date(item)
                    
                    # 生成item_id
                    timestamp = datetime.now().strftime("%Y%m%d")
                    item_id = f"{category_name}_{timestamp}_{serial_no}"
                    
                    logger.info(f"{serial_no} -- {title}")
                    
                    # 爬取文章內容
                    content = self._scrape_article_content(full_link)
                    
                    # 檢查是否AI相關
                    text_for_check = title + ' ' + content
                    is_ai_related = any(keyword in text_for_check for keyword in self.ai_keywords)
                    
                    # 存儲數據
                    news_data = {
                        'item_id': item_id,
                        'date': news_date_str,
                        'category': category_name,
                        'title': title,
                        'content': content,
                        'link': full_link,
                        'photo_link': photo_link,
                        'is_ai_related': is_ai_related
                    }
                    
                    self.all_news_data.append(news_data)
                    
                    if is_ai_related:
                        logger.info(f"✓ 發現AI相關新聞: {title}")
                    
                    serial_no += 1
                    processed_count += 1
                    
                    # 延遲避免被封鎖
                    time.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    logger.error(f"處理新聞項目時出錯: {e}")
                    continue
            
            return processed_count
            
        except Exception as e:
            logger.error(f"爬取頁面 {url} 失敗: {e}")
            return 0

    def _extract_title(self, item):
        """提取標題 - 改進版"""
        # 嘗試多種標題提取方法
        title_selectors = [
            'div.title',
            '.title',
            'h3',
            'h4',
            'h5', 
            'a[title]',
            'span.title'
        ]
        
        for selector in title_selectors:
            title_element = item.select_one(selector)
            if title_element:
                title = title_element.get_text(strip=True)
                if title and len(title) > 5:
                    return title
        
        # 如果上述都找不到，嘗試從a標籤的title屬性獲取
        link_tag = item.find('a')
        if link_tag and link_tag.get('title'):
            title = link_tag.get('title').strip()
            if len(title) > 5:
                return title
        
        # 最後嘗試從a標籤的文本內容獲取
        if link_tag:
            title = link_tag.get_text(strip=True)
            if len(title) > 5:
                return title
        
        return ""

    def _extract_date(self, item):
        """提取日期 - 改進版"""
        date_selectors = [
            'div.time',
            '.time',
            '.date',
            'span.date',
            'time'
        ]
        
        for selector in date_selectors:
            date_element = item.select_one(selector)
            if date_element:
                date_text = date_element.get_text(strip=True)
                try:
                    # 嘗試解析多種日期格式
                    formats = ['%Y.%m.%d %H:%M', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y.%m.%d']
                    for fmt in formats:
                        try:
                            dtime = datetime.strptime(date_text, fmt)
                            return dtime.strftime("%Y-%m-%d")
                        except:
                            continue
                except:
                    pass
        
        # 如果找不到日期，使用當前日期
        return datetime.now().strftime("%Y-%m-%d")

    def _extract_photo_link(self, item):
        """提取圖片連結"""
        try:
            img_tag = item.find('img')
            if img_tag:
                if img_tag.has_attr('data-src'):
                    return img_tag.get('data-src')
                elif img_tag.has_attr('src'):
                    return img_tag.get('src')
        except:
            pass
        return ''

    def _scrape_article_content(self, url):
        """爬取文章內容 - 改進版"""
        try:
            response = requests.get(url, headers=self.get_random_headers(), timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 嘗試多種內容選擇器
            content_selectors = [
                'div#newscontent',
                'div.content',
                'div[class*="content"]',
                'div[class*="article"]',
                'article',
                'div.news-content'
            ]
            
            content = ""
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    # 清理不需要的元素
                    for unwanted in content_div.find_all(['figure', 'figcaption', 'script', 'style']):
                        unwanted.decompose()
                    
                    content = content_div.get_text(strip=True)
                    content = re.sub(r'責任編輯／.*', '', content)
                    content = re.sub(r'\n+', ' ', content)
                    if len(content) > 50:  # 只有當內容夠長時才返回
                        break
            
            return content
            
        except Exception as e:
            logger.warning(f"爬取內容失敗 {url}: {e}")
        
        return ""

    def test_category_access(self, category_name):
        """測試分類頁面是否可以訪問"""
        encoded_category = quote(category_name)
        url = f"{self.base_url}/category/{encoded_category}"
        
        try:
            response = requests.get(url, headers=self.get_random_headers(), timeout=15)
            logger.info(f"測試分類 '{category_name}': {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                # 檢查頁面是否包含新聞內容
                news_indicators = soup.find_all(['li', 'article', 'div'], limit=10)
                logger.info(f"找到 {len(news_indicators)} 個可能的內容元素")
                return True
            return False
        except Exception as e:
            logger.error(f"測試分類失敗: {e}")
            return False

    def crawl_all_categories(self, max_pages_per_category=3, categories_to_crawl=None):
        """爬取所有分類的新聞"""
        if categories_to_crawl is None:
            categories_to_crawl = ['財經', '政治', '國際']  # 使用正確的中文分類名稱
        
        # 先測試各分類是否可訪問
        logger.info("=== 測試分類訪問性 ===")
        valid_categories = []
        for category in categories_to_crawl:
            if self.test_category_access(category):
                valid_categories.append(category)
                logger.info(f"✓ {category} 分類可訪問")
            else:
                logger.warning(f"✗ {category} 分類無法訪問")
        
        if not valid_categories:
            logger.error("沒有可訪問的分類！")
            return 0, 0
        
        total_ai_news = 0
        total_news = 0
        
        for category_name in valid_categories:
            logger.info(f"\n=== 開始爬取 {category_name} 類別 ===")
            
            category_ai_count = 0
            category_total_count = 0
            
            for page_num in range(1, max_pages_per_category + 1):
                logger.info(f"爬取 {category_name} 第 {page_num} 頁...")
                
                processed = self.scrape_category_page(category_name, page_num)
                
                if processed == 0:
                    logger.info(f"{category_name} 第 {page_num} 頁沒有新聞，停止該分類爬取")
                    break
                
                category_total_count += processed
                
                # 計算AI相關新聞數量
                ai_count_in_page = len([n for n in self.all_news_data[-processed:] if n['is_ai_related']])
                category_ai_count += ai_count_in_page
                
                logger.info(f"{category_name} 第 {page_num} 頁完成，本頁AI新聞: {ai_count_in_page}/{processed}")
                
                # 頁面間延遲
                time.sleep(random.uniform(3, 6))
            
            total_ai_news += category_ai_count
            total_news += category_total_count
            
            logger.info(f"{category_name} 分類完成: AI新聞 {category_ai_count}/{category_total_count}")
        
        logger.info(f"\n爬取完成！總計: AI新聞 {total_ai_news}/{total_news}")
        return total_ai_news, total_news

    def save_to_csv(self, filename=None, ai_only=False):
        """保存數據到CSV"""
        if not self.all_news_data:
            logger.warning("沒有數據可保存")
            return None
        
        # 篩選數據
        data_to_save = [news for news in self.all_news_data if news['is_ai_related']] if ai_only else self.all_news_data
        
        if not data_to_save:
            logger.warning("沒有符合條件的數據")
            return None
        
        # 生成檔案名
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            suffix = "_ai_only" if ai_only else "_all"
            filename = f"ttv_news{suffix}_{timestamp}.csv"
        
        # 確保目錄存在
        os.makedirs('dataset', exist_ok=True)
        filepath = f"dataset/{filename}"
        
        # 轉換為DataFrame並保存
        df = pd.DataFrame(data_to_save)
        
        # 重新排列欄位
        columns = ['item_id', 'date', 'category', 'title', 'content', 'link', 'photo_link', 'is_ai_related']
        df = df[columns]
        
        # 保存
        df.to_csv(filepath, sep='|', index=False, encoding='utf-8-sig')
        
        logger.info(f"數據已保存: {filepath}")
        logger.info(f"共 {len(df)} 條記錄")
        
        return filepath

    def print_statistics(self):
        """印出統計資訊"""
        if not self.all_news_data:
            print("沒有數據")
            return
        
        total_news = len(self.all_news_data)
        ai_news = len([n for n in self.all_news_data if n['is_ai_related']])
        
        print(f"\n{'='*50}")
        print(f"爬取統計報告")
        print(f"{'='*50}")
        print(f"總新聞數量: {total_news}")
        print(f"AI相關新聞: {ai_news}")
        print(f"AI比例: {ai_news/total_news*100:.1f}%" if total_news > 0 else "AI比例: 0%")
        
        # 按分類統計
        print(f"\n按分類統計:")
        for category in set(n['category'] for n in self.all_news_data):
            cat_total = len([n for n in self.all_news_data if n['category'] == category])
            cat_ai = len([n for n in self.all_news_data if n['category'] == category and n['is_ai_related']])
            print(f"  {category}: {cat_ai}/{cat_total}")
        
        # 顯示AI新聞標題
        print(f"\nAI相關新聞標題預覽:")
        ai_news_list = [n for n in self.all_news_data if n['is_ai_related']]
        for i, news in enumerate(ai_news_list[:10], 1):
            print(f"  {i}. {news['title']}")
        
        if len(ai_news_list) > 10:
            print(f"  ... 還有 {len(ai_news_list)-10} 條")

def main():
    """主函數"""
    print("台視新聞AI股票爬蟲開始執行...")
    print("="*60)
    
    crawler = TTVAINewsCrawler()
    
    # 設定爬取參數 - 使用正確的中文分類名稱
    categories_to_crawl = ['財經', '政治', '國際']  
    max_pages = 3  # 每個分類爬取3頁（先測試）
    
    print(f"爬取分類: {categories_to_crawl}")
    print(f"每分類頁數: {max_pages}")
    print(f"預估時間: {len(categories_to_crawl) * max_pages * 2} 分鐘")
    print("-"*60)
    
    # 開始爬取
    start_time = datetime.now()
    ai_count, total_count = crawler.crawl_all_categories(max_pages, categories_to_crawl)
    end_time = datetime.now()
    
    # 顯示統計
    crawler.print_statistics()
    
    # 保存數據
    if total_count > 0:
        print(f"\n正在保存數據...")
        all_file = crawler.save_to_csv(ai_only=False)  # 保存所有新聞
        ai_file = crawler.save_to_csv(ai_only=True)    # 只保存AI新聞
        
        print(f"\n{'='*60}")
        print(f"爬取完成！")
        print(f"執行時間: {end_time - start_time}")
        print(f"全部新聞檔案: {all_file}")
        print(f"AI新聞檔案: {ai_file}")
    else:
        print(f"\n{'='*60}")
        print(f"爬取完成但沒有獲取到數據")
        print(f"執行時間: {end_time - start_time}")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    main()