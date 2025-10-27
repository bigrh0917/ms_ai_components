package com.yizhaoqi.manshu.config;

import com.yizhaoqi.manshu.service.CustomUserDetailsService;
import com.yizhaoqi.manshu.utils.JwtUtils;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;


@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Autowired
    private JwtUtils jwtUtils;

    @Autowired
    private CustomUserDetailsService userDetailsService;


    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        try {

            String token = extractToken(request);
            if (token != null) {
                String newToken = null;
                String username = null;


                if (jwtUtils.validateToken(token)) {

                    if (jwtUtils.shouldRefreshToken(token)) {
                        newToken = jwtUtils.refreshToken(token);
                        if (newToken != null) {
                            logger.info("Token auto-refreshed proactively");
                        }
                    }
                    username = jwtUtils.extractUsernameFromToken(token);
                } else {

                    if (jwtUtils.canRefreshExpiredToken(token)) {
                        newToken = jwtUtils.refreshToken(token);
                        if (newToken != null) {
                            logger.info("Expired token refreshed within grace period");
                            username = jwtUtils.extractUsernameFromToken(newToken);
                        }
                    }
                }


                if (newToken != null) {
                    response.setHeader("New-Token", newToken);
                }


                if (username != null && !username.isEmpty()) {
                    UserDetails userDetails = userDetailsService.loadUserByUsername(username);
                    UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                            userDetails, null, userDetails.getAuthorities());
                    authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                    SecurityContextHolder.getContext().setAuthentication(authentication);
                }
            }
            filterChain.doFilter(request, response);
        } catch (Exception e) {

            logger.error("Cannot set user authentication: {}", e);
        }
    }


    private String extractToken(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}