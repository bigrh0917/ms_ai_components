package com.yizhaoqi.manshu.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;


@Component
@ConfigurationProperties(prefix = "ai")
@Data
public class AiProperties {

    private Prompt prompt = new Prompt();
    private Generation generation = new Generation();

    @Data
    public static class Prompt {

        private String rules;

        private String refStart;

        private String refEnd;

        private String noResultText;
    }

    @Data
    public static class Generation {

        private Double temperature = 0.3;

        private Integer maxTokens = 2000;

        private Double topP = 0.9;
    }
}