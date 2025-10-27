package com.yizhaoqi.manshu.controller;

import com.yizhaoqi.manshu.exception.CustomException;
import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.UserRepository;
import com.yizhaoqi.manshu.service.UserService;
import com.yizhaoqi.manshu.utils.JwtUtils;
import com.yizhaoqi.manshu.utils.LogUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    @Autowired
    private UserService userService;

    @Autowired
    private JwtUtils jwtUtils;

    @Autowired
    private UserRepository userRepository;



    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody UserRequest request) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("USER_REGISTER");
        try {
            if (request.username() == null || request.username().isEmpty() ||
                    request.password() == null || request.password().isEmpty()) {
                LogUtils.logUserOperation("anonymous", "REGISTER", "validation", "FAILED_EMPTY_PARAMS");
                monitor.end("English textEnglish textEnglish text");
                return ResponseEntity.badRequest().body(Map.of("code", 400, "message", "Username and password cannot be empty"));
            }

            userService.registerUser(request.username(), request.password());
            LogUtils.logUserOperation(request.username(), "REGISTER", "user_creation", "SUCCESS");
            monitor.end("English text");

            return ResponseEntity.ok(Map.of("code", 200, "message", "User registered successfully"));
        } catch (CustomException e) {
            LogUtils.logBusinessError("USER_REGISTER", request.username(), "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("USER_REGISTER", request.username(), "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("code", 500, "message", "Internal server error"));
        }
    }



    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody UserRequest request) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("USER_LOGIN");
        try {
            if (request.username() == null || request.username().isEmpty() ||
                    request.password() == null || request.password().isEmpty()) {
                LogUtils.logUserOperation("anonymous", "LOGIN", "validation", "FAILED_EMPTY_PARAMS");
                return ResponseEntity.badRequest().body(Map.of("code", 400, "message", "Username and password cannot be empty"));
            }

            String username = userService.authenticateUser(request.username(), request.password());
            if (username == null) {
                LogUtils.logUserOperation(request.username(), "LOGIN", "authentication", "FAILED_INVALID_CREDENTIALS");
                return ResponseEntity.status(401).body(Map.of("code", 401, "message", "Invalid credentials"));
            }

            String token = jwtUtils.generateToken(username);
            String refreshToken = jwtUtils.generateRefreshToken(username);
            LogUtils.logUserOperation(username, "LOGIN", "token_generation", "SUCCESS");
            monitor.end("English text");

            return ResponseEntity.ok(Map.of("code", 200, "message", "Login successful", "data", Map.of(
                "token", token,
                "refreshToken", refreshToken
            )));
        } catch (CustomException e) {
            LogUtils.logBusinessError("USER_LOGIN", request.username(), "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("USER_LOGIN", request.username(), "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(500).body(Map.of("code", 500, "message", "Internal server error"));
        }
    }


    @GetMapping("/me")
    public ResponseEntity<?> getCurrentUser(@RequestHeader("Authorization") String token) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("GET_USER_INFO");
        String username = null;
        try {
            username = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
            if (username == null || username.isEmpty()) {
                LogUtils.logUserOperation("anonymous", "GET_USER_INFO", "token_validation", "FAILED_INVALID_TOKEN");
                monitor.end("English textEnglish textEnglish texttoken");
                throw new CustomException("Invalid token", HttpStatus.UNAUTHORIZED);
            }

            User user = userRepository.findByUsername(username)
                    .orElseThrow(() -> new CustomException("User not found", HttpStatus.NOT_FOUND));


            Map<String, Object> displayUserData = new LinkedHashMap<>();
            displayUserData.put("id", user.getId());
            displayUserData.put("username", user.getUsername());
            displayUserData.put("role", user.getRole());


            if (user.getOrgTags() != null && !user.getOrgTags().isEmpty()) {
                List<String> orgTagsList = Arrays.asList(user.getOrgTags().split(","));
                displayUserData.put("orgTags", orgTagsList);
            } else {
                displayUserData.put("orgTags", List.of());
            }


            displayUserData.put("primaryOrg", user.getPrimaryOrg());

            displayUserData.put("createdAt", user.getCreatedAt());
            displayUserData.put("updatedAt", user.getUpdatedAt());

            LogUtils.logUserOperation(username, "GET_USER_INFO", "user_profile", "SUCCESS");
            monitor.end("English text");


            return ResponseEntity.ok(Map.of("code", 200, "message", "Get user detail successful", "data", displayUserData));
        } catch (CustomException e) {
            LogUtils.logBusinessError("GET_USER_INFO", username, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("GET_USER_INFO", username, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("code", 500, "message", "Internal server error"));
        }
    }


    @GetMapping("/org-tags")
    public ResponseEntity<?> getUserOrgTags(@RequestHeader("Authorization") String token) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("GET_USER_ORG_TAGS");
        String username = null;
        try {
            username = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
            if (username == null || username.isEmpty()) {
                LogUtils.logUserOperation("anonymous", "GET_ORG_TAGS", "token_validation", "FAILED_INVALID_TOKEN");
                monitor.end("English textEnglish textEnglish texttoken");
                throw new CustomException("Invalid token", HttpStatus.UNAUTHORIZED);
            }

            Map<String, Object> orgTagsInfo = userService.getUserOrgTags(username);

            LogUtils.logUserOperation(username, "GET_ORG_TAGS", "organization_tags", "SUCCESS");
            monitor.end("English text");

            return ResponseEntity.ok(Map.of(
                "code", 200,
                "message", "Get user organization tags successful",
                "data", orgTagsInfo
            ));
        } catch (CustomException e) {
            LogUtils.logBusinessError("GET_USER_ORG_TAGS", username, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("GET_USER_ORG_TAGS", username, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("code", 500, "message", "Internal server error"));
        }
    }


    @PutMapping("/primary-org")
    public ResponseEntity<?> setPrimaryOrg(@RequestHeader("Authorization") String token, @RequestBody PrimaryOrgRequest request) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("SET_PRIMARY_ORG");
        String username = null;
        try {
            username = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
            if (username == null || username.isEmpty()) {
                LogUtils.logUserOperation("anonymous", "SET_PRIMARY_ORG", "token_validation", "FAILED_INVALID_TOKEN");
                monitor.end("English textEnglish textEnglish texttoken");
                throw new CustomException("Invalid token", HttpStatus.UNAUTHORIZED);
            }

            if (request.primaryOrg() == null || request.primaryOrg().isEmpty()) {
                LogUtils.logUserOperation(username, "SET_PRIMARY_ORG", "validation", "FAILED_EMPTY_ORG");
                monitor.end("English textEnglish textEnglish text");
                return ResponseEntity.badRequest().body(Map.of("code", 400, "message", "Primary organization tag cannot be empty"));
            }

            userService.setUserPrimaryOrg(username, request.primaryOrg());

            LogUtils.logUserOperation(username, "SET_PRIMARY_ORG", request.primaryOrg(), "SUCCESS");
            monitor.end("English text");

            return ResponseEntity.ok(Map.of("code", 200, "message", "Primary organization set successfully"));
        } catch (CustomException e) {
            LogUtils.logBusinessError("SET_PRIMARY_ORG", username, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("SET_PRIMARY_ORG", username, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("code", 500, "message", "Internal server error"));
        }
    }


    @GetMapping("/upload-orgs")
    public ResponseEntity<?> getUploadOrgTags(@RequestAttribute("userId") String userId) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("GET_UPLOAD_ORG_TAGS");
        try {
            LogUtils.logBusiness("GET_UPLOAD_ORG_TAGS", userId, "English text");


            List<String> orgTags = Arrays.asList(userService.getUserOrgTags(userId).get("orgTags").toString().split(","));

            String primaryOrg = userService.getUserPrimaryOrg(userId);

            Map<String, Object> responseData = new HashMap<>();
            responseData.put("orgTags", orgTags);
            responseData.put("primaryOrg", primaryOrg);

            LogUtils.logUserOperation(userId, "GET_UPLOAD_ORG_TAGS", "upload_organizations", "SUCCESS");
            monitor.end("English text");

            return ResponseEntity.ok(Map.of(
                "code", 200,
                "message", "English text",
                "data", responseData
            ));
        } catch (Exception e) {
            LogUtils.logBusinessError("GET_UPLOAD_ORG_TAGS", userId, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of(
                "code", 500,
                "message", "English text: " + e.getMessage()
            ));
        }
    }


    @PostMapping("/logout")
    public ResponseEntity<?> logout(@RequestHeader("Authorization") String token) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("USER_LOGOUT");
        String username = null;
        try {
            if (token == null || !token.startsWith("Bearer ")) {
                LogUtils.logUserOperation("anonymous", "LOGOUT", "validation", "FAILED_INVALID_TOKEN");
                monitor.end("English textEnglish texttokenEnglish text");
                return ResponseEntity.badRequest().body(Map.of("code", 400, "message", "Invalid token format"));
            }

            String jwtToken = token.replace("Bearer ", "");
            username = jwtUtils.extractUsernameFromToken(jwtToken);

            if (username == null || username.isEmpty()) {
                LogUtils.logUserOperation("anonymous", "LOGOUT", "token_extraction", "FAILED_NO_USERNAME");
                monitor.end("English textEnglish textEnglish text");
                return ResponseEntity.status(401).body(Map.of("code", 401, "message", "Invalid token"));
            }


            jwtUtils.invalidateToken(jwtToken);

            LogUtils.logUserOperation(username, "LOGOUT", "token_invalidation", "SUCCESS");
            monitor.end("English text");

            return ResponseEntity.ok(Map.of("code", 200, "message", "Logout successful"));
        } catch (Exception e) {
            LogUtils.logBusinessError("USER_LOGOUT", username, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("code", 500, "message", "Internal server error"));
        }
    }


    @PostMapping("/logout-all")
    public ResponseEntity<?> logoutAll(@RequestHeader("Authorization") String token) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("USER_LOGOUT_ALL");
        String username = null;
        try {
            if (token == null || !token.startsWith("Bearer ")) {
                LogUtils.logUserOperation("anonymous", "LOGOUT_ALL", "validation", "FAILED_INVALID_TOKEN");
                monitor.end("English textEnglish texttokenEnglish text");
                return ResponseEntity.badRequest().body(Map.of("code", 400, "message", "Invalid token format"));
            }

            String jwtToken = token.replace("Bearer ", "");
            username = jwtUtils.extractUsernameFromToken(jwtToken);
            String userId = jwtUtils.extractUserIdFromToken(jwtToken);

            if (username == null || username.isEmpty() || userId == null) {
                LogUtils.logUserOperation("anonymous", "LOGOUT_ALL", "token_extraction", "FAILED_NO_USER_INFO");
                monitor.end("English textEnglish textEnglish text");
                return ResponseEntity.status(401).body(Map.of("code", 401, "message", "Invalid token"));
            }


            jwtUtils.invalidateAllUserTokens(userId);

            LogUtils.logUserOperation(username, "LOGOUT_ALL", "all_tokens_invalidation", "SUCCESS");
            monitor.end("English text");

            return ResponseEntity.ok(Map.of("code", 200, "message", "Logout from all devices successful"));
        } catch (Exception e) {
            LogUtils.logBusinessError("USER_LOGOUT_ALL", username, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("code", 500, "message", "Internal server error"));
        }
    }
}


record UserRequest(String username, String password) {}


record PrimaryOrgRequest(String primaryOrg) {}