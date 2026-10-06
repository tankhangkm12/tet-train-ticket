package vn.tetticket.security;

import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.tetticket.shared.security.UserPrincipal;

import java.util.Map;

@RestController
@RequestMapping("/api/v1")
public class TestSecurityController {

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
