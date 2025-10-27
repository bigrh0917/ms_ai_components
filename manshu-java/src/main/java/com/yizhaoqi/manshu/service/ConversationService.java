package com.yizhaoqi.manshu.service;

import com.yizhaoqi.manshu.exception.CustomException;
import com.yizhaoqi.manshu.model.Conversation;
import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.repository.ConversationRepository;
import com.yizhaoqi.manshu.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class ConversationService {

    @Autowired
    private ConversationRepository conversationRepository;

    @Autowired
    private UserRepository userRepository;


    public void recordConversation(String username, String question, String answer) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new CustomException("User not found", HttpStatus.NOT_FOUND));

        Conversation conversation = new Conversation();
        conversation.setUser(user);
        conversation.setQuestion(question);
        conversation.setAnswer(answer);

        conversationRepository.save(conversation);
    }


    public List<Conversation> getConversations(String username, LocalDateTime startDate, LocalDateTime endDate) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new CustomException("User not found", HttpStatus.NOT_FOUND));


        if (user.getRole() == User.Role.ADMIN && "all".equals(username)) {
            if (startDate != null && endDate != null) {
                return conversationRepository.findByTimestampBetween(startDate, endDate);
            } else {
                return conversationRepository.findAll();
            }
        } else {

            if (startDate != null && endDate != null) {
                return conversationRepository.findByUserIdAndTimestampBetween(
                        user.getId(), startDate, endDate);
            } else {
                return conversationRepository.findByUserId(user.getId());
            }
        }
    }


    public List<Conversation> getAllConversations(String adminUsername, String targetUsername,
                                                 LocalDateTime startDate, LocalDateTime endDate) {
        User admin = userRepository.findByUsername(adminUsername)
                .orElseThrow(() -> new CustomException("Admin not found", HttpStatus.NOT_FOUND));


        if (admin.getRole() != User.Role.ADMIN) {
            throw new CustomException("Unauthorized access", HttpStatus.FORBIDDEN);
        }


        if (targetUsername != null && !targetUsername.isEmpty()) {
            User targetUser = userRepository.findByUsername(targetUsername)
                    .orElseThrow(() -> new CustomException("Target user not found", HttpStatus.NOT_FOUND));

            if (startDate != null && endDate != null) {
                return conversationRepository.findByUserIdAndTimestampBetween(
                        targetUser.getId(), startDate, endDate);
            } else {
                return conversationRepository.findByUserId(targetUser.getId());
            }
        } else {

            if (startDate != null && endDate != null) {
                return conversationRepository.findByTimestampBetween(startDate, endDate);
            } else {
                return conversationRepository.findAll();
            }
        }
    }
}