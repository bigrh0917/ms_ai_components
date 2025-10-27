package com.yizhaoqi.manshu.model;

import jakarta.persistence.*;
import lombok.Data;


@Data
@Entity
@Table(name = "document_vectors")
public class DocumentVector {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long vectorId;

    @Column(nullable = false, length = 32)
    private String fileMd5;

    @Column(nullable = false)
    private Integer chunkId;

    @Lob
    private String textContent;

    @Column(length = 32)
    private String modelVersion;


    @Column(nullable = false, name = "user_id", length = 64)
    private String userId;


    @Column(name = "org_tag", length = 50)
    private String orgTag;


    @Column(name = "is_public", nullable = false)
    private boolean isPublic = false;
}