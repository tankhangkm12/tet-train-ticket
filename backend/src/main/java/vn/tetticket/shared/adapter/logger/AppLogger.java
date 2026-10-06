package vn.tetticket.shared.adapter.logger;

public interface AppLogger {
    void info(String message, Object... args);
    void warn(String message, Object... args);
    void error(String message, Throwable throwable, Object... args);
    void debug(String message, Object... args);
}
