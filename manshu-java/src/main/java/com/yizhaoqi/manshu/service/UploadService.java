package com.yizhaoqi.manshu.service;

import com.yizhaoqi.manshu.model.ChunkInfo;
import com.yizhaoqi.manshu.model.FileUpload;
import com.yizhaoqi.manshu.repository.ChunkInfoRepository;
import com.yizhaoqi.manshu.repository.FileUploadRepository;
import io.minio.*;
import io.minio.http.Method;
import org.apache.commons.codec.digest.DigestUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class UploadService {

    private static final Logger logger = LoggerFactory.getLogger(UploadService.class);


    @Autowired
    private RedisTemplate<String, Object> redisTemplate;


    @Autowired
    private MinioClient minioClient;


    @Autowired
    private FileUploadRepository fileUploadRepository;


    @Autowired
    private ChunkInfoRepository chunkInfoRepository;

    @Autowired
    private String minioPublicUrl;


    public void uploadChunk(String fileMd5, int chunkIndex, long totalSize, String fileName,
                           MultipartFile file, String orgTag, boolean isPublic, String userId) throws IOException {

        String fileType = getFileType(fileName);
        String contentType = file.getContentType();

        logger.info("[uploadChunk] English text => fileMd5: {}, chunkIndex: {}, totalSize: {}, fileName: {}, fileType: {}, contentType: {}, fileSize: {}, orgTag: {}, isPublic: {}, userId: {}",
                   fileMd5, chunkIndex, totalSize, fileName, fileType, contentType, file.getSize(), orgTag, isPublic, userId);

        try {

            boolean fileExists = fileUploadRepository.findByFileMd5AndUserId(fileMd5, userId).isPresent();
            logger.debug("English text => fileMd5: {}, fileName: {}, fileType: {}, exists: {}", fileMd5, fileName, fileType, fileExists);

            if (!fileExists) {
                logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}, totalSize: {}, userId: {}, orgTag: {}, isPublic: {}",
                          fileMd5, fileName, fileType, totalSize, userId, orgTag, isPublic);

                FileUpload fileUpload = new FileUpload();
                fileUpload.setFileMd5(fileMd5);
                fileUpload.setFileName(fileName);
                fileUpload.setTotalSize(totalSize);
                fileUpload.setStatus(0);
                fileUpload.setUserId(userId);
                fileUpload.setOrgTag(orgTag);
                fileUpload.setPublic(isPublic);
                try {
                    fileUploadRepository.save(fileUpload);
                    logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}", fileMd5, fileName, fileType);
                } catch (Exception e) {
                    logger.error("English text => fileMd5: {}, fileName: {}, fileType: {}, English text: {}", fileMd5, fileName, fileType, e.getMessage(), e);
                    throw new RuntimeException("English text: " + e.getMessage(), e);
                }
            }


            boolean chunkUploaded = isChunkUploaded(fileMd5, chunkIndex, userId);
            logger.debug("English text => fileMd5: {}, fileName: {}, chunkIndex: {}, isUploaded: {}",
                      fileMd5, fileName, chunkIndex, chunkUploaded);


            boolean chunkInfoExists = false;
            try {
                List<ChunkInfo> chunkInfos = chunkInfoRepository.findByFileMd5OrderByChunkIndexAsc(fileMd5);
                chunkInfoExists = chunkInfos.stream()
                    .anyMatch(chunk -> chunk.getChunkIndex() == chunkIndex);
                logger.debug("English text => fileMd5: {}, fileName: {}, chunkIndex: {}, exists: {}",
                          fileMd5, fileName, chunkIndex, chunkInfoExists);
            } catch (Exception e) {
                logger.warn("English text => fileMd5: {}, fileName: {}, chunkIndex: {}, English text: {}",
                          fileMd5, fileName, chunkIndex, e.getMessage(), e);

                chunkInfoExists = false;
            }

            String chunkMd5 = null;
            String storagePath = null;

            if (chunkUploaded) {
                logger.warn("English textRedisEnglish text => fileMd5: {}, fileName: {}, fileType: {}, chunkIndex: {}", fileMd5, fileName, fileType, chunkIndex);


                if (!chunkInfoExists) {
                    logger.info("English textEnglish textEnglish text => fileMd5: {}, fileName: {}, chunkIndex: {}", fileMd5, fileName, chunkIndex);


                    byte[] fileBytes = file.getBytes();
                    chunkMd5 = DigestUtils.md5Hex(fileBytes);


                    storagePath = "chunks/" + fileMd5 + "/" + chunkIndex;


                    try {
                        StatObjectResponse stat = minioClient.statObject(
                            StatObjectArgs.builder()
                                .bucket("uploads")
                                .object(storagePath)
                                .build()
                        );
                        logger.info("MinIOEnglish text => fileMd5: {}, fileName: {}, chunkIndex: {}, path: {}, size: {}",
                                  fileMd5, fileName, chunkIndex, storagePath, stat.size());
                    } catch (Exception e) {
                        logger.warn("MinIOEnglish textEnglish textEnglish text => fileMd5: {}, fileName: {}, chunkIndex: {}, English text: {}",
                                  fileMd5, fileName, chunkIndex, e.getMessage());

                        chunkUploaded = false;
                    }
                } else {
                    logger.info("English textEnglish textEnglish text => fileMd5: {}, fileName: {}, chunkIndex: {}", fileMd5, fileName, chunkIndex);
                    return;
                }
            }


            if (!chunkUploaded) {

                logger.debug("English textMD5 => fileMd5: {}, fileName: {}, chunkIndex: {}", fileMd5, fileName, chunkIndex);
                byte[] fileBytes = file.getBytes();
                chunkMd5 = DigestUtils.md5Hex(fileBytes);
                logger.debug("English textMD5English text => fileMd5: {}, fileName: {}, chunkIndex: {}, chunkMd5: {}",
                           fileMd5, fileName, chunkIndex, chunkMd5);


                storagePath = "chunks/" + fileMd5 + "/" + chunkIndex;
                logger.debug("English text => fileName: {}, path: {}", fileName, storagePath);

                try {

                    logger.info("English textMinIO => fileMd5: {}, fileName: {}, fileType: {}, chunkIndex: {}, bucket: uploads, path: {}, size: {}, contentType: {}",
                              fileMd5, fileName, fileType, chunkIndex, storagePath, file.getSize(), contentType);

                    PutObjectArgs putObjectArgs = PutObjectArgs.builder()
                            .bucket("uploads")
                            .object(storagePath)
                            .stream(file.getInputStream(), file.getSize(), -1)
                            .contentType(file.getContentType())
                            .build();

                    minioClient.putObject(putObjectArgs);
                    logger.info("English textMinIOEnglish text => fileMd5: {}, fileName: {}, fileType: {}, chunkIndex: {}", fileMd5, fileName, fileType, chunkIndex);
                } catch (Exception e) {
                    logger.error("English textMinIOEnglish text => fileMd5: {}, fileName: {}, fileType: {}, chunkIndex: {}, English text: {}, English text: {}",
                              fileMd5, fileName, fileType, chunkIndex, e.getClass().getName(), e.getMessage(), e);


                    if (e instanceof io.minio.errors.ErrorResponseException) {
                        io.minio.errors.ErrorResponseException ere = (io.minio.errors.ErrorResponseException) e;
                        logger.error("MinIOEnglish text => fileName: {}, code: {}, message: {}, resource: {}, requestId: {}",
                                 fileName, ere.errorResponse().code(), ere.errorResponse().message(),
                                 ere.errorResponse().resource(), ere.errorResponse().requestId());
                    }

                    throw new RuntimeException("English textMinIOEnglish text: " + e.getMessage(), e);
                }


                try {
                    logger.debug("English text => fileMd5: {}, fileName: {}, chunkIndex: {}", fileMd5, fileName, chunkIndex);
                    markChunkUploaded(fileMd5, chunkIndex, userId);
                    logger.debug("English text => fileMd5: {}, fileName: {}, chunkIndex: {}", fileMd5, fileName, chunkIndex);
                } catch (Exception e) {
                    logger.error("English text => fileMd5: {}, fileName: {}, chunkIndex: {}, English text: {}",
                              fileMd5, fileName, chunkIndex, e.getMessage(), e);

                }
            }


            if (!chunkInfoExists && chunkMd5 != null && storagePath != null) {
                try {
                    logger.debug("English text => fileMd5: {}, fileName: {}, chunkIndex: {}, chunkMd5: {}, storagePath: {}",
                              fileMd5, fileName, chunkIndex, chunkMd5, storagePath);
                    saveChunkInfo(fileMd5, chunkIndex, chunkMd5, storagePath);
                    logger.info("English text => fileMd5: {}, fileName: {}, chunkIndex: {}", fileMd5, fileName, chunkIndex);
                } catch (Exception e) {
                    logger.error("English text => fileMd5: {}, fileName: {}, chunkIndex: {}, English text: {}",
                              fileMd5, fileName, chunkIndex, e.getMessage(), e);
                    throw new RuntimeException("English text: " + e.getMessage(), e);
                }
            }

            logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}, chunkIndex: {}", fileMd5, fileName, fileType, chunkIndex);
        } catch (Exception e) {
            logger.error("English text => fileMd5: {}, fileName: {}, fileType: {}, chunkIndex: {}, English text: {}, English text: {}",
                       fileMd5, fileName, fileType, chunkIndex, e.getClass().getName(), e.getMessage(), e);
            throw e;
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


    public boolean isChunkUploaded(String fileMd5, int chunkIndex, String userId) {
        logger.debug("English text => fileMd5: {}, chunkIndex: {}, userId: {}", fileMd5, chunkIndex, userId);
        try {
            if (chunkIndex < 0) {
                logger.error("English text => fileMd5: {}, chunkIndex: {}", fileMd5, chunkIndex);
                throw new IllegalArgumentException("chunkIndex must be non-negative");
            }
            String redisKey = "upload:" + userId + ":" + fileMd5;
            boolean isUploaded = redisTemplate.opsForValue().getBit(redisKey, chunkIndex);
            logger.debug("English text => fileMd5: {}, chunkIndex: {}, userId: {}, isUploaded: {}",
                      fileMd5, chunkIndex, userId, isUploaded);
            return isUploaded;
        } catch (Exception e) {
            logger.error("English text => fileMd5: {}, chunkIndex: {}, userId: {}, English text: {}",
                      fileMd5, chunkIndex, userId, e.getMessage(), e);
            return false;
        }
    }


    public void markChunkUploaded(String fileMd5, int chunkIndex, String userId) {
        logger.debug("English text => fileMd5: {}, chunkIndex: {}, userId: {}", fileMd5, chunkIndex, userId);
        try {
            if (chunkIndex < 0) {
                logger.error("English text => fileMd5: {}, chunkIndex: {}", fileMd5, chunkIndex);
                throw new IllegalArgumentException("chunkIndex must be non-negative");
            }
            String redisKey = "upload:" + userId + ":" + fileMd5;
            redisTemplate.opsForValue().setBit(redisKey, chunkIndex, true);
            logger.debug("English text => fileMd5: {}, chunkIndex: {}, userId: {}", fileMd5, chunkIndex, userId);
        } catch (Exception e) {
            logger.error("English text => fileMd5: {}, chunkIndex: {}, userId: {}, English text: {}",
                      fileMd5, chunkIndex, userId, e.getMessage(), e);
            throw new RuntimeException("Failed to mark chunk as uploaded", e);
        }
    }


    public void deleteFileMark(String fileMd5, String userId) {
        logger.debug("English text => fileMd5: {}, userId: {}", fileMd5, userId);
        try {
            String redisKey = "upload:" + userId + ":" + fileMd5;
            redisTemplate.delete(redisKey);
            logger.info("English text => fileMd5: {}, userId: {}", fileMd5, userId);
        } catch (Exception e) {
            logger.error("English text => fileMd5: {}, userId: {}, English text: {}", fileMd5, userId, e.getMessage(), e);
            throw new RuntimeException("Failed to delete file mark", e);
        }
    }



    public List<Integer> getUploadedChunks(String fileMd5, String userId) {
        logger.info("English text => fileMd5: {}, userId: {}", fileMd5, userId);
        List<Integer> uploadedChunks = new ArrayList<>();
        try {
            int totalChunks = getTotalChunks(fileMd5, userId);
            logger.debug("English text => fileMd5: {}, userId: {}, totalChunks: {}", fileMd5, userId, totalChunks);

            if (totalChunks == 0) {
                logger.warn("English text0 => fileMd5: {}, userId: {}", fileMd5, userId);
                return uploadedChunks;
            }


            String redisKey = "upload:" + userId + ":" + fileMd5;
            byte[] bitmapData = redisTemplate.execute((RedisCallback<byte[]>) connection -> {
                return connection.get(redisKey.getBytes());
            });

            if (bitmapData == null) {
                logger.info("RedisEnglish text => fileMd5: {}, userId: {}", fileMd5, userId);
                return uploadedChunks;
            }


            for (int chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
                if (isBitSet(bitmapData, chunkIndex)) {
                    uploadedChunks.add(chunkIndex);
                }
            }

            logger.info("English text => fileMd5: {}, userId: {}, English text: {}, English text: {}, English text: English text",
                      fileMd5, userId, uploadedChunks.size(), totalChunks);
            return uploadedChunks;
        } catch (Exception e) {
            logger.error("English text => fileMd5: {}, userId: {}, English text: {}", fileMd5, userId, e.getMessage(), e);
            throw new RuntimeException("Failed to get uploaded chunks", e);
        }
    }


    private boolean isBitSet(byte[] bitmapData, int bitIndex) {
        try {
            int byteIndex = bitIndex / 8;
            int bitPosition = 7 - (bitIndex % 8);

            if (byteIndex >= bitmapData.length) {
                return false;
            }

            return (bitmapData[byteIndex] & (1 << bitPosition)) != 0;
        } catch (Exception e) {
            logger.error("English textbitmapEnglish text => bitIndex: {}, English text: {}", bitIndex, e.getMessage(), e);
            return false;
        }
    }


    public int getTotalChunks(String fileMd5, String userId) {
        logger.info("English text => fileMd5: {}, userId: {}", fileMd5, userId);
        try {
            Optional<FileUpload> fileUpload = fileUploadRepository.findByFileMd5AndUserId(fileMd5, userId);

            if (fileUpload.isEmpty()) {
                logger.warn("English textEnglish textEnglish text => fileMd5: {}, userId: {}", fileMd5, userId);
                return 0;
            }

            long totalSize = fileUpload.get().getTotalSize();

            int chunkSize = 5 * 1024 * 1024;
            int totalChunks = (int) Math.ceil((double) totalSize / chunkSize);

            logger.info("English text => fileMd5: {}, userId: {}, totalSize: {}, chunkSize: {}, totalChunks: {}",
                      fileMd5, userId, totalSize, chunkSize, totalChunks);
            return totalChunks;
        } catch (Exception e) {
            logger.error("English text => fileMd5: {}, userId: {}, English text: {}", fileMd5, userId, e.getMessage(), e);
            throw new RuntimeException("Failed to calculate total chunks", e);
        }
    }


    private void saveChunkInfo(String fileMd5, int chunkIndex, String chunkMd5, String storagePath) {
        logger.debug("English text => fileMd5: {}, chunkIndex: {}, chunkMd5: {}, storagePath: {}",
                   fileMd5, chunkIndex, chunkMd5, storagePath);
        try {
            ChunkInfo chunkInfo = new ChunkInfo();
            chunkInfo.setFileMd5(fileMd5);
            chunkInfo.setChunkIndex(chunkIndex);
            chunkInfo.setChunkMd5(chunkMd5);
            chunkInfo.setStoragePath(storagePath);

            chunkInfoRepository.save(chunkInfo);
            logger.debug("English text => fileMd5: {}, chunkIndex: {}", fileMd5, chunkIndex);
        } catch (Exception e) {
            logger.error("English text => fileMd5: {}, chunkIndex: {}, English text: {}",
                      fileMd5, chunkIndex, e.getMessage(), e);
            throw new RuntimeException("Failed to save chunk info", e);
        }
    }


    public String mergeChunks(String fileMd5, String fileName, String userId) {
        String fileType = getFileType(fileName);
        logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}, userId: {}", fileMd5, fileName, fileType, userId);
        try {

            logger.debug("English text => fileMd5: {}, fileName: {}", fileMd5, fileName);
            List<ChunkInfo> chunks = chunkInfoRepository.findByFileMd5OrderByChunkIndexAsc(fileMd5);
            logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}, English text: {}", fileMd5, fileName, fileType, chunks.size());


            int expectedChunks = getTotalChunks(fileMd5, userId);
            if (chunks.size() != expectedChunks) {
                logger.error("English text => fileMd5: {}, fileName: {}, fileType: {}, English text: {}, English text: {}",
                          fileMd5, fileName, fileType, expectedChunks, chunks.size());
                throw new RuntimeException(String.format(
                    "English textEnglish textEnglish text: %d, English text: %d", expectedChunks, chunks.size()));
            }

            List<String> partPaths = chunks.stream()
                    .map(ChunkInfo::getStoragePath)
                    .collect(Collectors.toList());
            logger.debug("English text => fileMd5: {}, fileName: {}, English text: {}", fileMd5, fileName, partPaths.size());


            logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}", fileMd5, fileName, fileType);
            for (int i = 0; i < partPaths.size(); i++) {
                String path = partPaths.get(i);
                try {
                    StatObjectResponse stat = minioClient.statObject(
                        StatObjectArgs.builder()
                            .bucket("uploads")
                            .object(path)
                            .build()
                    );
                    logger.debug("English text => fileName: {}, index: {}, path: {}, size: {}", fileName, i, path, stat.size());
                } catch (Exception e) {
                    logger.error("English text => fileName: {}, index: {}, path: {}, English text: {}",
                              fileName, i, path, e.getMessage(), e);
                    throw new RuntimeException("English text " + i + " English text: " + e.getMessage(), e);
                }
            }
            logger.info("English textEnglish textEnglish text => fileMd5: {}, fileName: {}, fileType: {}", fileMd5, fileName, fileType);

            String mergedPath = "merged/" + fileName;
            logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}, English text: {}", fileMd5, fileName, fileType, mergedPath);

            try {

                List<ComposeSource> sources = partPaths.stream()
                        .map(path -> ComposeSource.builder().bucket("uploads").object(path).build())
                        .collect(Collectors.toList());

                logger.debug("English text => fileMd5: {}, fileName: {}, targetPath: {}, sourcePaths: {}",
                          fileMd5, fileName, mergedPath, partPaths);

                minioClient.composeObject(
                        ComposeObjectArgs.builder()
                                .bucket("uploads")
                                .object(mergedPath)
                                .sources(sources)
                                .build()
                );
                logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}, mergedPath: {}", fileMd5, fileName, fileType, mergedPath);


                StatObjectResponse stat = minioClient.statObject(
                    StatObjectArgs.builder()
                        .bucket("uploads")
                        .object(mergedPath)
                        .build()
                );
                logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}, path: {}, size: {}", fileMd5, fileName, fileType, mergedPath, stat.size());


                logger.info("English text => fileMd5: {}, fileName: {}, English text: {}", fileMd5, fileName, partPaths.size());
                for (String path : partPaths) {
                    try {
                        minioClient.removeObject(
                                RemoveObjectArgs.builder()
                                        .bucket("uploads")
                                        .object(path)
                                        .build()
                        );
                        logger.debug("English text => fileName: {}, path: {}", fileName, path);
                    } catch (Exception e) {

                        logger.warn("English textEnglish textEnglish text => fileName: {}, path: {}, English text: {}", fileName, path, e.getMessage());
                    }
                }
                logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}", fileMd5, fileName, fileType);


                logger.info("English textRedisEnglish text => fileMd5: {}, fileName: {}, userId: {}", fileMd5, fileName, userId);
                deleteFileMark(fileMd5, userId);
                logger.info("English text => fileMd5: {}, fileName: {}, userId: {}", fileMd5, fileName, userId);


                logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}, userId: {}", fileMd5, fileName, fileType, userId);
                FileUpload fileUpload = fileUploadRepository.findByFileMd5AndUserId(fileMd5, userId)
                        .orElseThrow(() -> {
                            logger.error("English textEnglish textEnglish text => fileMd5: {}, fileName: {}", fileMd5, fileName);
                            return new RuntimeException("English text: " + fileMd5);
                        });
                fileUpload.setStatus(1);
                fileUpload.setMergedAt(LocalDateTime.now());
                fileUploadRepository.save(fileUpload);
                logger.info("English text => fileMd5: {}, fileName: {}, fileType: {}", fileMd5, fileName, fileType);


                logger.info("English textURL => fileMd5: {}, fileName: {}, path: {}", fileMd5, fileName, mergedPath);
                String presignedUrl = minioClient.getPresignedObjectUrl(
                        GetPresignedObjectUrlArgs.builder()
                                .method(Method.GET)
                                .bucket("uploads")
                                .object(mergedPath)
                                .expiry(1, TimeUnit.HOURS)
                                .build()
                );
                logger.info("English textURLEnglish text => fileMd5: {}, fileName: {}, fileType: {}, URL: {}", fileMd5, fileName, fileType, presignedUrl);

                return presignedUrl;
            } catch (Exception e) {
                logger.error("English text => fileMd5: {}, fileName: {}, fileType: {}, English text: {}, English text: {}",
                          fileMd5, fileName, fileType, e.getClass().getName(), e.getMessage(), e);
                throw new RuntimeException("English text: " + e.getMessage(), e);
            }
        } catch (Exception e) {
            logger.error("English text => fileMd5: {}, fileName: {}, fileType: {}, English text: {}, English text: {}",
                      fileMd5, fileName, fileType, e.getClass().getName(), e.getMessage(), e);
            throw new RuntimeException("English text: " + e.getMessage(), e);
        }
    }
}