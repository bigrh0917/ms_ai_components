package com.yizhaoqi.manshu.service;

import com.yizhaoqi.manshu.repository.DocumentVectorRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Method;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;


@SpringBootTest
class ParseServiceTest {

    @Mock
    private DocumentVectorRepository documentVectorRepository;

    @InjectMocks
    private ParseService parseService;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);

        ReflectionTestUtils.setField(parseService, "chunkSize", 1000);
        ReflectionTestUtils.setField(parseService, "bufferSize", 8192);
        ReflectionTestUtils.setField(parseService, "maxMemoryThreshold", 0.8);
    }

    @Test
    void testSplitLongSentence_NormalChineseText() throws Exception {

        String sentence = "English textEnglish textEnglish textHanLPEnglish textEnglish textEnglish textEnglish textEnglish textEnglish text";
        int chunkSize = 30;


        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);

        @SuppressWarnings("unchecked")
        List<String> result = (List<String>) method.invoke(parseService, sentence, chunkSize);


        assertNotNull(result, "English text");
        assertFalse(result.isEmpty(), "English text");


        for (int i = 0; i < result.size() - 1; i++) {
            assertTrue(result.get(i).length() <= chunkSize,
                "English text " + i + " English text: " + result.get(i).length());
        }


        String reconstructed = String.join("", result);
        assertEquals(sentence, reconstructed, "English text");


        System.out.println("English text: " + sentence.length());
        System.out.println("English text: " + result.size());
        for (int i = 0; i < result.size(); i++) {
            System.out.println("English text " + i + " (English text:" + result.get(i).length() + "): " + result.get(i));
        }
    }

    @Test
    void testSplitLongSentence_ShortText() throws Exception {

        String sentence = "English text";
        int chunkSize = 100;

        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);

        @SuppressWarnings("unchecked")
        List<String> result = (List<String>) method.invoke(parseService, sentence, chunkSize);


        assertEquals(1, result.size(), "English text");
        assertEquals(sentence, result.get(0), "English text");
    }

    @Test
    void testSplitLongSentence_EmptyText() throws Exception {

        String sentence = "";
        int chunkSize = 100;

        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);

        @SuppressWarnings("unchecked")
        List<String> result = (List<String>) method.invoke(parseService, sentence, chunkSize);


        assertTrue(result.isEmpty() || (result.size() == 1 && result.get(0).isEmpty()),
            "English text");
    }

    @Test
    void testSplitLongSentence_MixedLanguage() throws Exception {

        String sentence = "English textChinese and EnglishEnglish texttextEnglish textEnglish textEnglish textmixed languageEnglish textEnglish text";
        int chunkSize = 25;

        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);

        @SuppressWarnings("unchecked")
        List<String> result = (List<String>) method.invoke(parseService, sentence, chunkSize);


        assertNotNull(result);
        assertFalse(result.isEmpty());


        String reconstructed = String.join("", result);
        assertEquals(sentence, reconstructed, "English text");

        System.out.println("English text - English text: " + sentence.length());
        System.out.println("English text: " + result.size());
        for (int i = 0; i < result.size(); i++) {
            System.out.println("English text " + i + ": " + result.get(i));
        }
    }

    @Test
    void testSplitLongSentence_VerySmallChunkSize() throws Exception {

        String sentence = "English text";
        int chunkSize = 3;

        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);

        @SuppressWarnings("unchecked")
        List<String> result = (List<String>) method.invoke(parseService, sentence, chunkSize);


        assertNotNull(result);
        assertFalse(result.isEmpty());


        String reconstructed = String.join("", result);
        assertEquals(sentence, reconstructed, "English text");
    }

    @Test
    void testSplitLongSentence_LongText() throws Exception {

        StringBuilder longText = new StringBuilder();
        for (int i = 0; i < 10; i++) {
            longText.append("English textEnglish textEnglish textHanLPEnglish textEnglish text");
            longText.append("English textEnglish textEnglish textEnglish text");
        }

        String sentence = longText.toString();
        int chunkSize = 50;

        Method method = ParseService.class.getDeclaredMethod("splitLongSentence", String.class, int.class);
        method.setAccessible(true);

        @SuppressWarnings("unchecked")
        List<String> result = (List<String>) method.invoke(parseService, sentence, chunkSize);


        assertNotNull(result);
        assertTrue(result.size() > 1, "English text");


        String reconstructed = String.join("", result);
        assertEquals(sentence, reconstructed, "English text");

        System.out.println("English text - English text: " + sentence.length());
        System.out.println("English text: " + result.size());
    }
}