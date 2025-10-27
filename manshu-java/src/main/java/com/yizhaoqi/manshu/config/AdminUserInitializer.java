package com.yizhaoqi.manshu.config;

import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.UserRepository;
import com.yizhaoqi.manshu.utils.PasswordUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.util.Optional;


@Component
@Order(1)
public class AdminUserInitializer implements CommandLineRunner {
    private static final Logger logger = LoggerFactory.getLogger(AdminUserInitializer.class);

    @Autowired
    private UserRepository userRepository;

    @Value("${admin.username:admin}")
    private String adminUsername;

    @Value("${admin.password:admin123}")
    private String adminPassword;

    @Value("${admin.primary-org:default}")
    private String adminPrimaryOrg;

    @Value("${admin.org-tags:default,admin}")
    private String adminOrgTags;

    @Override
    public void run(String... args) {
        logger.info("Checking whether an administrator account exists: {}", adminUsername);
        Optional<User> existingAdmin = userRepository.findByUsername(adminUsername);

        if (existingAdmin.isPresent()) {
            logger.info("Administrator account '{}' already exists; skipping creation.", adminUsername);
            return;
        }

        try {
            logger.info("Creating administrator account: {}", adminUsername);
            User adminUser = new User();
            adminUser.setUsername(adminUsername);
            adminUser.setPassword(PasswordUtil.encode(adminPassword));
            adminUser.setRole(User.Role.ADMIN);
            adminUser.setPrimaryOrg(adminPrimaryOrg);
            adminUser.setOrgTags(adminOrgTags);

            userRepository.save(adminUser);
            logger.info("Administrator account '{}' created successfully.", adminUsername);
        } catch (Exception e) {
            logger.error("Failed to create administrator account: {}", e.getMessage(), e);
            throw new RuntimeException("Unable to create administrator account", e);
        }
    }
}