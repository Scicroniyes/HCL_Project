# 06. MQTT Messaging

This document explains how the parts of the system communicate: the MQTT concepts used, the topics and message formats, how the two brokers are configured, and why the design allows real sensors to replace the simulator.

---

## 1. MQTT in brief

MQTT is a publish/subscribe messaging protocol designed for small devices and unreliable networks.

| Concept | Meaning in this project |
|---|---|
| **Broker** | The server that receives every message and delivers it to the programs interested in it |
| **Publisher** | A program that sends a message to a topic. The simulator is one |
| **Subscriber** | A program that asks the broker for all messages on a topic. The subscriber service is one |
| **Topic** | A path-like name that labels a message, for example `iotfault/turbine/wt01/telemetry` |
| **Wildcards** | `+` matches exactly one level (`iotfault/turbine/+/telemetry`), `#` matches everything below a level (`iotfault/#`). The `#` can only appear at the end |

Publishers and subscribers never talk to each other. They only talk to the broker. This is the property the whole architecture relies on: the simulator does not know who is listening, so anything can be added or replaced without changing it.

## 2. Topics

| Topic | Published by | Read by | Content |
|---|---|---|---|
| `iotfault/turbine/wt01/telemetry` | Simulator (or a real device) | Subscriber service | One sensor reading per second |
| `iotfault/turbine/wt01/diagnosis` | Subscriber service | Any listener, such as a broker web client | A diagnosis, sent only when the status is not normal |

**How the topic is built.**

```
iotfault / turbine / wt01 / telemetry
   |          |        |        |
 project   machine   machine   message
  name      type       id        type
```

Starting every topic with a project prefix keeps the project's messages in one namespace, so it can share a broker with other projects without collisions. The topic names are defined once, in `config.py`, so a change in one place applies to every program.

**Topic rules followed.** Lowercase only (topics are case-sensitive), no spaces, and no leading slash.

## 3. Message formats

### 3.1 Telemetry

The simulator publishes one JSON message per second:

```
{
  "machine_id": "wt01",
  "ts": "2026-10-29T10:15:00+00:00",
  "wind_speed": 8.1,
  "active_power": 312.4,
  "generator_rpm": 1490,
  "gearbox_oil_temp": 84.2,
  "gearbox_bearing_temp": 91.0,
  "gen_bearing_temp": 56.3,
  "stator_temp": 66.0,
  "vibration": 1.4,
  "sim_fault": "gearbox_overheat"
}
```

A message is roughly 300 bytes, so one message per second is a very small load for any broker.

The field names match the parameter names in the machine profile. The timestamp is in UTC. The `sim_fault` label is ground truth for testing, and the analyzer does not read it.

### 3.2 Diagnosis

When the status is warning or critical, the subscriber publishes:

```
{
  "machine_id": "wt01",
  "ts": "2026-10-29T10:15:00+00:00",
  "status": "critical",
  "symptoms": [
    {"parameter": "gearbox_oil_temp", "label": "Gearbox oil temperature",
     "value": 84.2, "unit": "°C", "status": "critical"}
  ],
  "diagnoses": [
    {"id": "gearbox_overheat", "name": "Gearbox overheating", "confidence": 100,
     "matched": ["gearbox_oil_temp", "gearbox_bearing_temp"],
     "causes": ["..."], "checks": ["..."], "severity": "high"}
  ]
}
```

The `confidence` field is the symptom match percentage, which is not a statistical probability. Publishing diagnoses on their own topic means other tools, such as an alerting service, could subscribe to them without reading the database.

## 4. The shared connection helper

Every program connects through one function in `mqtt_client.py`. It creates the client and applies a username and password and TLS only when the configuration asks for them. Keeping this in one place means the simulator, subscriber and any future program connect in exactly the same way.

Behaviour of the programs:

- The **simulator** publishes from a background network thread and sleeps one second between readings.
- The **subscriber** subscribes inside the `on_connect` callback. Doing it there means the subscription is made again automatically if the connection drops and returns.
- Each program has its own **client ID** (`turbine-simulator`, `turbine-subscriber`). A broker allows only one connection per client ID, and a second connection with the same ID disconnects the first, so IDs must stay unique.

## 5. The two brokers

The project works with either broker. Only configuration differs.

| Setting | Mosquitto (Docker) | HiveMQ Cloud |
|---|---|---|
| Host | `mosquitto` (the container name on the Compose network) | A cluster address of the form `xxxx.s1.eu.hivemq.cloud` |
| Port | 1883 | 8883 |
| TLS (encryption) | Off | On |
| Login | None | Username and password |

### 5.1 Mosquitto

Mosquitto runs as a container, using a two-line configuration file:

```
listener 1883
allow_anonymous true
```

This opens the standard MQTT port and allows connections without a password. It is suitable for a local demonstration, and it is the default in Docker Compose, so anyone who clones the repository can run the system with no account and no secrets.

### 5.2 HiveMQ Cloud

A managed broker, used during development to show the system working against a real cloud service. It requires TLS on port 8883 and a username and password. The credentials created in the HiveMQ console need permission to both **publish and subscribe**, and the account login used for the website is a different thing from these MQTT credentials.

A public test broker was considered and rejected, because anyone in the world can read and publish on it.

## 6. Configuration and secrets

Connection settings come from environment variables, with defaults for the laptop setup:

| Variable | Meaning |
|---|---|
| `MQTT_HOST` | Broker address |
| `MQTT_PORT` | Broker port |
| `MQTT_USER` and `MQTT_PASS` | Login, if any |
| `MQTT_TLS` | `true` or `false` |

**The password is never stored in the repository.** On a laptop it is read from `local_secrets.py`, which is listed in `.gitignore` and `.dockerignore`, so it is neither committed nor copied into a Docker image. In Docker Compose, the variables are set directly in `docker-compose.yml` for the local broker, which needs no secret.

## 7. Message delivery guarantees

MQTT offers three quality-of-service (QoS) levels: 0 (at most once), 1 (at least once) and 2 (exactly once). This project uses the default, QoS 0.

**Why this is acceptable.** Telemetry arrives every second, so a lost reading is replaced by the next one almost immediately. QoS 0 is also the lightest option.

**Where it would change.** For alert messages that must not be lost, QoS 1 would be the better choice. This is noted as a possible future improvement.

## 8. Watching the messages

Useful for demonstrating and debugging:

- **HiveMQ Cloud web client.** Connect with the MQTT credentials and subscribe to `iotfault/#` to see both topics live. The topic must be typed exactly with the `#` at the end.
- **Mosquitto command line**, from the project folder: `docker compose exec mosquitto mosquitto_sub -t "iotfault/#" -v`

## 9. Replacing the simulator with real sensors

A real device only has to do three things:

1. Connect to the broker.
2. Publish JSON with the same field names to `iotfault/turbine/wt01/telemetry`.
3. Include `machine_id` and a UTC timestamp.

An ESP32 board with the right sensors could do this with an MQTT library. No change is needed in the subscriber, the analyzer, the database or the dashboard, which is the practical benefit of putting a broker in the middle. A real device would not send the `sim_fault` field, and the system does not depend on it.

## 10. Preparing for several turbines

The current configuration has one fixed telemetry topic. To support several turbines, each would publish to its own topic (`iotfault/turbine/wt02/telemetry`, and so on), and the subscriber would subscribe once using a wildcard:

```
iotfault/turbine/+/telemetry
```

The turbine identifier is already in every message and could be read from the topic or the payload. The database tables and the dashboard would then need to filter by turbine. This is planned future work.

## 11. Limitations

- Anonymous access on the local broker is for demonstration only. A production setup would add authentication and TLS.
- QoS 0 means no delivery guarantee.
- Messages are not retained, so a program that starts later does not receive the last reading until the next one arrives.