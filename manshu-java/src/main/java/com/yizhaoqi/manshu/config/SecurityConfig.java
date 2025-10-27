package com.yizhaoqi.manshu.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;


@Configuration
@EnableWebSecurity
public class SecurityConfig {


    private static final Logger logger = LoggerFactory.getLogger(SecurityConfig.class);

    @Autowired
    private JwtAuthenticationFilter jwtAuthenticationFilter;

    @Autowired
    private OrgTagAuthorizationFilter orgTagAuthorizationFilter;


    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        try {

            http.csrf(csrf -> csrf.disable())

                    .authorizeHttpRequests(authorize -> authorize

                            .requestMatchers("/", "/test.html", "/static/test.html", "/static/**", "/*.js", "/*.css", "/*.ico").permitAll()

                            .requestMatchers("/chat/**", "/ws/**").permitAll()

                            .requestMatchers("/api/v1/users/register", "/api/v1/users/login").permitAll()

                            .requestMatchers("/api/v1/test/**").permitAll()

                            .requestMatchers("/api/v1/upload/**", "/api/v1/parse", "/api/v1/documents/download", "/api/v1/documents/preview").hasAnyRole("USER", "ADMIN")

                            .requestMatchers("/api/v1/users/conversation/**").hasAnyRole("USER", "ADMIN")

                            .requestMatchers("/api/search/**").hasAnyRole("USER", "ADMIN")

                            .requestMatchers("/api/chat/websocket-token").permitAll()

                            .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")

                            .requestMatchers("/api/v1/users/primary-org").hasAnyRole("USER", "ADMIN")

                            .anyRequest().authenticated())


                    .sessionManagement(session -> session
                            .sessionCreationPolicy(SessionCreationPolicy.STATELESS))

                    .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class)

                    .addFilterAfter(orgTagAuthorizationFilter, JwtAuthenticationFilter.class);


            logger.info("Security configuration loaded successfully.");

            return http.build();
        } catch (Exception e) {

            logger.error("Failed to configure security filter chain", e);

            throw e;
        }
    }
}
