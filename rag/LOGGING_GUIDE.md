# 日志系统使用指南

## 📝 配置说明

项目已配置完整的日志系统，包括：

### 日志文件

```
logs/
├── app.log      # 主日志文件（INFO 及以上）
├── error.log    # 错误日志文件（ERROR 及以上）
└── daily.log    # 按天轮转的日志（生产环境）
```

### 日志级别

- **DEBUG**: 详细调试信息（仅开发环境）
- **INFO**: 常规信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

---

## 🚀 使用方法

### 1. 在模块中使用日志

```python
from app.utils.logger import get_logger

# 创建 logger（建议使用 __name__）
logger = get_logger(__name__)

# 记录不同级别的日志
logger.debug("这是调试信息")
logger.info("这是普通信息")
logger.warning("这是警告信息")
logger.error("这是错误信息")
logger.critical("这是严重错误")
```

### 2. 记录异常堆栈

```python
try:
    # 业务代码
    result = do_something()
except Exception as e:
    # 自动记录完整的异常堆栈
    logger.error("操作失败", exc_info=True)
```

### 3. 记录结构化信息

```python
logger.info(f"用户登录 | 用户ID: {user_id} | IP: {client_ip}")
```

### 4. 敏感信息脱敏

```python
from app.utils.logger import mask_sensitive

# 脱敏邮箱
masked_email = mask_sensitive("user@example.com", visible=3)
logger.info(f"用户注册 | 邮箱: {masked_email}")
# 输出: 用户注册 | 邮箱: use**********

# 脱敏手机号
masked_phone = mask_sensitive("13800138000", visible=4)
logger.info(f"手机号: {masked_phone}")
# 输出: 手机号: 1380*******
```

---

## 💡 最佳实践

### ✅ 应该记录的内容

```python
# 1. 用户关键操作
logger.info(f"用户注册成功 | 邮箱: {email} | ID: {user_id}")
logger.info(f"用户登录 | 邮箱: {email} | IP: {client_ip}")

# 2. 业务逻辑错误
logger.warning(f"登录失败 - 密码错误 | 邮箱: {email}")

# 3. 系统错误
logger.error("数据库连接失败", exc_info=True)

# 4. 性能问题
logger.warning(f"查询超时 | 耗时: {duration}ms | SQL: {sql}")

# 5. 安全事件
logger.warning(f"可疑登录尝试 | IP: {ip} | 次数: {count}")
```

### ❌ 不应该记录的内容

```python
# ❌ 不要记录密码
logger.info(f"用户密码: {password}")  # 危险！

# ❌ 不要在循环中大量日志
for item in large_list:
    logger.debug(f"处理项: {item}")  # 会产生海量日志

# ❌ 不要记录完整的敏感数据
logger.info(f"用户信息: {user}")  # 可能包含敏感字段
```

---

## 📊 日志示例

### 启动日志

```
2025-10-24 15:30:00 | INFO     | ============================================================
2025-10-24 15:30:00 | INFO     | 日志系统初始化完成 | 环境: 开发
2025-10-24 15:30:00 | INFO     | 日志目录: C:\...\logs
2025-10-24 15:30:00 | INFO     | 日志级别: DEBUG
2025-10-24 15:30:00 | INFO     | ============================================================
2025-10-24 15:30:01 | INFO     | FastAPI 应用启动中...
2025-10-24 15:30:01 | INFO     | ✓ MySQL 数据库连接成功
2025-10-24 15:30:01 | INFO     | ✓ Redis 连接成功
2025-10-24 15:30:01 | INFO     | FastAPI 应用启动完成！
```

### 业务日志

```
2025-10-24 15:31:00 | INFO     | 请求图形验证码 | IP: 127.0.0.1
2025-10-24 15:31:00 | INFO     | 生成图形验证码成功 | IP: 127.0.0.1 | ID: a3f8c2d1...
2025-10-24 15:31:15 | INFO     | 请求发送验证码 | 邮箱: use**********
2025-10-24 15:31:15 | INFO     | 邮箱验证码发送成功 | 邮箱: use**********
2025-10-24 15:31:45 | INFO     | 用户开始注册 | 邮箱: use**********
2025-10-24 15:31:46 | INFO     | 用户注册成功 | 邮箱: use********** | ID: b4e9d3f2...
```

### 错误日志

```
2025-10-24 15:32:00 | WARNING  | 图形验证码错误 | 邮箱: use**********
2025-10-24 15:33:00 | ERROR    | 数据库连接失败
Traceback (most recent call last):
  File "app/api/v1/auth.py", line 123, in register
    await db.execute(query)
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server")
```

---

## 🔍 日志查看命令

### Windows PowerShell

```powershell
# 实时查看日志
Get-Content logs\app.log -Wait

# 查看最后 50 行
Get-Content logs\app.log -Tail 50

# 搜索错误日志
Select-String "ERROR" logs\app.log

# 搜索特定用户
Select-String "user@example.com" logs\app.log
```

### Linux/Mac

```bash
# 实时查看日志
tail -f logs/app.log

# 查看最后 50 行
tail -n 50 logs/app.log

# 搜索错误日志
grep "ERROR" logs/app.log

# 统计错误数量
grep -c "ERROR" logs/app.log
```

---

## ⚙️ 环境配置

### 开发环境（DEBUG=True）

- 日志级别：DEBUG
- 输出：控制台 + 文件
- 格式：简洁

### 生产环境（DEBUG=False）

- 日志级别：INFO
- 输出：控制台 + 文件 + 按天轮转
- 格式：详细（包含文件名、行号）

---

## 📌 注意事项

1. **不要删除 logs 目录**：日志系统会自动创建
2. **日志自动轮转**：单个文件超过 10MB 会自动轮转，保留 5 个备份
3. **定期清理**：按天轮转的日志保留 30 天
4. **敏感信息**：使用 `mask_sensitive()` 函数脱敏
5. **性能影响**：DEBUG 级别会产生大量日志，仅在开发环境使用

---

## 🎯 快速开始

```python
# 1. 导入 logger
from app.utils.logger import get_logger, mask_sensitive

# 2. 创建 logger
logger = get_logger(__name__)

# 3. 记录日志
logger.info("操作成功")
logger.error("操作失败", exc_info=True)

# 4. 脱敏敏感信息
masked = mask_sensitive("sensitive_data")
logger.info(f"数据: {masked}")
```

---

完整配置见：`app/utils/logger.py`

