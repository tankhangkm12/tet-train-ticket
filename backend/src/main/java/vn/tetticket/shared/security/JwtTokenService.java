package vn.tetticket.shared.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;

@Service
public class JwtTokenService {

    private static final Logger log = LoggerFactory.getLogger(JwtTokenService.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

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
            long now = Instant.now().getEpochSecond();
            long exp = now + validitySeconds;

            Map<String, Object> header = Map.of("alg", "EdDSA", "typ", "JWT");
            Map<String, Object> payload = Map.of(
                    "sub", userId,
                    "email", email,
                    "role", role,
                    "iat", now,
                    "exp", exp
            );

            String headerJson = MAPPER.writeValueAsString(header);
            String payloadJson = MAPPER.writeValueAsString(payload);

            String encodedHeader = Base64.getUrlEncoder().withoutPadding().encodeToString(headerJson.getBytes(StandardCharsets.UTF_8));
            String encodedPayload = Base64.getUrlEncoder().withoutPadding().encodeToString(payloadJson.getBytes(StandardCharsets.UTF_8));

            String signingInput = encodedHeader + "." + encodedPayload;

            Signature sig = Signature.getInstance("Ed25519");
            sig.initSign(privateKey);
            sig.update(signingInput.getBytes(StandardCharsets.UTF_8));
            byte[] signatureBytes = sig.sign();
            String encodedSignature = Base64.getUrlEncoder().withoutPadding().encodeToString(signatureBytes);

            return signingInput + "." + encodedSignature;
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
            String[] parts = token.split("\\.");
            if (parts.length != 3) {
                return null;
            }

            String signingInput = parts[0] + "." + parts[1];
            byte[] signatureBytes = Base64.getUrlDecoder().decode(parts[2]);

            Signature sig = Signature.getInstance("Ed25519");
            sig.initVerify(publicKey);
            sig.update(signingInput.getBytes(StandardCharsets.UTF_8));
            if (!sig.verify(signatureBytes)) {
                return null;
            }

            byte[] payloadBytes = Base64.getUrlDecoder().decode(parts[1]);
            JsonNode payload = MAPPER.readTree(payloadBytes);

            long exp = payload.has("exp") ? payload.get("exp").asLong() : 0;
            if (Instant.now().getEpochSecond() > exp) {
                log.debug("Token expired at: {}", exp);
                return null;
            }

            String userId = payload.has("sub") ? payload.get("sub").asText() : "";
            String email = payload.has("email") ? payload.get("email").asText() : "";
            String role = payload.has("role") ? payload.get("role").asText() : "CUSTOMER";

            return new UserPrincipal(userId, email, role);
        } catch (Exception e) {
            log.debug("Token verification failed: {}", e.getMessage());
            return null;
        }
    }
}
