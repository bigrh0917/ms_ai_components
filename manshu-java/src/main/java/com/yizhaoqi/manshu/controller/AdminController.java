package com.yizhaoqi.manshu.controller;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.yizhaoqi.manshu.exception.CustomException;
import com.yizhaoqi.manshu.model.OrganizationTag;
import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.OrganizationTagRepository;
import com.yizhaoqi.manshu.repository.UserRepository;
import com.yizhaoqi.manshu.service.UserService;
import com.yizhaoqi.manshu.utils.JwtUtils;
import com.yizhaoqi.manshu.utils.LogUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.*;
import java.util.stream.Collectors;


@RestController
@RequestMapping("/api/v1/admin")
public class AdminController {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JwtUtils jwtUtils;

    @Autowired
    private UserService userService;

    @Autowired
    private OrganizationTagRepository organizationTagRepository;

    @Autowired
    private RedisTemplate<String, String> redisTemplate;

    @Autowired
    private ObjectMapper objectMapper;


    @GetMapping("/users")
    public ResponseEntity<?> getAllUsers(@RequestHeader("Authorization") String token) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("ADMIN_GET_ALL_USERS");
        String adminUsername = null;
        try {
            adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
            User admin = validateAdmin(adminUsername);

            LogUtils.logBusiness("ADMIN_GET_ALL_USERS", adminUsername, "English text");

            List<User> users = userRepository.findAll();

            users.forEach(user -> user.setPassword(null));

            LogUtils.logUserOperation(adminUsername, "ADMIN_GET_ALL_USERS", "user_list", "SUCCESS");
            LogUtils.logBusiness("ADMIN_GET_ALL_USERS", adminUsername, "English textEnglish textEnglish text: %d", users.size());
            monitor.end("English text");

            return ResponseEntity.ok(Map.of("code", 200, "message", "Get all users successful", "data", users));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_GET_ALL_USERS", adminUsername, "English text", e);
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("code", 500, "message", "Failed to get users: " + e.getMessage()));
        }
    }


    @PostMapping("/knowledge/add")
    public ResponseEntity<?> addKnowledgeDocument(
            @RequestHeader("Authorization") String token,
            @RequestParam("file") MultipartFile file,
            @RequestParam("description") String description) {

        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {



            Map<String, String> response = new HashMap<>();
            response.put("message", "English text");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_ADD_KNOWLEDGE", adminUsername, "English text", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "English text: " + e.getMessage()));
        }
    }


    @DeleteMapping("/knowledge/{documentId}")
    public ResponseEntity<?> deleteKnowledgeDocument(
            @RequestHeader("Authorization") String token,
            @PathVariable("documentId") String documentId) {

        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {



            Map<String, String> response = new HashMap<>();
            response.put("message", "English text");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_DELETE_KNOWLEDGE", adminUsername, "English text", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "English text: " + e.getMessage()));
        }
    }


    @GetMapping("/system/status")
    public ResponseEntity<?> getSystemStatus(@RequestHeader("Authorization") String token) {
        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {




            Map<String, Object> status = new HashMap<>();
            status.put("cpu_usage", "30%");
            status.put("memory_usage", "45%");
            status.put("disk_usage", "60%");
            status.put("active_users", 15);
            status.put("total_documents", 250);
            status.put("total_conversations", 1200);

            return ResponseEntity.ok(Map.of("data", status));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_GET_SYSTEM_STATUS", adminUsername, "English text", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "English text: " + e.getMessage()));
        }
    }


    @GetMapping("/user-activities")
    public ResponseEntity<?> getUserActivities(
            @RequestHeader("Authorization") String token,
            @RequestParam(required = false) String username,
            @RequestParam(required = false) String start_date,
            @RequestParam(required = false) String end_date) {

        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {




            List<Map<String, Object>> activities = List.of(
                Map.of(
                    "username", "user1",
                    "action", "LOGIN",
                    "timestamp", "2023-03-01T10:15:30",
                    "ip_address", "192.168.1.100"
                ),
                Map.of(
                    "username", "user2",
                    "action", "UPLOAD_FILE",
                    "timestamp", "2023-03-01T11:20:45",
                    "ip_address", "192.168.1.101"
                )
            );

            return ResponseEntity.ok(Map.of("data", activities));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_GET_USER_ACTIVITIES", adminUsername, "English text", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "English text: " + e.getMessage()));
        }
    }


    @PostMapping("/users/create-admin")
    public ResponseEntity<?> createAdminUser(
            @RequestHeader("Authorization") String token,
            @RequestBody AdminUserRequest request) {

        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {
            userService.createAdminUser(request.username(), request.password(), adminUsername);
            return ResponseEntity.ok(Map.of("code", 200, "message", "English text"));
        } catch (CustomException e) {
            LogUtils.logBusinessError("ADMIN_CREATE_ADMIN_USER", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_CREATE_ADMIN_USER", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("code", 500, "message", "English text: " + e.getMessage()));
        }
    }


    @PostMapping("/org-tags")
    public ResponseEntity<?> createOrganizationTag(
            @RequestHeader("Authorization") String token,
            @RequestBody OrgTagRequest request) {

        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {
            OrganizationTag tag = userService.createOrganizationTag(
                request.tagId(),
                request.name(),
                request.description(),
                request.parentTag(),
                adminUsername
            );
            return ResponseEntity.ok(Map.of("code", 200, "message", "English text", "data", tag));
        } catch (CustomException e) {
            LogUtils.logBusinessError("ADMIN_CREATE_ORG_TAG", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_CREATE_ORG_TAG", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("code", 500, "message", "English text: " + e.getMessage()));
        }
    }


    @GetMapping("/org-tags")
    public ResponseEntity<?> getAllOrganizationTags(@RequestHeader("Authorization") String token) {
        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {
            List<OrganizationTag> tags = organizationTagRepository.findAll();
            return ResponseEntity.ok(Map.of("code", 200, "message", "English text", "data", tags));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_GET_ORG_TAGS", adminUsername, "English text", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("code", 500, "message", "English text: " + e.getMessage()));
        }
    }


    @PutMapping("/users/{userId}/org-tags")
    public ResponseEntity<?> assignOrgTagsToUser(
            @RequestHeader("Authorization") String token,
            @PathVariable Long userId,
            @RequestBody AssignOrgTagsRequest request) {

        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {
            userService.assignOrgTagsToUser(userId, request.orgTags(), adminUsername);
            return ResponseEntity.ok(Map.of("code", 200, "message", "English text"));
        } catch (CustomException e) {
            LogUtils.logBusinessError("ADMIN_ASSIGN_ORG_TAGS", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_ASSIGN_ORG_TAGS", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("code", 500, "message", "English text: " + e.getMessage()));
        }
    }


    @GetMapping("/org-tags/tree")
    public ResponseEntity<?> getOrganizationTagTree(@RequestHeader("Authorization") String token) {
        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {
            List<Map<String, Object>> tagTree = userService.getOrganizationTagTree();
            return ResponseEntity.ok(Map.of(
                "code", 200,
                "message", "English text",
                "data", tagTree
            ));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_GET_ORG_TAG_TREE", adminUsername, "English text", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("code", 500, "message", "English text: " + e.getMessage()));
        }
    }


    @PutMapping("/org-tags/{tagId}")
    public ResponseEntity<?> updateOrganizationTag(
            @RequestHeader("Authorization") String token,
            @PathVariable String tagId,
            @RequestBody OrgTagUpdateRequest request) {

        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {
            OrganizationTag updatedTag = userService.updateOrganizationTag(
                tagId,
                request.name(),
                request.description(),
                request.parentTag(),
                adminUsername
            );
            return ResponseEntity.ok(Map.of(
                "code", 200,
                "message", "English text",
                "data", updatedTag
            ));
        } catch (CustomException e) {
            LogUtils.logBusinessError("ADMIN_UPDATE_ORG_TAG", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_UPDATE_ORG_TAG", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("code", 500, "message", "English text: " + e.getMessage()));
        }
    }


    @DeleteMapping("/org-tags/{tagId}")
    public ResponseEntity<?> deleteOrganizationTag(
            @RequestHeader("Authorization") String token,
            @PathVariable String tagId) {

        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {
            userService.deleteOrganizationTag(tagId, adminUsername);
            return ResponseEntity.ok(Map.of(
                "code", 200,
                "message", "English text"
            ));
        } catch (CustomException e) {
            LogUtils.logBusinessError("ADMIN_DELETE_ORG_TAG", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_DELETE_ORG_TAG", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("code", 500, "message", "English text: " + e.getMessage()));
        }
    }


    @GetMapping("/users/list")
    public ResponseEntity<?> getUserList(
            @RequestHeader("Authorization") String token,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String orgTag,
            @RequestParam(required = false) Integer status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {

        String adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
        validateAdmin(adminUsername);

        try {
            Map<String, Object> usersData = userService.getUserList(keyword, orgTag, status, page, size);
            return ResponseEntity.ok(Map.of(
                "code", 200,
                "message", "English text",
                "data", usersData
            ));
        } catch (CustomException e) {
            LogUtils.logBusinessError("ADMIN_GET_USER_LIST", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_GET_USER_LIST", adminUsername, "English text: %s", e, e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("code", 500, "message", "English text: " + e.getMessage()));
        }
    }


    @GetMapping("/conversation")
    public ResponseEntity<?> getAllConversations(
            @RequestHeader("Authorization") String token,
            @RequestParam(required = false) String userid,
            @RequestParam(required = false) String start_date,
            @RequestParam(required = false) String end_date) {

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("ADMIN_GET_ALL_CONVERSATIONS");
        String adminUsername = null;
        try {

            adminUsername = jwtUtils.extractUsernameFromToken(token.replace("Bearer ", ""));
            User admin = validateAdmin(adminUsername);

            LogUtils.logBusiness("ADMIN_GET_ALL_CONVERSATIONS", adminUsername, "English textEnglish textEnglish textID: %s, English text: %s English text %s", userid, start_date, end_date);

            List<Map<String, Object>> allConversations = new ArrayList<>();


            String targetUsername = null;
            if (userid != null && !userid.isEmpty()) {
                try {
                    Long userIdLong = Long.parseLong(userid);
                    Optional<User> targetUser = userRepository.findById(userIdLong);
                    if (targetUser.isPresent()) {
                        targetUsername = targetUser.get().getUsername();
                        LogUtils.logBusiness("ADMIN_GET_ALL_CONVERSATIONS", adminUsername, "English text: ID=%s, English text=%s", userid, targetUsername);
                    } else {
                        LogUtils.logBusiness("ADMIN_GET_ALL_CONVERSATIONS", adminUsername, "English textIDEnglish text: %s", userid);
                        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                                .body(Map.of("code", 404, "message", "English text"));
                    }
                } catch (NumberFormatException e) {
                    LogUtils.logBusiness("ADMIN_GET_ALL_CONVERSATIONS", adminUsername, "English textIDEnglish text: %s", userid);
                    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                            .body(Map.of("code", 400, "message", "English textIDEnglish text"));
                }
            }


            Set<String> userKeys = redisTemplate.keys("user:*:current_conversation");

            if (userKeys != null && !userKeys.isEmpty()) {
                for (String userKey : userKeys) {
                    String conversationId = redisTemplate.opsForValue().get(userKey);
                    if (conversationId != null) {

                        String redisUserId = userKey.replace("user:", "").replace(":current_conversation", "");


                        if (userid != null && !userid.isEmpty()) {

                            if (!redisUserId.equals(userid) && !redisUserId.equals(targetUsername)) {
                                continue;
                            }
                        }


                        String conversationKey = "conversation:" + conversationId;
                        String json = redisTemplate.opsForValue().get(conversationKey);
                        if (json != null) {
                            String displayUsername = targetUsername != null ? targetUsername : redisUserId;
                            processRedisConversation(json, allConversations, displayUsername, start_date, end_date);
                        }
                    }
                }
            }

            LogUtils.logBusiness("ADMIN_GET_ALL_CONVERSATIONS", adminUsername, "English textEnglish textEnglish text %d English text", allConversations.size());
            LogUtils.logUserOperation(adminUsername, "ADMIN_GET_ALL_CONVERSATIONS", "conversation_history", "SUCCESS");
            monitor.end("English text");


            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English text");
            response.put("data", allConversations);
            return ResponseEntity.ok().body(response);

        } catch (CustomException e) {
            LogUtils.logBusinessError("ADMIN_GET_ALL_CONVERSATIONS", adminUsername, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(e.getStatus()).body(Map.of("code", e.getStatus().value(), "message", e.getMessage()));
        } catch (Exception e) {
            LogUtils.logBusinessError("ADMIN_GET_ALL_CONVERSATIONS", adminUsername, "English text: %s", e, e.getMessage());
            monitor.end("English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of("code", 500, "message", "English text: " + e.getMessage()));
        }
    }


    private void processRedisConversation(String json, List<Map<String, Object>> targetList, String username, String startDate, String endDate) throws JsonProcessingException {
        List<Map<String, String>> history = objectMapper.readValue(json,
                new TypeReference<List<Map<String, String>>>() {});


        java.time.LocalDateTime startDateTime = null;
        java.time.LocalDateTime endDateTime = null;

        if (startDate != null && !startDate.trim().isEmpty()) {
            try {
                startDateTime = parseDateTime(startDate);
            } catch (Exception e) {
                LogUtils.logBusinessError("ADMIN_GET_ALL_CONVERSATIONS", username, "English text: %s", e, startDate);
            }
        }

        if (endDate != null && !endDate.trim().isEmpty()) {
            try {
                endDateTime = parseDateTime(endDate);
            } catch (Exception e) {
                LogUtils.logBusinessError("ADMIN_GET_ALL_CONVERSATIONS", username, "English text: %s", e, endDate);
            }
        }


        for (Map<String, String> message : history) {
            String messageTimestamp = message.getOrDefault("timestamp", "English text");


            if (startDateTime != null || endDateTime != null) {
                if (!"English text".equals(messageTimestamp)) {
                    try {
                        java.time.LocalDateTime messageDateTime = java.time.LocalDateTime.parse(messageTimestamp,
                            java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss"));


                        if (startDateTime != null && messageDateTime.isBefore(startDateTime)) {
                            continue;
                        }
                        if (endDateTime != null && messageDateTime.isAfter(endDateTime)) {
                            continue;
                        }
                    } catch (Exception e) {

                        LogUtils.logBusinessError("ADMIN_GET_ALL_CONVERSATIONS", username, "English text: %s", e, messageTimestamp);
                    }
                }

                else if (startDateTime != null || endDateTime != null) {
                    continue;
                }
            }

            Map<String, Object> messageWithMetadata = new HashMap<>();
            messageWithMetadata.put("role", message.get("role"));
            messageWithMetadata.put("content", message.get("content"));
            messageWithMetadata.put("timestamp", messageTimestamp);
            messageWithMetadata.put("username", username);
            targetList.add(messageWithMetadata);
        }
    }


    private java.time.LocalDateTime parseDateTime(String dateTimeStr) {
        if (dateTimeStr == null || dateTimeStr.trim().isEmpty()) {
            return null;
        }

        try {

            return java.time.LocalDateTime.parse(dateTimeStr);
        } catch (java.time.format.DateTimeParseException e1) {
            try {

                if (dateTimeStr.length() == 16) {
                    return java.time.LocalDateTime.parse(dateTimeStr + ":00");
                }


                if (dateTimeStr.length() == 13) {
                    return java.time.LocalDateTime.parse(dateTimeStr + ":00:00");
                }


                if (dateTimeStr.length() == 10) {
                    return java.time.LocalDateTime.parse(dateTimeStr + "T00:00:00");
                }


                java.time.format.DateTimeFormatter formatter = java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm");
                return java.time.LocalDateTime.parse(dateTimeStr, formatter);
            } catch (Exception e2) {
                LogUtils.logBusinessError("PARSE_DATETIME", "system", "English text: %s", e2, dateTimeStr);
                throw new CustomException("English text: " + dateTimeStr, HttpStatus.BAD_REQUEST);
            }
        }
    }


    private User validateAdmin(String username) {
        if (username == null || username.isEmpty()) {
            throw new CustomException("Invalid token", HttpStatus.UNAUTHORIZED);
        }

        User admin = userRepository.findByUsername(username)
                .orElseThrow(() -> new CustomException("User not found", HttpStatus.NOT_FOUND));

        if (admin.getRole() != User.Role.ADMIN) {
            throw new CustomException("Unauthorized access: Admin role required", HttpStatus.FORBIDDEN);
        }

        return admin;
    }
}


record AdminUserRequest(String username, String password) {}


record OrgTagRequest(String tagId, String name, String description, String parentTag) {}


record AssignOrgTagsRequest(List<String> orgTags) {}


record OrgTagUpdateRequest(String name, String description, String parentTag) {}