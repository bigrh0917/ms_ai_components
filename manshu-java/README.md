# Knowledge Hub Backend

This repository contains my Spring Boot service for managing a document knowledge base with semantic search and AI-assisted conversations. It powers the workflow I use in deployments: ingest files, split them into chunks, vectorize the content, and expose secure APIs for retrieval and chat.

## Highlights
- Document upload pipeline backed by Kafka, MinIO object storage, and Apache Tika text extraction.
- Vector storage in Elasticsearch with optional Redis caching for frequently accessed results.
- REST and WebSocket endpoints secured with Spring Security and JWT.
- Clients for embedding and chat providers (DashScope-compatible embeddings and DeepSeek chat).

## Prerequisites
- JDK 17+, Maven 3.8+
- MySQL 8, Redis 7, Kafka 3, Elasticsearch 8.10, MinIO 2025-04
- API keys for the embedding and chat services you plan to call

## Getting Started
1. Copy the sample config from `src/main/resources/application.yml` (or the dev/docker variants) and set database credentials, Redis/Kafka endpoints, and AI keys.
2. Provision the required services manually or with Docker Compose (see `docs/docker-compose.yaml`).
3. Build and run the backend:
   ```bash
   mvn clean package
   java -jar target/manshu-0.0.1-SNAPSHOT.jar
   ```
4. Call REST endpoints under `/api/v1/**` or open the WebSocket endpoint at `/ws/chat` for streaming replies.

## Database Schema
`docs/databases/ddl.sql` contains the DDL I use to bootstrap MySQL with the tables for users, organization tags, uploads, chunk metadata, and vector storage.

## Testing
Run the automated tests with:
```bash
mvn test
```

## Notes
- Default credentials in configuration files are meant for local testing—override them before deploying anywhere else.
- Update Docker volume mounts and passwords in `docs/docker-compose.yaml` so they match your environment or hosting provider.
