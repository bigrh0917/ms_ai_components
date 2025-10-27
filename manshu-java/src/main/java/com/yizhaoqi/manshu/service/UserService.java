package com.yizhaoqi.manshu.service;

import com.yizhaoqi.manshu.exception.CustomException;
import com.yizhaoqi.manshu.model.OrganizationTag;
import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.OrganizationTagRepository;
import com.yizhaoqi.manshu.repository.UserRepository;
import com.yizhaoqi.manshu.utils.PasswordUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.domain.PageImpl;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.HashMap;
import java.util.ArrayList;
import java.util.HashSet;


@Service
public class UserService {

    private static final Logger logger = LoggerFactory.getLogger(UserService.class);

    private static final String DEFAULT_ORG_TAG = "DEFAULT";
    private static final String DEFAULT_ORG_NAME = "English text";
    private static final String DEFAULT_ORG_DESCRIPTION = "English textEnglish textEnglish text";
    private static final String PRIVATE_TAG_PREFIX = "PRIVATE_";
    private static final String PRIVATE_ORG_NAME_SUFFIX = "English text";
    private static final String PRIVATE_ORG_DESCRIPTION = "English textEnglish textEnglish text";

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private OrganizationTagRepository organizationTagRepository;

    @Autowired
    private OrgTagCacheService orgTagCacheService;


    @Transactional
    public void registerUser(String username, String password) {

        if (userRepository.findByUsername(username).isPresent()) {

            throw new CustomException("Username already exists", HttpStatus.BAD_REQUEST);
        }


        ensureDefaultOrgTagExists();

        User user = new User();
        user.setUsername(username);

        user.setPassword(PasswordUtil.encode(password));

        user.setRole(User.Role.USER);


        userRepository.save(user);


        String privateTagId = PRIVATE_TAG_PREFIX + username;
        createPrivateOrgTag(privateTagId, username, user);


        user.setOrgTags(privateTagId);


        user.setPrimaryOrg(privateTagId);

        userRepository.save(user);


        orgTagCacheService.cacheUserOrgTags(username, List.of(privateTagId));
        orgTagCacheService.cacheUserPrimaryOrg(username, privateTagId);

        logger.info("User registered successfully with private organization tag: {}", username);
    }


    private void createPrivateOrgTag(String privateTagId, String username, User owner) {

        if (!organizationTagRepository.existsByTagId(privateTagId)) {
            logger.info("Creating private organization tag for user: {}", username);


            OrganizationTag privateTag = new OrganizationTag();
            privateTag.setTagId(privateTagId);
            privateTag.setName(username + PRIVATE_ORG_NAME_SUFFIX);
            privateTag.setDescription(PRIVATE_ORG_DESCRIPTION);
            privateTag.setCreatedBy(owner);

            organizationTagRepository.save(privateTag);
            logger.info("Private organization tag created successfully for user: {}", username);
        }
    }


    private void ensureDefaultOrgTagExists() {
        if (!organizationTagRepository.existsByTagId(DEFAULT_ORG_TAG)) {
            logger.info("Creating default organization tag");


            Optional<User> adminUser = userRepository.findAll().stream()
                    .filter(user -> User.Role.ADMIN.equals(user.getRole()))
                    .findFirst();

            User creator;
            if (adminUser.isPresent()) {
                creator = adminUser.get();
            } else {

                creator = createSystemAdminIfNotExists();
            }


            OrganizationTag defaultTag = new OrganizationTag();
            defaultTag.setTagId(DEFAULT_ORG_TAG);
            defaultTag.setName(DEFAULT_ORG_NAME);
            defaultTag.setDescription(DEFAULT_ORG_DESCRIPTION);
            defaultTag.setCreatedBy(creator);

            organizationTagRepository.save(defaultTag);
            logger.info("Default organization tag created successfully");
        }
    }


    private User createSystemAdminIfNotExists() {
        String systemAdminUsername = "system_admin";

        return userRepository.findByUsername(systemAdminUsername)
                .orElseGet(() -> {
                    logger.info("Creating system admin user");
                    User systemAdmin = new User();
                    systemAdmin.setUsername(systemAdminUsername);

                    String randomPassword = generateRandomPassword();
                    systemAdmin.setPassword(PasswordUtil.encode(randomPassword));
                    systemAdmin.setRole(User.Role.ADMIN);

                    logger.info("System admin created with password: {}", randomPassword);
                    return userRepository.save(systemAdmin);
                });
    }


    private String generateRandomPassword() {

        String chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 16; i++) {
            int index = (int) (Math.random() * chars.length());
            sb.append(chars.charAt(index));
        }
        return sb.toString();
    }


    public void createAdminUser(String username, String password, String creatorUsername) {

        User creator = userRepository.findByUsername(creatorUsername)
                .orElseThrow(() -> new CustomException("Creator not found", HttpStatus.NOT_FOUND));

        if (creator.getRole() != User.Role.ADMIN) {
            throw new CustomException("Only administrators can create admin accounts", HttpStatus.FORBIDDEN);
        }


        if (userRepository.findByUsername(username).isPresent()) {
            throw new CustomException("Username already exists", HttpStatus.BAD_REQUEST);
        }

        User adminUser = new User();
        adminUser.setUsername(username);
        adminUser.setPassword(PasswordUtil.encode(password));
        adminUser.setRole(User.Role.ADMIN);
        userRepository.save(adminUser);
    }


    public String authenticateUser(String username, String password) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new CustomException("Invalid username or password", HttpStatus.UNAUTHORIZED));

        if (!PasswordUtil.matches(password, user.getPassword())) {

            throw new CustomException("Invalid username or password", HttpStatus.UNAUTHORIZED);
        }

        return user.getUsername();
    }


    @Transactional
    public OrganizationTag createOrganizationTag(String tagId, String name, String description,
                                                String parentTag, String creatorUsername) {

        User creator = userRepository.findByUsername(creatorUsername)
                .orElseThrow(() -> new CustomException("Creator not found", HttpStatus.NOT_FOUND));

        if (creator.getRole() != User.Role.ADMIN) {
            throw new CustomException("Only administrators can create organization tags", HttpStatus.FORBIDDEN);
        }


        if (organizationTagRepository.existsByTagId(tagId)) {
            throw new CustomException("Tag ID already exists", HttpStatus.BAD_REQUEST);
        }


        if (parentTag != null && !parentTag.isEmpty()) {
            organizationTagRepository.findByTagId(parentTag)
                    .orElseThrow(() -> new CustomException("Parent tag not found", HttpStatus.NOT_FOUND));
        }

        OrganizationTag tag = new OrganizationTag();
        tag.setTagId(tagId);
        tag.setName(name);
        tag.setDescription(description);
        tag.setParentTag(parentTag);
        tag.setCreatedBy(creator);

        OrganizationTag savedTag = organizationTagRepository.save(tag);


        orgTagCacheService.invalidateAllEffectiveTagsCache();

        return savedTag;
    }


    @Transactional
    public void assignOrgTagsToUser(Long userId, List<String> orgTags, String adminUsername) {

        User admin = userRepository.findByUsername(adminUsername)
                .orElseThrow(() -> new CustomException("Admin not found", HttpStatus.NOT_FOUND));

        if (admin.getRole() != User.Role.ADMIN) {
            throw new CustomException("Only administrators can assign organization tags", HttpStatus.FORBIDDEN);
        }


        User user = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException("User not found", HttpStatus.NOT_FOUND));


        for (String tagId : orgTags) {
            if (!organizationTagRepository.existsByTagId(tagId)) {
                throw new CustomException("Organization tag " + tagId + " not found", HttpStatus.NOT_FOUND);
            }
        }


        Set<String> existingTags = new HashSet<>();
        if (user.getOrgTags() != null && !user.getOrgTags().isEmpty()) {
            existingTags = Arrays.stream(user.getOrgTags().split(",")).collect(Collectors.toSet());
        }


        String privateTagId = PRIVATE_TAG_PREFIX + user.getUsername();
        boolean hasPrivateTag = existingTags.contains(privateTagId);


        Set<String> finalTags = new HashSet<>(orgTags);
        if (hasPrivateTag && !finalTags.contains(privateTagId)) {
            finalTags.add(privateTagId);
        }


        String orgTagsStr = String.join(",", finalTags);
        user.setOrgTags(orgTagsStr);


        if ((user.getPrimaryOrg() == null || user.getPrimaryOrg().isEmpty()) && !finalTags.isEmpty()) {
            if (hasPrivateTag) {
                user.setPrimaryOrg(privateTagId);
            } else {
                user.setPrimaryOrg(new ArrayList<>(finalTags).get(0));
            }
        }

        userRepository.save(user);


        orgTagCacheService.deleteUserOrgTagsCache(user.getUsername());
        orgTagCacheService.cacheUserOrgTags(user.getUsername(), new ArrayList<>(finalTags));

        orgTagCacheService.deleteUserEffectiveTagsCache(user.getUsername());

        if (user.getPrimaryOrg() != null && !user.getPrimaryOrg().isEmpty()) {
            orgTagCacheService.cacheUserPrimaryOrg(user.getUsername(), user.getPrimaryOrg());
        }
    }


    public Map<String, Object> getUserOrgTags(String username) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new CustomException("User not found", HttpStatus.NOT_FOUND));


        List<String> orgTags = orgTagCacheService.getUserOrgTags(username);
        String primaryOrg = orgTagCacheService.getUserPrimaryOrg(username);


        if (orgTags == null || orgTags.isEmpty()) {
            orgTags = Arrays.asList(user.getOrgTags().split(","));

            orgTagCacheService.cacheUserOrgTags(username, orgTags);
        }

        if (primaryOrg == null || primaryOrg.isEmpty()) {
            primaryOrg = user.getPrimaryOrg();

            orgTagCacheService.cacheUserPrimaryOrg(username, primaryOrg);
        }


        List<Map<String, String>> orgTagDetails = new ArrayList<>();
        for (String tagId : orgTags) {
            OrganizationTag tag = organizationTagRepository.findByTagId(tagId)
                    .orElse(null);
            if (tag != null) {
                Map<String, String> tagInfo = new HashMap<>();
                tagInfo.put("tagId", tag.getTagId());
                tagInfo.put("name", tag.getName());
                tagInfo.put("description", tag.getDescription());
                orgTagDetails.add(tagInfo);
            }
        }

        Map<String, Object> result = new HashMap<>();
        result.put("orgTags", orgTags);
        result.put("primaryOrg", primaryOrg);
        result.put("orgTagDetails", orgTagDetails);

        return result;
    }


    public void setUserPrimaryOrg(String username, String primaryOrg) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new CustomException("User not found", HttpStatus.NOT_FOUND));


        Set<String> userTags = Arrays.stream(user.getOrgTags().split(",")).collect(Collectors.toSet());
        if (!userTags.contains(primaryOrg)) {
            throw new CustomException("Organization tag not assigned to user", HttpStatus.BAD_REQUEST);
        }

        user.setPrimaryOrg(primaryOrg);
        userRepository.save(user);


        orgTagCacheService.cacheUserPrimaryOrg(username, primaryOrg);
    }


    public String getUserPrimaryOrg(String userId) {

        User user;
        try {
            Long userIdLong = Long.parseLong(userId);
            user = userRepository.findById(userIdLong)
                .orElseThrow(() -> new CustomException("User not found with ID: " + userId, HttpStatus.NOT_FOUND));
        } catch (NumberFormatException e) {

            user = userRepository.findByUsername(userId)
                .orElseThrow(() -> new CustomException("User not found: " + userId, HttpStatus.NOT_FOUND));
        }

        String username = user.getUsername();


        String primaryOrg = orgTagCacheService.getUserPrimaryOrg(username);


        if (primaryOrg == null || primaryOrg.isEmpty()) {
            primaryOrg = user.getPrimaryOrg();


            if (primaryOrg == null || primaryOrg.isEmpty()) {
                String[] tags = user.getOrgTags().split(",");
                if (tags.length > 0) {
                    primaryOrg = tags[0];

                    user.setPrimaryOrg(primaryOrg);
                    userRepository.save(user);
                } else {

                    primaryOrg = DEFAULT_ORG_TAG;
                }
            }


            orgTagCacheService.cacheUserPrimaryOrg(username, primaryOrg);
        }

        return primaryOrg;
    }


    public List<Map<String, Object>> getOrganizationTagTree() {

        List<OrganizationTag> rootTags = organizationTagRepository.findByParentTag(null);


        return buildTagTreeRecursive(rootTags);
    }


    private List<Map<String, Object>> buildTagTreeRecursive(List<OrganizationTag> tags) {
        List<Map<String, Object>> result = new ArrayList<>();

        for (OrganizationTag tag : tags) {
            Map<String, Object> node = new HashMap<>();
            node.put("tagId", tag.getTagId());
            node.put("name", tag.getName());
            node.put("description", tag.getDescription());
            node.put("parentTag", tag.getParentTag());


            List<OrganizationTag> children = organizationTagRepository.findByParentTag(tag.getTagId());
            if (!children.isEmpty()) {
                node.put("children", buildTagTreeRecursive(children));
            }


            result.add(node);
        }

        return result;
    }


    @Transactional
    public OrganizationTag updateOrganizationTag(String tagId, String name, String description,
                                                String parentTag, String adminUsername) {

        User admin = userRepository.findByUsername(adminUsername)
                .orElseThrow(() -> new CustomException("Admin not found", HttpStatus.NOT_FOUND));

        if (admin.getRole() != User.Role.ADMIN) {
            throw new CustomException("Only administrators can update organization tags", HttpStatus.FORBIDDEN);
        }


        OrganizationTag tag = organizationTagRepository.findByTagId(tagId)
                .orElseThrow(() -> new CustomException("Organization tag not found", HttpStatus.NOT_FOUND));


        if (parentTag != null && !parentTag.isEmpty()) {

            if (tagId.equals(parentTag)) {
                throw new CustomException("A tag cannot be its own parent", HttpStatus.BAD_REQUEST);
            }


            organizationTagRepository.findByTagId(parentTag)
                    .orElseThrow(() -> new CustomException("Parent tag not found", HttpStatus.NOT_FOUND));


            if (wouldFormCycle(tagId, parentTag)) {
                throw new CustomException("Setting this parent would create a cycle in the tag hierarchy", HttpStatus.BAD_REQUEST);
            }
        }


        if (name != null && !name.isEmpty()) {
            tag.setName(name);
        }

        if (description != null) {
            tag.setDescription(description);
        }

        tag.setParentTag(parentTag);

        OrganizationTag updatedTag = organizationTagRepository.save(tag);


        orgTagCacheService.invalidateAllEffectiveTagsCache();

        return updatedTag;
    }


    private boolean wouldFormCycle(String tagId, String newParentId) {
        String currentParentId = newParentId;


        while (currentParentId != null && !currentParentId.isEmpty()) {
            if (tagId.equals(currentParentId)) {
                return true;
            }


            Optional<OrganizationTag> parentTag = organizationTagRepository.findByTagId(currentParentId);
            if (parentTag.isEmpty()) {
                break;
            }

            currentParentId = parentTag.get().getParentTag();
        }

        return false;
    }


    @Transactional
    public void deleteOrganizationTag(String tagId, String adminUsername) {

        User admin = userRepository.findByUsername(adminUsername)
                .orElseThrow(() -> new CustomException("Admin not found", HttpStatus.NOT_FOUND));

        if (admin.getRole() != User.Role.ADMIN) {
            throw new CustomException("Only administrators can delete organization tags", HttpStatus.FORBIDDEN);
        }


        OrganizationTag tag = organizationTagRepository.findByTagId(tagId)
                .orElseThrow(() -> new CustomException("Organization tag not found", HttpStatus.NOT_FOUND));


        if (DEFAULT_ORG_TAG.equals(tagId)) {
            throw new CustomException("Cannot delete the default organization tag", HttpStatus.BAD_REQUEST);
        }


        List<OrganizationTag> children = organizationTagRepository.findByParentTag(tagId);
        if (!children.isEmpty()) {
            throw new CustomException("Cannot delete a tag with child tags", HttpStatus.BAD_REQUEST);
        }


        List<User> users = userRepository.findAll();
        for (User user : users) {
            if (user.getOrgTags() != null && !user.getOrgTags().isEmpty()) {
                Set<String> userTags = new HashSet<>(Arrays.asList(user.getOrgTags().split(",")));
                if (userTags.contains(tagId)) {
                    throw new CustomException("Cannot delete a tag that is assigned to users", HttpStatus.CONFLICT);
                }


                if (tagId.equals(user.getPrimaryOrg())) {
                    throw new CustomException("Cannot delete a tag that is used as primary organization", HttpStatus.CONFLICT);
                }
            }
        }




        try {
            long fileCount = 0;
            if (fileCount > 0) {
                throw new CustomException("Cannot delete a tag that is associated with documents", HttpStatus.CONFLICT);
            }
        } catch (Exception e) {
            logger.error("Error checking file usage of tag: {}", tagId, e);
            throw new CustomException("Failed to check if tag is used by documents", HttpStatus.INTERNAL_SERVER_ERROR);
        }


        organizationTagRepository.delete(tag);


        orgTagCacheService.invalidateAllEffectiveTagsCache();

        logger.info("Organization tag deleted successfully: {}", tagId);
    }


    public Map<String, Object> getUserList(String keyword, String orgTag, Integer status, int page, int size) {

        int pageIndex = page > 0 ? page - 1 : 0;

        Pageable pageable = PageRequest.of(pageIndex, size, Sort.by("createdAt").descending());


        Page<User> userPage;

        if (orgTag != null && !orgTag.isEmpty()) {



            List<User> allUsers = userRepository.findAll();
            List<User> filteredUsers = allUsers.stream()
                    .filter(user -> {

                        if (user.getOrgTags() != null && !user.getOrgTags().isEmpty()) {
                            Set<String> userTags = new HashSet<>(Arrays.asList(user.getOrgTags().split(",")));
                            if (!userTags.contains(orgTag)) {
                                return false;
                            }
                        } else {
                            return false;
                        }


                        if (keyword != null && !keyword.isEmpty()) {
                            boolean matchesKeyword = user.getUsername().contains(keyword);
                            if (!matchesKeyword) {
                                return false;
                            }
                        }


                        if (status != null) {
                            return user.getRole() == (status == 1 ? User.Role.USER : User.Role.ADMIN);
                        }

                        return true;
                    })
                    .collect(Collectors.toList());


            int start = (int) pageable.getOffset();
            int end = Math.min((start + pageable.getPageSize()), filteredUsers.size());

            List<User> pageContent = start < end ? filteredUsers.subList(start, end) : Collections.emptyList();
            userPage = new PageImpl<>(pageContent, pageable, filteredUsers.size());
        } else {


            userPage = userRepository.findAll(pageable);


            List<User> filteredUsers = userPage.getContent().stream()
                    .filter(user -> {

                        if (keyword != null && !keyword.isEmpty()) {
                            boolean matchesKeyword = user.getUsername().contains(keyword);
                            if (!matchesKeyword) {
                                return false;
                            }
                        }


                        if (status != null) {
                            return user.getRole() == (status == 1 ? User.Role.USER : User.Role.ADMIN);
                        }

                        return true;
                    })
                    .collect(Collectors.toList());

            userPage = new PageImpl<>(filteredUsers, pageable, filteredUsers.size());
        }


        List<Map<String, Object>> userList = userPage.getContent().stream()
                .map(user -> {
                    Map<String, Object> userMap = new HashMap<>();
                    userMap.put("userId", user.getId());
                    userMap.put("username", user.getUsername());


                    List<Map<String, String>> orgTagDetails = new ArrayList<>();
                    if (user.getOrgTags() != null && !user.getOrgTags().isEmpty()) {
                        Arrays.stream(user.getOrgTags().split(","))
                                .forEach(tagId -> {
                                    OrganizationTag tag = organizationTagRepository.findByTagId(tagId)
                                            .orElse(null);
                                    if (tag != null) {
                                        Map<String, String> tagInfo = new HashMap<>();
                                        tagInfo.put("tagId", tag.getTagId());
                                        tagInfo.put("name", tag.getName());
                                        orgTagDetails.add(tagInfo);
                                    }
                                });
                    }

                    userMap.put("orgTags", orgTagDetails);
                    userMap.put("primaryOrg", user.getPrimaryOrg());
                    userMap.put("status", user.getRole() == User.Role.USER ? 1 : 0);
                    userMap.put("createdAt", user.getCreatedAt());

                    return userMap;
                })
                .collect(Collectors.toList());


        Map<String, Object> result = new HashMap<>();
        result.put("content", userList);
        result.put("totalElements", userPage.getTotalElements());
        result.put("totalPages", userPage.getTotalPages());
        result.put("size", userPage.getSize());
        result.put("number", userPage.getNumber() + 1);

        return result;
    }
}
