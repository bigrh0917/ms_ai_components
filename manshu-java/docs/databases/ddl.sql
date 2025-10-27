CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Unique user identifier',
    username VARCHAR(255) NOT NULL UNIQUE COMMENT 'Login name (unique)',
    password VARCHAR(255) NOT NULL COMMENT 'BCrypt hashed password',
    role ENUM('USER', 'ADMIN') NOT NULL DEFAULT 'USER' COMMENT 'Authorization role',
    org_tags VARCHAR(255) DEFAULT NULL COMMENT 'Comma-separated organization tags',
    primary_org VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Primary organization tag',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Tenant-aware user registry';

CREATE TABLE organization_tags (
    tag_id VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin PRIMARY KEY COMMENT 'Organization tag identifier',
    name VARCHAR(100) NOT NULL COMMENT 'Display name',
    description TEXT COMMENT 'Optional description',
    parent_tag VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Parent tag (if nested)',
    created_by BIGINT NOT NULL COMMENT 'Creator user id',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    FOREIGN KEY (parent_tag) REFERENCES organization_tags(tag_id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Organization/tag metadata';

CREATE TABLE file_upload (
    id BIGINT NOT NULL AUTO_INCREMENT COMMENT 'Primary key',
    file_md5 VARCHAR(32) NOT NULL COMMENT 'MD5 hash of the uploaded file',
    file_name VARCHAR(255) NOT NULL COMMENT 'Original file name',
    total_size BIGINT NOT NULL COMMENT 'Total size in bytes',
    status TINYINT NOT NULL DEFAULT 0 COMMENT 'Upload status flag',
    user_id VARCHAR(64) NOT NULL COMMENT 'Uploader identifier',
    org_tag VARCHAR(50) DEFAULT NULL COMMENT 'Organization tag scope',
    is_public BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Whether the file is public',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Creation timestamp',
    merged_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT 'Time the chunks were merged',
    PRIMARY KEY (id),
    UNIQUE KEY uk_md5_user (file_md5, user_id),
    INDEX idx_user (user_id),
    INDEX idx_org_tag (org_tag)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='File upload ledger';

CREATE TABLE chunk_info (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Chunk record identifier',
    file_md5 VARCHAR(32) NOT NULL COMMENT 'Parent file MD5',
    chunk_index INT NOT NULL COMMENT 'Chunk sequence number',
    chunk_md5 VARCHAR(32) NOT NULL COMMENT 'Chunk level MD5 hash',
    storage_path VARCHAR(255) NOT NULL COMMENT 'Path to the chunk inside the object store'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Chunk metadata table';

CREATE TABLE document_vectors (
    vector_id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'Vector record identifier',
    file_md5 VARCHAR(32) NOT NULL COMMENT 'Related file MD5 hash',
    chunk_id INT NOT NULL COMMENT 'Chunk reference',
    text_content TEXT COMMENT 'Chunk text used to build the vector',
    model_version VARCHAR(32) COMMENT 'Embedding model version',
    user_id VARCHAR(64) NOT NULL COMMENT 'Uploader identifier',
    org_tag VARCHAR(50) COMMENT 'Organization tag scope',
    is_public BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Whether the chunk is publicly searchable'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Semantic vector storage';