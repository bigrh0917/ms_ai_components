package com.yizhaoqi.manshu.entity;

import lombok.Getter;
import lombok.Setter;


@Setter
@Getter
public class TextChunk {

    private int chunkId;
    private String content;


    public TextChunk(int chunkId, String content) {
        this.chunkId = chunkId;
        this.content = content;
    }
}