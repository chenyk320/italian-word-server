#!/bin/bash
set -e  # 出现错误立即退出

# 进入项目目录
cd /var/www/italian-word-app

# 更新代码
git fetch origin main
git reset --hard origin/main

# 安装依赖
source venv/bin/activate
pip install -r requirements.txt

# 收集静态文件
python src/manage.py collectstatic --noinput  # 如果使用Django需添加

# 重启服务
sudo systemctl restart italian-word

# 可选：数据库迁移
# python src/manage.py migrate

echo "Deployment completed successfully"