# RAG API - 用户注册认证流程

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp env.example .env
# 编辑 .env 文件，配置数据库、Redis、邮件服务器等
```

### 3. 初始化数据库

```bash
# 初始化 Alembic
alembic init alembic

# 创建迁移脚本
alembic revision --autogenerate -m "创建用户表"

# 执行迁移
alembic upgrade head
```

### 4. 启动服务

```bash
# 开发环境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产环境
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📋 API 接口

### 1. 获取图形验证码

**请求：**
```http
GET /api/v1/auth/captcha
```

**响应：**
```json
{
  "captcha_id": "uuid",
  "captcha_image": "data:image/png;base64,..."
}
```

---

### 2. 发送邮箱验证码

**请求：**
```http
POST /api/v1/auth/send_code
Content-Type: application/json

{
  "email": "user@example.com",
  "captcha_id": "uuid",
  "captcha_code": "X9PQ"
}
```

**响应：**
```json
{
  "temp_token": "jwt-token",
  "message": "验证码已发送到您的邮箱，有效期5分钟"
}
```

---

### 3. 用户注册

**请求：**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "email_code": "123456",
  "temp_token": "jwt-token"
}
```

**响应：**
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "access_token": "jwt-access-token",
  "token_type": "bearer",
  "message": "注册成功"
}
```

---

### 4. 用户登录

**请求：**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应：**
```json
{
  "access_token": "jwt-access-token",
  "token_type": "bearer",
  "user_id": "user-uuid",
  "email": "user@example.com"
}
```

---

## 🔐 安全特性

### 1. 图形验证码
- 随机生成 4 位字符（排除易混淆字符）
- 存储在 Redis，有效期 120 秒
- 使用后立即删除

### 2. 邮箱验证码
- 随机生成 6 位数字
- 存储在 Redis，有效期 300 秒（5分钟）
- 使用后立即删除

### 3. 临时令牌（temp_token）
- JWT 格式，有效期 5 分钟
- 用于关联图形验证和邮箱验证流程
- 防止跳过图形验证直接注册

### 4. 速率限制
- 图形验证码：每 IP 每分钟最多 10 次
- 邮箱验证码：每邮箱每分钟最多 3 次
- 用户注册：每 IP 每小时最多 5 次

### 5. 密码安全
- 使用 bcrypt 哈希
- 最小长度 6 位
- 存储哈希值，不存储明文

---

## 📊 数据流程图

```
1. 用户访问注册页面
   ↓
2. 请求图形验证码
   GET /api/v1/auth/captcha
   ← 返回 captcha_id + 图片
   ↓
3. 用户填写邮箱并输入图形验证码
   POST /api/v1/auth/send_code
   → 验证图形验证码
   → 生成 temp_token
   → 生成邮箱验证码
   → 异步发送邮件
   ← 返回 temp_token
   ↓
4. 用户收到邮件，输入验证码和密码
   POST /api/v1/auth/register
   → 验证 temp_token
   → 验证邮箱验证码
   → 创建用户
   ← 返回 access_token（自动登录）
```

---

## 🗄️ Redis 键设计

```
# 图形验证码
captcha:<uuid> = "X9PQ"
TTL: 120s

# 邮箱验证码
email_code:<email> = "123456"
TTL: 300s

# 速率限制
rate_limit:captcha:<ip> = count
TTL: 60s

rate_limit:email_code:<email> = count
TTL: 60s

rate_limit:register:<ip> = count
TTL: 3600s
```

---

## 🛠️ 邮件配置（以 Gmail 为例）

### 1. 启用两步验证

登录 Google 账号 → 安全性 → 两步验证

### 2. 生成应用专用密码

登录 Google 账号 → 安全性 → 应用专用密码 → 生成

### 3. 配置 .env

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

---

## ⚠️ 注意事项

1. **生产环境必须修改 SECRET_KEY**（至少 32 位随机字符）
2. **配置真实的邮件服务器**
3. **PostgreSQL 和 Redis 必须正确配置**
4. **建议使用 Nginx 反向代理**
5. **启用 HTTPS**

---

## 📦 目录结构

```
rag/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   └── auth.py          # 认证接口
│   │   ├── __init__.py
│   │   └── deps.py              # 依赖注入
│   ├── clients/
│   │   └── redis_client.py      # Redis 客户端
│   ├── core/
│   │   └── config.py            # 配置
│   ├── models/
│   │   └── user.py              # 用户模型
│   ├── schemas/
│   │   └── auth.py              # 数据模型
│   ├── services/
│   │   └── email_service.py     # 邮件服务
│   ├── utils/
│   │   ├── captcha.py           # 验证码工具
│   │   ├── email_code.py        # 邮箱验证码
│   │   ├── rate_limit.py        # 速率限制
│   │   └── security.py          # 安全工具
│   └── main.py                  # 应用入口
├── alembic/                     # 数据库迁移
├── requirements.txt             # 依赖
├── env.example                  # 环境变量示例
└── README_API.md                # 本文档
```

---

## 🧪 测试流程

### 使用 curl 测试

```bash
# 1. 获取图形验证码
curl http://localhost:8000/api/v1/auth/captcha

# 2. 发送邮箱验证码（替换实际的 captcha_id 和 captcha_code）
curl -X POST http://localhost:8000/api/v1/auth/send_code \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "captcha_id": "your-captcha-id",
    "captcha_code": "X9PQ"
  }'

# 3. 注册用户（替换实际的验证码和 temp_token）
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "email_code": "123456",
    "temp_token": "your-temp-token"
  }'

# 4. 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

---

## 🎉 完成！

后端用户注册认证系统已完成，包括：

✅ 图形验证码生成和验证  
✅ 邮箱验证码发送  
✅ 用户注册（自动登录）  
✅ 用户登录  
✅ 速率限制  
✅ 安全优化（temp_token、验证码大小写处理、防重复请求）  

现在可以启动服务并测试所有功能！🚀

