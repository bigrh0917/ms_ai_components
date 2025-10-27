package com.yizhaoqi.manshu.controller;

import com.yizhaoqi.manshu.service.ParseService;
import com.yizhaoqi.manshu.utils.LogUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/parse")
public class ParseController {

    @Autowired
    private ParseService parseService;

    @PostMapping
    public ResponseEntity<String> parseDocument(@RequestParam("file") MultipartFile file,
                                                @RequestParam("file_md5") String fileMd5,
                                                @RequestAttribute(value = "userId", required = false) String userId) {
        LogUtils.PerformanceMonitor monitor = LogUtils.startPerformanceMonitor("PARSE_DOCUMENT");
        try {
            LogUtils.logBusiness("PARSE_DOCUMENT", userId != null ? userId : "system",
                    "English text: fileMd5=%s, fileName=%s, fileSize=%d",
                    fileMd5, file.getOriginalFilename(), file.getSize());

            parseService.parseAndSave(fileMd5, file.getInputStream());

            LogUtils.logFileOperation(userId != null ? userId : "system", "PARSE",
                    file.getOriginalFilename(), fileMd5, "SUCCESS");
            LogUtils.logUserOperation(userId != null ? userId : "system", "PARSE_DOCUMENT",
                    fileMd5, "SUCCESS");
            monitor.end("English text");

            return ResponseEntity.ok("English text");
        } catch (Exception e) {
            LogUtils.logBusinessError("PARSE_DOCUMENT", userId != null ? userId : "system",
                    "English text: fileMd5=%s, fileName=%s", e, fileMd5, file.getOriginalFilename());
            LogUtils.logFileOperation(userId != null ? userId : "system", "PARSE",
                    file.getOriginalFilename(), fileMd5, "FAILED");
            monitor.end("English text: " + e.getMessage());

            return ResponseEntity.badRequest().body("English textEnglish text" + e.getMessage());
        }
    }
}