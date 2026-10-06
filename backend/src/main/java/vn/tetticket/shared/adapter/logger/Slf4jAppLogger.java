package vn.tetticket.shared.adapter.logger;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Slf4jAppLogger implements AppLogger {

    private final Logger logger;

    public Slf4jAppLogger(Class<?> clazz) {
        this.logger = LoggerFactory.getLogger(clazz);
    }

    public Slf4jAppLogger(String name) {
        this.logger = LoggerFactory.getLogger(name);
    }

    @Override
    public void info(String message, Object... args) {
        logger.info(message, args);
    }

    @Override
    public void warn(String message, Object... args) {
        logger.warn(message, args);
    }

    @Override
    public void error(String message, Throwable throwable, Object... args) {
        if (throwable != null) {
            logger.error(message, throwable);
        } else {
            logger.error(message, args);
        }
    }

    @Override
    public void debug(String message, Object... args) {
        logger.debug(message, args);
    }
}
