package vn.tetticket.shared.health;

import org.apache.kafka.clients.admin.AdminClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

@RestController
public class HealthController {

    private final DataSource dataSource;
    private final RedisConnectionFactory redisConnectionFactory;
    private final AdminClient kafkaAdminClient;
    private final ExecutorService healthExecutor = Executors.newVirtualThreadPerTaskExecutor();

    public HealthController(
            @Autowired(required = false) DataSource dataSource,
            @Autowired(required = false) RedisConnectionFactory redisConnectionFactory,
            @Autowired(required = false) AdminClient kafkaAdminClient) {
        this.dataSource = dataSource;
        this.redisConnectionFactory = redisConnectionFactory;
        this.kafkaAdminClient = kafkaAdminClient;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP"));
    }

    @GetMapping("/health/ready")
    public ResponseEntity<Map<String, Object>> ready() {
        // Run all 3 checks in parallel with 1s timeout each
        CompletableFuture<String> dbFuture = CompletableFuture.supplyAsync(this::checkDatabase, healthExecutor)
                .completeOnTimeout("DOWN", 1000, TimeUnit.MILLISECONDS)
                .exceptionally(ex -> "DOWN");

        CompletableFuture<String> redisFuture = CompletableFuture.supplyAsync(this::checkRedis, healthExecutor)
                .completeOnTimeout("DOWN", 1000, TimeUnit.MILLISECONDS)
                .exceptionally(ex -> "DOWN");

        CompletableFuture<String> kafkaFuture = CompletableFuture.supplyAsync(this::checkKafka, healthExecutor)
                .completeOnTimeout("DOWN", 1000, TimeUnit.MILLISECONDS)
                .exceptionally(ex -> "DOWN");

        CompletableFuture.allOf(dbFuture, redisFuture, kafkaFuture).join();

        String dbStatus = dbFuture.join();
        String redisStatus = redisFuture.join();
        String kafkaStatus = kafkaFuture.join();

        Map<String, String> checks = new LinkedHashMap<>();
        checks.put("database", dbStatus);
        checks.put("redis", redisStatus);
        checks.put("kafka", kafkaStatus);

        boolean allUp = !checks.containsValue("DOWN");
        HttpStatus status = allUp ? HttpStatus.OK : HttpStatus.SERVICE_UNAVAILABLE;

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", allUp ? "UP" : "DOWN");
        response.put("checks", checks);

        return ResponseEntity.status(status).body(response);
    }

    private String checkDatabase() {
        if (dataSource == null) {
            return "DISABLED";
        }
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement()) {
            stmt.setQueryTimeout(1);
            try (ResultSet rs = stmt.executeQuery("SELECT 1")) {
                if (rs.next()) {
                    return "UP";
                }
            }
        } catch (Exception e) {
            return "DOWN";
        }
        return "DOWN";
    }

    private String checkRedis() {
        if (redisConnectionFactory == null) {
            return "DISABLED";
        }
        try (RedisConnection conn = redisConnectionFactory.getConnection()) {
            String ping = conn.ping();
            return "PONG".equalsIgnoreCase(ping) ? "UP" : "DOWN";
        } catch (Exception e) {
            return "DOWN";
        }
    }

    private String checkKafka() {
        if (kafkaAdminClient == null) {
            return "DISABLED";
        }
        try {
            kafkaAdminClient.describeCluster().clusterId().get(1, TimeUnit.SECONDS);
            return "UP";
        } catch (Exception e) {
            return "DOWN";
        }
    }
}
