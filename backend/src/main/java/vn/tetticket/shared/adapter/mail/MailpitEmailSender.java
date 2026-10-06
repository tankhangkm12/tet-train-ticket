package vn.tetticket.shared.adapter.mail;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

public class MailpitEmailSender implements EmailSender {

    private static final Logger log = LoggerFactory.getLogger(MailpitEmailSender.class);

    private final String host;
    private final int port;

    public MailpitEmailSender(String host, int port) {
        this.host = host;
        this.port = port;
    }

    @Override
    public void sendEmail(String to, String subject, String body) {
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress(host, port), 2000);
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
                 BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8))) {

                reader.readLine(); // 220 banner
                writer.write("HELO localhost\r\n");
                writer.flush();
                reader.readLine();

                writer.write("MAIL FROM:<noreply@tetticket.vn>\r\n");
                writer.flush();
                reader.readLine();

                writer.write("RCPT TO:<" + to + ">\r\n");
                writer.flush();
                reader.readLine();

                writer.write("DATA\r\n");
                writer.flush();
                reader.readLine();

                writer.write("Subject: " + subject + "\r\n");
                writer.write("To: " + to + "\r\n");
                writer.write("Content-Type: text/plain; charset=UTF-8\r\n\r\n");
                writer.write(body + "\r\n.\r\n");
                writer.flush();
                reader.readLine();

                writer.write("QUIT\r\n");
                writer.flush();
                reader.readLine();
                log.info("Sent email to {} with subject: {}", to, subject);
            }
        } catch (Exception e) {
            log.warn("Could not send email via Mailpit ({}:{}): {}", host, port, e.getMessage());
        }
    }
}
