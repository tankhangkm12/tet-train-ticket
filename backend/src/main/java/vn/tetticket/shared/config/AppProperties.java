package vn.tetticket.shared.config;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@ConfigurationProperties(prefix = "app")
@Validated
public record AppProperties(
    @NotBlank(message = "JWT_PUBLIC_KEY (app.jwt-public-key) is required and must not be blank")
    String jwtPublicKey,

    @Min(value = 1, message = "APP_QUEUE_ADMIT_RATE (app.queue-admit-rate) must be at least 1")
    int queueAdmitRate
) {}
