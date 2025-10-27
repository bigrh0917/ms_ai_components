package com.yizhaoqi.manshu.controller;

import com.yizhaoqi.manshu.config.KafkaConfig;
import com.yizhaoqi.manshu.model.FileProcessingTask;
import com.yizhaoqi.manshu.model.FileUpload;
import com.yizhaoqi.manshu.repository.FileUploadRepository;
import com.yizhaoqi.manshu.service.FileTypeValidationService;
import com.yizhaoqi.manshu.service.UploadService;
import com.yizhaoqi.manshu.service.UserService;
import com.yizhaoqi.manshu.utils.LogUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

@RestController
@RequestMapping("/api/v1/upload")
public class UploadController {

    @Autowired
    private UploadService uploadService;

    @Autowired
    private KafkaTemplate<String, Object> kafkaTemplate;

    @Autowired
    private KafkaConfig kafkaConfig;

    @Autowired
    private UserService userService;

    @Autowired
    private FileUploadRepository fileUploadRepository;

    @Autowired
    private FileTypeValidationService fileTypeValidationService;

    public UploadController(UploadService uploadService, KafkaTemplate<String, Object> kafkaTemplate) {
        this.uploadService = uploadService;
        this.kafkaTemplate = kafkaTemplate;
    }


    @PostMapping("/chunk")
    public ResponseEntity<Map<String, Object>> uploadChunk(
            @RequestParam("fileMd5") String fileMd5,
            @RequestParam("chunkIndex") int chunkIndex,
            @RequestParam("totalSize") long totalSize,
            @RequestParam("fileName") String fileName,
            @RequestParam(value = "totalChunks", required = false) Integer totalChunks,
            @RequestParam(value = "orgTag", required = false) String orgTag,
            @RequestParam(value = "isPublic", required = false, defaultValue = "false") boolean isPublic,
            @RequestParam("file") MultipartFile file,
            @RequestAttribute("userId") String userId) throws IOException {

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("UPLOAD_CHUNK");
        try {

            if (chunkIndex == 0) {
                FileTypeValidationService.FileTypeValidationResult validationResult =
                    fileTypeValidationService.validateFileType(fileName);

                LogUtils.logBusiness("UPLOAD_CHUNK", userId, "English text: fileName=%s, valid=%s, fileType=%s, message=%s",
                        fileName, validationResult.isValid(), validationResult.getFileType(), validationResult.getMessage());

                if (!validationResult.isValid()) {
                    LogUtils.logBusinessError("UPLOAD_CHUNK", userId, "English text: fileName=%s, fileType=%s",
                            new RuntimeException(validationResult.getMessage()), fileName, validationResult.getFileType());
                    monitor.end("English text: " + validationResult.getMessage());

                    Map<String, Object> errorResponse = new HashMap<>();
                    errorResponse.put("code", HttpStatus.BAD_REQUEST.value());
                    errorResponse.put("message", validationResult.getMessage());
                    errorResponse.put("fileType", validationResult.getFileType());
                    errorResponse.put("supportedTypes", fileTypeValidationService.getSupportedFileTypes());
                    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errorResponse);
                }
            }

            String fileType = getFileType(fileName);
            String contentType = file.getContentType();

            LogUtils.logBusiness("UPLOAD_CHUNK", userId, "English text: fileMd5=%s, chunkIndex=%d, fileName=%s, fileType=%s, contentType=%s, fileSize=%d, totalSize=%d, orgTag=%s, isPublic=%s",
                    fileMd5, chunkIndex, fileName, fileType, contentType, file.getSize(), totalSize, orgTag, isPublic);


        if (orgTag == null || orgTag.isEmpty()) {
            try {
                    LogUtils.logBusiness("UPLOAD_CHUNK", userId, "English textEnglish textEnglish text: fileName=%s", fileName);
                String primaryOrg = userService.getUserPrimaryOrg(userId);
                orgTag = primaryOrg;
                    LogUtils.logBusiness("UPLOAD_CHUNK", userId, "English text: fileName=%s, orgTag=%s", fileName, orgTag);
            } catch (Exception e) {
                    LogUtils.logBusinessError("UPLOAD_CHUNK", userId, "English text: fileName=%s", e, fileName);
                    monitor.end("English text: " + e.getMessage());
                Map<String, Object> errorResponse = new HashMap<>();
                errorResponse.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
                errorResponse.put("message", "English text: " + e.getMessage());
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
            }
        }

            LogUtils.logFileOperation(userId, "UPLOAD_CHUNK", fileName, fileMd5, "PROCESSING");

            uploadService.uploadChunk(fileMd5, chunkIndex, totalSize, fileName, file, orgTag, isPublic, userId);

            List<Integer> uploadedChunks = uploadService.getUploadedChunks(fileMd5, userId);
            int actualTotalChunks = uploadService.getTotalChunks(fileMd5, userId);
            double progress = calculateProgress(uploadedChunks, actualTotalChunks);

            LogUtils.logBusiness("UPLOAD_CHUNK", userId, "English text: fileMd5=%s, fileName=%s, fileType=%s, chunkIndex=%d, English text=%.2f%%",
                    fileMd5, fileName, fileType, chunkIndex, progress);
            monitor.end("English text");


            Map<String, Object> data = new HashMap<>();
            data.put("uploaded", uploadedChunks);
            data.put("progress", progress);


            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English text");
            response.put("data", data);

            return ResponseEntity.ok(response);
        } catch (Exception e) {
            String fileType = getFileType(fileName);
            LogUtils.logBusinessError("UPLOAD_CHUNK", userId, "English text: fileMd5=%s, fileName=%s, fileType=%s, chunkIndex=%d", e, fileMd5, fileName, fileType, chunkIndex);
            monitor.end("English text: " + e.getMessage());
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
            errorResponse.put("message", "English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }


    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getUploadStatus(@RequestParam("file_md5") String fileMd5, @RequestAttribute("userId") String userId) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("GET_UPLOAD_STATUS");
        try {

            String fileName = "unknown";
            String fileType = "unknown";
            try {
                Optional<FileUpload> fileUpload = fileUploadRepository.findByFileMd5(fileMd5);
                if (fileUpload.isPresent()) {
                    fileName = fileUpload.get().getFileName();
                    fileType = getFileType(fileName);
                }
            } catch (Exception e) {

                LogUtils.logBusiness("GET_UPLOAD_STATUS", "system", "English textEnglish textEnglish text: fileMd5=%s, English text=%s", fileMd5, e.getMessage());
            }

            LogUtils.logBusiness("GET_UPLOAD_STATUS", "system", "English text: fileMd5=%s, fileName=%s, fileType=%s", fileMd5, fileName, fileType);

            List<Integer> uploadedChunks = uploadService.getUploadedChunks(fileMd5, userId);
            int totalChunks = uploadService.getTotalChunks(fileMd5, userId);
            double progress = calculateProgress(uploadedChunks, totalChunks);

            LogUtils.logBusiness("GET_UPLOAD_STATUS", "system", "English text: fileMd5=%s, fileName=%s, fileType=%s, English text=%d/%d, English text=%.2f%%",
                    fileMd5, fileName, fileType, uploadedChunks.size(), totalChunks, progress);
            monitor.end("English text");


            Map<String, Object> data = new HashMap<>();
            data.put("uploaded", uploadedChunks);
            data.put("progress", progress);
            data.put("fileName", fileName);
            data.put("fileType", fileType);


            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English text");
            response.put("data", data);

            return ResponseEntity.ok(response);
        } catch (Exception e) {
            LogUtils.logBusinessError("GET_UPLOAD_STATUS", "system", "English text: fileMd5=%s", e, fileMd5);
            monitor.end("English text: " + e.getMessage());
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
            errorResponse.put("message", "English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }


    @Transactional
    @PostMapping("/merge")
    public ResponseEntity<Map<String, Object>> mergeFile(
            @RequestBody MergeRequest request,
            @RequestAttribute("userId") String userId) {

        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("MERGE_FILE");
        try {
            String fileType = getFileType(request.fileName());
            LogUtils.logBusiness("MERGE_FILE", userId, "English text: fileMd5=%s, fileName=%s, fileType=%s",
                    request.fileMd5(), request.fileName(), fileType);


            LogUtils.logBusiness("MERGE_FILE", userId, "English text: fileMd5=%s, fileName=%s", request.fileMd5(), request.fileName());
            FileUpload fileUpload = fileUploadRepository.findByFileMd5AndUserId(request.fileMd5(), userId)
                    .orElseThrow(() -> {
                        LogUtils.logUserOperation(userId, "MERGE_FILE", request.fileMd5(), "FAILED_FILE_NOT_FOUND");
                        return new RuntimeException("English text");
                    });


            if (!fileUpload.getUserId().equals(userId)) {
                LogUtils.logUserOperation(userId, "MERGE_FILE", request.fileMd5(), "FAILED_PERMISSION_DENIED");
                LogUtils.logBusiness("MERGE_FILE", userId, "English text: English text, fileMd5=%s, fileName=%s, English text=%s",
                        request.fileMd5(), request.fileName(), fileUpload.getUserId());
                monitor.end("English textEnglish textEnglish text");
                Map<String, Object> errorResponse = new HashMap<>();
                errorResponse.put("code", HttpStatus.FORBIDDEN.value());
                errorResponse.put("message", "English text");
                return ResponseEntity.status(HttpStatus.FORBIDDEN).body(errorResponse);
            }

            LogUtils.logBusiness("MERGE_FILE", userId, "English textEnglish textEnglish text: fileMd5=%s, fileName=%s, fileType=%s", request.fileMd5(), request.fileName(), fileType);


            List<Integer> uploadedChunks = uploadService.getUploadedChunks(request.fileMd5(), userId);
            int totalChunks = uploadService.getTotalChunks(request.fileMd5(), userId);
            LogUtils.logBusiness("MERGE_FILE", userId, "English text: fileMd5=%s, fileName=%s, English text=%d/%d",
                    request.fileMd5(), request.fileName(), uploadedChunks.size(), totalChunks);

            if (uploadedChunks.size() < totalChunks) {
                LogUtils.logUserOperation(userId, "MERGE_FILE", request.fileMd5(), "FAILED_INCOMPLETE_CHUNKS");
                monitor.end("English textEnglish textEnglish text");
                Map<String, Object> errorResponse = new HashMap<>();
                errorResponse.put("code", HttpStatus.BAD_REQUEST.value());
                errorResponse.put("message", "English textEnglish textEnglish text");
                return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(errorResponse);
            }


            LogUtils.logBusiness("MERGE_FILE", userId, "English text: fileMd5=%s, fileName=%s, fileType=%s, English text=%d", request.fileMd5(), request.fileName(), fileType, totalChunks);
            String objectUrl = uploadService.mergeChunks(request.fileMd5(), request.fileName(), userId);
            LogUtils.logFileOperation(userId, "MERGE", request.fileName(), request.fileMd5(), "SUCCESS");


            LogUtils.logBusiness("MERGE_FILE", userId, "English text: fileMd5=%s, fileName=%s, fileType=%s, orgTag=%s, isPublic=%s",
                    request.fileMd5(), request.fileName(), fileType, fileUpload.getOrgTag(), fileUpload.isPublic());

            FileProcessingTask task = new FileProcessingTask(
                    request.fileMd5(),
                    objectUrl,
                    request.fileName(),
                    fileUpload.getUserId(),
                    fileUpload.getOrgTag(),
                    fileUpload.isPublic()
            );

            LogUtils.logBusiness("MERGE_FILE", userId, "English textKafka(English text): topic=%s, fileMd5=%s, fileName=%s",
                    kafkaConfig.getFileProcessingTopic(), request.fileMd5(), request.fileName());
            kafkaTemplate.executeInTransaction(kt -> {
                kt.send(kafkaConfig.getFileProcessingTopic(), task);
                return true;
            });
            LogUtils.logBusiness("MERGE_FILE", userId, "English text: fileMd5=%s, fileName=%s, fileType=%s", request.fileMd5(), request.fileName(), fileType);


            Map<String, Object> data = new HashMap<>();
            data.put("object_url", objectUrl);


            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English textEnglish textEnglish text Kafka");
            response.put("data", data);

            LogUtils.logUserOperation(userId, "MERGE_FILE", request.fileMd5(), "SUCCESS");
            monitor.end("English text");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            String fileType = getFileType(request.fileName());
            LogUtils.logBusinessError("MERGE_FILE", userId, "English text: fileMd5=%s, fileName=%s, fileType=%s", e,
                    request.fileMd5(), request.fileName(), fileType);
            monitor.end("English text: " + e.getMessage());
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
            errorResponse.put("message", "English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }


    private double calculateProgress(List<Integer> uploadedChunks, int totalChunks) {
        if (totalChunks == 0) {
            LogUtils.logBusiness("CALCULATE_PROGRESS", "system", "English text0");
            return 0.0;
        }
        return (double) uploadedChunks.size() / totalChunks * 100;
    }


    public record MergeRequest(String fileMd5, String fileName) {}


    @GetMapping("/supported-types")
    public ResponseEntity<Map<String, Object>> getSupportedFileTypes() {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("GET_SUPPORTED_TYPES");
        try {
            LogUtils.logBusiness("GET_SUPPORTED_TYPES", "system", "English text");

            Set<String> supportedTypes = fileTypeValidationService.getSupportedFileTypes();
            Set<String> supportedExtensions = fileTypeValidationService.getSupportedExtensions();


            Map<String, Object> data = new HashMap<>();
            data.put("supportedTypes", supportedTypes);
            data.put("supportedExtensions", supportedExtensions);
            data.put("description", "English textEnglish textEnglish text");


            Map<String, Object> response = new HashMap<>();
            response.put("code", 200);
            response.put("message", "English text");
            response.put("data", data);

            LogUtils.logBusiness("GET_SUPPORTED_TYPES", "system", "English text: English text=%d, English text=%d",
                    supportedTypes.size(), supportedExtensions.size());
            monitor.end("English text");

            return ResponseEntity.ok(response);
        } catch (Exception e) {
            LogUtils.logBusinessError("GET_SUPPORTED_TYPES", "system", "English text", e);
            monitor.end("English text: " + e.getMessage());
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("code", HttpStatus.INTERNAL_SERVER_ERROR.value());
            errorResponse.put("message", "English text: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }


    private String getFileType(String fileName) {
        if (fileName == null || fileName.isEmpty()) {
            return "unknown";
        }

        int lastDotIndex = fileName.lastIndexOf('.');
        if (lastDotIndex == -1 || lastDotIndex == fileName.length() - 1) {
            return "unknown";
        }

        String extension = fileName.substring(lastDotIndex + 1).toLowerCase();


        switch (extension) {
            case "pdf":
                return "PDFEnglish text";
            case "doc":
            case "docx":
                return "WordEnglish text";
            case "xls":
            case "xlsx":
                return "ExcelEnglish text";
            case "ppt":
            case "pptx":
                return "PowerPointEnglish text";
            case "txt":
                return "English text";
            case "md":
                return "MarkdownEnglish text";
            case "jpg":
            case "jpeg":
                return "JPEGEnglish text";
            case "png":
                return "PNGEnglish text";
            case "gif":
                return "GIFEnglish text";
            case "bmp":
                return "BMPEnglish text";
            case "svg":
                return "SVGEnglish text";
            case "mp4":
                return "MP4English text";
            case "avi":
                return "AVIEnglish text";
            case "mov":
                return "MOVEnglish text";
            case "wmv":
                return "WMVEnglish text";
            case "mp3":
                return "MP3English text";
            case "wav":
                return "WAVEnglish text";
            case "flac":
                return "FLACEnglish text";
            case "zip":
                return "ZIPEnglish text";
            case "rar":
                return "RAREnglish text";
            case "7z":
                return "7ZEnglish text";
            case "tar":
                return "TAREnglish text";
            case "gz":
                return "GZEnglish text";
            case "json":
                return "JSONEnglish text";
            case "xml":
                return "XMLEnglish text";
            case "csv":
                return "CSVEnglish text";
            case "html":
            case "htm":
                return "HTMLEnglish text";
            case "css":
                return "CSSEnglish text";
            case "js":
                return "JavaScriptEnglish text";
            case "java":
                return "JavaEnglish text";
            case "py":
                return "PythonEnglish text";
            case "cpp":
            case "c":
                return "C/C++English text";
            case "sql":
                return "SQLEnglish text";
            default:
                return extension.toUpperCase() + "English text";
        }
    }
}
