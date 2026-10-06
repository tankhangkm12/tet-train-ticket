package vn.tetticket;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import vn.tetticket.shared.config.AppProperties;

@SpringBootApplication
@EnableConfigurationProperties(AppProperties.class)
public class TetTicketApplication {

    public static void main(String[] args) {
        SpringApplication.run(TetTicketApplication.class, args);
    }
}
