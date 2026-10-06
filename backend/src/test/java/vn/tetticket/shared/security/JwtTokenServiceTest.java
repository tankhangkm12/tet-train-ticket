package vn.tetticket.shared.security;

import io.jsonwebtoken.Jwts;
import org.junit.jupiter.api.Test;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
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
    void verifyToken_withExpiredToken_shouldReturnNull() {
        KeyPair kp = JwtTokenService.generateEd25519KeyPair();
        String pubStr = Base64.getEncoder().encodeToString(kp.getPublic().getEncoded());
        String privStr = Base64.getEncoder().encodeToString(kp.getPrivate().getEncoded());

        JwtTokenService service = new JwtTokenService(pubStr, privStr);
        String expiredToken = service.createToken("usr-expired", "exp@tetticket.vn", "CUSTOMER", -10);
        assertNull(service.verifyToken(expiredToken));
    }

    @Test
    void verifyToken_withWrongSignature_shouldReturnNull() {
        KeyPair kp1 = JwtTokenService.generateEd25519KeyPair();
        KeyPair kp2 = JwtTokenService.generateEd25519KeyPair();

        String pub1 = Base64.getEncoder().encodeToString(kp1.getPublic().getEncoded());
        String priv2 = Base64.getEncoder().encodeToString(kp2.getPrivate().getEncoded());

        // Service configured with kp1 public key
        JwtTokenService verifier = new JwtTokenService(pub1, null);

        // Signer using kp2 private key
        JwtTokenService attacker = new JwtTokenService(null, priv2);
        String forgedToken = attacker.createToken("usr-forged", "forged@tetticket.vn", "ADMIN", 3600);

        assertNull(verifier.verifyToken(forgedToken));
    }

    @Test
    void verifyToken_withAlgNone_shouldReturnNull() {
        KeyPair kp = JwtTokenService.generateEd25519KeyPair();
        String pubStr = Base64.getEncoder().encodeToString(kp.getPublic().getEncoded());
        JwtTokenService verifier = new JwtTokenService(pubStr, null);

        String header = Base64.getUrlEncoder().withoutPadding().encodeToString("{\"alg\":\"none\",\"typ\":\"JWT\"}".getBytes(StandardCharsets.UTF_8));
        String payload = Base64.getUrlEncoder().withoutPadding().encodeToString("{\"sub\":\"usr-none\",\"email\":\"none@tetticket.vn\",\"role\":\"CUSTOMER\"}".getBytes(StandardCharsets.UTF_8));
        String algNoneToken = header + "." + payload + ".";

        assertNull(verifier.verifyToken(algNoneToken));
    }

    @Test
    void verifyToken_withHS256_shouldReturnNull() {
        KeyPair kp = JwtTokenService.generateEd25519KeyPair();
        String pubStr = Base64.getEncoder().encodeToString(kp.getPublic().getEncoded());
        JwtTokenService verifier = new JwtTokenService(pubStr, null);

        SecretKey secretKey = Jwts.SIG.HS256.key().build();
        String hs256Token = Jwts.builder()
                .subject("usr-hs256")
                .claim("email", "hs256@tetticket.vn")
                .claim("role", "CUSTOMER")
                .signWith(secretKey, Jwts.SIG.HS256)
                .compact();

        assertNull(verifier.verifyToken(hs256Token));
    }
}
