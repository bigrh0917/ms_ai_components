package com.yizhaoqi.manshu.config;

import co.elastic.clients.transport.endpoints.BooleanResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.indices.CreateIndexRequest;
import co.elastic.clients.elasticsearch.indices.ExistsRequest;
import org.apache.http.ConnectionClosedException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Files;
import java.nio.charset.StandardCharsets;
import java.io.StringReader;

@Component
public class EsIndexInitializer implements CommandLineRunner {

    private static final Logger logger = LoggerFactory.getLogger(EsIndexInitializer.class);

    @Autowired
    private ElasticsearchClient esClient;

    @Value("classpath:es-mappings/knowledge_base.json")
    private org.springframework.core.io.Resource mappingResource;

    @Override
    public void run(String... args) throws Exception {
        try {
            initializeIndex();
        } catch (Exception exception) {

            if (exception instanceof ConnectionClosedException || (exception.getCause() instanceof ConnectionClosedException)) {
                logger.error("Elasticsearch connection closed unexpectedly. Retrying in 5 seconds...");
                try {
                    Thread.sleep(5000);
                    initializeIndex();
                } catch (Exception retryException) {
                    logger.error("Retry failed. Verify that Elasticsearch is reachable and configured correctly (e.g., HTTPS). {}", retryException.getMessage());
                    throw new RuntimeException("Failed to initialize index after retry", retryException);
                }
            } else {
                throw new RuntimeException("Failed to initialize index", exception);
            }
        }
    }


    private void initializeIndex() throws Exception {
        BooleanResponse existsResponse = esClient.indices().exists(ExistsRequest.of(e -> e.index("knowledge_base")));
        if (!existsResponse.value()) {
            createIndex();
        } else {
            logger.info("Elasticsearch index 'knowledge_base' already exists");
        }
    }


    private void createIndex() throws Exception {
        String mappingJson = new String(Files.readAllBytes(mappingResource.getFile().toPath()), StandardCharsets.UTF_8);

        CreateIndexRequest createIndexRequest = CreateIndexRequest.of(c -> c
                .index("knowledge_base")
                .withJson(new StringReader(mappingJson))
        );
        esClient.indices().create(createIndexRequest);
        logger.info("Elasticsearch index 'knowledge_base' created successfully");
    }
}