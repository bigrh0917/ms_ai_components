package com.yizhaoqi.manshu.controller;

import com.yizhaoqi.manshu.service.HybridSearchService;
import com.yizhaoqi.manshu.utils.LogUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import com.yizhaoqi.manshu.entity.SearchResult;

import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.Collections;


@RestController
@RequestMapping("/api/v1/search")
public class SearchController {

    @Autowired
    private HybridSearchService hybridSearchService;


    @GetMapping("/hybrid")
    public Map<String, Object> hybridSearch(@RequestParam String query,
                                            @RequestParam(defaultValue = "10") int topK,
                                            @RequestAttribute(value = "userId", required = false) String userId) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("HYBRID_SEARCH");
        try {
            LogUtils.logBusiness("HYBRID_SEARCH", userId != null ? userId : "anonymous",
                    "English text: query=%s, topK=%d", query, topK);

            List<SearchResult> results;
            if (userId != null) {

                results = hybridSearchService.searchWithPermission(query, userId, topK);
            } else {

                results = hybridSearchService.search(query, topK);
            }

            LogUtils.logUserOperation(userId != null ? userId : "anonymous", "HYBRID_SEARCH",
                    "search_query", "SUCCESS");
            LogUtils.logBusiness("HYBRID_SEARCH", userId != null ? userId : "anonymous",
                    "English text: English text=%d", results.size());
            monitor.end("English text");


            Map<String, Object> responseBody = new HashMap<>(4);
            responseBody.put("code", 200);
            responseBody.put("message", "success");
            responseBody.put("data", results);

            return responseBody;
        } catch (Exception e) {
            LogUtils.logBusinessError("HYBRID_SEARCH", userId != null ? userId : "anonymous",
                    "English text: query=%s", e, query);
            monitor.end("English text: " + e.getMessage());


            Map<String, Object> errorBody = new HashMap<>(4);
            errorBody.put("code", 500);
            errorBody.put("message", e.getMessage());
            errorBody.put("data", Collections.emptyList());
            return errorBody;
        }
    }
}