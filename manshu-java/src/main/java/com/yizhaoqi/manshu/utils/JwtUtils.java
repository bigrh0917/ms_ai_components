package com.yizhaoqi.manshu.utils;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.UserRepository;
import com.yizhaoqi.manshu.service.TokenCacheService;

import javax.crypto.SecretKey;
import java.util.Base64;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Component
public class JwtUtils {
    private static final Logger logger = LoggerFactory.getLogger(JwtUtils.class);

    @Value("${jwt.secret-key}")
    private String secretKeyBase64;

    private static final long EXPIRATION_TIME = 3600000;
    private static final long REFRESH_TOKEN_EXPIRATION_TIME = 604800000;
    private static final long REFRESH_THRESHOLD = 300000;
    private static final long REFRESH_WINDOW = 600000;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private TokenCacheService tokenCacheService;


    private SecretKey getSigningKey() {
        byte[] keyBytes = Base64.getDecoder().decode(secretKeyBase64);
        return Keys.hmacShaKeyFor(keyBytes);
    }


    public String generateToken(String username) {
        SecretKey key = getSigningKey();


        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new RuntimeException("User not found"));


        String tokenId = generateTokenId();
        long expireTime = System.currentTimeMillis() + EXPIRATION_TIME;


        Map<String, Object> claims = new HashMap<>();
        claims.put("tokenId", tokenId);
        claims.put("role", user.getRole().name());
        claims.put("userId", user.getId().toString());


        if (user.getOrgTags() != null && !user.getOrgTags().isEmpty()) {
            claims.put("orgTags", user.getOrgTags());
        }


        if (user.getPrimaryOrg() != null && !user.getPrimaryOrg().isEmpty()) {
            claims.put("primaryOrg", user.getPrimaryOrg());
        }

        String token = Jwts.builder()
                .setClaims(claims)
                .setSubject(username)
                .setExpiration(new Date(expireTime))
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();


        tokenCacheService.cacheToken(tokenId, user.getId().toString(), username, expireTime);

        logger.info("Token generated and cached for user: {}, tokenId: {}", username, tokenId);
        return token;
    }


    public boolean validateToken(String token) {
        try {

            String tokenId = extractTokenIdFromToken(token);
            if (tokenId == null) {
                logger.warn("Token does not contain tokenId");
                return false;
            }


            if (!tokenCacheService.isTokenValid(tokenId)) {
                logger.debug("Token invalid in cache: {}", tokenId);
                return false;
            }


            Jwts.parserBuilder()
                    .setSigningKey(getSigningKey())
                    .build()
                    .parseClaimsJws(token);

            logger.debug("Token validation successful: {}", tokenId);
            return true;
        } catch (ExpiredJwtException e) {
            logger.warn("Token expired: {}", e.getClaims().get("tokenId", String.class));
        } catch (SignatureException e) {
            logger.warn("Invalid token signature");
        } catch (Exception e) {
            logger.error("Error validating token", e);
        }
        return false;
    }


    public String extractUsernameFromToken(String token) {
        try {
            Claims claims = extractClaimsIgnoreExpiration(token);
            return claims != null ? claims.getSubject() : null;
        } catch (Exception e) {
            logger.error("Error extracting username from token: {}", token, e);
            return null;
        }
    }


    public String extractUserIdFromToken(String token) {
        try {
            Claims claims = extractClaimsIgnoreExpiration(token);
            return claims != null ? claims.get("userId", String.class) : null;
        } catch (Exception e) {
            logger.error("Error extracting userId from token: {}", token, e);
            return null;
        }
    }


    public String extractRoleFromToken(String token) {
        try {
            Claims claims = extractClaimsIgnoreExpiration(token);
            return claims != null ? claims.get("role", String.class) : null;
        } catch (Exception e) {
            logger.error("Error extracting role from token: {}", token, e);
            return null;
        }
    }


    public String extractOrgTagsFromToken(String token) {
        try {
            Claims claims = extractClaimsIgnoreExpiration(token);
            return claims != null ? claims.get("orgTags", String.class) : null;
        } catch (Exception e) {
            logger.error("Error extracting organization tags from token: {}", token, e);
            return null;
        }
    }


    public String extractPrimaryOrgFromToken(String token) {
        try {
            Claims claims = extractClaimsIgnoreExpiration(token);
            return claims != null ? claims.get("primaryOrg", String.class) : null;
        } catch (Exception e) {
            logger.error("Error extracting primary organization from token: {}", token, e);
            return null;
        }
    }


    public boolean shouldRefreshToken(String token) {
        try {
            Claims claims = extractClaims(token);
            if (claims == null) return false;

            long expirationTime = claims.getExpiration().getTime();
            long currentTime = System.currentTimeMillis();
            long remainingTime = expirationTime - currentTime;

            return remainingTime > 0 && remainingTime < REFRESH_THRESHOLD;
        } catch (Exception e) {
            logger.debug("Cannot check if token should refresh: {}", e.getMessage());
            return false;
        }
    }


    public boolean canRefreshExpiredToken(String token) {
        try {
            Claims claims = extractClaimsIgnoreExpiration(token);
            if (claims == null) return false;

            long expirationTime = claims.getExpiration().getTime();
            long currentTime = System.currentTimeMillis();
            long expiredTime = currentTime - expirationTime;

            return expiredTime > 0 && expiredTime < REFRESH_WINDOW;
        } catch (Exception e) {
            logger.debug("Cannot check if expired token can refresh: {}", e.getMessage());
            return false;
        }
    }


    public String refreshToken(String oldToken) {
        try {
            Claims claims = extractClaimsIgnoreExpiration(oldToken);
            if (claims == null) return null;

            String username = claims.getSubject();
            if (username == null || username.isEmpty()) return null;


            String newToken = generateToken(username);
            logger.info("Token refreshed successfully for user: {}", username);
            return newToken;
        } catch (Exception e) {
            logger.error("Error refreshing token: {}", e.getMessage());
            return null;
        }
    }


    private Claims extractClaimsIgnoreExpiration(String token) {
        try {
            return Jwts.parserBuilder()
                    .setSigningKey(getSigningKey())
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
        } catch (ExpiredJwtException e) {

            return e.getClaims();
        } catch (Exception e) {
            logger.debug("Cannot extract claims from token: {}", e.getMessage());
            return null;
        }
    }


    private Claims extractClaims(String token) {
        try {
            return Jwts.parserBuilder()
                    .setSigningKey(getSigningKey())
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
        } catch (Exception e) {
            return null;
        }
    }


    public String generateRefreshToken(String username) {
        SecretKey key = getSigningKey();


        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new RuntimeException("User not found"));


        String refreshTokenId = generateTokenId();
        long expireTime = System.currentTimeMillis() + REFRESH_TOKEN_EXPIRATION_TIME;


        Map<String, Object> claims = new HashMap<>();
        claims.put("refreshTokenId", refreshTokenId);
        claims.put("userId", user.getId().toString());
        claims.put("type", "refresh");

        String refreshToken = Jwts.builder()
                .setClaims(claims)
                .setSubject(username)
                .setExpiration(new Date(expireTime))
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();


        tokenCacheService.cacheRefreshToken(refreshTokenId, user.getId().toString(), null, expireTime);

        logger.info("Refresh token generated and cached for user: {}, refreshTokenId: {}", username, refreshTokenId);
        return refreshToken;
    }


    public boolean validateRefreshToken(String refreshToken) {
        try {

            String refreshTokenId = extractRefreshTokenIdFromToken(refreshToken);
            if (refreshTokenId == null) {
                logger.warn("Refresh token does not contain refreshTokenId");
                return false;
            }


            if (!tokenCacheService.isRefreshTokenValid(refreshTokenId)) {
                logger.debug("Refresh token invalid in cache: {}", refreshTokenId);
                return false;
            }


            Claims claims = Jwts.parserBuilder()
                    .setSigningKey(getSigningKey())
                    .build()
                    .parseClaimsJws(refreshToken)
                    .getBody();


            String tokenType = claims.get("type", String.class);
            if (!"refresh".equals(tokenType)) {
                logger.warn("Token is not a refresh token");
                return false;
            }

            logger.debug("Refresh token validation successful: {}", refreshTokenId);
            return true;
        } catch (ExpiredJwtException e) {
            logger.warn("Refresh token expired: {}", e.getClaims().get("refreshTokenId", String.class));
        } catch (SignatureException e) {
            logger.warn("Invalid refresh token signature");
        } catch (Exception e) {
            logger.error("Error validating refresh token", e);
        }
        return false;
    }


    public String extractRefreshTokenIdFromToken(String refreshToken) {
        try {
            Claims claims = extractClaimsIgnoreExpiration(refreshToken);
            return claims != null ? claims.get("refreshTokenId", String.class) : null;
        } catch (Exception e) {
            logger.debug("Error extracting refreshTokenId from token", e);
            return null;
        }
    }


    private String generateTokenId() {
        return UUID.randomUUID().toString().replace("-", "");
    }


    public String extractTokenIdFromToken(String token) {
        try {
            Claims claims = extractClaimsIgnoreExpiration(token);
            return claims != null ? claims.get("tokenId", String.class) : null;
        } catch (Exception e) {
            logger.debug("Error extracting tokenId from token", e);
            return null;
        }
    }


    public void invalidateToken(String token) {
        try {
            String tokenId = extractTokenIdFromToken(token);
            if (tokenId != null) {
                Claims claims = extractClaimsIgnoreExpiration(token);
                if (claims != null) {
                    long expireTime = claims.getExpiration().getTime();
                    String userId = claims.get("userId", String.class);


                    tokenCacheService.blacklistToken(tokenId, expireTime);

                    tokenCacheService.removeToken(tokenId, userId);

                    logger.info("Token invalidated: {}", tokenId);
                }
            }
        } catch (Exception e) {
            logger.error("Error invalidating token", e);
        }
    }


    public void invalidateAllUserTokens(String userId) {
        try {
            tokenCacheService.removeAllUserTokens(userId);
            logger.info("All tokens invalidated for user: {}", userId);
        } catch (Exception e) {
            logger.error("Error invalidating all user tokens: {}", userId, e);
        }
    }
}