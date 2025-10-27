package com.yizhaoqi.manshu.repository;

import com.yizhaoqi.manshu.model.FileUpload;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface FileUploadRepository extends JpaRepository<FileUpload, Long> {
    Optional<FileUpload> findByFileMd5(String fileMd5);

    Optional<FileUpload> findByFileMd5AndUserId(String fileMd5, String userId);

    Optional<FileUpload> findByFileNameAndIsPublicTrue(String fileName);

    long countByFileMd5(String fileMd5);

    void deleteByFileMd5(String fileMd5);

    void deleteByFileMd5AndUserId(String fileMd5, String userId);


    List<FileUpload> findByUserIdOrIsPublicTrue(String userId);


    @Query("SELECT f FROM FileUpload f WHERE f.userId = :userId OR f.isPublic = true OR (f.orgTag IN :orgTagList AND f.isPublic = false)")
    List<FileUpload> findAccessibleFilesWithTags(@Param("userId") String userId, @Param("orgTagList") List<String> orgTagList);


    @Query("SELECT f FROM FileUpload f WHERE f.userId = :userId OR f.isPublic = true OR (f.orgTag IN :orgTagList AND f.isPublic = false)")
    List<FileUpload> findAccessibleFiles(@Param("userId") String userId, @Param("orgTagList") List<String> orgTagList);


    List<FileUpload> findByUserId(String userId);

    List<FileUpload> findByFileMd5In(List<String> md5List);
}