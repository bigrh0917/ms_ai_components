package com.yizhaoqi.manshu.model;

import jakarta.persistence.*;
import lombok.Data;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;


@Data
@Entity
@Table(name = "file_upload")
public class FileUpload {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "file_md5", length = 32, nullable = false)
    private String fileMd5;


    private String fileName;


    private long totalSize;


    private int status;


    @Column(name = "user_id", length = 64, nullable = false)
    private String userId;


    @Column(name = "org_tag")
    private String orgTag;


    @Column(name = "is_public", nullable = false)
    private boolean isPublic = false;


    @CreationTimestamp
    private LocalDateTime createdAt;


    @UpdateTimestamp
    private LocalDateTime mergedAt;
}