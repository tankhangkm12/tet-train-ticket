package vn.tetticket.identity.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.tetticket.shared.security.JwtTokenService;
import vn.tetticket.shared.security.UserPrincipal;

import java.util.Map;

@RestController
@RequestMapping("/api/v1")
public class AuthController {

    private final JwtTokenService jwtTokenService;

    public AuthController(JwtTokenService jwtTokenService) {
        this.jwtTokenService = jwtTokenService;
    }

    public record TokenRequest(String userId, String email, String role) {}

    @PostMapping("/auth/token")
    public ResponseEntity<Map<String, String>> generateToken(@RequestBody(required = false) TokenRequest req) {
        String userId = req != null && req.userId() != null ? req.userId() : "usr-001";
        String email = req != null && req.email() != null ? req.email() : "user@tetticket.vn";
        String role = req != null && req.role() != null ? req.role() : "CUSTOMER";

        String token = jwtTokenService.createToken(userId, email, role, 3600);
        return ResponseEntity.ok(Map.of("accessToken", token, "tokenType", "Bearer"));
    }

    @GetMapping("/profile")
    public ResponseEntity<Map<String, Object>> profile(@AuthenticationPrincipal UserPrincipal principal) {
        return ResponseEntity.ok(Map.of(
                "userId", principal.userId(),
                "email", principal.email(),
                "role", principal.role()
        ));
    }

    @GetMapping("/admin/dashboard")
    public ResponseEntity<Map<String, String>> adminDashboard() {
        return ResponseEntity.ok(Map.of("message", "Welcome to admin dashboard"));
    }

    @GetMapping("/staff/check-in")
    public ResponseEntity<Map<String, String>> staffCheckIn() {
        return ResponseEntity.ok(Map.of("message", "Staff check-in access granted"));
    }
}
