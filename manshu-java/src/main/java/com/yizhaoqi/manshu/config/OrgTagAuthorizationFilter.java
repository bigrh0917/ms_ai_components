package com.yizhaoqi.manshu.config;

import com.yizhaoqi.manshu.model.FileUpload;
import com.yizhaoqi.manshu.repository.FileUploadRepository;
import com.yizhaoqi.manshu.utils.JwtUtils;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Arrays;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;


@Component
public class OrgTagAuthorizationFilter extends OncePerRequestFilter {

    private static final Logger logger = LoggerFactory.getLogger(OrgTagAuthorizationFilter.class);
    private static final String DEFAULT_ORG_TAG = "DEFAULT";
    private static final String PRIVATE_TAG_PREFIX = "PRIVATE_";

    @Autowired
    private JwtUtils jwtUtils;

    @Autowired
    private FileUploadRepository fileUploadRepository;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        try {
            String path = request.getRequestURI();




            if (path.matches(".*/upload/chunk.*") ||
                path.matches(".*/upload/merge.*") ||
                path.matches(".*/documents/uploads.*") ||
                path.matches(".*/search/hybrid.*") ||
                (path.matches(".*/documents/[a-fA-F0-9]{32}.*") && "DELETE".equals(request.getMethod()))) {

                String operation = "English text";
                if (path.contains("/chunk")) {
                    operation = "English text";
                } else if (path.contains("/merge")) {
                    operation = "English text";
                } else if (path.contains("/uploads")) {
                    operation = "English text";
                } else if (path.contains("/search/hybrid")) {
                    operation = "English text";
                } else if ("DELETE".equals(request.getMethod()) && path.matches(".*/documents/[a-fA-F0-9]{32}.*")) {
                    operation = "English text";
                }

                logger.info("English text{}English text: {}", operation, path);


                String token = extractToken(request);
                if (token != null) {
                    String userId = jwtUtils.extractUserIdFromToken(token);
                    String role = jwtUtils.extractRoleFromToken(token);
                    if (userId != null) {
                        request.setAttribute("userId", userId);
                        request.setAttribute("role", role);
                        logger.debug("English text{}English textuserIdEnglish text: {}, role: {}", operation, userId, role);
                    } else {
                        logger.warn("{}English texttokenEnglish textuserId", operation);
                    }
                } else {
                    logger.warn("{}English texttoken", operation);
                }

                filterChain.doFilter(request, response);
                return;
            }

            boolean isChunkUpload = path.matches(".*/upload/chunk.*");
            logger.debug("English text: {}, English text: {}", path, isChunkUpload);


            String resourceId = extractResourceIdFromPath(request);


            if (resourceId == null) {
                logger.debug("English textIDEnglish textEnglish text");
                filterChain.doFilter(request, response);
                return;
            }


            ResourceInfo resourceInfo = getResourceInfo(resourceId);


            if (isChunkUpload && resourceInfo == null) {
                logger.debug("English text - English text(English text)English textEnglish text: {}", resourceId);
                filterChain.doFilter(request, response);
                return;
            }


            if (resourceInfo == null) {
                logger.debug("English textEnglish textEnglish text404: {}", resourceId);
                response.setStatus(HttpServletResponse.SC_NOT_FOUND);
                return;
            }

            String resourceOrgTag = resourceInfo.getOrgTag();


            if (resourceInfo.isPublic() ||
                resourceOrgTag == null ||
                resourceOrgTag.isEmpty() ||
                DEFAULT_ORG_TAG.equals(resourceOrgTag)) {
                logger.debug("English textEnglish textEnglish text");
                filterChain.doFilter(request, response);
                return;
            }


            String token = extractToken(request);
            if (token == null) {
                logger.debug("English textTokenEnglish textEnglish text401");
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                return;
            }


            String username = jwtUtils.extractUsernameFromToken(token);
            String role = jwtUtils.extractRoleFromToken(token);


            if (username != null && username.equals(resourceInfo.getOwner())) {
                logger.debug("English textEnglish textEnglish text");
                filterChain.doFilter(request, response);
                return;
            }


            if ("ADMIN".equals(role)) {
                logger.debug("English textEnglish textEnglish text");
                filterChain.doFilter(request, response);
                return;
            }


            if (resourceOrgTag.startsWith(PRIVATE_TAG_PREFIX)) {

                logger.debug("English textEnglish textEnglish textEnglish textEnglish text");
                response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                return;
            }


            String userOrgTags = jwtUtils.extractOrgTagsFromToken(token);
            if (userOrgTags == null || userOrgTags.isEmpty()) {
                logger.debug("English textEnglish textEnglish text");
                response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                return;
            }


            if (isUserAuthorized(userOrgTags, resourceOrgTag)) {
                logger.debug("English textEnglish textEnglish text");
                filterChain.doFilter(request, response);
            } else {
                logger.debug("English textEnglish textEnglish text");
                response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            }
        } catch (Exception e) {
            logger.error("English text: {}", e.getMessage(), e);
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }


    private String extractResourceIdFromPath(HttpServletRequest request) {
        String path = request.getRequestURI();
        logger.debug("English textIDEnglish textEnglish text: {}", path);



        if (path.matches(".*/files/[^/]+.*")) {
            String fileId = path.replaceAll(".*/files/([^/]+).*", "$1");
            logger.debug("English textEnglish textEnglish textID: {}", fileId);
            return fileId;
        }


        if (path.matches(".*/documents/[a-fA-F0-9]{32}.*")) {
            String fileMd5 = path.replaceAll(".*/documents/([a-fA-F0-9]{32}).*", "$1");
            logger.debug("English textEnglish textEnglish textMD5: {}", fileMd5);
            return fileMd5;
        }


        if (path.matches(".*/documents/\\d+.*")) {
            String docId = path.replaceAll(".*/documents/(\\d+).*", "$1");
            logger.debug("English textEnglish textEnglish textID: {}", docId);
            return docId;
        }


        if (path.matches(".*/upload/chunk.*")) {
            String fileMd5 = request.getHeader("X-File-MD5");
            logger.debug("English textEnglish textEnglish textMD5: {}", fileMd5);
            return fileMd5;
        }


        if (path.matches(".*/knowledge/[^/]+.*")) {
            String knowledgeId = path.replaceAll(".*/knowledge/([^/]+).*", "$1");
            logger.debug("English textEnglish textEnglish textID: {}", knowledgeId);
            return knowledgeId;
        }

        logger.debug("English textEnglish textEnglish textnull");
        return null;
    }


    private ResourceInfo getResourceInfo(String resourceId) {
        if (resourceId == null) {
            logger.debug("English textIDEnglish textEnglish textEnglish text");
            return null;
        }

        logger.debug("English textEnglish textEnglish textID: {}", resourceId);


        Optional<FileUpload> fileUpload = fileUploadRepository.findByFileMd5(resourceId);
        if (fileUpload.isPresent()) {
            FileUpload file = fileUpload.get();
            ResourceInfo info = new ResourceInfo(
                file.getUserId(),
                file.getOrgTag(),
                file.isPublic()
            );
            logger.debug("English text => English textID: {}, English text: {}, English text: {}, English text: {}",
                        resourceId, info.getOwner(), info.getOrgTag(), info.isPublic());
            return info;
        } else {
            logger.debug("English text => English textID: {}", resourceId);
        }




        logger.debug("English text => English textID: {}", resourceId);
        return null;
    }


    private boolean isPublicResource(String resourceId) {
        ResourceInfo resourceInfo = getResourceInfo(resourceId);
        return resourceInfo != null && resourceInfo.isPublic();
    }


    private String extractToken(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }


    private boolean isUserAuthorized(String userOrgTags, String resourceOrgTag) {

        Set<String> userTags = Arrays.stream(userOrgTags.split(","))
                .collect(Collectors.toSet());


        return userTags.contains(resourceOrgTag);
    }


    private static class ResourceInfo {
        private final String owner;
        private final String orgTag;
        private final boolean isPublic;

        public ResourceInfo(String owner, String orgTag, boolean isPublic) {
            this.owner = owner;
            this.orgTag = orgTag;
            this.isPublic = isPublic;
        }

        public String getOwner() {
            return owner;
        }

        public String getOrgTag() {
            return orgTag;
        }

        public boolean isPublic() {
            return isPublic;
        }
    }
}