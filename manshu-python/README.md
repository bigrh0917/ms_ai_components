```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp env.example .env

# 初始化数据库
python scripts/init_db.py

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```



minio
minio.exe server C:\minio-data --console-address ":9001"

