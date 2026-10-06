package vn.tetticket.shared.adapter;

import org.junit.jupiter.api.Test;
import vn.tetticket.shared.adapter.cache.CacheClient;
import vn.tetticket.shared.adapter.cache.RedisCacheClient;
import vn.tetticket.shared.adapter.logger.AppLogger;
import vn.tetticket.shared.adapter.logger.Slf4jAppLogger;
import vn.tetticket.shared.adapter.mail.EmailSender;
import vn.tetticket.shared.adapter.mail.SmtpEmailSender;
import vn.tetticket.shared.adapter.messaging.EventPublisher;
import vn.tetticket.shared.adapter.messaging.KafkaEventPublisher;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class AdapterTest {

    @Test
    void appLogger_shouldLogWithoutExceptions() {
        AppLogger logger = new Slf4jAppLogger(AdapterTest.class);
        assertDoesNotThrow(() -> {
            logger.info("Test info message: {}", "arg");
            logger.warn("Test warn message");
            logger.debug("Test debug message");
            logger.error("Test error message", new RuntimeException("Test exception"));
        });
    }

    @Test
    void cacheClient_shouldHandleNullGracefully() {
        CacheClient cacheClient = new RedisCacheClient(null);
        assertTrue(cacheClient.get("any-key").isEmpty());
        assertFalse(cacheClient.delete("any-key"));
        assertFalse(cacheClient.hasKey("any-key"));
        assertDoesNotThrow(() -> cacheClient.set("key", "val", Duration.ofSeconds(10)));
    }

    @Test
    void eventPublisher_shouldHandleNullGracefully() {
        EventPublisher publisher = new KafkaEventPublisher(null);
        assertDoesNotThrow(() -> publisher.publish("topic", "key", "payload"));
    }

    @Test
    void emailSender_shouldHandleNullMailSenderGracefully() {
        EmailSender emailSender = new SmtpEmailSender(null);
        assertDoesNotThrow(() -> emailSender.sendEmail("user@example.com", "Test Subject", "Test Body"));
    }
}
