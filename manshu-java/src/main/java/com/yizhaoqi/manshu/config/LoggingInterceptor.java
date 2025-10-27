package com.yizhaoqi.manshu.config;

import com.yizhaoqi.manshu.utils.JwtUtils;
import com.yizhaoqi.manshu.utils.LogUtils;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.UUID;


@Component
public class LoggingInterceptor implements HandlerInterceptor {

    @Autowired
    private JwtUtils jwtUtils;

    private static final String START_TIME_ATTRIBUTE = "startTime";
    private static final String REQUEST_ID_ATTRIBUTE = "requestId";

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {

        long startTime = System.currentTimeMillis();
        request.setAttribute(START_TIME_ATTRIBUTE, startTime);


        String requestId = UUID.randomUUID().toString().substring(0, 8);
        request.setAttribute(REQUEST_ID_ATTRIBUTE, requestId);


        String userId = extractUserId(request);
        String sessionId = request.getSession(false) != null ? request.getSession().getId() : null;


        LogUtils.setRequestContext(requestId, userId, sessionId);


        String path = request.getRequestURI();
        if (isApiRequest(path)) {
            LogUtils.logBusiness("REQUEST_START", userId,
                "English text [%s] %s", request.getMethod(), path);
        }

        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                              Object handler, Exception ex) {
        try {

            Long startTime = (Long) request.getAttribute(START_TIME_ATTRIBUTE);
            if (startTime != null) {
                long duration = System.currentTimeMillis() - startTime;
                String userId = extractUserId(request);
                String path = request.getRequestURI();


                if (isApiRequest(path)) {
                    LogUtils.logApiCall(request.getMethod(), path, userId, response.getStatus(), duration);


                    if (ex != null) {
                        LogUtils.logBusinessError("REQUEST_ERROR", userId,
                            "English text [%s] %s", ex, request.getMethod(), path);
                    }


                    if (duration > 3000) {
                        LogUtils.logPerformance("SLOW_REQUEST", duration,
                            String.format("[%s] %s [English text:%s]", request.getMethod(), path, userId));
                    }
                }
            }
        } finally {

            LogUtils.clearRequestContext();
        }
    }


    private String extractUserId(HttpServletRequest request) {
        try {
            String token = extractToken(request);
            if (token != null) {
                return jwtUtils.extractUserIdFromToken(token);
            }
        } catch (Exception e) {

        }
        return "anonymous";
    }


    private String extractToken(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }


    private boolean isApiRequest(String path) {
        return path.startsWith("/api/") || path.startsWith("/chat/");
    }
}