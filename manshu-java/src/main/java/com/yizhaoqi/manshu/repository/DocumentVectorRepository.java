package com.yizhaoqi.manshu.repository;

import com.yizhaoqi.manshu.model.DocumentVector;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

public interface DocumentVectorRepository extends JpaRepository<DocumentVector, Long> {
    List<DocumentVector> findByFileMd5(String fileMd5);


    @Transactional
    @Modifying
    @Query(value = "DELETE FROM document_vectors WHERE file_md5 = ?1", nativeQuery = true)
    void deleteByFileMd5(String fileMd5);
}