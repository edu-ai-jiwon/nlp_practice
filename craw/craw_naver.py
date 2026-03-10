import os
import re
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

#상수
BASE_URL = 'https://openapi.naver.com/v1/search/news.json'
CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = PROJECT_ROOT / 'data' / 'raw' / 'economy_news.csv'

# 경제 관련 검색 키워드
ECONOMY_QUERIES = ['금리', '환율', '주식', '코스피', '부동산', '인플레이션', '수출', '무역수지']

def parse_response(load):
    """
    API 응답 JSON 파싱하기
    load: API 응답 JSON
    """
    items=load.get('itmes',[])
    total_count=load.get('toal',0)
    # itmes:기사리스트
    # total_count: 전체 검색 결과 수

def clean_html(text):
    """
    HTML 태그 및 특수문자 제거과정"""
    text=re.sub(r'<.?>','',text)
    text=re.sub(r'&[a-zA-Z]+;', '',text)

def featch_news_data(query, start=1, display=100):
    """
    네이버 뉴스 검색 API 호출과정
    auery: 검색 키워드
    start: 검색 시작 위치 (1~1000)
    display: 한 번 가져올 때 결과"""

    try:
        response = requests.get(BASE_URL, headers=headers, params=params)
        response.raise_for_status()
        load = response.json()
    items, total_count = parse_response(load)

    rows = []
    for item in items:
        rows.append({
            'title': clean_html(item.get('title', '')),
            'description': clean_html(item.get('description', '')),
            'pub_date': item.get('pubDate', ''),
            'link': item.get('originallink') or item.get('link', ''),
            'query': query,
        })

    
