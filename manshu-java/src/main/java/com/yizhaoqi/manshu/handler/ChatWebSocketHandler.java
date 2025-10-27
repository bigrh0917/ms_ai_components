package com.yizhaoqi.manshu.handler;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.yizhaoqi.manshu.service.ChatHandler;
import com.yizhaoqi.manshu.utils.JwtUtils;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;

@Component
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private static final Logger logger = LoggerFactory.getLogger(ChatWebSocketHandler.class);
    private final ChatHandler chatHandler;
    private final ConcurrentHashMap<String, WebSocketSession> sessions = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final JwtUtils jwtUtils;


    private static final String INTERNAL_CMD_TOKEN = "WSS_STOP_CMD_" + System.currentTimeMillis() % 1_000_000;

    public ChatWebSocketHandler(ChatHandler chatHandler, JwtUtils jwtUtils) {
        this.chatHandler = chatHandler;
        this.jwtUtils = jwtUtils;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        String userId = extractUserId(session);
        sessions.put(userId, session);
        logger.info("WebSocket connection established. userId={}, sessionId={}, uri={}",
                userId, session.getId(), session.getUri().getPath());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        String userId = extractUserId(session);
        try {
            String payload = message.getPayload();
            logger.info("Received message. userId={}, sessionId={}, length={}",
                    userId, session.getId(), payload.length());


            if (payload.trim().startsWith("{")) {
                try {
                    Map<String, Object> jsonMessage = objectMapper.readValue(payload, Map.class);
                    String messageType = (String) jsonMessage.get("type");
                    String internalToken = (String) jsonMessage.get("_internal_cmd_token");


                    if ("stop".equals(messageType) && INTERNAL_CMD_TOKEN.equals(internalToken)) {
                        logger.info("Received a valid stop command. userId={}, sessionId={}", userId, session.getId());
                        chatHandler.stopResponse(userId, session);
                        return;
                    }


                    logger.debug("JSON payload is treated as a normal chat message.");
                } catch (Exception jsonParseError) {
                    logger.debug("Failed to parse control JSON. Treating as plain text: {}", jsonParseError.getMessage());
                }
            }

            chatHandler.processMessage(userId, payload, session);

        } catch (Exception e) {
            logger.error("Failed to handle message. userId={}, sessionId={}, error={}",
                    userId, session.getId(), e.getMessage(), e);
            sendErrorMessage(session, "Failed to process message: " + e.getMessage());
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        String userId = extractUserId(session);
        sessions.remove(userId);
        logger.info("WebSocket connection closed. userId={}, sessionId={}, status={}",
                userId, session.getId(), status);
    }

    private String extractUserId(WebSocketSession session) {
        String path = session.getUri().getPath();
        String[] segments = path.split("/");
        String jwtToken = segments[segments.length - 1];


        String username = jwtUtils.extractUsernameFromToken(jwtToken);
        if (username == null) {
            logger.warn("Unable to extract username from JWT. Using raw token as the user id: {}", jwtToken);
            return jwtToken;
        }

        logger.debug("Extracted username {} from JWT token", username);
        return username;
    }

    private void sendErrorMessage(WebSocketSession session, String errorMessage) {
        try {
            Map<String, String> error = Map.of("error", errorMessage);
            session.sendMessage(new TextMessage(objectMapper.writeValueAsString(error)));
            logger.info("Sent error message to session {}: {}", session.getId(), errorMessage);
        } catch (Exception e) {
            logger.error("Failed to send error message: {}", e.getMessage(), e);
        }
    }


    public static String getInternalCmdToken() {
        return INTERNAL_CMD_TOKEN;
    }
}