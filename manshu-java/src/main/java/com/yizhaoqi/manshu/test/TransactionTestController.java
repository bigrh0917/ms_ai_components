package com.yizhaoqi.manshu.test;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.yizhaoqi.manshu.test.dto.TestResponse;

@RestController
@RequestMapping("/api/v1/test")
public class TransactionTestController {

    @Autowired
    private TransactionTestService transactionTestService;

    @GetMapping("/transaction/protected/proxy")
    public TestResponse testProtectedTransactionWithProxy() {
        try {
            transactionTestService.testProtectedTransactionWithSelfProxy();
        } catch (Exception e) {

            return new TestResponse("failed", e.getMessage());
        }
        return new TestResponse("success", "This indicates the transaction was not rolled back, which is unexpected for the proxy call.");
    }

    @GetMapping("/transaction/protected")
    public TestResponse testProtectedTransaction() {
        try {
            transactionTestService.testProtectedTransaction();
        } catch (Exception e) {

            return new TestResponse("failed", e.getMessage());
        }
        return new TestResponse("success", "This indicates the transaction was not rolled back, demonstrating the self-invocation issue.");
    }
}