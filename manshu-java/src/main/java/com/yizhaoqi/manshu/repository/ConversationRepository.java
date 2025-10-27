package com.yizhaoqi.manshu.repository;

import com.yizhaoqi.manshu.model.Conversation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface ConversationRepository extends JpaRepository<Conversation, Long> {


    List<Conversation> findByUserIdAndTimestampBetween(Long userId, LocalDateTime startDate, LocalDateTime endDate);


    List<Conversation> findByUserId(Long userId);


    List<Conversation> findByTimestampBetween(LocalDateTime startDate, LocalDateTime endDate);
}