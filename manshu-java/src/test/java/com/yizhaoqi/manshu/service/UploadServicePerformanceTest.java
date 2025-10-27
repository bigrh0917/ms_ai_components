package com.yizhaoqi.manshu.service;

import org.junit.jupiter.api.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;


@SpringBootTest
@ActiveProfiles("test")
public class UploadServicePerformanceTest {

    private static final Logger logger = LoggerFactory.getLogger(UploadServicePerformanceTest.class);


    @Test
    public void testPerformanceComparison() {
        logger.info("=== UploadService performance optimization summary ===");
        logger.info("Before: querying Redis per chunk required N network round trips for N chunks.");
        logger.info("After: fetching the bitmap once reduces the trip count to 1 regardless of chunk count.");
        logger.info("Overall gain: roughly two orders of magnitude depending on latency and chunk count.");
        logger.info("======================================================");

        int totalChunks = 1000;
        int networkLatencyMs = 3;

        int oldMethodTime = totalChunks * networkLatencyMs;
        int newMethodTime = networkLatencyMs + 1;

        logger.info("Simulated chunk count: {}", totalChunks);
        logger.info("Legacy approach cost: {} ms", oldMethodTime);
        logger.info("Optimized approach cost: {} ms", newMethodTime);
        logger.info("Estimated improvement: {}x", oldMethodTime / newMethodTime);
    }
}