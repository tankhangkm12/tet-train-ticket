package vn.tetticket.shared.config;

import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.security.KeyFactory;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;

@ConfigurationProperties(prefix = "app")
@Validated
public record AppProperties(
    @NotBlank(message = "JWT_PUBLIC_KEY (app.jwt-public-key) is required and must not be blank")
    String jwtPublicKey,

    String jwtPrivateKey,

    @Min(value = 1, message = "APP_QUEUE_ADMIT_RATE (app.queue-admit-rate) must be at least 1")
    int queueAdmitRate
) {
    @AssertTrue(message = "JWT_PUBLIC_KEY (app.jwt-public-key) is invalid: cannot decode Ed25519 public key. Placeholder not replaced or invalid key format.")
    public boolean isJwtPublicKeyValid() {
        return isValidEd25519PublicKey(jwtPublicKey);
    }

    @AssertTrue(message = "JWT_PRIVATE_KEY (app.jwt-private-key) is invalid: cannot decode Ed25519 private key. Placeholder not replaced or invalid key format.")
    public boolean isJwtPrivateKeyValid() {
        if (jwtPrivateKey == null || jwtPrivateKey.isBlank()) {
            return true; // Optional on non-identity nodes
        }
        return isValidEd25519PrivateKey(jwtPrivateKey);
    }

    public static boolean isValidEd25519PublicKey(String keyStr) {
        if (keyStr == null || keyStr.isBlank() || keyStr.startsWith("<") || keyStr.contains("placeholder")) {
            return false;
        }
        try {
            byte[] keyBytes = Base64.getDecoder().decode(keyStr.trim());
            KeyFactory kf = KeyFactory.getInstance("Ed25519");
            kf.generatePublic(new X509EncodedKeySpec(keyBytes));
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public static boolean isValidEd25519PrivateKey(String keyStr) {
        if (keyStr == null || keyStr.isBlank() || keyStr.startsWith("<") || keyStr.contains("placeholder")) {
            return false;
        }
        try {
            byte[] keyBytes = Base64.getDecoder().decode(keyStr.trim());
            KeyFactory kf = KeyFactory.getInstance("Ed25519");
            kf.generatePrivate(new PKCS8EncodedKeySpec(keyBytes));
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
