package com.yizhaoqi.manshu.service;

import com.yizhaoqi.manshu.client.EmbeddingClient;
import com.yizhaoqi.manshu.model.DocumentVector;
import com.yizhaoqi.manshu.entity.EsDocument;
import com.yizhaoqi.manshu.entity.TextChunk;
import com.yizhaoqi.manshu.repository.DocumentVectorRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;
import java.util.stream.IntStream;


@Service
public class VectorizationService {

    private static final Logger logger = LoggerFactory.getLogger(VectorizationService.class);

    @Autowired
    private EmbeddingClient embeddingClient;

    @Autowired
    private ElasticsearchService elasticsearchService;

    @Autowired
    private DocumentVectorRepository documentVectorRepository;


    public void vectorize(String fileMd5, String userId, String orgTag, boolean isPublic) {
        try {
            logger.info("English textEnglish textfileMd5: {}, userId: {}, orgTag: {}, isPublic: {}",
                       fileMd5, userId, orgTag, isPublic);


            List<TextChunk> chunks = fetchTextChunks(fileMd5);
            if (chunks == null || chunks.isEmpty()) {
                logger.warn("English textEnglish textfileMd5: {}", fileMd5);
                return;
            }


            List<String> texts = chunks.stream()
                    .map(TextChunk::getContent)
                    .toList();


            List<float[]> vectors = embeddingClient.embed(texts);


            List<EsDocument> esDocuments = IntStream.range(0, chunks.size())
                    .mapToObj(i -> new EsDocument(
                            UUID.randomUUID().toString(),
                            fileMd5,
                            chunks.get(i).getChunkId(),
                            chunks.get(i).getContent(),
                            vectors.get(i),
                            "deepseek-embed",
                            userId,
                            orgTag,
                            isPublic
                    ))
                    .toList();

            elasticsearchService.bulkIndex(esDocuments);

            logger.info("English textEnglish textfileMd5: {}", fileMd5);
        } catch (Exception e) {
            logger.error("English textEnglish textfileMd5: {}", fileMd5, e);
            throw new RuntimeException("English text", e);
        }
    }




    private List<TextChunk> fetchTextChunks(String fileMd5) {

        List<DocumentVector> vectors = documentVectorRepository.findByFileMd5(fileMd5);


        return vectors.stream()
                .map(vector -> new TextChunk(
                        vector.getChunkId(),
                        vector.getTextContent()
                ))
                .toList();
    }
}