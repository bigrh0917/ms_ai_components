package com.yizhaoqi.manshu.service;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.BulkRequest;
import co.elastic.clients.elasticsearch.core.BulkResponse;
import co.elastic.clients.elasticsearch.core.DeleteByQueryRequest;
import co.elastic.clients.elasticsearch.core.bulk.BulkOperation;
import co.elastic.clients.elasticsearch.core.bulk.BulkResponseItem;
import com.yizhaoqi.manshu.entity.EsDocument;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;


@Service
public class ElasticsearchService {

    private static final Logger logger = LoggerFactory.getLogger(ElasticsearchService.class);

    @Autowired
    private ElasticsearchClient esClient;


    public void bulkIndex(List<EsDocument> documents) {
        try {
            logger.info("English textElasticsearchEnglish textEnglish text: {}", documents.size());


            List<BulkOperation> bulkOperations = documents.stream()
                    .map(doc -> BulkOperation.of(op -> op.index(idx -> idx
                            .index("knowledge_base")
                            .id(doc.getId())
                            .document(doc)
                    )))
                    .toList();


            BulkRequest request = BulkRequest.of(b -> b.operations(bulkOperations));


            BulkResponse response = esClient.bulk(request);


            if (response.errors()) {
                logger.error("English text:");
                for (BulkResponseItem item : response.items()) {
                    if (item.error() != null) {
                        logger.error("English text - ID: {}, English text: {}", item.id(), item.error().reason());
                    }
                }
                throw new RuntimeException("English textEnglish textEnglish text");
            } else {
                logger.info("English textEnglish textEnglish text: {}", documents.size());
            }
        } catch (Exception e) {
            logger.error("English textEnglish textEnglish text: {}", documents.size(), e);

            throw new RuntimeException("English text", e);
        }
    }


    public void deleteByFileMd5(String fileMd5) {
        try {
            DeleteByQueryRequest request = DeleteByQueryRequest.of(d -> d
                    .index("knowledge_base")
                    .query(q -> q.term(t -> t.field("fileMd5").value(fileMd5)))
            );
            esClient.deleteByQuery(request);
        } catch (Exception e) {
            throw new RuntimeException("English text", e);
        }
    }
}