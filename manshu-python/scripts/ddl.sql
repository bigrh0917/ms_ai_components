1. 用户表 `users`

```sql
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户唯一标识',
    username VARCHAR(255) NOT NULL UNIQUE COMMENT '用户名，唯一',
    password VARCHAR(255) NOT NULL COMMENT '加密后的密码',
    role ENUM('USER', 'ADMIN') NOT NULL DEFAULT 'USER' COMMENT '用户角色',
    org_tags VARCHAR(255) DEFAULT NULL COMMENT '用户所属组织标签，多个用逗号分隔',
    primary_org VARCHAR(50) DEFAULT NULL COMMENT '用户主组织标签',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username) COMMENT '用户名索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
```

---

2. 组织标签表 `organization_tags`

```sql
CREATE TABLE organization_tags (
    tag_id VARCHAR(50) PRIMARY KEY COMMENT '标签唯一标识',
    name VARCHAR(100) NOT NULL COMMENT '标签名称',
    description TEXT COMMENT '描述',
    parent_tag VARCHAR(50) DEFAULT NULL COMMENT '父标签ID',
    created_by BIGINT NOT NULL COMMENT '创建者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (parent_tag) REFERENCES organization_tags(tag_id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='组织标签表';
```

---

3. 文件主表 `file_upload`

```sql
CREATE TABLE file_upload (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    file_md5 CHAR(32) NOT NULL COMMENT '文件MD5指纹',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名称',
    total_size BIGINT NOT NULL COMMENT '文件大小（字节）',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '上传状态：0=上传中，1=已完成，2=失败',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    org_tag VARCHAR(50) DEFAULT NULL COMMENT '组织标签',
    is_public BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否公开',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    merged_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '合并时间',
    UNIQUE KEY uk_md5_user (file_md5, user_id),
    INDEX idx_user (user_id),
    INDEX idx_org_tag (org_tag),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (org_tag) REFERENCES organization_tags(tag_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件上传记录表';
```

---

4. 文件分片表 `chunk_info`

```sql
CREATE TABLE chunk_info (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    file_md5 CHAR(32) NOT NULL COMMENT '文件MD5（外键）',
    chunk_index INT NOT NULL COMMENT '分片序号（0-based）',
    chunk_md5 CHAR(32) NOT NULL COMMENT '分片MD5校验',
    storage_path VARCHAR(255) NOT NULL COMMENT '分片存储路径（如 MinIO URL）',
    FOREIGN KEY (file_md5) REFERENCES file_upload(file_md5) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_file_chunk (file_md5, chunk_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件分片信息表';
```

---

5. 文档向量表 `document_vectors`

```sql
CREATE TABLE document_vectors (
    vector_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键，自增ID',
    file_md5 CHAR(32) NOT NULL COMMENT '文件指纹（关联file_upload表）',
    chunk_id INT NOT NULL COMMENT '文本分块序号',
    text_content LONGTEXT COMMENT '原始文本内容',
    model_version VARCHAR(32) DEFAULT 'all-MiniLM-L6-v2' COMMENT '生成向量所使用的模型版本',
    FOREIGN KEY (file_md5) REFERENCES file_upload(file_md5) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_file_chunk (file_md5, chunk_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文档向量化结果表';
```