package vn.tetticket.shared.security;

import org.junit.jupiter.api.Test;

import java.security.KeyPair;
import java.util.Base64;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

public class JwtTokenServiceTest {

    @Test
    void keyPairGeneration_andTokenSignVerify_shouldSucceed() {
        KeyPair kp = JwtTokenService.generateEd25519KeyPair();
        String pubStr = Base64.getEncoder().encodeToString(kp.getPublic().getEncoded());
        String privStr = Base64.getEncoder().encodeToString(kp.getPrivate().getEncoded());

        JwtTokenService service = new JwtTokenService(pubStr, privStr);
        String token = service.createToken("usr-100", "test@tetticket.vn", "CUSTOMER", 3600);
        assertNotNull(token);

        UserPrincipal principal = service.verifyToken(token);
        assertNotNull(principal);
        assertEquals("usr-100", principal.userId());
        assertEquals("test@tetticket.vn", principal.email());
        assertEquals("CUSTOMER", principal.role());
    }

    @Test
    void verifyToken_withExpiredOrTamperedToken_shouldReturnNull() {
        KeyPair kp = JwtTokenService.generateEd25519KeyPair();
        String pubStr = Base64.getEncoder().encodeToString(kp.getPublic().getEncoded());
        String privStr = Base64.getEncoder().encodeToString(kp.getPrivate().getEncoded());

        JwtTokenService service = new JwtTokenService(pubStr, privStr);
        // Expired token (negative validity)
        String expiredToken = service.createToken("usr-expired", "exp@tetticket.vn", "CUSTOMER", -10);
        assertNull(service.verifyToken(expiredToken));

        // Tampered token
        String validToken = service.createToken("usr-valid", "val@tetticket.vn", "CUSTOMER", 3600);
        String tamperedToken = validToken + "tamper";
        assertNull(service.verifyToken(tamperedToken));
    }
}
