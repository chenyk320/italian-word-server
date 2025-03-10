import os
from decouple import config  # 推荐安装python-decouple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 应用配置
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here')

# 路径配置
DATA_DIR = os.path.join(BASE_DIR, 'data')
STATIC_ROOT = os.path.join(BASE_DIR, 'src/static')