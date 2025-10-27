package com.yizhaoqi.manshu.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Method;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;


class ParseServiceUnitTest {

    private ParseService parseService;

    @BeforeEach
    void setUp() {
        parseService = new ParseService();

        ReflectionTestUtils.setField(parseService, "chunkSize", 1000);
        ReflectionTestUtils.setField(parseService, "bufferSize", 8192);
        ReflectionTestUtils.setField(parseService, "maxMemoryThreshold", 0.8);
    }

    @Test
    void testSplitLongSentence_BasicFunctionality() throws Exception {

        String sentence = "English textEnglish textEnglish textEnglish text";
        int chunkSize = 15;

        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);

        @SuppressWarnings("unchecked")
        List<String> result = (List<String>) method.invoke(parseService, sentence, chunkSize);

        assertNotNull(result);
        assertFalse(result.isEmpty());


        String reconstructed = String.join("", result);
        assertEquals(sentence, reconstructed);

        System.out.println("=== English text ===");
        System.out.println("English text: " + sentence + " (English text: " + sentence.length() + ")");
        System.out.println("English text: " + result.size());
        for (int i = 0; i < result.size(); i++) {
            System.out.println("English text " + i + ": " + result.get(i) + " (English text: " + result.get(i).length() + ")");
        }
    }

    @Test
    void testSplitLongSentence_EdgeCases() throws Exception {
        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);


        @SuppressWarnings("unchecked")
        List<String> emptyResult = (List<String>) method.invoke(parseService, "", 100);
        assertTrue(emptyResult.isEmpty() || (emptyResult.size() == 1 && emptyResult.get(0).isEmpty()));


        @SuppressWarnings("unchecked")
        List<String> singleCharResult = (List<String>) method.invoke(parseService, "English text", 10);
        assertEquals(1, singleCharResult.size());
        assertEquals("English text", singleCharResult.get(0));


        StringBuilder longText = new StringBuilder();
        for (int i = 0; i < 20; i++) {
            longText.append("English text").append(i).append("English textEnglish text");
        }

        @SuppressWarnings("unchecked")
        List<String> longResult = (List<String>) method.invoke(parseService, longText.toString(), 30);
        assertTrue(longResult.size() > 1);


        String reconstructed = String.join("", longResult);
        assertEquals(longText.toString(), reconstructed);

        System.out.println("=== English text ===");
        System.out.println("English text: " + longResult.size());
    }

    @Test
    void testSplitLongSentence_ChunkSizeValidation() throws Exception {
        String sentence = "English textEnglish textEnglish text123English text";

        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);


        int[] chunkSizes = {5, 10, 20, 50};

        for (int chunkSize : chunkSizes) {
            @SuppressWarnings("unchecked")
            List<String> result = (List<String>) method.invoke(parseService, sentence, chunkSize);


            for (int i = 0; i < result.size() - 1; i++) {
                assertTrue(result.get(i).length() <= chunkSize,
                    "English text " + chunkSize + " English textEnglish textEnglish text " + i + " English text: " + result.get(i).length());
            }


            String reconstructed = String.join("", result);
            assertEquals(sentence, reconstructed, "English text " + chunkSize + " English text");

            System.out.println("English text " + chunkSize + " -> English text: " + result.size());
        }
    }

    @Test
    void testSplitLongSentence_Performance() throws Exception {

        StringBuilder largeText = new StringBuilder();
        for (int i = 0; i < 100; i++) {
            largeText.append("English textEnglish textEnglish textEnglish text");
        }

        String sentence = largeText.toString();
        int chunkSize = 100;

        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);

        long startTime = System.currentTimeMillis();

        @SuppressWarnings("unchecked")
        List<String> result = (List<String>) method.invoke(parseService, sentence, chunkSize);

        long endTime = System.currentTimeMillis();
        long duration = endTime - startTime;

        assertNotNull(result);
        assertTrue(result.size() > 1);


        String reconstructed = String.join("", result);
        assertEquals(sentence, reconstructed);

        System.out.println("=== English text ===");
        System.out.println("English text: " + sentence.length());
        System.out.println("English text: " + result.size());
        System.out.println("English text: " + duration + "ms");


        assertTrue(duration < 5000, "English text: " + duration + "ms");
    }
}