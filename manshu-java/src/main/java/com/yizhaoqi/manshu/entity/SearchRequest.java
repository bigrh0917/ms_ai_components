package com.yizhaoqi.manshu.entity;

import lombok.Data;

@Data
public class SearchRequest {
    private String query;
    private int topK;
}