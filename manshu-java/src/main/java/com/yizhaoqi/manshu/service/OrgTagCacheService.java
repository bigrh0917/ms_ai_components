package com.yizhaoqi.manshu.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import com.yizhaoqi.manshu.model.OrganizationTag;
import com.yizhaoqi.manshu.repository.OrganizationTagRepository;

import java.util.List;
import java.util.Set;
import java.util.HashSet;
import java.util.ArrayList;
import java.util.Collections;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;


@Service
public class OrgTagCacheService {

    private static final Logger logger = LoggerFactory.getLogger(OrgTagCacheService.class);

    private static final String USER_ORG_TAGS_KEY_PREFIX = "user:org_tags:";
    private static final String USER_PRIMARY_ORG_KEY_PREFIX = "user:primary_org:";
    private static final String USER_EFFECTIVE_TAGS_KEY_PREFIX = "user:effective_org_tags:";
    private static final long CACHE_TTL_HOURS = 24;
    private static final String DEFAULT_ORG_TAG = "DEFAULT";

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private OrganizationTagRepository organizationTagRepository;


    public void cacheUserOrgTags(String username, List<String> orgTags) {
        try {
            String key = USER_ORG_TAGS_KEY_PREFIX + username;
            redisTemplate.opsForList().rightPushAll(key, orgTags.toArray());
            redisTemplate.expire(key, CACHE_TTL_HOURS, TimeUnit.HOURS);
            logger.debug("Cached organization tags for user: {}", username);
        } catch (Exception e) {
            logger.error("Failed to cache organization tags for user: {}", username, e);
        }
    }


    @SuppressWarnings("unchecked")
    public List<String> getUserOrgTags(String username) {
        try {
            String key = USER_ORG_TAGS_KEY_PREFIX + username;
            List<Object> result = redisTemplate.opsForList().range(key, 0, -1);
            if (result != null && !result.isEmpty()) {
                return result.stream()
                        .map(obj -> (String) obj)
                        .toList();
            }
        } catch (Exception e) {
            logger.error("Failed to get organization tags for user: {}", username, e);
        }
        return null;
    }


    public void cacheUserPrimaryOrg(String username, String primaryOrg) {
        try {
            String key = USER_PRIMARY_ORG_KEY_PREFIX + username;
            redisTemplate.opsForValue().set(key, primaryOrg);
            redisTemplate.expire(key, CACHE_TTL_HOURS, TimeUnit.HOURS);
            logger.debug("Cached primary organization for user: {}", username);
        } catch (Exception e) {
            logger.error("Failed to cache primary organization for user: {}", username, e);
        }
    }


    public String getUserPrimaryOrg(String username) {
        try {
            String key = USER_PRIMARY_ORG_KEY_PREFIX + username;
            return (String) redisTemplate.opsForValue().get(key);
        } catch (Exception e) {
            logger.error("Failed to get primary organization for user: {}", username, e);
            return null;
        }
    }


    public void deleteUserOrgTagsCache(String username) {
        try {
            String orgTagsKey = USER_ORG_TAGS_KEY_PREFIX + username;
            String primaryOrgKey = USER_PRIMARY_ORG_KEY_PREFIX + username;
            redisTemplate.delete(orgTagsKey);
            redisTemplate.delete(primaryOrgKey);
            logger.debug("Deleted organization tags cache for user: {}", username);
        } catch (Exception e) {
            logger.error("Failed to delete organization tags cache for user: {}", username, e);
        }
    }


    public List<String> getUserEffectiveOrgTags(String username) {
        try {

            String cacheKey = USER_EFFECTIVE_TAGS_KEY_PREFIX + username;
            List<Object> cachedTags = redisTemplate.opsForList().range(cacheKey, 0, -1);

            if (cachedTags != null && !cachedTags.isEmpty()) {
                List<String> effectiveTags = cachedTags.stream()
                        .map(Object::toString)
                        .collect(Collectors.toList());


                if (!effectiveTags.contains(DEFAULT_ORG_TAG)) {
                    effectiveTags.add(DEFAULT_ORG_TAG);
                }

                return effectiveTags;
            }


            List<String> userTags = getUserOrgTags(username);
            Set<String> allEffectiveTags = new HashSet<>();


            if (userTags != null && !userTags.isEmpty()) {
                allEffectiveTags.addAll(userTags);


            for (String tagId : userTags) {
                collectParentTags(tagId, allEffectiveTags);
                }
            }


            allEffectiveTags.add(DEFAULT_ORG_TAG);

            List<String> result = new ArrayList<>(allEffectiveTags);


            if (!result.isEmpty()) {
                redisTemplate.opsForList().rightPushAll(cacheKey, result.toArray());
                redisTemplate.expire(cacheKey, CACHE_TTL_HOURS, TimeUnit.HOURS);
            }

            return result;
        } catch (Exception e) {
            logger.error("Failed to get effective organization tags for user: {}", username, e);

            return Collections.singletonList(DEFAULT_ORG_TAG);
        }
    }


    private void collectParentTags(String tagId, Set<String> result) {
        try {
            OrganizationTag tag = organizationTagRepository.findByTagId(tagId).orElse(null);
            if (tag != null && tag.getParentTag() != null && !tag.getParentTag().isEmpty()) {
                String parentTagId = tag.getParentTag();
                result.add(parentTagId);
                collectParentTags(parentTagId, result);
            }
        } catch (Exception e) {
            logger.error("Error collecting parent tags for tag: {}", tagId, e);
        }
    }


    public void deleteUserEffectiveTagsCache(String username) {
        try {
            String key = USER_EFFECTIVE_TAGS_KEY_PREFIX + username;
            redisTemplate.delete(key);
            logger.debug("Deleted effective organization tags cache for user: {}", username);
        } catch (Exception e) {
            logger.error("Failed to delete effective organization tags cache for user: {}", username, e);
        }
    }


    public void invalidateAllEffectiveTagsCache() {
        try {
            Set<String> keys = redisTemplate.keys(USER_EFFECTIVE_TAGS_KEY_PREFIX + "*");
            if (keys != null && !keys.isEmpty()) {
                redisTemplate.delete(keys);
                logger.info("Invalidated all effective organization tags cache");
            }
        } catch (Exception e) {
            logger.error("Failed to invalidate effective organization tags cache", e);
        }
    }
}