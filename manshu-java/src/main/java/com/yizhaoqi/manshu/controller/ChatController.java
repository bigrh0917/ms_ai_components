package com.yizhaoqi.manshu.controller;

import com.yizhaoqi.manshu.handler.ChatWebSocketHandler;
import com.yizhaoqi.manshu.service.ChatHandler;
import com.yizhaoqi.manshu.utils.LogUtils;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.Map;

@Component
@RestController
@RequestMapping("/api/v1/chat")
public class ChatController extends TextWebSocketHandler {

    private final ChatHandler chatHandler;

    public ChatController(ChatHandler chatHandler) {
        this.chatHandler = chatHandler;
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String userMessage = message.getPayload();
        String userId = session.getId();

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("WEBSOCKET_CHAT");
        try {
            LogUtils.logChat(userId, session.getId(), "USER_MESSAGE", userMessage.length());
            LogUtils.logBusiness("WEBSOCKET_CHAT", userId, "English textWebSocketEnglish text: messageLength=%d", userMessage.length());

        chatHandler.processMessage(userId, userMessage, session);

            LogUtils.logUserOperation(userId, "WEBSOCKET_CHAT", "message_processing", "SUCCESS");
            monitor.end("WebSocketEnglish text");
        } catch (Exception e) {
            LogUtils.logBusinessError("WEBSOCKET_CHAT", userId, "WebSocketEnglish text", e);
            monitor.end("WebSocketEnglish text: " + e.getMessage());
            throw e;
        }
    }


    @GetMapping("/websocket-token")
    public ResponseEntity<?> getWebSocketToken() {
        try {
            String cmdToken = ChatWebSocketHandler.getInternalCmdToken();


            if (cmdToken == null || cmdToken.trim().isEmpty()) {
                return ResponseEntity.status(500).body(Map.of(
                    "code", 500,
                    "message", "TokenEnglish text",
                    "data", null
                ));
            }

            return ResponseEntity.ok(Map.of(
                "code", 200,
                "message", "English textWebSocketEnglish textTokenEnglish text",
                "data", Map.of("cmdToken", cmdToken)
            ));

        } catch (Exception e) {
            LogUtils.logBusinessError("GET_WEBSOCKET_TOKEN", "system", "English textWebSocket TokenEnglish text", e);
            return ResponseEntity.status(500).body(Map.of(
                "code", 500,
                "message", "English textEnglish text" + e.getMessage(),
                "data", null
            ));
        }
    }
}