package com.yizhaoqi.manshu.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.util.retry.Retry;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;


@Component
public class EmbeddingClient {

    @Value("${embedding.api.model}")
    private String modelId;

    @Value("${embedding.api.batch-size:100}")
    private int batchSize;

    @Value("${embedding.api.dimension:2048}")
    private int dimension;

    private static final Logger logger = LoggerFactory.getLogger(EmbeddingClient.class);
    private final WebClient webClient;
    private final ObjectMapper objectMapper;

    public EmbeddingClient(WebClient embeddingWebClient, ObjectMapper objectMapper) {
        this.webClient = embeddingWebClient;
        this.objectMapper = objectMapper;
    }


    public List<float[]> embed(List<String> texts) {
        try {
            logger.info("Starting embedding generation, number of texts {}", texts.size());

            List<float[]> all = new ArrayList<>(texts.size());
            for (int start = 0; start < texts.size(); start += batchSize) {
                int end = Math.min(start + batchSize, texts.size());
                List<String> sub = texts.subList(start, end);
                logger.debug("Calling embedding API, batch range: {}-{} (size={})", start, end - 1, sub.size());
                String response = callApiOnce(sub);
                all.addAll(parseVectors(response));
            }
            logger.info("Successfully generated {} embeddings", all.size());
            return all;
        } catch (Exception e) {
            logger.error("Embedding API call failed: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to generate embeddings", e);
        }
    }

    private String callApiOnce(List<String> batch) {
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", modelId);
        requestBody.put("input", batch);
        requestBody.put("dimension", dimension);
        requestBody.put("encoding_format", "float");

        return webClient.post()
                .uri("/embeddings")
                .bodyValue(requestBody)
                .retrieve()
                .bodyToMono(String.class)
                .retryWhen(Retry.fixedDelay(3, Duration.ofSeconds(1))
                        .filter(e -> e instanceof WebClientResponseException))
                .block(Duration.ofSeconds(30));
    }

    private List<float[]> parseVectors(String response) throws Exception {
        JsonNode jsonNode = objectMapper.readTree(response);
        JsonNode data = jsonNode.get("data");
        if (data == null || !data.isArray()) {
            throw new RuntimeException("API response format error: data field is missing or not an array");
        }

        List<float[]> vectors = new ArrayList<>();
        for (JsonNode item : data) {
            JsonNode embedding = item.get("embedding");
            if (embedding != null && embedding.isArray()) {
                float[] vector = new float[embedding.size()];
                for (int i = 0; i < embedding.size(); i++) {
                    vector[i] = (float) embedding.get(i).asDouble();
                }
                vectors.add(vector);
            }
        }
        return vectors;
    }
}