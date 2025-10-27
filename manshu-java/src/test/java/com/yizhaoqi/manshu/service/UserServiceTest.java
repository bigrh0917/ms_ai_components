package com.yizhaoqi.manshu.service;

import com.yizhaoqi.manshu.exception.CustomException;
import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.UserRepository;
import com.yizhaoqi.manshu.utils.PasswordUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.HttpStatus;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;


class UserServiceTest {
    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserService userService;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    void testRegisterUser_Success() {
        when(userRepository.findByUsername("testuser")).thenReturn(Optional.empty());

        userService.registerUser("testuser", "password123");

        ArgumentCaptor<User> userCaptor = ArgumentCaptor.forClass(User.class);
        verify(userRepository, times(1)).save(userCaptor.capture());

        User savedUser = userCaptor.getValue();
        assertNotNull(savedUser);
        assertEquals("testuser", savedUser.getUsername());
    }

    @Test
    void testRegisterUser_UsernameExists() {
        when(userRepository.findByUsername("testuser")).thenReturn(Optional.of(new User()));

        CustomException exception = assertThrows(CustomException.class,
                () -> userService.registerUser("testuser", "password123"));
        assertEquals("Username already exists", exception.getMessage());
        assertEquals(HttpStatus.BAD_REQUEST, exception.getStatus());
    }

    @Test
    void testAuthenticateUser_Success() {
        String rawPassword = "password123";
        String encodedPassword = PasswordUtil.encode(rawPassword);

        User user = new User();
        user.setUsername("testuser");
        user.setPassword(encodedPassword);

        when(userRepository.findByUsername("testuser")).thenReturn(Optional.of(user));

        String username = userService.authenticateUser("testuser", rawPassword);
        assertEquals("testuser", username);
    }

    @Test
    void testAuthenticateUser_InvalidCredentials() {
        when(userRepository.findByUsername("testuser")).thenReturn(Optional.empty());

        CustomException exception = assertThrows(CustomException.class,
                () -> userService.authenticateUser("testuser", "wrongpassword"));
        assertEquals("Invalid username or password", exception.getMessage());
        assertEquals(HttpStatus.UNAUTHORIZED, exception.getStatus());
    }
}