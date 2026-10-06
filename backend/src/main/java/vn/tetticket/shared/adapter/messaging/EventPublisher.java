package vn.tetticket.shared.adapter.messaging;

public interface EventPublisher {
    void publish(String topic, String key, Object payload);
}
