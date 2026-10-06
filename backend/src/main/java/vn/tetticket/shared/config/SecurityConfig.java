package vn.tetticket.shared.config;

import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import tools.jackson.databind.ObjectMapper;
import vn.tetticket.shared.security.JwtAuthenticationFilter;
import vn.tetticket.shared.security.RequestIdFilter;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private final JwtAuthenticationFilter jwtAuthenticationFilter;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter) {
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint((request, response, authException) -> {
                    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
                    Map<String, Object> body = new LinkedHashMap<>();
                    body.put("type", "about:blank");
                    body.put("title", "Unauthorized");
                    body.put("status", 401);
                    body.put("detail", "Authentication required or token invalid");
                    body.put("instance", request.getRequestURI());
                    body.put("requestId", MDC.get(RequestIdFilter.MDC_REQUEST_ID_KEY));
                    body.put("timestamp", Instant.now().toString());
                    response.getOutputStream().write(MAPPER.writeValueAsBytes(body));
                })
                .accessDeniedHandler((request, response, accessDeniedException) -> {
                    response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                    response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
                    Map<String, Object> body = new LinkedHashMap<>();
                    body.put("type", "about:blank");
                    body.put("title", "Forbidden");
                    body.put("status", 403);
                    body.put("detail", "Access denied: insufficient permissions");
                    body.put("instance", request.getRequestURI());
                    body.put("requestId", MDC.get(RequestIdFilter.MDC_REQUEST_ID_KEY));
                    body.put("timestamp", Instant.now().toString());
                    response.getOutputStream().write(MAPPER.writeValueAsBytes(body));
                })
            )
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/health", "/health/ready", "/error", "/actuator/**").permitAll()
                .requestMatchers("/api/v1/public/**", "/api/v1/auth/**").permitAll()
                .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                .requestMatchers("/api/v1/staff/**").hasAnyRole("STAFF", "ADMIN")
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
