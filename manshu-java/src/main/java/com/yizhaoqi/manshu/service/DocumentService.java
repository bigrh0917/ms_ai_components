package com.yizhaoqi.manshu.service;

import com.yizhaoqi.manshu.model.FileUpload;
import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.DocumentVectorRepository;
import com.yizhaoqi.manshu.repository.FileUploadRepository;
import com.yizhaoqi.manshu.repository.UserRepository;
import io.minio.GetObjectArgs;
import io.minio.GetPresignedObjectUrlArgs;
import io.minio.MinioClient;
import io.minio.RemoveObjectArgs;
import io.minio.http.Method;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;


@Service
public class DocumentService {

    private static final Logger logger = LoggerFactory.getLogger(DocumentService.class);

    @Autowired
    private FileUploadRepository fileUploadRepository;

    @Autowired
    private DocumentVectorRepository documentVectorRepository;

    @Autowired
    private MinioClient minioClient;

    @Autowired
    private ElasticsearchService elasticsearchService;

    @Autowired
    private OrgTagCacheService orgTagCacheService;

    @Autowired
    private UserRepository userRepository;


    @Transactional
    public void deleteDocument(String fileMd5, String userId) {
        logger.info("English text: {}", fileMd5);

        try {

            FileUpload fileUpload = fileUploadRepository.findByFileMd5AndUserId(fileMd5, userId)
                    .orElseThrow(() -> new RuntimeException("English text"));


            try {
                elasticsearchService.deleteByFileMd5(fileMd5);
                logger.info("English textElasticsearchEnglish text: {}", fileMd5);
            } catch (Exception e) {
                logger.error("English textElasticsearchEnglish text: {}", fileMd5, e);

            }


            try {
                String objectName = "merged/" + fileUpload.getFileName();
                minioClient.removeObject(
                        RemoveObjectArgs.builder()
                                .bucket("uploads")
                                .object(objectName)
                                .build()
                );
                logger.info("English textMinIOEnglish text: {}", objectName);
            } catch (Exception e) {
                logger.error("English textMinIOEnglish text: {}", fileMd5, e);

            }


            try {
                documentVectorRepository.deleteByFileMd5(fileMd5);
                logger.info("English text: {}", fileMd5);
            } catch (Exception e) {
                logger.error("English text: {}", fileMd5, e);

            }


            fileUploadRepository.deleteByFileMd5(fileMd5);
            logger.info("English text: {}", fileMd5);

            logger.info("English text: {}", fileMd5);
        } catch (Exception e) {
            logger.error("English text: {}", fileMd5, e);
            throw new RuntimeException("English text: " + e.getMessage(), e);
        }
    }


    public List<FileUpload> getAccessibleFiles(String userId, String orgTags) {
        logger.info("English text: userId={}", userId);

        try {

            User user = userRepository.findByUsername(userId)
                .orElseThrow(() -> new RuntimeException("English text: " + userId));

            List<String> userEffectiveTags = orgTagCacheService.getUserEffectiveOrgTags(user.getUsername());
            logger.debug("English text: {}", userEffectiveTags);


            List<FileUpload> files;
            if (userEffectiveTags.isEmpty()) {

                files = fileUploadRepository.findByUserIdOrIsPublicTrue(userId);
                logger.debug("English textEnglish textEnglish text");
            } else {

                files = fileUploadRepository.findAccessibleFilesWithTags(userId, userEffectiveTags);
                logger.debug("English text");
            }

            logger.info("English text: userId={}, fileCount={}", userId, files.size());
            return files;
        } catch (Exception e) {
            logger.error("English text: userId={}", userId, e);
            throw new RuntimeException("English text: " + e.getMessage(), e);
        }
    }


    public List<FileUpload> getUserUploadedFiles(String userId) {
        logger.info("English text: userId={}", userId);

        try {
            List<FileUpload> files = fileUploadRepository.findByUserId(userId);
            logger.info("English text: userId={}, fileCount={}", userId, files.size());
            return files;
        } catch (Exception e) {
            logger.error("English text: userId={}", userId, e);
            throw new RuntimeException("English text: " + e.getMessage(), e);
        }
    }


    public String generateDownloadUrl(String fileMd5) {
        logger.info("English text: fileMd5={}", fileMd5);

        try {

            FileUpload fileUpload = fileUploadRepository.findByFileMd5(fileMd5)
                    .orElseThrow(() -> new RuntimeException("English text: " + fileMd5));


            String objectName = "merged/" + fileUpload.getFileName();


            String presignedUrl = minioClient.getPresignedObjectUrl(
                    GetPresignedObjectUrlArgs.builder()
                            .method(Method.GET)
                            .bucket("uploads")
                            .object(objectName)
                            .expiry(3600)
                            .build()
            );

            logger.info("English text: fileMd5={}, fileName={}, objectName={}",
                    fileMd5, fileUpload.getFileName(), objectName);
            return presignedUrl;
        } catch (Exception e) {
            logger.error("English text: fileMd5={}", fileMd5, e);
            return null;
        }
    }


    public String getFilePreviewContent(String fileMd5, String fileName) {
        logger.info("English text: fileMd5={}, fileName={}", fileMd5, fileName);

        try {

            String objectName = "merged/" + fileName;


            String fileExtension = getFileExtension(fileName).toLowerCase();
            boolean isTextFile = isTextFile(fileExtension);

            if (isTextFile) {

                try (InputStream inputStream = minioClient.getObject(
                        GetObjectArgs.builder()
                                .bucket("uploads")
                                .object(objectName)
                                .build())) {

                    BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream, "UTF-8"));
                    StringBuilder content = new StringBuilder();
                    String line;
                    int bytesRead = 0;
                    int maxBytes = 10240;

                    while ((line = reader.readLine()) != null && bytesRead < maxBytes) {
                        content.append(line).append("\n");
                        bytesRead += line.getBytes("UTF-8").length + 1;
                    }

                    String result = content.toString();
                    if (bytesRead >= maxBytes) {
                        result += "\n... (English textEnglish textEnglish text10KB)";
                    }

                    logger.info("English text: fileMd5={}, contentLength={}", fileMd5, result.length());
                    return result;
                }
            } else {

                FileUpload fileUpload = fileUploadRepository.findByFileMd5(fileMd5)
                        .orElseThrow(() -> new RuntimeException("English text: " + fileMd5));

                String fileInfo = String.format(
                    "English text: %s\n" +
                    "English text: %s\n" +
                    "English text: %s\n" +
                    "English text: %s\n\n" +
                    "English textEnglish textEnglish textEnglish text",
                    fileName,
                    formatFileSize(fileUpload.getTotalSize()),
                    fileExtension.toUpperCase(),
                    fileUpload.getCreatedAt()
                );

                logger.info("English text: fileMd5={}", fileMd5);
                return fileInfo;
            }

        } catch (Exception e) {
            logger.error("English text: fileMd5={}, fileName={}", fileMd5, fileName, e);
            return "English text: " + e.getMessage();
        }
    }


    private String getFileExtension(String fileName) {
        int lastDotIndex = fileName.lastIndexOf('.');
        if (lastDotIndex == -1) {
            return "";
        }
        return fileName.substring(lastDotIndex + 1);
    }


    private boolean isTextFile(String extension) {
        String[] textExtensions = {
            "txt", "md", "doc", "docx", "pdf", "html", "htm", "xml", "json",
            "csv", "log", "java", "js", "ts", "py", "cpp", "c", "h", "css",
            "scss", "less", "sql", "yml", "yaml", "properties", "conf", "config"
        };

        return Arrays.stream(textExtensions)
                .anyMatch(ext -> ext.equalsIgnoreCase(extension));
    }


    private String formatFileSize(Long size) {
        if (size == null) return "English text";

        if (size < 1024) {
            return size + " B";
        } else if (size < 1024 * 1024) {
            return String.format("%.1f KB", size / 1024.0);
        } else if (size < 1024 * 1024 * 1024) {
            return String.format("%.1f MB", size / (1024.0 * 1024.0));
        } else {
            return String.format("%.1f GB", size / (1024.0 * 1024.0 * 1024.0));
        }
    }
}