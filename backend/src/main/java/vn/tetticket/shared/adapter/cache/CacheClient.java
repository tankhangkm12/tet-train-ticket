package vn.tetticket.shared.adapter.cache;

import java.time.Duration;
import java.util.Optional;

public interface CacheClient {
    Optional<String> get(String key);
    void set(String key, String value, Duration ttl);
    boolean delete(String key);
    boolean hasKey(String key);
}
