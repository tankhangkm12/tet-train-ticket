package vn.tetticket.shared.config;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.validation.BindValidationException;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.NestedExceptionUtils;
import vn.tetticket.shared.security.JwtTokenService;

import java.security.KeyPair;
import java.util.Base64;

import static org.assertj.core.api.Assertions.assertThat;

public class AppPropertiesValidationTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
        .withUserConfiguration(TestConfig.class);

    @Configuration
    @EnableConfigurationProperties(AppProperties.class)
    static class TestConfig {}

    private static String validPublicKey;
    private static String validPrivateKey;

    @BeforeAll
    static void generateTestKeys() {
        KeyPair kp = JwtTokenService.generateEd25519KeyPair();
        validPublicKey = Base64.getEncoder().encodeToString(kp.getPublic().getEncoded());
        validPrivateKey = Base64.getEncoder().encodeToString(kp.getPrivate().getEncoded());
    }

    @Test
    void whenJwtPublicKeyIsProvided_contextStartsSuccessfully() {
        contextRunner
            .withPropertyValues(
                "app.jwt-public-key=" + validPublicKey,
                "app.jwt-private-key=" + validPrivateKey,
                "app.queue-admit-rate=150"
            )
            .run(context -> {
                assertThat(context).hasNotFailed();
                AppProperties props = context.getBean(AppProperties.class);
                assertThat(props.jwtPublicKey()).isEqualTo(validPublicKey);
                assertThat(props.jwtPrivateKey()).isEqualTo(validPrivateKey);
                assertThat(props.queueAdmitRate()).isEqualTo(150);
            });
    }

    @Test
    void whenJwtPublicKeyIsMissing_startupFailsNamingTheMissingVariable() {
        contextRunner
            .withPropertyValues("app.queue-admit-rate=50")
            .run(context -> {
                assertThat(context).hasFailed();
                Throwable failure = context.getStartupFailure();
                Throwable rootCause = NestedExceptionUtils.getRootCause(failure);
                assertThat(rootCause).isInstanceOf(BindValidationException.class);
                assertThat(rootCause.getMessage()).contains("jwtPublicKey");
            });
    }

    @Test
    void whenJwtPublicKeyIsPlaceholder_startupFailsNamingTheVariable() {
        contextRunner
            .withPropertyValues(
                "app.jwt-public-key=<base64-ed25519-public-key>",
                "app.queue-admit-rate=100"
            )
            .run(context -> {
                assertThat(context).hasFailed();
                Throwable failure = context.getStartupFailure();
                Throwable rootCause = NestedExceptionUtils.getRootCause(failure);
                assertThat(rootCause).isInstanceOf(BindValidationException.class);
                assertThat(rootCause.getMessage()).contains("jwtPublicKey");
            });
    }

    @Test
    void whenJwtPublicKeyIsInvalidFormat_startupFailsNamingTheVariable() {
        contextRunner
            .withPropertyValues(
                "app.jwt-public-key=invalid-not-base64-or-not-ed25519",
                "app.queue-admit-rate=100"
            )
            .run(context -> {
                assertThat(context).hasFailed();
                Throwable failure = context.getStartupFailure();
                Throwable rootCause = NestedExceptionUtils.getRootCause(failure);
                assertThat(rootCause).isInstanceOf(BindValidationException.class);
                assertThat(rootCause.getMessage()).contains("jwtPublicKey");
            });
    }

    @Test
    void whenJwtPrivateKeyIsPlaceholder_startupFailsNamingTheVariable() {
        contextRunner
            .withPropertyValues(
                "app.jwt-public-key=" + validPublicKey,
                "app.jwt-private-key=<base64-ed25519-private-key>",
                "app.queue-admit-rate=100"
            )
            .run(context -> {
                assertThat(context).hasFailed();
                Throwable failure = context.getStartupFailure();
                Throwable rootCause = NestedExceptionUtils.getRootCause(failure);
                assertThat(rootCause).isInstanceOf(BindValidationException.class);
                assertThat(rootCause.getMessage()).contains("jwtPrivateKey");
            });
    }

    @Test
    void whenJwtPrivateKeyIsInvalidFormat_startupFailsNamingTheVariable() {
        contextRunner
            .withPropertyValues(
                "app.jwt-public-key=" + validPublicKey,
                "app.jwt-private-key=invalid-private-key-data",
                "app.queue-admit-rate=100"
            )
            .run(context -> {
                assertThat(context).hasFailed();
                Throwable failure = context.getStartupFailure();
                Throwable rootCause = NestedExceptionUtils.getRootCause(failure);
                assertThat(rootCause).isInstanceOf(BindValidationException.class);
                assertThat(rootCause.getMessage()).contains("jwtPrivateKey");
            });
    }

    @Test
    void whenQueueAdmitRateIsZeroOrNegative_startupFailsNamingTheVariable() {
        contextRunner
            .withPropertyValues(
                "app.jwt-public-key=" + validPublicKey,
                "app.queue-admit-rate=0"
            )
            .run(context -> {
                assertThat(context).hasFailed();
                Throwable failure = context.getStartupFailure();
                Throwable rootCause = NestedExceptionUtils.getRootCause(failure);
                assertThat(rootCause).isInstanceOf(BindValidationException.class);
                assertThat(rootCause.getMessage()).contains("queueAdmitRate");
            });
    }
}
