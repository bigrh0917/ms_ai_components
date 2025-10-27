package com.yizhaoqi.manshu.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.yizhaoqi.manshu.client.DeepSeekClient;
import com.yizhaoqi.manshu.entity.SearchResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;


@Service
public class ChatHandler {

    private static final Logger logger = LoggerFactory.getLogger(ChatHandler.class);
    private final RedisTemplate<String, String> redisTemplate;
    private final HybridSearchService searchService;
    private final DeepSeekClient deepSeekClient;
    private final ObjectMapper objectMapper;


    private final Map<String, StringBuilder> responseBuilders = new ConcurrentHashMap<>();

    private final Map<String, CompletableFuture<String>> responseFutures = new ConcurrentHashMap<>();

    private final Map<String, Boolean> stopFlags = new ConcurrentHashMap<>();

    public ChatHandler(RedisTemplate<String, String> redisTemplate,
                      HybridSearchService searchService,
                      DeepSeekClient deepSeekClient) {
        this.redisTemplate = redisTemplate;
        this.searchService = searchService;
        this.deepSeekClient = deepSeekClient;
        this.objectMapper = new ObjectMapper();
    }

    public void processMessage(String userId, String userMessage, WebSocketSession session) {
        logger.info("English textEnglish textEnglish textID: {}, English textID: {}", userId, session.getId());
        try {

            String conversationId = getOrCreateConversationId(userId);
            logger.info("English textID: {}, English textID: {}", conversationId, userId);


            responseBuilders.put(session.getId(), new StringBuilder());

            CompletableFuture<String> responseFuture = new CompletableFuture<>();
            responseFutures.put(session.getId(), responseFuture);


            List<Map<String, String>> history = getConversationHistory(conversationId);
            logger.debug("English text {} English text", history.size());


            List<SearchResult> searchResults = searchService.searchWithPermission(userMessage, userId, 5);
            logger.debug("English text: {}", searchResults.size());


            String context = buildContext(searchResults);


            logger.info("English textDeepSeek APIEnglish text");
            deepSeekClient.streamResponse(userMessage, context, history,
                chunk -> {

                    StringBuilder responseBuilder = responseBuilders.get(session.getId());
                    if (responseBuilder != null) {
                        responseBuilder.append(chunk);
                    }
                    sendResponseChunk(session, chunk);
                },
                error -> {

                    handleError(session, error);

                    sendCompletionNotification(session);
                    responseFuture.completeExceptionally(error);

                    responseBuilders.remove(session.getId());
                    responseFutures.remove(session.getId());
                });


            new Thread(() -> {
                try {

                    Thread.sleep(3000);


                    StringBuilder responseBuilder = responseBuilders.get(session.getId());


                    if (responseBuilder != null) {

                        String lastResponse = responseBuilder.toString();
                        int lastLength = lastResponse.length();

                        Thread.sleep(2000);


                        if (responseBuilder.length() == lastLength) {

                            responseFuture.complete(responseBuilder.toString());
                            logger.info("DeepSeekEnglish textEnglish textEnglish text: {}", responseBuilder.length());


                            sendCompletionNotification(session);


                            String completeResponse = responseBuilder.toString();
                            updateConversationHistory(conversationId, userMessage, completeResponse);


                            String redisKey = "user:" + userId + ":current_conversation";
                            logger.info("English text - RedisEnglish text: {}, English text: {}", redisKey, conversationId);


                            responseBuilders.remove(session.getId());
                            responseFutures.remove(session.getId());
                            logger.info("English textEnglish textEnglish textID: {}", userId);
                        } else {

                            logger.debug("English textEnglish textEnglish text...");

                            for (int i = 0; i < 5; i++) {
                                Thread.sleep(5000);
                                if (responseBuilder != null) {
                                    lastLength = responseBuilder.length();

                                    Thread.sleep(2000);
                                    if (responseBuilder.length() == lastLength) {

                                        responseFuture.complete(responseBuilder.toString());


                                        sendCompletionNotification(session);


                                        String completeResponse = responseBuilder.toString();
                                        updateConversationHistory(conversationId, userMessage, completeResponse);


                                        String redisKey = "user:" + userId + ":current_conversation";
                                        logger.info("English text - RedisEnglish text: {}, English text: {}", redisKey, conversationId);


                                        responseBuilders.remove(session.getId());
                                        responseFutures.remove(session.getId());
                                        logger.info("English textEnglish textEnglish textID: {}", userId);
                                        return;
                                    }
                                }
                            }


                            if (!responseFuture.isDone()) {
                                responseFuture.complete(responseBuilder.toString());


                                sendCompletionNotification(session);


                                String completeResponse = responseBuilder.toString();
                                updateConversationHistory(conversationId, userMessage, completeResponse);


                                String redisKey = "user:" + userId + ":current_conversation";
                                logger.info("English text - RedisEnglish text: {}, English text: {}", redisKey, conversationId);


                                responseBuilders.remove(session.getId());
                                responseFutures.remove(session.getId());
                                logger.info("English textEnglish textEnglish textID: {}", userId);
                            }
                        }
                    } else {
                        logger.warn("English textEnglish textEnglish textEnglish textEnglish textID: {}", session.getId());
                        RuntimeException exception = new RuntimeException("English text");
                        responseFuture.completeExceptionally(exception);

                        handleError(session, exception);
                    }
                } catch (Exception e) {
                    logger.error("English text: {}", e.getMessage(), e);
                    responseFuture.completeExceptionally(e);


                    responseBuilders.remove(session.getId());
                    responseFutures.remove(session.getId());
                }
            }).start();

        } catch (Exception e) {
            logger.error("English text: {}", e.getMessage(), e);
            handleError(session, e);

            responseBuilders.remove(session.getId());

            CompletableFuture<String> future = responseFutures.remove(session.getId());
            if (future != null && !future.isDone()) {
                future.completeExceptionally(e);
            }
        }
    }

    private String getOrCreateConversationId(String userId) {
        String key = "user:" + userId + ":current_conversation";
        String conversationId = redisTemplate.opsForValue().get(key);

        if (conversationId == null) {
            conversationId = UUID.randomUUID().toString();
            redisTemplate.opsForValue().set(key, conversationId, Duration.ofDays(7));
            logger.info("English text {} English textID: {}", userId, conversationId);
        } else {
            logger.info("English text {} English textID: {}", userId, conversationId);
        }

        return conversationId;
    }

    private List<Map<String, String>> getConversationHistory(String conversationId) {
        String key = "conversation:" + conversationId;
        String json = redisTemplate.opsForValue().get(key);
        try {
            if (json == null) {
                logger.debug("English text {} English text", conversationId);
                return new ArrayList<>();
            }

            List<Map<String, String>> history = objectMapper.readValue(json, new TypeReference<List<Map<String, String>>>() {});
            logger.debug("English text {} English text {} English text", conversationId, history.size());
            return history;
        } catch (JsonProcessingException e) {
            logger.error("English text: {}, English textID: {}", e.getMessage(), conversationId, e);
            return new ArrayList<>();
        }
    }

    private void updateConversationHistory(String conversationId, String userMessage, String response) {
        String key = "conversation:" + conversationId;
        List<Map<String, String>> history = getConversationHistory(conversationId);


        String currentTimestamp = java.time.LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss"));


        Map<String, String> userMsgMap = new HashMap<>();
        userMsgMap.put("role", "user");
        userMsgMap.put("content", userMessage);
        userMsgMap.put("timestamp", currentTimestamp);
        history.add(userMsgMap);


        Map<String, String> assistantMsgMap = new HashMap<>();
        assistantMsgMap.put("role", "assistant");
        assistantMsgMap.put("content", response);
        assistantMsgMap.put("timestamp", currentTimestamp);
        history.add(assistantMsgMap);


        if (history.size() > 20) {
            history = history.subList(history.size() - 20, history.size());
        }

        try {
            String json = objectMapper.writeValueAsString(history);
            redisTemplate.opsForValue().set(key, json, Duration.ofDays(7));
            logger.debug("English textEnglish textEnglish textID: {}, English text: {}", conversationId, history.size());
        } catch (JsonProcessingException e) {
            logger.error("English text: {}, English textID: {}", e.getMessage(), conversationId, e);
        }
    }

    private String buildContext(List<SearchResult> searchResults) {
        if (searchResults == null || searchResults.isEmpty()) {

            return "";
        }

        final int MAX_SNIPPET_LEN = 300;
        StringBuilder context = new StringBuilder();
        for (int i = 0; i < searchResults.size(); i++) {
            SearchResult result = searchResults.get(i);
            String snippet = result.getTextContent();
            if (snippet.length() > MAX_SNIPPET_LEN) {
                snippet = snippet.substring(0, MAX_SNIPPET_LEN) + "…";
            }
            String fileLabel = result.getFileName() != null ? result.getFileName() : "unknown";
            context.append(String.format("[%d] (%s) %s\n", i + 1, fileLabel, snippet));
        }
        return context.toString();
    }

    private void sendResponseChunk(WebSocketSession session, String chunk) {
        try {

            if (Boolean.TRUE.equals(stopFlags.get(session.getId()))) {
                logger.debug("English textEnglish textEnglish text");
                return;
            }


            Map<String, String> chunkResponse = Map.of("chunk", chunk);
            String jsonChunk = objectMapper.writeValueAsString(chunkResponse);
            logger.debug("English text {}: {}", session.getId(), jsonChunk);
            session.sendMessage(new TextMessage(jsonChunk));
        } catch (Exception e) {
            logger.error("English text: {}", e.getMessage(), e);
        }
    }

    private void sendCompletionNotification(WebSocketSession session) {
        try {
            long currentTime = System.currentTimeMillis();
            Map<String, Object> notification = Map.of(
                "type", "completion",
                "status", "finished",
                "message", "English text",
                "timestamp", currentTime,
                "date", java.time.LocalDateTime.now().toString()
            );
            String notificationJson = objectMapper.writeValueAsString(notification);
            logger.info("English text {}: {}", session.getId(), notificationJson);
            session.sendMessage(new TextMessage(notificationJson));
            logger.info("English text: {}", session.getId());
        } catch (Exception e) {
            logger.error("English text: {}", e.getMessage(), e);
        }
    }

    private void handleError(WebSocketSession session, Throwable error) {
        logger.error("AIEnglish text: {}", error.getMessage(), error);
        try {
            Map<String, String> errorResponse = Map.of("error", "AIEnglish textEnglish textEnglish text");
            String errorJson = objectMapper.writeValueAsString(errorResponse);
            logger.error("English text {}: {}", session.getId(), errorJson);
            session.sendMessage(new TextMessage(errorJson));
            logger.error("English text: {}", session.getId());
        } catch (Exception e) {
            logger.error("English text: {}", e.getMessage(), e);
        }
    }


    public void stopResponse(String userId, WebSocketSession session) {
        String sessionId = session.getId();
        logger.info("English textEnglish textEnglish textID: {}, English textID: {}", userId, sessionId);


        stopFlags.put(sessionId, true);


        try {
            long currentTime = System.currentTimeMillis();
            Map<String, Object> response = Map.of(
                "type", "stop",
                "message", "English text",
                "timestamp", currentTime,
                "date", java.time.Instant.ofEpochMilli(currentTime).toString()
            );
            String stopJson = objectMapper.writeValueAsString(response);
            logger.info("English text {}: {}", sessionId, stopJson);
            session.sendMessage(new TextMessage(stopJson));
            logger.info("English textEnglish textEnglish textID: {}", sessionId);
        } catch (Exception e) {
            logger.error("English text: {}", e.getMessage(), e);
        }


        new Thread(() -> {
            try {
                Thread.sleep(2000);
                stopFlags.remove(sessionId);
                logger.debug("English textEnglish textEnglish textID: {}", sessionId);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }).start();
    }
}