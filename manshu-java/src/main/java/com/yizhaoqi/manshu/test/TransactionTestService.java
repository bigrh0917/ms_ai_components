package com.yizhaoqi.manshu.test;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TransactionTestService {

    @Autowired
    private TestEntityRepository testEntityRepository;

    @Lazy
    @Autowired
    private TransactionTestService self;

    public void testProtectedTransaction() {

        protectedTransactionalMethod("test-protected");
    }

    public void testProtectedTransactionWithSelfProxy() {

        self.protectedTransactionalMethod("test-protected-proxy");
    }

    @Transactional
    protected void protectedTransactionalMethod(String name) {
        TestEntity entity = new TestEntity();
        entity.setName(name);
        testEntityRepository.save(entity);
        throw new RuntimeException("Rollback test for protected method");
    }
}