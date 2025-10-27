package com.yizhaoqi.manshu.config;

import com.yizhaoqi.manshu.model.OrganizationTag;
import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.OrganizationTagRepository;
import com.yizhaoqi.manshu.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.Optional;


@Component
@Order(2)
public class OrgTagInitializer implements CommandLineRunner {
    private static final Logger logger = LoggerFactory.getLogger(OrgTagInitializer.class);

    private static final String DEFAULT_TAG = "default";
    private static final String DEFAULT_NAME = "English text";
    private static final String DEFAULT_DESCRIPTION = "English textEnglish textEnglish text";

    private static final String ADMIN_TAG = "admin";
    private static final String ADMIN_NAME = "English text";
    private static final String ADMIN_DESCRIPTION = "English textEnglish textEnglish text";

    @Autowired
    private OrganizationTagRepository organizationTagRepository;

    @Autowired
    private UserRepository userRepository;

    @Value("${admin.username:admin}")
    private String adminUsername;

    @Override
    public void run(String... args) throws Exception {

        User adminUser = userRepository.findByUsername(adminUsername)
                .orElseThrow(() -> new RuntimeException("English textEnglish textEnglish text"));


        createOrganizationTagIfNotExists(DEFAULT_TAG, DEFAULT_NAME, DEFAULT_DESCRIPTION, adminUser);


        createOrganizationTagIfNotExists(ADMIN_TAG, ADMIN_NAME, ADMIN_DESCRIPTION, adminUser);

        logger.info("English text");
    }


    private void createOrganizationTagIfNotExists(String tagId, String name, String description, User creator) {
        logger.info("English text: {}", tagId);
        if (!organizationTagRepository.existsByTagId(tagId)) {
            logger.info("English text: {}", tagId);
            OrganizationTag tag = new OrganizationTag();
            tag.setTagId(tagId);
            tag.setName(name);
            tag.setDescription(description);
            tag.setCreatedBy(creator);
            organizationTagRepository.save(tag);
            logger.info("English text '{}' English text", tagId);
        } else {
            logger.info("English text '{}' English textEnglish textEnglish text", tagId);
        }
    }
}