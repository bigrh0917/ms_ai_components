package com.yizhaoqi.manshu.controller;

import com.yizhaoqi.manshu.model.FileUpload;
import com.yizhaoqi.manshu.model.OrganizationTag;
import com.yizhaoqi.manshu.repository.FileUploadRepository;
import com.yizhaoqi.manshu.repository.OrganizationTagRepository;
import com.yizhaoqi.manshu.service.DocumentService;
import com.yizhaoqi.manshu.utils.LogUtils;
import com.yizhaoqi.manshu.utils.JwtUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;


@RestController
@RequestMapping("/api/v1/documents")
public class DocumentController {

    @Autowired
    private DocumentService documentService;

    @Autowired
    private FileUploadRepository fileUploadRepository;

    @Autowired
    private OrganizationTagRepository organizationTagRepository;

    @Autowired
    private JwtUtils jwtUtils;


    @DeleteMapping("/{fileMd5}")
    public ResponseEntity<?> deleteDocument(
            @PathVariable String fileMd5,
            @RequestAttribute("userId") String userId,
            @RequestAttribute("role") String role) {

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("DELETE_DOCUMENT");
        try {
            LogUtils.logBusiness("DELETE_DOCUMENT", userId, "English text: fileMd5=%s, role=%s", fileMd5, role);


            Optional<FileUpload> fileOpt = fileUploadRepository.findByFileMd5AndUserId(fileMd5, userId);
            if (fileOpt.isEmpty()) {
                LogUtils.logUserOperation(userId, "DELETE_DOCUMENT", fileMd5, "FAILED_NOT_FOUND");
                monitor.end("English textEnglish textEnglish text");
                Map<String, Object> response = new HashMap<>();
                response.put("code", HttpStatus.NOT_FOUND.value());
                response.put("message", "English text");
                return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
            }

            FileUpload file = fileOpt.get();


            if (!file.getUserId().equals(userId) && !"ADMIN".equals(role)) {
                LogUtils.logUserOperation(userId, "DELETE_DOCUMENT", fileMd5, "FAILED_PERMISSION_DENIED");
                LogUtils.logBusiness("DELETE_DOCUMENT", userId, "English text: fileMd5=%s, fileOwner=%s", fileMd5, file.getUserId());
                monitor.end("English textEnglish textEnglish text");
                Map<String, Object> response = new HashMap<>();
                response.put("code", HttpStatus.FORBIDDEN.value());
                response.put("message", "English text");
                return ResponseEntity.status(HttpStatus.FORBIDDEN).body(response);
            }


            documentService.deleteDocument(fileMd5, userId);

            LogUtils.logFileOperation(userId, "DELETE", file.getFileName(), fileMd5, "SUCCESS");
            monitor.end("English text");
            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English text");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            LogUtils.logBusinessError("DELETE_DOCUMENT", userId, "English text: fileMd5=%s", e, fileMd5);
            monitor.end("English text: " + e.getMessage());
            Map<String, Object> response = new HashMap<>();
            response.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
            response.put("message", "English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }


    @GetMapping("/accessible")
    public ResponseEntity<?> getAccessibleFiles(
            @RequestAttribute("userId") String userId,
            @RequestAttribute("orgTags") String orgTags) {

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("GET_ACCESSIBLE_FILES");
        try {
            LogUtils.logBusiness("GET_ACCESSIBLE_FILES", userId, "English text: orgTags=%s", orgTags);

            List<FileUpload> files = documentService.getAccessibleFiles(userId, orgTags);

            LogUtils.logUserOperation(userId, "GET_ACCESSIBLE_FILES", "file_list", "SUCCESS");
            LogUtils.logBusiness("GET_ACCESSIBLE_FILES", userId, "English text: fileCount=%d", files.size());
            monitor.end("English text");

            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English text");
            response.put("data", files);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            LogUtils.logBusinessError("GET_ACCESSIBLE_FILES", userId, "English text", e);
            monitor.end("English text: " + e.getMessage());
            Map<String, Object> response = new HashMap<>();
            response.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
            response.put("message", "English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }


    @GetMapping("/uploads")
    public ResponseEntity<?> getUserUploadedFiles(
            @RequestAttribute("userId") String userId) {

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("GET_USER_UPLOADED_FILES");
        try {
            LogUtils.logBusiness("GET_USER_UPLOADED_FILES", userId, "English text");

            List<FileUpload> files = documentService.getUserUploadedFiles(userId);


            List<Map<String, Object>> fileData = files.stream().map(file -> {
                Map<String, Object> dto = new HashMap<>();
                dto.put("fileMd5", file.getFileMd5());
                dto.put("fileName", file.getFileName());
                dto.put("totalSize", file.getTotalSize());
                dto.put("status", file.getStatus());
                dto.put("userId", file.getUserId());
                dto.put("public", file.isPublic());
                dto.put("createdAt", file.getCreatedAt());
                dto.put("mergedAt", file.getMergedAt());


                String orgTagName = getOrgTagName(file.getOrgTag());
                dto.put("orgTagName", orgTagName);

                return dto;
            }).collect(Collectors.toList());

            LogUtils.logUserOperation(userId, "GET_USER_UPLOADED_FILES", "file_list", "SUCCESS");
            LogUtils.logBusiness("GET_USER_UPLOADED_FILES", userId, "English text: fileCount=%d", files.size());
            monitor.end("English text");

            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English text");
            response.put("data", fileData);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            LogUtils.logBusinessError("GET_USER_UPLOADED_FILES", userId, "English text", e);
            monitor.end("English text: " + e.getMessage());
            Map<String, Object> response = new HashMap<>();
            response.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
            response.put("message", "English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }


    @GetMapping("/download")
    public ResponseEntity<?> downloadFileByName(
            @RequestParam String fileName,
            @RequestParam(required = false) String token) {

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("DOWNLOAD_FILE_BY_NAME");
        try {

            String userId = null;
            String orgTags = null;

            if (token != null && !token.trim().isEmpty()) {
                try {


                    userId = jwtUtils.extractUsernameFromToken(token);
                    orgTags = jwtUtils.extractOrgTagsFromToken(token);
                } catch (Exception e) {
                    LogUtils.logBusiness("DOWNLOAD_FILE_BY_NAME", "anonymous", "TokenEnglish text: fileName=%s", fileName);
                }
            }

            LogUtils.logBusiness("DOWNLOAD_FILE_BY_NAME", userId != null ? userId : "anonymous", "English text: fileName=%s", fileName);


            if (userId == null) {

                Optional<FileUpload> publicFile = fileUploadRepository.findByFileNameAndIsPublicTrue(fileName);
                if (publicFile.isEmpty()) {
                    Map<String, Object> response = new HashMap<>();
                    response.put("code", HttpStatus.NOT_FOUND.value());
                    response.put("message", "English text");
                    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
                }

                FileUpload file = publicFile.get();
                String downloadUrl = documentService.generateDownloadUrl(file.getFileMd5());

                if (downloadUrl == null) {
                    Map<String, Object> response = new HashMap<>();
                    response.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
                    response.put("message", "English text");
                    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
                }

                Map<String, Object> response = new HashMap<>();
                response.put("code", 200);
                response.put("message", "English text");
                response.put("data", Map.of(
                    "fileName", file.getFileName(),
                    "downloadUrl", downloadUrl,
                    "fileSize", file.getTotalSize()
                ));
                return ResponseEntity.ok(response);
            }


            List<FileUpload> accessibleFiles = documentService.getAccessibleFiles(userId, orgTags);


            Optional<FileUpload> targetFile = accessibleFiles.stream()
                    .filter(file -> file.getFileName().equals(fileName))
                    .findFirst();

            if (targetFile.isEmpty()) {
                LogUtils.logUserOperation(userId, "DOWNLOAD_FILE_BY_NAME", fileName, "FAILED_NOT_FOUND");
                monitor.end("English textEnglish textEnglish text");
                Map<String, Object> response = new HashMap<>();
                response.put("code", HttpStatus.NOT_FOUND.value());
                response.put("message", "English text");
                return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
            }

            FileUpload file = targetFile.get();


            String downloadUrl = documentService.generateDownloadUrl(file.getFileMd5());

            if (downloadUrl == null) {
                LogUtils.logUserOperation(userId, "DOWNLOAD_FILE_BY_NAME", fileName, "FAILED_GENERATE_URL");
                monitor.end("English textEnglish textEnglish text");
                Map<String, Object> response = new HashMap<>();
                response.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
                response.put("message", "English text");
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
            }

            LogUtils.logFileOperation(userId, "DOWNLOAD", file.getFileName(), file.getFileMd5(), "SUCCESS");
            LogUtils.logUserOperation(userId, "DOWNLOAD_FILE_BY_NAME", fileName, "SUCCESS");
            monitor.end("English text");

            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English text");
            response.put("data", Map.of(
                "fileName", file.getFileName(),
                "downloadUrl", downloadUrl,
                "fileSize", file.getTotalSize()
            ));
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            String userId = "unknown";
            try {
                if (token != null && !token.trim().isEmpty()) {
                    userId = jwtUtils.extractUsernameFromToken(token);
                }
            } catch (Exception ignored) {}

            LogUtils.logBusinessError("DOWNLOAD_FILE_BY_NAME", userId, "English text: fileName=%s", e, fileName);
            monitor.end("English text: " + e.getMessage());
            Map<String, Object> response = new HashMap<>();
            response.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
            response.put("message", "English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }


    @GetMapping("/preview")
    public ResponseEntity<?> previewFileByName(
            @RequestParam String fileName,
            @RequestParam(required = false) String token) {

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("PREVIEW_FILE_BY_NAME");
        try {

            String userId = null;
            String orgTags = null;


            try {
                var authentication = SecurityContextHolder.getContext().getAuthentication();
                if (authentication != null && authentication.isAuthenticated()
                    && authentication.getPrincipal() instanceof UserDetails) {
                    UserDetails userDetails = (UserDetails) authentication.getPrincipal();
                    userId = userDetails.getUsername();

                    orgTags = userDetails.getAuthorities().stream()
                        .map(auth -> auth.getAuthority().replace("ROLE_", ""))
                        .findFirst()
                        .orElse(null);
                }
            } catch (Exception e) {
                LogUtils.logBusiness("PREVIEW_FILE_BY_NAME", "anonymous", "SecurityEnglish text: fileName=%s", fileName);
            }


            if (userId == null && token != null && !token.trim().isEmpty()) {
                try {
                    userId = jwtUtils.extractUsernameFromToken(token);
                    orgTags = jwtUtils.extractOrgTagsFromToken(token);
                } catch (Exception e) {
                    LogUtils.logBusiness("PREVIEW_FILE_BY_NAME", "anonymous", "TokenEnglish text: fileName=%s", fileName);
                }
            }

            LogUtils.logBusiness("PREVIEW_FILE_BY_NAME", userId != null ? userId : "anonymous", "English text: fileName=%s", fileName);


            if (userId == null) {
                Optional<FileUpload> publicFile = fileUploadRepository.findByFileNameAndIsPublicTrue(fileName);
                if (publicFile.isEmpty()) {
                    Map<String, Object> response = new HashMap<>();
                    response.put("code", HttpStatus.NOT_FOUND.value());
                    response.put("message", "English text");
                    return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
                }

                FileUpload file = publicFile.get();
                String previewContent = documentService.getFilePreviewContent(file.getFileMd5(), file.getFileName());

                if (previewContent == null) {
                    Map<String, Object> response = new HashMap<>();
                    response.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
                    response.put("message", "English text");
                    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
                }

                Map<String, Object> response = new HashMap<>();
                response.put("code", 200);
                response.put("message", "English text");
                response.put("data", Map.of(
                    "fileName", file.getFileName(),
                    "content", previewContent,
                    "fileSize", file.getTotalSize()
                ));
                return ResponseEntity.ok(response);
            }


            List<FileUpload> accessibleFiles = documentService.getAccessibleFiles(userId, orgTags);


            Optional<FileUpload> targetFile = accessibleFiles.stream()
                    .filter(file -> file.getFileName().equals(fileName))
                    .findFirst();

            if (targetFile.isEmpty()) {
                LogUtils.logUserOperation(userId, "PREVIEW_FILE_BY_NAME", fileName, "FAILED_NOT_FOUND");
                monitor.end("English textEnglish textEnglish text");
                Map<String, Object> response = new HashMap<>();
                response.put("code", HttpStatus.NOT_FOUND.value());
                response.put("message", "English text");
                return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
            }

            FileUpload file = targetFile.get();


            String previewContent = documentService.getFilePreviewContent(file.getFileMd5(), file.getFileName());

            if (previewContent == null) {
                LogUtils.logUserOperation(userId, "PREVIEW_FILE_BY_NAME", fileName, "FAILED_GET_CONTENT");
                monitor.end("English textEnglish textEnglish text");
                Map<String, Object> response = new HashMap<>();
                response.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
                response.put("message", "English text");
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
            }

            LogUtils.logFileOperation(userId, "PREVIEW", file.getFileName(), file.getFileMd5(), "SUCCESS");
            LogUtils.logUserOperation(userId, "PREVIEW_FILE_BY_NAME", fileName, "SUCCESS");
            monitor.end("English text");

            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English text");
            response.put("data", Map.of(
                "fileName", file.getFileName(),
                "content", previewContent,
                "fileSize", file.getTotalSize()
            ));
            return ResponseEntity.ok(response);

        } catch (Exception e) {
            String userId = "unknown";
            try {
                if (token != null && !token.trim().isEmpty()) {
                    userId = jwtUtils.extractUsernameFromToken(token);
                }
            } catch (Exception ignored) {}

            LogUtils.logBusinessError("PREVIEW_FILE_BY_NAME", userId, "English text: fileName=%s", e, fileName);
            monitor.end("English text: " + e.getMessage());
            Map<String, Object> response = new HashMap<>();
            response.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
            response.put("message", "English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
        }
    }


    private String getOrgTagName(String tagId) {
        if (tagId == null || tagId.isEmpty()) {
            return null;
        }

        try {
            Optional<OrganizationTag> tagOpt = organizationTagRepository.findByTagId(tagId);
            if (tagOpt.isPresent()) {
                return tagOpt.get().getName();
            } else {
                LogUtils.logBusiness("GET_ORG_TAG_NAME", "system", "English text: tagId=%s", tagId);
                return tagId;
            }
        } catch (Exception e) {
            LogUtils.logBusinessError("GET_ORG_TAG_NAME", "system", "English text: tagId=%s", e, tagId);
            return tagId;
        }
    }
}