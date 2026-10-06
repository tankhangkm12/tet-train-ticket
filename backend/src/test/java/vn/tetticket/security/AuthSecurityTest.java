package vn.tetticket.security;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import vn.tetticket.identity.controller.AuthController;
import vn.tetticket.shared.config.SecurityConfig;
import vn.tetticket.shared.health.HealthController;
import vn.tetticket.shared.security.JwtAuthenticationFilter;
import vn.tetticket.shared.security.JwtTokenService;
import vn.tetticket.shared.security.RequestIdFilter;

import java.security.KeyPair;
import java.util.Base64;

import static org.hamcrest.Matchers.notNullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest({AuthController.class, HealthController.class})
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, JwtTokenService.class, RequestIdFilter.class})
@TestPropertySource(properties = {
    "spring.kafka.bootstrap-servers=",
    "app.jwt-public-key=MCowBQYDK2VwAyEAVmTvQ8njvYoQ1WBKOvbcsrqi9Nvaery5qD2LHTyII+0=",
    "app.jwt-private-key=MC4CAQAwBQYDK2VwBCIEICyou5y8vnEP0V3Kl61JGlfmho3Hhd6pCWNsqF318zTP"
})
public class AuthSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtTokenService jwtTokenService;

    private static String customerToken;
    private static String staffToken;
    private static String adminToken;

    @BeforeEach
    void setUp() {
        if (customerToken == null) {
            KeyPair kp = JwtTokenService.generateEd25519KeyPair();
            String pubStr = Base64.getEncoder().encodeToString(kp.getPublic().getEncoded());
            String privStr = Base64.getEncoder().encodeToString(kp.getPrivate().getEncoded());
            JwtTokenService localSigner = new JwtTokenService(pubStr, privStr);

            customerToken = localSigner.createToken("cust-01", "cust@tetticket.vn", "CUSTOMER", 3600);
            staffToken = localSigner.createToken("staff-01", "staff@tetticket.vn", "STAFF", 3600);
            adminToken = localSigner.createToken("admin-01", "admin@tetticket.vn", "ADMIN", 3600);
        }
    }

    @Test
    void requestId_shouldBePropagatedInResponseHeader() throws Exception {
        mockMvc.perform(get("/health")
                .header("X-Request-Id", "test-request-123"))
                .andExpect(status().isOk())
                .andExpect(header().string("X-Request-Id", "test-request-123"));

        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(header().string("X-Request-Id", notNullValue()));
    }

    @Test
    void unauthenticatedRequest_toProfile_shouldReturn401ProblemDetail() throws Exception {
        mockMvc.perform(get("/api/v1/profile"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PROBLEM_JSON_VALUE))
                .andExpect(jsonPath("$.status").value(401))
                .andExpect(jsonPath("$.title").value("Unauthorized"));
    }

    @Test
    void invalidToken_toProfile_shouldReturn401ProblemDetail() throws Exception {
        mockMvc.perform(get("/api/v1/profile")
                .header("Authorization", "Bearer invalid.jwt.token"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PROBLEM_JSON_VALUE))
                .andExpect(jsonPath("$.status").value(401));
    }

    @Test
    void customerToken_canAccessProfile() throws Exception {
        // We sign a token using jwtTokenService if private key is present
        // Or verify that with a valid token, profile is 200
        // When dynamic keys are tested, we test with jwtTokenService
        String token = jwtTokenService.createToken("usr-77", "cust77@tetticket.vn", "CUSTOMER", 3600);
        mockMvc.perform(get("/api/v1/profile")
                .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value("usr-77"))
                .andExpect(jsonPath("$.role").value("CUSTOMER"));
    }

    @Test
    void customerToken_cannotAccessAdminDashboard_shouldReturn403() throws Exception {
        String token = jwtTokenService.createToken("usr-88", "cust88@tetticket.vn", "CUSTOMER", 3600);
        mockMvc.perform(get("/api/v1/admin/dashboard")
                .header("Authorization", "Bearer " + token))
                .andExpect(status().isForbidden())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PROBLEM_JSON_VALUE))
                .andExpect(jsonPath("$.status").value(403))
                .andExpect(jsonPath("$.title").value("Forbidden"));
    }

    @Test
    void adminToken_canAccessAdminDashboard_shouldReturn200() throws Exception {
        String token = jwtTokenService.createToken("admin-99", "admin99@tetticket.vn", "ADMIN", 3600);
        mockMvc.perform(get("/api/v1/admin/dashboard")
                .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Welcome to admin dashboard"));
    }

    @Test
    void staffToken_canAccessStaffCheckIn_shouldReturn200() throws Exception {
        String token = jwtTokenService.createToken("staff-11", "staff11@tetticket.vn", "STAFF", 3600);
        mockMvc.perform(get("/api/v1/staff/check-in")
                .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Staff check-in access granted"));
    }
}
