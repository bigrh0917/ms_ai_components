package com.yizhaoqi.manshu.service;

import com.yizhaoqi.manshu.model.DocumentVector;
import com.yizhaoqi.manshu.repository.DocumentVectorRepository;
import org.apache.tika.exception.TikaException;
import org.apache.tika.metadata.Metadata;
import org.apache.tika.parser.ParseContext;
import org.apache.tika.parser.AutoDetectParser;
import org.apache.tika.sax.BodyContentHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.xml.sax.SAXException;

import java.io.*;
import java.util.ArrayList;
import java.util.List;
import com.hankcs.hanlp.seg.common.Term;
import com.hankcs.hanlp.tokenizer.StandardTokenizer;

@Service
public class ParseService {

    private static final Logger logger = LoggerFactory.getLogger(ParseService.class);

    @Autowired
    private DocumentVectorRepository documentVectorRepository;

    @Value("${file.parsing.chunk-size}")
    private int chunkSize;

    @Value("${file.parsing.parent-chunk-size:1048576}")
    private int parentChunkSize;

    @Value("${file.parsing.buffer-size:8192}")
    private int bufferSize;

    @Value("${file.parsing.max-memory-threshold:0.8}")
    private double maxMemoryThreshold;

    public ParseService() {

    }


    public void parseAndSave(String fileMd5, InputStream fileStream,
            String userId, String orgTag, boolean isPublic) throws IOException, TikaException {
        logger.info("English textEnglish textfileMd5: {}, userId: {}, orgTag: {}, isPublic: {}",
                fileMd5, userId, orgTag, isPublic);

        checkMemoryThreshold();

        try (BufferedInputStream bufferedStream = new BufferedInputStream(fileStream, bufferSize)) {

            StreamingContentHandler handler = new StreamingContentHandler(fileMd5, userId, orgTag, isPublic);
            Metadata metadata = new Metadata();
            ParseContext context = new ParseContext();
            AutoDetectParser parser = new AutoDetectParser();



            parser.parse(bufferedStream, handler, metadata, context);

            logger.info("English textEnglish textfileMd5: {}", fileMd5);

        } catch (SAXException e) {
            logger.error("English textEnglish textfileMd5: {}", fileMd5, e);
            throw new RuntimeException("English text", e);
        }
    }


    public void parseAndSave(String fileMd5, InputStream fileStream) throws IOException, TikaException {

        parseAndSave(fileMd5, fileStream, "unknown", "DEFAULT", false);
    }

    private void checkMemoryThreshold() {
        Runtime runtime = Runtime.getRuntime();
        long maxMemory = runtime.maxMemory();
        long totalMemory = runtime.totalMemory();
        long freeMemory = runtime.freeMemory();
        long usedMemory = totalMemory - freeMemory;

        double memoryUsage = (double) usedMemory / maxMemory;

        if (memoryUsage > maxMemoryThreshold) {
            logger.warn("English text: {:.2f}%, English text", memoryUsage * 100);
            System.gc();


            usedMemory = runtime.totalMemory() - runtime.freeMemory();
            memoryUsage = (double) usedMemory / maxMemory;

            if (memoryUsage > maxMemoryThreshold) {
                throw new RuntimeException("English textEnglish textEnglish textEnglish textEnglish text: " +
                    String.format("%.2f%%", memoryUsage * 100));
            }
        }
    }


    private class StreamingContentHandler extends BodyContentHandler {
        private final StringBuilder buffer = new StringBuilder();
        private final String fileMd5;
        private final String userId;
        private final String orgTag;
        private final boolean isPublic;
        private int savedChunkCount = 0;

        public StreamingContentHandler(String fileMd5, String userId, String orgTag, boolean isPublic) {
            super(-1);
            this.fileMd5 = fileMd5;
            this.userId = userId;
            this.orgTag = orgTag;
            this.isPublic = isPublic;
        }

        @Override
        public void characters(char[] ch, int start, int length) {
            buffer.append(ch, start, length);
            if (buffer.length() >= parentChunkSize) {
                processParentChunk();
            }
        }

        @Override
        public void endDocument() {

            if (buffer.length() > 0) {
                processParentChunk();
            }
        }

        private void processParentChunk() {
            String parentChunkText = buffer.toString();
            logger.debug("English textEnglish textEnglish text: {} bytes", parentChunkText.length());


            List<String> childChunks = ParseService.this.splitTextIntoChunksWithSemantics(parentChunkText, chunkSize);


            this.savedChunkCount = ParseService.this.saveChildChunks(fileMd5, childChunks, userId, orgTag, isPublic, this.savedChunkCount);


            buffer.setLength(0);
        }
    }


    private int saveChildChunks(String fileMd5, List<String> chunks,
            String userId, String orgTag, boolean isPublic, int startingChunkId) {
        int currentChunkId = startingChunkId;
        for (String chunk : chunks) {
            currentChunkId++;
            var vector = new DocumentVector();
            vector.setFileMd5(fileMd5);
            vector.setChunkId(currentChunkId);
            vector.setTextContent(chunk);
            vector.setUserId(userId);
            vector.setOrgTag(orgTag);
            vector.setPublic(isPublic);
            documentVectorRepository.save(vector);
        }
        logger.info("English text {} English text", chunks.size());
        return currentChunkId;
    }


    private List<String> splitTextIntoChunksWithSemantics(String text, int chunkSize) {
        List<String> chunks = new ArrayList<>();


        String[] paragraphs = text.split("\n\n+");

        StringBuilder currentChunk = new StringBuilder();

        for (String paragraph : paragraphs) {

            if (paragraph.length() > chunkSize) {

                if (currentChunk.length() > 0) {
                    chunks.add(currentChunk.toString().trim());
                    currentChunk = new StringBuilder();
                }


                List<String> sentenceChunks = splitLongParagraph(paragraph, chunkSize);
                chunks.addAll(sentenceChunks);
            }

            else if (currentChunk.length() + paragraph.length() > chunkSize) {

                if (currentChunk.length() > 0) {
                    chunks.add(currentChunk.toString().trim());
                }

                currentChunk = new StringBuilder(paragraph);
            }

            else {
                if (currentChunk.length() > 0) {
                    currentChunk.append("\n\n");
                }
                currentChunk.append(paragraph);
            }
        }


        if (currentChunk.length() > 0) {
            chunks.add(currentChunk.toString().trim());
        }

        return chunks;
    }


    private List<String> splitLongParagraph(String paragraph, int chunkSize) {
        List<String> chunks = new ArrayList<>();


        String[] sentences = paragraph.split("(?<=[English text])|(?<=[.!?;])\\s+");

        StringBuilder currentChunk = new StringBuilder();

        for (String sentence : sentences) {
            if (currentChunk.length() + sentence.length() > chunkSize) {
                if (currentChunk.length() > 0) {
                    chunks.add(currentChunk.toString().trim());
                    currentChunk = new StringBuilder();
                }


                if (sentence.length() > chunkSize) {
                    chunks.addAll(splitLongSentence(sentence, chunkSize));
                } else {
                    currentChunk.append(sentence);
                }
            } else {
                currentChunk.append(sentence);
            }
        }

        if (currentChunk.length() > 0) {
            chunks.add(currentChunk.toString().trim());
        }

        return chunks;
    }


    private List<String> splitLongSentence(String sentence, int chunkSize) {
        List<String> chunks = new ArrayList<>();

        try {

            List<Term> termList = StandardTokenizer.segment(sentence);

            StringBuilder currentChunk = new StringBuilder();
            for (Term term : termList) {
                String word = term.word;


                if (currentChunk.length() + word.length() > chunkSize && !currentChunk.isEmpty()) {
                    chunks.add(currentChunk.toString());
                    currentChunk = new StringBuilder();
                }

                currentChunk.append(word);
            }

            if (!currentChunk.isEmpty()) {
                chunks.add(currentChunk.toString());
            }

            logger.debug("HanLPEnglish textEnglish textEnglish text: {}, English text: {}, English text: {}",
                    sentence.length(), termList.size(), chunks.size());

        } catch (Exception e) {
            logger.warn("HanLPEnglish text: {}, English text", e.getMessage());
            chunks = splitByCharacters(sentence, chunkSize);
         }

        return chunks;
    }


    private List<String> splitByCharacters(String sentence, int chunkSize) {
        List<String> chunks = new ArrayList<>();
        StringBuilder currentChunk = new StringBuilder();

        for (int i = 0; i < sentence.length(); i++) {
            char c = sentence.charAt(i);

            if (currentChunk.length() + 1 > chunkSize && !currentChunk.isEmpty()) {
                chunks.add(currentChunk.toString());
                currentChunk = new StringBuilder();
            }

            currentChunk.append(c);
        }

        if (!currentChunk.isEmpty()) {
            chunks.add(currentChunk.toString());
        }

        return chunks;
    }
}