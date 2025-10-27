package com.yizhaoqi.manshu.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;


@Service
public class FileTypeValidationService {

    private static final Logger logger = LoggerFactory.getLogger(FileTypeValidationService.class);


    private static final Set<String> SUPPORTED_DOCUMENT_EXTENSIONS = new HashSet<>(Arrays.asList(

            "pdf",
            "doc", "docx",
            "xls", "xlsx",
            "ppt", "pptx",
            "txt",
            "rtf",
            "md",


            "odt",
            "ods",
            "odp",


            "html", "htm",
            "xml",
            "json",
            "csv",


            "epub",


            "pages",
            "numbers",
            "keynote"
    ));


    private static final Set<String> UNSUPPORTED_EXTENSIONS = new HashSet<>(Arrays.asList(

            "jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "tiff", "ico", "psd",


            "mp3", "wav", "flac", "aac", "ogg", "wma", "m4a",


            "mp4", "avi", "mov", "wmv", "flv", "mkv", "webm", "m4v", "3gp",


            "zip", "rar", "7z", "tar", "gz", "bz2", "xz",


            "exe", "msi", "dmg", "pkg", "deb", "rpm",


            "ttf", "otf", "woff", "woff2", "eot",


            "dwg", "dxf", "step", "iges",


            "db", "sqlite", "mdb", "accdb",


            "bin", "dat", "iso", "img"
    ));


    public FileTypeValidationResult validateFileType(String fileName) {
        logger.debug("English text: fileName={}", fileName);

        if (fileName == null || fileName.trim().isEmpty()) {
            logger.warn("English textnull");
            return new FileTypeValidationResult(false, "English text", "unknown", null);
        }


        String extension = extractFileExtension(fileName);
        if (extension == null) {
            logger.warn("English text: fileName={}", fileName);
            return new FileTypeValidationResult(false, "English text", "unknown", null);
        }

        String fileType = getFileTypeDescription(extension);
        logger.debug("English text: fileName={}, extension={}, fileType={}", fileName, extension, fileType);


        if (SUPPORTED_DOCUMENT_EXTENSIONS.contains(extension)) {
            logger.info("English text: fileName={}, extension={}, fileType={}", fileName, extension, fileType);
            return new FileTypeValidationResult(true, "English text", fileType, extension);
        }


        if (UNSUPPORTED_EXTENSIONS.contains(extension)) {
            String message = String.format("English textEnglish text%sEnglish textEnglish text", fileType);
            logger.warn("English text: fileName={}, extension={}, fileType={}, reason=unsupported_type",
                      fileName, extension, fileType);
            return new FileTypeValidationResult(false, message, fileType, extension);
        }


        String message = String.format("English textEnglish text%sEnglish textEnglish textEnglish textEnglish textPDFEnglish textWordEnglish textExcelEnglish textPowerPointEnglish textEnglish textEnglish text", fileType);
        logger.warn("English text: fileName={}, extension={}, fileType={}, reason=unknown_type",
                  fileName, extension, fileType);
        return new FileTypeValidationResult(false, message, fileType, extension);
    }


    private String extractFileExtension(String fileName) {
        if (fileName == null || fileName.trim().isEmpty()) {
            return null;
        }

        int lastDotIndex = fileName.lastIndexOf('.');
        if (lastDotIndex == -1 || lastDotIndex == fileName.length() - 1) {
            return null;
        }

        return fileName.substring(lastDotIndex + 1).toLowerCase();
    }


    private String getFileTypeDescription(String extension) {
        if (extension == null) {
            return "unknown";
        }


        switch (extension.toLowerCase()) {
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
            case "rtf":
                return "English text";
            case "md":
                return "MarkdownEnglish text";
            case "odt":
                return "OpenDocumentEnglish text";
            case "ods":
                return "OpenDocumentEnglish text";
            case "odp":
                return "OpenDocumentEnglish text";
            case "html":
            case "htm":
                return "HTMLEnglish text";
            case "xml":
                return "XMLEnglish text";
            case "json":
                return "JSONEnglish text";
            case "csv":
                return "CSVEnglish text";
            case "epub":
                return "EPUBEnglish text";
            case "pages":
                return "Apple PagesEnglish text";
            case "numbers":
                return "Apple NumbersEnglish text";
            case "keynote":
                return "Apple KeynoteEnglish text";
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
            case "mp3":
                return "MP3English text";
            case "wav":
                return "WAVEnglish text";
            case "zip":
                return "ZIPEnglish text";
            case "rar":
                return "RAREnglish text";
            case "7z":
                return "7ZEnglish text";
            default:
                return extension.toUpperCase() + "English text";
        }
    }


    public Set<String> getSupportedFileTypes() {
        Set<String> supportedTypes = new HashSet<>();
        for (String extension : SUPPORTED_DOCUMENT_EXTENSIONS) {
            supportedTypes.add(getFileTypeDescription(extension));
        }
        return supportedTypes;
    }


    public Set<String> getSupportedExtensions() {
        return new HashSet<>(SUPPORTED_DOCUMENT_EXTENSIONS);
    }


    public static class FileTypeValidationResult {
        private final boolean valid;
        private final String message;
        private final String fileType;
        private final String extension;

        public FileTypeValidationResult(boolean valid, String message, String fileType, String extension) {
            this.valid = valid;
            this.message = message;
            this.fileType = fileType;
            this.extension = extension;
        }

        public boolean isValid() {
            return valid;
        }

        public String getMessage() {
            return message;
        }

        public String getFileType() {
            return fileType;
        }

        public String getExtension() {
            return extension;
        }

        @Override
        public String toString() {
            return String.format("FileTypeValidationResult{valid=%s, message='%s', fileType='%s', extension='%s'}",
                               valid, message, fileType, extension);
        }
    }
}