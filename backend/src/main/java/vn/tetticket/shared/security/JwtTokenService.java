package vn.tetticket.shared.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;

@Service
public class JwtTokenService {

    private static final Logger log = LoggerFactory.getLogger(JwtTokenService.class);

    private final PublicKey publicKey;
    private final PrivateKey privateKey;

    public JwtTokenService(
            @Value("${app.jwt-public-key:}") String publicKeyStr,
            @Value("${app.jwt-private-key:${JWT_PRIVATE_KEY:}}") String privateKeyStr) {
        this.publicKey = parsePublicKey(publicKeyStr);
        this.privateKey = parsePrivateKey(privateKeyStr);
    }

    public static KeyPair generateEd25519KeyPair() {
        try {
            KeyPairGenerator kpg = KeyPairGenerator.getInstance("Ed25519");
            return kpg.generateKeyPair();
        } catch (Exception e) {
            throw new IllegalStateException("Failed to generate Ed25519 key pair", e);
        }
    }

    private PublicKey parsePublicKey(String keyStr) {
        if (keyStr == null || keyStr.isBlank()) {
            return null;
        }
        try {
            byte[] keyBytes = Base64.getDecoder().decode(keyStr.trim());
            KeyFactory kf = KeyFactory.getInstance("Ed25519");
            return kf.generatePublic(new X509EncodedKeySpec(keyBytes));
        } catch (Exception e) {
            log.error("Failed to parse Ed25519 public key: {}", e.getMessage());
            return null;
        }
    }

    private PrivateKey parsePrivateKey(String keyStr) {
        if (keyStr == null || keyStr.isBlank()) {
            return null;
        }
        try {
            byte[] keyBytes = Base64.getDecoder().decode(keyStr.trim());
            KeyFactory kf = KeyFactory.getInstance("Ed25519");
            return kf.generatePrivate(new PKCS8EncodedKeySpec(keyBytes));
        } catch (Exception e) {
            log.warn("Failed to parse Ed25519 private key (normal on non-identity nodes): {}", e.getMessage());
            return null;
        }
    }

    public String createToken(String userId, String email, String role, long validitySeconds) {
        if (privateKey == null) {
            throw new IllegalStateException("Cannot create token: Ed25519 private key is not configured");
        }
        try {
            Instant now = Instant.now();
            Instant exp = now.plusSeconds(validitySeconds);

            return Jwts.builder()
                    .subject(userId)
                    .claim("email", email)
                    .claim("role", role)
                    .issuedAt(Date.from(now))
                    .expiration(Date.from(exp))
                    .signWith(privateKey, Jwts.SIG.EdDSA)
                    .compact();
        } catch (Exception e) {
            throw new IllegalStateException("Failed to sign JWT token", e);
        }
    }

    public UserPrincipal verifyToken(String token) {
        if (publicKey == null) {
            throw new IllegalStateException("Cannot verify token: Ed25519 public key is not configured");
        }
        if (token == null || token.isBlank()) {
            return null;
        }
        try {
            Claims claims = Jwts.parser()
                    .verifyWith(publicKey)
                    .build()
                    .parseSignedClaims(token.trim())
                    .getPayload();

            String userId = claims.getSubject();
            String email = claims.get("email", String.class);
            String role = claims.get("role", String.class);

            if (userId == null || role == null) {
                return null;
            }

            return new UserPrincipal(userId, email != null ? email : "", role);
        } catch (JwtException | IllegalArgumentException e) {
            log.debug("Token verification failed: {}", e.getMessage());
            return null;
        }
    }
}
