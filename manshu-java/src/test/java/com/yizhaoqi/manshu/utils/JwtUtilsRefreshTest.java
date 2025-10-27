package com.yizhaoqi.manshu.utils;

import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.lenient;


@ExtendWith(MockitoExtension.class)
public class JwtUtilsRefreshTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private JwtUtils jwtUtils;

    private User testUser;
    private String testSecretKey = "dGVzdC1zZWNyZXQta2V5LWZvci1qd3QtdG9rZW4tZ2VuZXJhdGlvbi1hbmQtdmVyaWZpY2F0aW9u";

    @BeforeEach
    void setUp() {

        ReflectionTestUtils.setField(jwtUtils, "secretKeyBase64", testSecretKey);


        testUser = new User();
        testUser.setId(1L);
        testUser.setUsername("testuser");
        testUser.setRole(User.Role.USER);
        testUser.setOrgTags("org1,org2");
        testUser.setPrimaryOrg("org1");


        lenient().when(userRepository.findByUsername("testuser")).thenReturn(Optional.of(testUser));
    }

    @Test
    void testGenerateAndValidateToken() {
        String token = jwtUtils.generateToken("testuser");
        assertNotNull(token);

        assertTrue(jwtUtils.validateToken(token));

        String username = jwtUtils.extractUsernameFromToken(token);
        assertEquals("testuser", username);
    }

    @Test
    void testShouldRefreshToken() throws InterruptedException {

        String token = jwtUtils.generateToken("testuser");
        assertFalse(jwtUtils.shouldRefreshToken(token));


    }

    @Test
    void testCanRefreshExpiredToken() {

        String token = jwtUtils.generateToken("testuser");
        assertFalse(jwtUtils.canRefreshExpiredToken(token));
    }

    @Test
    void testRefreshToken() {
        String originalToken = jwtUtils.generateToken("testuser");
        assertNotNull(originalToken);

        String refreshedToken = jwtUtils.refreshToken(originalToken);
        assertNotNull(refreshedToken);

        assertTrue(jwtUtils.validateToken(refreshedToken));

        String username = jwtUtils.extractUsernameFromToken(refreshedToken);
        assertEquals("testuser", username);


        try {
            Thread.sleep(1000);
            String secondRefreshedToken = jwtUtils.refreshToken(originalToken);
            assertNotEquals(originalToken, secondRefreshedToken);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    @Test
    void testRefreshTokenWithInvalidToken() {

        String invalidToken = "invalid.token.here";
        String refreshedToken = jwtUtils.refreshToken(invalidToken);
        assertNull(refreshedToken);
    }

    @Test
    void testExtractClaimsFromValidToken() {
        String token = jwtUtils.generateToken("testuser");

        String username = jwtUtils.extractUsernameFromToken(token);
        assertEquals("testuser", username);

        String role = jwtUtils.extractRoleFromToken(token);
        assertEquals("USER", role);

        String orgTags = jwtUtils.extractOrgTagsFromToken(token);
        assertEquals("org1,org2", orgTags);

        String primaryOrg = jwtUtils.extractPrimaryOrgFromToken(token);
        assertEquals("org1", primaryOrg);
    }
}