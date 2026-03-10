import os
import re
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'https://openapi.naver.com/v1/search/news.json'
CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = PROJECT_ROOT / 'data' / 'raw' / 'economy_news.csv'

# 경제 관련 검색 키워드
ECONOMY_QUERIES = ['금리', '환율', '주식', '코스피', '부동산', '인플레이션', '수출', '무역수지']


def _parse_response(payload):
    """
    API 응답 JSON 파싱
        payload: API 응답 JSON
    """
    items = payload.get('items', [])
    total_cnt = payload.get('total', 0)
    return items, total_cnt
    """
    items: 기사 리스트
    total_count: 전체 검색 결과 수
    """

def _clean_html(text):
    """HTML 태그 및 특수문자 제거"""
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)  # &amp; &lt; 등 HTML 엔티티 제거
    return text.strip()


def fetch_news_data(query, start=1, display=100):
    """
    네이버 뉴스 검색 API 호출
        query: 검색 키워드
        start: 검색 시작 위치 (1~1000)
        display: 한 번에 가져올 결과 수 (최대 100)
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError('[CRAWL_NEWS] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수 설정 필요')

    headers = {
        'X-Naver-Client-Id': CLIENT_ID,
        'X-Naver-Client-Secret': CLIENT_SECRET,
    }
    params = {
        'query': query,
        'start': start,
        'display': display,
        'sort': 'date',  # date: 최신순 / sim: 정확도순
    }

    # 1. API 호출
    try:
        response = requests.get(BASE_URL, headers=headers, params=params)
        response.raise_for_status()
        payload = response.json()

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f'[CRAWL_NEWS] API 호출 오류: {e}')
    except ValueError as e:
        raise RuntimeError(f'[CRAWL_NEWS] JSON 파싱 오류: {e}')

    # 2. 응답 파싱
    items, total_cnt = _parse_response(payload)

    # 3. 텍스트 정제
    rows = []
    for item in items:
        rows.append({
            'title': _clean_html(item.get('title', '')),
            'description': _clean_html(item.get('description', '')),
            'pub_date': item.get('pubDate', ''),
            'link': item.get('originallink') or item.get('link', ''),
            'query': query,
        })

    return pd.DataFrame(rows), total_cnt


def save_news_data(output_path=OUTPUT_PATH, queries=ECONOMY_QUERIES, max_rows=None):
    """
    경제 뉴스 데이터를 수집하여 data/raw/ 에 CSV로 저장
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    print(f'[CRAWL_NEWS] 경제 뉴스 수집 시작: {output_path}')

    DISPLAY = 100          # 네이버 API 최대 100건/호출
    MAX_START = 1000       # 네이버 API start 최대값 제한
    all_dfs = []

    for query in queries:
        print(f'\n[CRAWL_NEWS] 키워드: [{query}] 수집 중...')

        # 첫 페이지 호출로 총 건수 확인
        df_init, total_cnt = fetch_news_data(query, start=1, display=DISPLAY)
        all_dfs.append(df_init)

        fetchable = min(total_cnt, MAX_START)  # API 제한상 최대 1000건까지
        total_pages = (fetchable + DISPLAY - 1) // DISPLAY

        print(f'[CRAWL_NEWS] [{query}] 전체: {total_cnt}건 | 수집 가능: {fetchable}건')

        # 나머지 페이지 수집
        for page in range(2, total_pages + 1):
            start_idx = (page - 1) * DISPLAY + 1
            try:
                df_page, _ = fetch_news_data(query, start=start_idx, display=DISPLAY)
                all_dfs.append(df_page)

                current_total = sum(len(d) for d in all_dfs)
                print(f'[CRAWL_NEWS] [{query}] {page}/{total_pages} 완료 (누적: {current_total}건)')

                if max_rows and current_total >= max_rows:
                    break

                time.sleep(0.1)  # API 호출 간격 (초당 10회 제한)

            except Exception as e:
                raise RuntimeError(f'[CRAWL_NEWS] [{query}] {page}페이지 수집 실패: {e}')

        if max_rows and sum(len(d) for d in all_dfs) >= max_rows:
            break

    df = pd.concat(all_dfs, ignore_index=True)
    df = df.drop_duplicates(subset=['link'])  # 중복 기사 제거

    if max_rows:
        df = df.head(max_rows)

    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'\n[CRAWL_NEWS] 수집 완료: {len(df)}건 → {path}')


if __name__ == '__main__':
    save_news_data()