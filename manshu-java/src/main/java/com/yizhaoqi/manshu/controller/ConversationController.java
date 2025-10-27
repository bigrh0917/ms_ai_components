package com.yizhaoqi.manshu.controller;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.yizhaoqi.manshu.exception.CustomException;
import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.UserRepository;
import com.yizhaoqi.manshu.utils.JwtUtils;
import com.yizhaoqi.manshu.utils.LogUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/users/conversation")
public class ConversationController {

    @Autowired
    private RedisTemplate<String, String> redisTemplate;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JwtUtils jwtUtils;

    @Autowired
    private ObjectMapper objectMapper;


    @GetMapping
    public ResponseEntity<?> getConversations(
            @RequestHeader("Authorization") String token,
            @RequestParam(required = false, name = "start_date") String startDate,
            @RequestParam(required = false, name = "end_date") String endDate) {

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("GET_CONVERSATIONS");
        String username = null;
        try {
            username = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
            if (username == null || username.isEmpty()) {
                LogUtils.logUserOperation("anonymous", "GET_CONVERSATIONS", "token_validation", "FAILED_INVALID_TOKEN");
                monitor.end("Failed to fetch conversation history: invalid token");
                throw new CustomException("Invalid token", HttpStatus.UNAUTHORIZED);
            }

            LogUtils.logBusiness("GET_CONVERSATIONS", username, "Start fetching user conversation history");

            User user = userRepository.findByUsername(username)
                    .orElseThrow(() -> new CustomException("User not found", HttpStatus.NOT_FOUND));

            List<String> candidateIds = new ArrayList<>();
            candidateIds.add(String.valueOf(user.getId()));
            candidateIds.add(username);
            candidateIds.add(String.format("%s", user.getId()));

            for (String candidate : candidateIds) {
                String key = "user:" + candidate + ":current_conversation";
                String conversationId = redisTemplate.opsForValue().get(key);
                if (conversationId != null) {
                    LogUtils.logBusiness("GET_CONVERSATIONS", username, "Found conversation id: %s", conversationId);
                    return getConversationsFromRedis(conversationId, username, startDate, endDate, monitor);
                }
                LogUtils.logBusiness("GET_CONVERSATIONS", username, "Tried Redis key %s but it was empty", key);
            }

            LogUtils.logBusiness("GET_CONVERSATIONS", username, "No conversation history found, attempted user ids: %s", candidateIds);
            LogUtils.logUserOperation(username, "GET_CONVERSATIONS", "conversation_history", "SUCCESS_EMPTY");
            monitor.end("Conversation history fetched successfully (empty result)");

            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "Conversation history fetched successfully");
            response.put("data", new ArrayList<>());
            return ResponseEntity.ok(response);

        } catch (CustomException e) {
            LogUtils.logBusinessError("GET_CONVERSATIONS", username, "Failed to fetch conversation history: %s", e, e.getMessage());
            monitor.end("Failed to fetch conversation history: " + e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("GET_CONVERSATIONS", username, "Unexpected error while fetching conversation history: %s", e, e.getMessage());
            monitor.end("Unexpected error while fetching conversation history: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("code", 500, "message", "Internal server error: " + e.getMessage()));
        }
    }


    private ResponseEntity<?> getConversationsFromRedis(String conversationId, String username, String startDate,
                                                        String endDate, LogUtils.PerformanceMonitor monitor) {
        String key = "conversation:" + conversationId;
        String json = redisTemplate.opsForValue().get(key);

        List<Map<String, Object>> formattedConversations = new ArrayList<>();
        if (json != null) {
            try {
                List<Map<String, Object>> history = objectMapper.readValue(json, new TypeReference<>() {});

                LocalDateTime startDateTime = parseDateTime(startDate);
                LocalDateTime endDateTime = parseDateTime(endDate);

                if (startDateTime != null) {
                    LogUtils.logBusiness("GET_CONVERSATIONS", username, "Parsed start time: %s", startDateTime);
                }
                if (endDateTime != null) {
                    LogUtils.logBusiness("GET_CONVERSATIONS", username, "Parsed end time: %s", endDateTime);
                }

                for (Map<String, Object> message : history) {
                    String messageTimestamp = String.valueOf(message.getOrDefault("timestamp", "UNKNOWN_TIME"));

                    if (startDateTime != null || endDateTime != null) {
                        if (!"UNKNOWN_TIME".equals(messageTimestamp)) {
                            try {
                                LocalDateTime messageDateTime = LocalDateTime.parse(
                                        messageTimestamp, DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss"));
                                if (startDateTime != null && messageDateTime.isBefore(startDateTime)) {
                                    continue;
                                }
                                if (endDateTime != null && messageDateTime.isAfter(endDateTime)) {
                                    continue;
                                }
                            } catch (Exception e) {
                                LogUtils.logBusinessError("GET_CONVERSATIONS", username,
                                        "Message timestamp format error: %s", e, messageTimestamp);
                            }
                        } else {
                            continue;
                        }
                    }

                    Map<String, Object> messageWithTimestamp = new HashMap<>();
                    messageWithTimestamp.put("role", message.get("role"));
                    messageWithTimestamp.put("content", message.get("content"));
                    messageWithTimestamp.put("timestamp", messageTimestamp);
                    formattedConversations.add(messageWithTimestamp);
                }

                LogUtils.logBusiness("GET_CONVERSATIONS", username,
                        "Retrieved %d entries from Redis, %d after filtering, conversationId: %s",
                        history.size(), formattedConversations.size(), conversationId);
                LogUtils.logUserOperation(username, "GET_CONVERSATIONS", "conversation_history", "SUCCESS");
                monitor.end("Conversation history fetched successfully");
            } catch (JsonProcessingException e) {
                LogUtils.logBusinessError("GET_CONVERSATIONS", username, "Failed to parse conversation history", e);
                monitor.end("Failed to parse conversation history");
                throw new CustomException("Failed to parse conversation history", HttpStatus.INTERNAL_SERVER_ERROR);
            }
        } else {
            LogUtils.logBusiness("GET_CONVERSATIONS", username, "Conversation id %s was not found in Redis", conversationId);
            LogUtils.logUserOperation(username, "GET_CONVERSATIONS", "conversation_history", "SUCCESS_EMPTY");
            monitor.end("Conversation history fetched successfully (empty result)");
        }

        Map<String, Object> response = new HashMap<>();
        response.put("code", 200);
        response.put("message", "Conversation history fetched successfully");
        response.put("data", formattedConversations);
        return ResponseEntity.ok(response);
    }


    private LocalDateTime parseDateTime(String dateTimeStr) {
        if (dateTimeStr == null || dateTimeStr.trim().isEmpty()) {
            return null;
        }

        try {
            return LocalDateTime.parse(dateTimeStr);
        } catch (DateTimeParseException e1) {
            try {
                if (dateTimeStr.length() == 16) {
                    return LocalDateTime.parse(dateTimeStr + ":00");
                }

                if (dateTimeStr.length() == 13) {
                    return LocalDateTime.parse(dateTimeStr + ":00:00");
                }

                if (dateTimeStr.length() == 10) {
                    return LocalDateTime.parse(dateTimeStr + "T00:00:00");
                }

                DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm");
                return LocalDateTime.parse(dateTimeStr, formatter);
            } catch (Exception e2) {
                LogUtils.logBusinessError("PARSE_DATETIME", "system", "Unable to parse date-time: %s", e2, dateTimeStr);
                throw new CustomException("Invalid date format: " + dateTimeStr, HttpStatus.BAD_REQUEST);
            }
        }
    }
}