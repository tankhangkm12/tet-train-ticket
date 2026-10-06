package vn.tetticket.shared.health;

import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
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
import java.util.concurrent.TimeUnit;

@RestController
public class HealthController {

    private final DataSource dataSource;
    private final RedisConnectionFactory redisConnectionFactory;
    private final String kafkaBootstrapServers;

    public HealthController(
            @Autowired(required = false) DataSource dataSource,
            @Autowired(required = false) RedisConnectionFactory redisConnectionFactory,
            @Value("${spring.kafka.bootstrap-servers:localhost:9092}") String kafkaBootstrapServers) {
        this.dataSource = dataSource;
        this.redisConnectionFactory = redisConnectionFactory;
        this.kafkaBootstrapServers = kafkaBootstrapServers;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP"));
    }

    @GetMapping("/health/ready")
    public ResponseEntity<Map<String, Object>> ready() {
        Map<String, String> checks = new LinkedHashMap<>();
        boolean allUp = true;

        // Check Database
        if (dataSource != null) {
            String dbStatus = checkDatabase();
            checks.put("database", dbStatus);
            if (!"UP".equals(dbStatus)) {
                allUp = false;
            }
        } else {
            checks.put("database", "DISABLED");
        }

        // Check Redis
        if (redisConnectionFactory != null) {
            String redisStatus = checkRedis();
            checks.put("redis", redisStatus);
            if (!"UP".equals(redisStatus)) {
                allUp = false;
            }
        } else {
            checks.put("redis", "DISABLED");
        }

        // Check Kafka
        if (kafkaBootstrapServers != null && !kafkaBootstrapServers.isBlank()) {
            String kafkaStatus = checkKafka();
            checks.put("kafka", kafkaStatus);
            if (!"UP".equals(kafkaStatus)) {
                allUp = false;
            }
        } else {
            checks.put("kafka", "DISABLED");
        }

        HttpStatus status = allUp ? HttpStatus.OK : HttpStatus.SERVICE_UNAVAILABLE;
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", allUp ? "UP" : "DOWN");
        response.put("checks", checks);

        return ResponseEntity.status(status).body(response);
    }

    private String checkDatabase() {
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement()) {
            stmt.setQueryTimeout(2);
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
        try (RedisConnection conn = redisConnectionFactory.getConnection()) {
            String ping = conn.ping();
            return "PONG".equalsIgnoreCase(ping) ? "UP" : "DOWN";
        } catch (Exception e) {
            return "DOWN";
        }
    }

    private String checkKafka() {
        Map<String, Object> conf = new LinkedHashMap<>();
        conf.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, kafkaBootstrapServers);
        conf.put(AdminClientConfig.REQUEST_TIMEOUT_MS_CONFIG, "2000");
        conf.put(AdminClientConfig.DEFAULT_API_TIMEOUT_MS_CONFIG, "2000");
        try (AdminClient client = AdminClient.create(conf)) {
            client.describeCluster().clusterId().get(2, TimeUnit.SECONDS);
            return "UP";
        } catch (Exception e) {
            return "DOWN";
        }
    }
}
