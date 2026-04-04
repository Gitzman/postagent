FROM eclipse-mosquitto:2

# Install mosquitto-go-auth plugin
COPY --from=iegomez/mosquitto-go-auth:latest /mosquitto/go-auth.so /mosquitto/go-auth.so

COPY mosquitto.conf /mosquitto/config/mosquitto.conf

RUN mkdir -p /mosquitto/data && chown -R mosquitto:mosquitto /mosquitto/data

EXPOSE 1883

CMD ["mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
