package com.yizhaoqi.manshu.consumer;

import com.yizhaoqi.manshu.config.KafkaConfig;
import com.yizhaoqi.manshu.model.FileProcessingTask;
import com.yizhaoqi.manshu.service.ParseService;
import com.yizhaoqi.manshu.service.VectorizationService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;

@Service
@Slf4j
public class FileProcessingConsumer {

    private final ParseService parseService;
    private final VectorizationService vectorizationService;
    @Autowired
    private KafkaConfig kafkaConfig;


    public FileProcessingConsumer(ParseService parseService, VectorizationService vectorizationService) {
        this.parseService = parseService;
        this.vectorizationService = vectorizationService;
    }

    @KafkaListener(topics = "#{kafkaConfig.getFileProcessingTopic()}", groupId = "#{kafkaConfig.getFileProcessingGroupId()}")
    public void processTask(FileProcessingTask task) {
        log.info("Received task: {}", task);
        log.info("File permission info: userId={}, orgTag={}, isPublic={}",
                task.getUserId(), task.getOrgTag(), task.isPublic());

        InputStream fileStream = null;
        try {

            fileStream = downloadFileFromStorage(task.getFilePath());
            if (fileStream == null) {
                throw new IOException("Input stream is null");
            }

            if (!fileStream.markSupported()) {
                fileStream = new BufferedInputStream(fileStream);
            }

            parseService.parseAndSave(task.getFileMd5(), fileStream,
                    task.getUserId(), task.getOrgTag(), task.isPublic());
            log.info("File parsed successfully, fileMd5: {}", task.getFileMd5());

            vectorizationService.vectorize(task.getFileMd5(),
                    task.getUserId(), task.getOrgTag(), task.isPublic());
            log.info("Vectorization completed, fileMd5: {}", task.getFileMd5());
        } catch (Exception e) {
            log.error("Error processing task: {}", task, e);
            throw new RuntimeException("Error processing task", e);
        } finally {
            if (fileStream != null) {
                try {
                    fileStream.close();
                } catch (IOException e) {
                    log.error("Error closing file stream", e);
                }
            }
        }
    }


    private InputStream downloadFileFromStorage(String filePath) throws IOException {
        log.info("Downloading file from storage: {}", filePath);

        try {
            File file = new File(filePath);
            if (file.exists()) {
                log.info("Detected file system path: {}", filePath);
                return new FileInputStream(file);
            }

            if (filePath.startsWith("http://") || filePath.startsWith("https://")) {
                log.info("Detected remote URL: {}", filePath);
                URL url = new URL(filePath);
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(30000);
                connection.setReadTimeout(180000);

                connection.setRequestProperty("User-Agent", "Manshu-FileProcessor/1.0");

                int responseCode = connection.getResponseCode();
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    log.info("Successfully connected to URL, starting download...");
                    return connection.getInputStream();
                } else if (responseCode == HttpURLConnection.HTTP_FORBIDDEN) {
                    log.error("Access forbidden - possible expired presigned URL");
                    throw new IOException("Access forbidden - the presigned URL may have expired");
                } else {
                    log.error("Failed to download file, HTTP response code: {} for URL: {}", responseCode, filePath);
                    throw new IOException(String.format("Failed to download file, HTTP response code: %d", responseCode));
                }
            }

            throw new IllegalArgumentException("Unsupported file path format: " + filePath);
        } catch (Exception e) {
            log.error("Error downloading file from storage: {}", filePath, e);
            return null;
        }
    }
}