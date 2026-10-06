# Stage 1: Build
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /workspace

COPY backend/.mvn/ backend/.mvn/
COPY backend/mvnw backend/pom.xml backend/
WORKDIR /workspace/backend
RUN sed -i 's/\r$//' ./mvnw && chmod +x ./mvnw && ./mvnw dependency:resolve -B

COPY backend/src/ src/
RUN ./mvnw clean package -DskipTests -B

# Stage 2: Development target
FROM eclipse-temurin:21-jdk-alpine AS dev
WORKDIR /app
COPY --from=builder /workspace/backend/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]

# Stage 3: Production target
FROM eclipse-temurin:21-jre-alpine AS prod
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app
COPY --from=builder /workspace/backend/target/*.jar app.jar
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
