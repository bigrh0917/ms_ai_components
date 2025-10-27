package com.yizhaoqi.manshu.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;


@Service
public class TokenCacheService {

    private static final Logger logger = LoggerFactory.getLogger(TokenCacheService.class);

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;


    private static final String TOKEN_PREFIX = "jwt:valid:";
    private static final String USER_TOKENS_PREFIX = "jwt:user:";
    private static final String REFRESH_PREFIX = "jwt:refresh:";
    private static final String BLACKLIST_PREFIX = "jwt:blacklist:";


    public void cacheToken(String tokenId, String userId, String username, long expireTimeMs) {
        try {
            String key = TOKEN_PREFIX + tokenId;
            Map<String, Object> tokenInfo = new HashMap<>();
            tokenInfo.put("userId", userId);
            tokenInfo.put("username", username);
            tokenInfo.put("expireTime", expireTimeMs);


            long ttlSeconds = (expireTimeMs - System.currentTimeMillis()) / 1000 + 300;

            redisTemplate.opsForValue().set(key, tokenInfo, ttlSeconds, TimeUnit.SECONDS);


            addTokenToUser(userId, tokenId, expireTimeMs);

            logger.debug("Token cached: {} for user: {}", tokenId, username);
        } catch (Exception e) {
            logger.error("Failed to cache token: {}", tokenId, e);
        }
    }


    public void cacheRefreshToken(String refreshTokenId, String userId, String tokenId, long expireTimeMs) {
        try {
            String key = REFRESH_PREFIX + refreshTokenId;
            Map<String, Object> refreshInfo = new HashMap<>();
            refreshInfo.put("userId", userId);
            refreshInfo.put("tokenId", tokenId);
            refreshInfo.put("expireTime", expireTimeMs);

            long ttlSeconds = (expireTimeMs - System.currentTimeMillis()) / 1000;
            redisTemplate.opsForValue().set(key, refreshInfo, ttlSeconds, TimeUnit.SECONDS);

            logger.debug("Refresh token cached: {} for user: {}", refreshTokenId, userId);
        } catch (Exception e) {
            logger.error("Failed to cache refresh token: {}", refreshTokenId, e);
        }
    }


    public boolean isTokenValid(String tokenId) {
        try {

            if (isTokenBlacklisted(tokenId)) {
                return false;
            }


            String key = TOKEN_PREFIX + tokenId;
            return Boolean.TRUE.equals(redisTemplate.hasKey(key));
        } catch (Exception e) {
            logger.error("Failed to check token validity: {}", tokenId, e);
            return false;
        }
    }


    @SuppressWarnings("unchecked")
    public Map<String, Object> getTokenInfo(String tokenId) {
        try {
            String key = TOKEN_PREFIX + tokenId;
            Object tokenInfo = redisTemplate.opsForValue().get(key);
            return tokenInfo != null ? (Map<String, Object>) tokenInfo : null;
        } catch (Exception e) {
            logger.error("Failed to get token info: {}", tokenId, e);
            return null;
        }
    }


    public boolean isRefreshTokenValid(String refreshTokenId) {
        try {
            String key = REFRESH_PREFIX + refreshTokenId;
            return Boolean.TRUE.equals(redisTemplate.hasKey(key));
        } catch (Exception e) {
            logger.error("Failed to check refresh token validity: {}", refreshTokenId, e);
            return false;
        }
    }


    @SuppressWarnings("unchecked")
    public Map<String, Object> getRefreshTokenInfo(String refreshTokenId) {
        try {
            String key = REFRESH_PREFIX + refreshTokenId;
            Object refreshInfo = redisTemplate.opsForValue().get(key);
            return refreshInfo != null ? (Map<String, Object>) refreshInfo : null;
        } catch (Exception e) {
            logger.error("Failed to get refresh token info: {}", refreshTokenId, e);
            return null;
        }
    }


    public void blacklistToken(String tokenId, long expireTimeMs) {
        try {
            String key = BLACKLIST_PREFIX + tokenId;
            long ttlSeconds = Math.max((expireTimeMs - System.currentTimeMillis()) / 1000, 0);

            if (ttlSeconds > 0) {
                redisTemplate.opsForValue().set(key, System.currentTimeMillis(), ttlSeconds, TimeUnit.SECONDS);
                logger.debug("Token blacklisted: {}", tokenId);
            }
        } catch (Exception e) {
            logger.error("Failed to blacklist token: {}", tokenId, e);
        }
    }


    public boolean isTokenBlacklisted(String tokenId) {
        try {
            String key = BLACKLIST_PREFIX + tokenId;
            return Boolean.TRUE.equals(redisTemplate.hasKey(key));
        } catch (Exception e) {
            logger.error("Failed to check token blacklist: {}", tokenId, e);
            return false;
        }
    }


    public void removeToken(String tokenId, String userId) {
        try {

            redisTemplate.delete(TOKEN_PREFIX + tokenId);


            if (userId != null) {
                removeTokenFromUser(userId, tokenId);
            }

            logger.debug("Token removed from cache: {}", tokenId);
        } catch (Exception e) {
            logger.error("Failed to remove token: {}", tokenId, e);
        }
    }


    public void removeAllUserTokens(String userId) {
        try {
            String userTokenKey = USER_TOKENS_PREFIX + userId + ":tokens";
            Set<Object> tokenIds = redisTemplate.opsForSet().members(userTokenKey);

            if (tokenIds != null && !tokenIds.isEmpty()) {
                for (Object tokenId : tokenIds) {
                    removeToken(tokenId.toString(), null);
                }
            }


            redisTemplate.delete(userTokenKey);

            logger.info("All tokens removed for user: {}", userId);
        } catch (Exception e) {
            logger.error("Failed to remove all user tokens: {}", userId, e);
        }
    }


    private void addTokenToUser(String userId, String tokenId, long expireTimeMs) {
        try {
            String key = USER_TOKENS_PREFIX + userId + ":tokens";
            redisTemplate.opsForSet().add(key, tokenId);


            long ttlSeconds = (expireTimeMs - System.currentTimeMillis()) / 1000 + 300;
            redisTemplate.expire(key, Duration.ofSeconds(ttlSeconds));
        } catch (Exception e) {
            logger.error("Failed to add token to user set: {} - {}", userId, tokenId, e);
        }
    }


    private void removeTokenFromUser(String userId, String tokenId) {
        try {
            String key = USER_TOKENS_PREFIX + userId + ":tokens";
            redisTemplate.opsForSet().remove(key, tokenId);
        } catch (Exception e) {
            logger.error("Failed to remove token from user set: {} - {}", userId, tokenId, e);
        }
    }


    public long getUserActiveTokenCount(String userId) {
        try {
            String key = USER_TOKENS_PREFIX + userId + ":tokens";
            Long count = redisTemplate.opsForSet().size(key);
            return count != null ? count : 0;
        } catch (Exception e) {
            logger.error("Failed to get user active token count: {}", userId, e);
            return 0;
        }
    }
}