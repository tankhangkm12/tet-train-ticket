package vn.tetticket.shared.adapter.messaging;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;

public class KafkaEventPublisher implements EventPublisher {

    private static final Logger log = LoggerFactory.getLogger(KafkaEventPublisher.class);
    private final KafkaTemplate<String, Object> kafkaTemplate;

    public KafkaEventPublisher(KafkaTemplate<String, Object> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    @Override
    public void publish(String topic, String key, Object payload) {
        if (kafkaTemplate == null) {
            log.warn("KafkaTemplate not configured, dropping message to topic: {}", topic);
            return;
        }
        kafkaTemplate.send(topic, key, payload)
            .whenComplete((result, ex) -> {
                if (ex != null) {
                    log.error("Failed to publish message to topic: {} key: {}", topic, key, ex);
                } else {
                    log.debug("Published message to topic: {} key: {} partition: {}",
                            topic, key, result.getRecordMetadata().partition());
                }
            });
    }
}
