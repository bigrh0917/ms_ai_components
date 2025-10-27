package com.yizhaoqi.manshu.model;

import jakarta.persistence.*;
import lombok.Data;


@Data
@Entity
@Table(name = "chunk_info")
public class ChunkInfo {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;


    private String fileMd5;


    private int chunkIndex;


    private String chunkMd5;


    private String storagePath;
}