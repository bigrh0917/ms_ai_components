# Docker 部署指南

## 📋 前置要求

- Docker >= 20.10
- Docker Compose >= 2.0

## 🚀 快速开始

### 1. 配置环境变量

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要的环境变量：

```env
# 数据库配置（Docker会自动使用服务名）
DATABASE_HOST=mysql
DATABASE_PORT=3306
DATABASE_USER=root
DATABASE_PASSWORD=your_password
DATABASE_NAME=fastapi

# Redis配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Elasticsearch配置
ES_HOST=http://elasticsearch:9200
ES_DEFAULT_INDEX=default

# MinIO配置
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=False
MINIO_DEFAULT_BUCKET=default

# Kafka配置
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_DEFAULT_TOPIC=default

# 其他配置...
```

### 2. 启动服务

#### 开发环境

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f fastapi-app

# 查看所有服务状态
docker-compose ps
```

#### 生产环境

```bash
# 使用生产环境配置
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f fastapi-app
```

### 3. 验证部署

访问健康检查端点：

```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细健康检查（包含所有服务状态）
curl http://localhost:8000/health/detailed
```

访问 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📦 包含的服务

### 必需服务

1. **FastAPI 应用** (端口 8000)
   - 主应用服务
   - 支持动态 workers 数量

2. **MySQL 8.0** (端口 3306)
   - 主数据库
   - 数据持久化

3. **Redis 7** (端口 6379)
   - 缓存和会话存储
   - 支持 AOF 持久化

4. **Elasticsearch 8.11.0** (端口 9200)
   - 搜索引擎
   - 向量检索和全文检索

5. **MinIO** (端口 9000, 控制台 9001)
   - 对象存储
   - S3 兼容 API

### 可选服务

6. **Kafka** (端口 9092)
   - 消息队列
   - 需要 Zookeeper (端口 2181)

## 🔧 常用命令

### 启动和停止

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v

# 重启服务
docker-compose restart fastapi-app
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f fastapi-app
docker-compose logs -f mysql
docker-compose logs -f elasticsearch
```

### 进入容器

```bash
# 进入 FastAPI 应用容器
docker-compose exec fastapi-app bash

# 进入 MySQL 容器
docker-compose exec mysql bash

# 进入 Redis 容器
docker-compose exec redis sh
```

### 数据库操作

```bash
# 连接 MySQL
docker-compose exec mysql mysql -uroot -p${DATABASE_PASSWORD} ${DATABASE_NAME}

# 连接 Redis CLI
docker-compose exec redis redis-cli
```

### 数据备份和恢复

```bash
# 备份 MySQL 数据
docker-compose exec mysql mysqldump -uroot -p${DATABASE_PASSWORD} ${DATABASE_NAME} > backup.sql

# 恢复 MySQL 数据
docker-compose exec -T mysql mysql -uroot -p${DATABASE_PASSWORD} ${DATABASE_NAME} < backup.sql
```

## 🔍 服务健康检查

所有服务都配置了健康检查：

```bash
# 查看服务健康状态
docker-compose ps

# 查看健康检查详情
docker inspect fastapi-app-local | grep -A 10 Healthcheck
```

## ⚙️ 配置说明

### Workers 数量

默认情况下，FastAPI 应用会根据 CPU 核心数自动设置 workers：

```bash
workers = (CPU核心数 * 2) + 1
```

可以通过环境变量手动设置：

```env
WORKERS=8
```

### 资源限制

生产环境配置（`docker-compose.prod.yml`）包含资源限制：

- FastAPI: 2 CPU, 2GB 内存
- MySQL: 1 CPU, 1GB 内存
- Elasticsearch: 2 CPU, 2GB 内存
- MinIO: 1 CPU, 1GB 内存
- Kafka: 1 CPU, 1GB 内存

### 数据持久化

所有数据都保存在 Docker volumes 中：

- `mysql-data`: MySQL 数据
- `redis-data`: Redis 数据
- `elasticsearch-data`: Elasticsearch 索引数据
- `minio-data`: MinIO 对象存储数据

## 🐛 故障排查

### 服务无法启动

1. 检查端口占用：
   ```bash
   netstat -tulpn | grep -E '8000|3306|6379|9200|9000|9092'
   ```

2. 查看服务日志：
   ```bash
   docker-compose logs fastapi-app
   ```

3. 检查服务健康状态：
   ```bash
   curl http://localhost:8000/health/detailed
   ```

### 数据库连接失败

1. 确保 MySQL 服务已启动：
   ```bash
   docker-compose ps mysql
   ```

2. 检查数据库配置：
   ```bash
   docker-compose exec fastapi-app env | grep DATABASE
   ```

3. 测试数据库连接：
   ```bash
   docker-compose exec mysql mysql -uroot -p${DATABASE_PASSWORD} -e "SELECT 1;"
   ```

### Elasticsearch 启动缓慢

Elasticsearch 需要较长时间启动（通常 30-60 秒）。如果启动失败，检查：

1. 内存限制是否足够（至少 512MB）
2. 系统 ulimits 配置
3. 查看日志：
   ```bash
   docker-compose logs elasticsearch
   ```

## 📝 注意事项

1. **生产环境部署**：
   - 使用 `docker-compose.prod.yml`
   - 修改所有默认密码
   - 启用 HTTPS（建议使用 Nginx 反向代理）
   - 配置防火墙规则

2. **数据备份**：
   - 定期备份 MySQL 数据
   - 定期备份 Elasticsearch 索引
   - 备份 MinIO 数据

3. **安全建议**：
   - 不要将 `.env` 文件提交到版本控制
   - 使用强密码
   - 限制端口暴露（仅暴露必要端口）
   - 使用 Docker secrets 管理敏感信息

## 🔗 相关链接

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Elasticsearch 文档](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [MinIO 文档](https://min.io/docs/)

