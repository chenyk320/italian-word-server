from flask import Flask, render_template, jsonify, request
from deep_translator import GoogleTranslator
from deep_translator.exceptions import (
    TranslationNotFound,
    NotValidPayload,
    RequestError
)
from requests.exceptions import ReadTimeout, ConnectTimeout
import json
import os
from datetime import datetime
from math import ceil
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import logging

# 初始化应用
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# 配置参数
HISTORY_DIR = os.getenv("HISTORY_DIR", "/home/chen/italian-word-server/data/")
TRANSLATE_TIMEOUT = int(os.getenv("TRANSLATE_TIMEOUT", "10"))
PER_PAGE = int(os.getenv("PER_PAGE", "50"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

# 初始化线程池
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

def get_available_dates():
    """获取所有历史日期"""
    files = [f for f in os.listdir(HISTORY_DIR) if f.startswith("word_data_")]
    return sorted([f[10:-5] for f in files], reverse=True)

@lru_cache(maxsize=5000)
def get_cached_translation(text: str) -> str:
    """带缓存和异常处理的翻译函数"""
    try:
        return GoogleTranslator(
            source='auto',
            target='zh-CN'
        ).translate(
            text,
            timeout=TRANSLATE_TIMEOUT
        )
    except (
        TranslationNotFound,
        NotValidPayload,
        RequestError,
        ReadTimeout,
        ConnectTimeout
    ) as e:
        app.logger.warning(f"翻译失败 [{text[:20]}]: {str(e)}")
        return "翻译暂不可用"
    except Exception as e:
        app.logger.error(f"未知翻译错误 [{text[:20]}]: {str(e)}")
        return "翻译错误"

def process_word(word: dict) -> dict:
    """处理单个单词的格式化"""
    text = word.get('text', '').strip().lower()
    if not text:
        return None

    return {
        "word": text,
        "translation": get_cached_translation(text),
        "count": word.get('count', 0),
        "date": word.get('date', '')
    }

@app.route('/')
def index():
    return render_template('index.html', dates=get_available_dates())

@app.route('/words')
def get_words():
    try:
        # 参数处理
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        sort_order = request.args.get('sort', 'desc').lower()
        page = max(1, int(request.args.get('page', 1)))
        
        # 数据加载
        file_path = os.path.join(HISTORY_DIR, f"word_data_{date_str}.json")
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # 数据预处理
        valid_data = [
            w for w in raw_data 
            if isinstance(w.get('count', 0), (int, float)) and w.get('text')
        ]
        
        # 排序逻辑
        reverse_sort = sort_order == 'desc'
        sorted_data = sorted(
            valid_data,
            key=lambda x: x['count'],
            reverse=reverse_sort
        )

        # 分页处理
        total_words = len(sorted_data)
        total_pages = ceil(total_words / PER_PAGE)
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * PER_PAGE
        end_idx = start_idx + PER_PAGE
        paged_data = sorted_data[start_idx:end_idx]

        # 并行处理翻译
        processed_words = list(
            filter(None, executor.map(process_word, paged_data))
        )

        return jsonify({
            "words": processed_words,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_words": total_words,
                "per_page": PER_PAGE
            }
        })
    
    except FileNotFoundError:
        app.logger.error(f"数据文件不存在: {date_str}")
        return jsonify({"error": f"{date_str} 数据不存在"}), 404
    except json.JSONDecodeError:
        app.logger.error(f"数据文件格式错误: {date_str}")
        return jsonify({"error": "数据解析失败"}), 500
    except Exception as e:
        app.logger.error(f"服务器错误: {str(e)}", exc_info=True)
        return jsonify({"error": "服务器内部错误"}), 500

if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', '5001')),
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    )
