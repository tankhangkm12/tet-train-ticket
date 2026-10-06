package vn.tetticket.shared.health;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import vn.tetticket.shared.config.SecurityConfig;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(HealthController.class)
@Import(SecurityConfig.class)
@TestPropertySource(properties = "spring.kafka.bootstrap-servers=")
public class HealthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void health_shouldReturnOkAndStatusUp() throws Exception {
        mockMvc.perform(get("/health"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void ready_shouldReturnOkAndStatusUp() throws Exception {
        mockMvc.perform(get("/health/ready"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("UP"));
    }

    @Test
    void ready_shouldReturnServiceUnavailableWhenDatabaseFails() throws Exception {
        DataSource faultyDataSource = mock(DataSource.class);
        when(faultyDataSource.getConnection()).thenThrow(new SQLException("Connection refused"));

        HealthController controller = new HealthController(faultyDataSource, null, null);
        ResponseEntity<Map<String, Object>> response = controller.ready();

        assertEquals(HttpStatus.SERVICE_UNAVAILABLE, response.getStatusCode());
        assertEquals("DOWN", response.getBody().get("status"));
    }

    @Test
    void ready_shouldTimeoutAndReturnDownWhenCheckHangs() throws Exception {
        DataSource hangingDataSource = mock(DataSource.class);
        when(hangingDataSource.getConnection()).thenAnswer(invocation -> {
            Thread.sleep(3000);
            return mock(Connection.class);
        });

        HealthController controller = new HealthController(hangingDataSource, null, null);
        Instant start = Instant.now();
        ResponseEntity<Map<String, Object>> response = controller.ready();
        long durationMs = Duration.between(start, Instant.now()).toMillis();

        // Must complete within 1.5s despite 3s sleep in dependency
        assertTrue(durationMs < 1500, "Response took " + durationMs + "ms, expected < 1500ms");
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE, response.getStatusCode());
        assertEquals("DOWN", response.getBody().get("status"));
    }
}
