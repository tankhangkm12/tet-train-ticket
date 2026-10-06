package vn.tetticket.shared.config;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.validation.BindValidationException;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.NestedExceptionUtils;

import static org.assertj.core.api.Assertions.assertThat;

public class AppPropertiesValidationTest {

    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
        .withUserConfiguration(TestConfig.class);

    @Configuration
    @EnableConfigurationProperties(AppProperties.class)
    static class TestConfig {}

    @Test
    void whenJwtPublicKeyIsProvided_contextStartsSuccessfully() {
        contextRunner
            .withPropertyValues(
                "app.jwt-public-key=MCowBQYDK2VwAyEAGb9ECz8d8q12Yf4K5P3m7N9w0qR8tU2vX5yZ1aBcDeE=",
                "app.queue-admit-rate=150"
            )
            .run(context -> {
                assertThat(context).hasNotFailed();
                AppProperties props = context.getBean(AppProperties.class);
                assertThat(props.jwtPublicKey()).isEqualTo("MCowBQYDK2VwAyEAGb9ECz8d8q12Yf4K5P3m7N9w0qR8tU2vX5yZ1aBcDeE=");
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
    void whenQueueAdmitRateIsZeroOrNegative_startupFailsNamingTheVariable() {
        contextRunner
            .withPropertyValues(
                "app.jwt-public-key=valid-key",
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
