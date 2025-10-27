package com.yizhaoqi.manshu.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import com.yizhaoqi.manshu.client.EmbeddingClient;
import com.yizhaoqi.manshu.entity.EsDocument;
import com.yizhaoqi.manshu.entity.SearchResult;
import com.yizhaoqi.manshu.model.User;
import com.yizhaoqi.manshu.exception.CustomException;
import com.yizhaoqi.manshu.repository.UserRepository;
import com.yizhaoqi.manshu.repository.FileUploadRepository;
import com.yizhaoqi.manshu.model.FileUpload;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import co.elastic.clients.elasticsearch._types.query_dsl.Operator;

import java.util.Collections;
import java.util.List;
import java.util.ArrayList;
import java.util.Set;
import java.util.Map;
import java.util.stream.Collectors;


@Service
public class HybridSearchService {

    private static final Logger logger = LoggerFactory.getLogger(HybridSearchService.class);

    @Autowired
    private ElasticsearchClient esClient;

    @Autowired
    private EmbeddingClient embeddingClient;

    @Autowired
    private UserService userService;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private OrgTagCacheService orgTagCacheService;

    @Autowired
    private FileUploadRepository fileUploadRepository;


    public List<SearchResult> searchWithPermission(String query, String userId, int topK) {
        logger.debug("English textEnglish textEnglish text: {}, English textID: {}", query, userId);

        try {

            List<String> userEffectiveTags = getUserEffectiveOrgTags(userId);
            logger.debug("English text {} English text: {}", userId, userEffectiveTags);


            String userDbId = getUserDbId(userId);
            logger.debug("English text {} English textID: {}", userId, userDbId);


            final List<Float> queryVector = embedToVectorList(query);


            if (queryVector == null) {
                logger.warn("English textEnglish textEnglish text");
                return textOnlySearchWithPermission(query, userDbId, userEffectiveTags, topK);
            }

            logger.debug("English textEnglish textEnglish text KNN");

            SearchResponse<EsDocument> response = esClient.search(s -> {
                        s.index("knowledge_base");

                        int recallK = topK * 30;
                        s.knn(kn -> kn
                                .field("vector")
                                .queryVector(queryVector)
                                .k(recallK)
                                .numCandidates(recallK)
                        );

                        s.query(q -> q.bool(b -> b
                                .must(mst -> mst.match(m -> m.field("textContent").query(query)))
                                .filter(f -> f.bool(bf -> bf

                                        .should(s1 -> s1.term(t -> t.field("userId").value(userDbId)))

                                        .should(s2 -> s2.term(t -> t.field("public").value(true)))

                                        .should(s3 -> {
                                            if (userEffectiveTags.isEmpty()) {
                                                return s3.matchNone(mn -> mn);
                                            } else if (userEffectiveTags.size() == 1) {
                                                return s3.term(t -> t.field("orgTag").value(userEffectiveTags.get(0)));
                                            } else {
                                                return s3.bool(inner -> {
                                                    userEffectiveTags.forEach(tag -> inner.should(sh2 -> sh2.term(t -> t.field("orgTag").value(tag))));
                                                    return inner;
                                                });
                                            }
                                        })
                                ))
                        ));


                        s.rescore(r -> r
                                .windowSize(recallK)
                                .query(rq -> rq
                                        .queryWeight(0.2d)
                                        .rescoreQueryWeight(1.0d)
                                        .query(rqq -> rqq.match(m -> m
                                                .field("textContent")
                                                .query(query)
                                                .operator(Operator.And)
                                        ))
                                )
                        );
                        s.size(topK);
                        return s;
                    }, EsDocument.class);

            logger.debug("ElasticsearchEnglish textEnglish textEnglish text: {}, English text: {}",
                response.hits().total().value(), response.hits().maxScore());

            List<SearchResult> results = response.hits().hits().stream()
                    .map(hit -> {
                        assert hit.source() != null;
                        logger.debug("English text - English text: {}, English text: {}, English text: {}, English text: {}",
                            hit.source().getFileMd5(), hit.source().getChunkId(), hit.score(),
                            hit.source().getTextContent().substring(0, Math.min(50, hit.source().getTextContent().length())));
                        return new SearchResult(
                                hit.source().getFileMd5(),
                                hit.source().getChunkId(),
                                hit.source().getTextContent(),
                                hit.score(),
                                hit.source().getUserId(),
                                hit.source().getOrgTag(),
                                hit.source().isPublic()
                        );
                    })
                    .toList();

            logger.debug("English text: {}", results.size());
            attachFileNames(results);
            return results;
        } catch (Exception e) {
            logger.error("English text", e);

            try {
                logger.info("English text");
                return textOnlySearchWithPermission(query, getUserDbId(userId), getUserEffectiveOrgTags(userId), topK);
            } catch (Exception fallbackError) {
                logger.error("English text", fallbackError);
                return Collections.emptyList();
            }
        }
    }


    private List<SearchResult> textOnlySearchWithPermission(String query, String userDbId, List<String> userEffectiveTags, int topK) {
        try {
            logger.debug("English textEnglish textEnglish textID: {}, English text: {}", userDbId, userEffectiveTags);

            SearchResponse<EsDocument> response = esClient.search(s -> s
                    .index("knowledge_base")
                    .query(q -> q
                            .bool(b -> b

                                    .must(m -> m
                                            .match(ma -> ma
                                                    .field("textContent")
                                                    .query(query)
                                            )
                                    )

                                    .filter(f -> f
                                            .bool(bf -> bf

                                                    .should(s1 -> s1
                                                            .term(t -> t
                                                                    .field("userId")
                                                                    .value(userDbId)
                                                            )
                                                    )

                                                    .should(s2 -> s2
                                                            .term(t -> t
                                                                    .field("public")
                                                                    .value(true)
                                                            )
                                                    )

                                                    .should(s3 -> {
                                                        if (userEffectiveTags.isEmpty()) {
                                                            return s3.matchNone(mn -> mn);
                                                        } else if (userEffectiveTags.size() == 1) {

                                                            return s3.term(t -> t
                                                                    .field("orgTag")
                                                                    .value(userEffectiveTags.get(0))
                                                            );
                                                        } else {

                                                            return s3.bool(innerBool -> {
                                                                userEffectiveTags.forEach(tag ->
                                                                        innerBool.should(sh -> sh.term(t -> t
                                                                                .field("orgTag")
                                                                                .value(tag)
                                                                        ))
                                                                );
                                                                return innerBool;
                                                            });
                                                        }
                                                    })
                                            )
                                    )
                            )
                    )
                    .minScore(0.3d)
                    .size(topK),
                    EsDocument.class
            );

            logger.debug("English textEnglish textEnglish text: {}, English text: {}",
                response.hits().total().value(), response.hits().maxScore());

            List<SearchResult> results = response.hits().hits().stream()
                    .map(hit -> {
                        assert hit.source() != null;
                        logger.debug("English text - English text: {}, English text: {}, English text: {}, English text: {}",
                            hit.source().getFileMd5(), hit.source().getChunkId(), hit.score(),
                            hit.source().getTextContent().substring(0, Math.min(50, hit.source().getTextContent().length())));
                        return new SearchResult(
                                hit.source().getFileMd5(),
                                hit.source().getChunkId(),
                                hit.source().getTextContent(),
                                hit.score(),
                                hit.source().getUserId(),
                                hit.source().getOrgTag(),
                                hit.source().isPublic()
                        );
                    })
                    .toList();

            logger.debug("English text: {}", results.size());
            attachFileNames(results);
            return results;
        } catch (Exception e) {
            logger.error("English text", e);
            return new ArrayList<>();
        }
    }


    public List<SearchResult> search(String query, int topK) {
        try {
            logger.debug("English textEnglish textEnglish text: {}, topK: {}", query, topK);
            logger.warn("English textEnglish textEnglish text searchWithPermission English text");


            final List<Float> queryVector = embedToVectorList(query);


            if (queryVector == null) {
                logger.warn("English textEnglish textEnglish text");
                return textOnlySearch(query, topK);
            }

            SearchResponse<EsDocument> response = esClient.search(s -> {
                        s.index("knowledge_base");
                        int recallK = topK * 30;
                        s.knn(kn -> kn
                                .field("vector")
                                .queryVector(queryVector)
                                .k(recallK)
                                .numCandidates(recallK)
                        );


                        s.query(q -> q.match(m -> m.field("textContent").query(query)));


                        s.rescore(r -> r
                                .windowSize(recallK)
                                .query(rq -> rq
                                        .queryWeight(0.2d)
                                        .rescoreQueryWeight(1.0d)
                                        .query(rqq -> rqq.match(m -> m
                                                .field("textContent")
                                                .query(query)
                                                .operator(Operator.And)
                                        ))
                                )
                        );
                        s.size(topK);
                        return s;
                    }, EsDocument.class);

            return response.hits().hits().stream()
                    .map(hit -> {
                        assert hit.source() != null;
                        return new SearchResult(
                                hit.source().getFileMd5(),
                                hit.source().getChunkId(),
                                hit.source().getTextContent(),
                                hit.score()
                        );
                    })
                    .toList();
        } catch (Exception e) {
            logger.error("English text", e);

            try {
                logger.info("English text");
                return textOnlySearch(query, topK);
            } catch (Exception fallbackError) {
                logger.error("English text", fallbackError);
                throw new RuntimeException("English text", fallbackError);
            }
        }
    }


    private List<SearchResult> textOnlySearch(String query, int topK) throws Exception {
        SearchResponse<EsDocument> response = esClient.search(s -> s
                .index("knowledge_base")
                .query(q -> q
                        .match(m -> m
                                .field("textContent")
                                .query(query)
                        )
                )
                .size(topK),
                EsDocument.class
        );

        return response.hits().hits().stream()
                .map(hit -> {
                    assert hit.source() != null;
                    return new SearchResult(
                            hit.source().getFileMd5(),
                            hit.source().getChunkId(),
                            hit.source().getTextContent(),
                            hit.score()
                    );
                })
                .toList();
    }


    private List<Float> embedToVectorList(String text) {
        try {
            List<float[]> vecs = embeddingClient.embed(List.of(text));
            if (vecs == null || vecs.isEmpty()) {
                logger.warn("English text");
                return null;
            }
            float[] raw = vecs.get(0);
            List<Float> list = new ArrayList<>(raw.length);
            for (float v : raw) {
                list.add(v);
            }
            return list;
        } catch (Exception e) {
            logger.error("English text", e);
            return null;
        }
    }


    private List<String> getUserEffectiveOrgTags(String userId) {
        logger.debug("English textEnglish textEnglish textID: {}", userId);
        try {

            User user;
            try {
                Long userIdLong = Long.parseLong(userId);
                logger.debug("English textIDEnglish textLong: {}", userIdLong);
                user = userRepository.findById(userIdLong)
                    .orElseThrow(() -> new CustomException("User not found with ID: " + userId, HttpStatus.NOT_FOUND));
                logger.debug("English textIDEnglish text: {}", user.getUsername());
            } catch (NumberFormatException e) {

                logger.debug("English textIDEnglish textEnglish textEnglish text: {}", userId);
                user = userRepository.findByUsername(userId)
                    .orElseThrow(() -> new CustomException("User not found: " + userId, HttpStatus.NOT_FOUND));
                logger.debug("English text: {}", user.getUsername());
            }


            List<String> effectiveTags = orgTagCacheService.getUserEffectiveOrgTags(user.getUsername());
            logger.debug("English text {} English text: {}", user.getUsername(), effectiveTags);
            return effectiveTags;
        } catch (Exception e) {
            logger.error("English text: {}", e.getMessage(), e);
            return Collections.emptyList();
        }
    }


    private String getUserDbId(String userId) {
        logger.debug("English textIDEnglish textEnglish textID: {}", userId);
        try {

            User user;
            try {
                Long userIdLong = Long.parseLong(userId);
                logger.debug("English textIDEnglish textLong: {}", userIdLong);
                user = userRepository.findById(userIdLong)
                    .orElseThrow(() -> new CustomException("User not found with ID: " + userId, HttpStatus.NOT_FOUND));
                logger.debug("English textIDEnglish text: {}", user.getUsername());
                return userIdLong.toString();
            } catch (NumberFormatException e) {

                logger.debug("English textIDEnglish textEnglish textEnglish text: {}", userId);
                user = userRepository.findByUsername(userId)
                    .orElseThrow(() -> new CustomException("User not found: " + userId, HttpStatus.NOT_FOUND));
                logger.debug("English text: {}, ID: {}", user.getUsername(), user.getId());
                return user.getId().toString();
            }
        } catch (Exception e) {
            logger.error("English textIDEnglish text: {}", e.getMessage(), e);
            throw new RuntimeException("English textIDEnglish text", e);
        }
    }

    private void attachFileNames(List<SearchResult> results) {
        if (results == null || results.isEmpty()) {
            return;
        }
        try {

            Set<String> md5Set = results.stream()
                    .map(SearchResult::getFileMd5)
                    .collect(Collectors.toSet());
            List<FileUpload> uploads = fileUploadRepository.findByFileMd5In(new java.util.ArrayList<>(md5Set));
            Map<String, String> md5ToName = uploads.stream()
                    .collect(Collectors.toMap(FileUpload::getFileMd5, FileUpload::getFileName));

            results.forEach(r -> r.setFileName(md5ToName.get(r.getFileMd5())));
        } catch (Exception e) {
            logger.error("English text", e);
        }
    }
}