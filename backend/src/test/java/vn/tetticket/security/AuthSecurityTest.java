package vn.tetticket.security;

import io.jsonwebtoken.Jwts;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import vn.tetticket.shared.config.SecurityConfig;
import vn.tetticket.shared.health.HealthController;
import vn.tetticket.shared.security.JwtAuthenticationFilter;
import vn.tetticket.shared.security.JwtTokenService;
import vn.tetticket.shared.security.RequestIdFilter;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.util.Base64;

import static org.hamcrest.Matchers.notNullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest({TestSecurityController.class, HealthController.class})
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

    private String customerToken;
    private String staffToken;
    private String adminToken;

    @BeforeEach
    void setUp() {
        customerToken = jwtTokenService.createToken("cust-01", "cust@tetticket.vn", "CUSTOMER", 3600);
        staffToken = jwtTokenService.createToken("staff-01", "staff@tetticket.vn", "STAFF", 3600);
        adminToken = jwtTokenService.createToken("admin-01", "admin@tetticket.vn", "ADMIN", 3600);
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
    void missingToken_toSecuredEndpoint_shouldReturn401() throws Exception {
        mockMvc.perform(get("/api/v1/profile"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PROBLEM_JSON_VALUE))
                .andExpect(jsonPath("$.status").value(401))
                .andExpect(jsonPath("$.title").value("Unauthorized"));
    }

    @Test
    void wrongSignatureToken_toSecuredEndpoint_shouldReturn401() throws Exception {
        // Sign with an untrusted, foreign Ed25519 key pair
        KeyPair foreignKp = JwtTokenService.generateEd25519KeyPair();
        String foreignPriv = Base64.getEncoder().encodeToString(foreignKp.getPrivate().getEncoded());
        JwtTokenService foreignSigner = new JwtTokenService(null, foreignPriv);
        String untrustedToken = foreignSigner.createToken("hacker", "hacker@evil.com", "ADMIN", 3600);

        mockMvc.perform(get("/api/v1/profile")
                .header("Authorization", "Bearer " + untrustedToken))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PROBLEM_JSON_VALUE))
                .andExpect(jsonPath("$.status").value(401));
    }

    @Test
    void expiredToken_toSecuredEndpoint_shouldReturn401() throws Exception {
        String expiredToken = jwtTokenService.createToken("cust-01", "cust@tetticket.vn", "CUSTOMER", -10);

        mockMvc.perform(get("/api/v1/profile")
                .header("Authorization", "Bearer " + expiredToken))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PROBLEM_JSON_VALUE))
                .andExpect(jsonPath("$.status").value(401));
    }

    @Test
    void headerAlgNone_toSecuredEndpoint_shouldReturn401() throws Exception {
        String header = Base64.getUrlEncoder().withoutPadding().encodeToString("{\"alg\":\"none\",\"typ\":\"JWT\"}".getBytes(StandardCharsets.UTF_8));
        String payload = Base64.getUrlEncoder().withoutPadding().encodeToString("{\"sub\":\"usr-none\",\"email\":\"none@tetticket.vn\",\"role\":\"CUSTOMER\"}".getBytes(StandardCharsets.UTF_8));
        String algNoneToken = header + "." + payload + ".";

        mockMvc.perform(get("/api/v1/profile")
                .header("Authorization", "Bearer " + algNoneToken))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PROBLEM_JSON_VALUE))
                .andExpect(jsonPath("$.status").value(401));
    }

    @Test
    void headerHS256_toSecuredEndpoint_shouldReturn401() throws Exception {
        SecretKey secretKey = Jwts.SIG.HS256.key().build();
        String hs256Token = Jwts.builder()
                .subject("usr-hs256")
                .claim("email", "hs256@tetticket.vn")
                .claim("role", "ADMIN")
                .signWith(secretKey, Jwts.SIG.HS256)
                .compact();

        mockMvc.perform(get("/api/v1/profile")
                .header("Authorization", "Bearer " + hs256Token))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PROBLEM_JSON_VALUE))
                .andExpect(jsonPath("$.status").value(401));
    }

    @Test
    void customerToken_cannotAccessAdminDashboard_shouldReturn403() throws Exception {
        mockMvc.perform(get("/api/v1/admin/dashboard")
                .header("Authorization", "Bearer " + customerToken))
                .andExpect(status().isForbidden())
                .andExpect(header().string("Content-Type", MediaType.APPLICATION_PROBLEM_JSON_VALUE))
                .andExpect(jsonPath("$.status").value(403))
                .andExpect(jsonPath("$.title").value("Forbidden"));
    }

    @Test
    void adminToken_canAccessAdminDashboard_shouldReturn200() throws Exception {
        mockMvc.perform(get("/api/v1/admin/dashboard")
                .header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Welcome to admin dashboard"));
    }

    @Test
    void customerToken_canAccessProfile_shouldReturn200() throws Exception {
        mockMvc.perform(get("/api/v1/profile")
                .header("Authorization", "Bearer " + customerToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value("cust-01"))
                .andExpect(jsonPath("$.role").value("CUSTOMER"));
    }

    @Test
    void staffToken_canAccessStaffCheckIn_shouldReturn200() throws Exception {
        mockMvc.perform(get("/api/v1/staff/check-in")
                .header("Authorization", "Bearer " + staffToken))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Staff check-in access granted"));
    }
}
