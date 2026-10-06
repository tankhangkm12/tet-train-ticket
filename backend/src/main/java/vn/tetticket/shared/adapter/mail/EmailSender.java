package vn.tetticket.shared.adapter.mail;

public interface EmailSender {
    void sendEmail(String to, String subject, String body);
}
