package vn.tetticket.shared.adapter.config;

import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import vn.tetticket.shared.adapter.cache.CacheClient;
import vn.tetticket.shared.adapter.cache.RedisCacheClient;
import vn.tetticket.shared.adapter.logger.AppLogger;
import vn.tetticket.shared.adapter.logger.Slf4jAppLogger;
import vn.tetticket.shared.adapter.mail.EmailSender;
import vn.tetticket.shared.adapter.mail.MailpitEmailSender;
import vn.tetticket.shared.adapter.messaging.EventPublisher;
import vn.tetticket.shared.adapter.messaging.KafkaEventPublisher;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class AdapterConfig {

    @Bean
    public AppLogger appLogger() {
        return new Slf4jAppLogger("vn.tetticket");
    }

    @Bean
    public CacheClient cacheClient(@Autowired(required = false) StringRedisTemplate redisTemplate) {
        return new RedisCacheClient(redisTemplate);
    }

    @Bean
    public EventPublisher eventPublisher(@Autowired(required = false) KafkaTemplate<String, Object> kafkaTemplate) {
        return new KafkaEventPublisher(kafkaTemplate);
    }

    @Bean
    public EmailSender emailSender(
            @Value("${mailpit.host:${MAILPIT_SMTP_HOST:localhost}}") String host,
            @Value("${mailpit.port:${MAILPIT_SMTP_PORT:1025}}") int port) {
        return new MailpitEmailSender(host, port);
    }

    @Bean(destroyMethod = "close")
    @ConditionalOnExpression("!'${spring.kafka.bootstrap-servers:}'.isBlank()")
    public AdminClient kafkaAdminClient(
            @Value("${spring.kafka.bootstrap-servers}") String bootstrapServers) {
        Map<String, Object> conf = new HashMap<>();
        conf.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        conf.put(AdminClientConfig.REQUEST_TIMEOUT_MS_CONFIG, "1000");
        conf.put(AdminClientConfig.DEFAULT_API_TIMEOUT_MS_CONFIG, "1000");
        return AdminClient.create(conf);
    }
}
