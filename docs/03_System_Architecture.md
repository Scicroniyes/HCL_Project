# 03. System Architecture

This document describes the parts of the system, what each one is responsible for, how data moves between them, and why the system is split this way.

---

## 1. The big picture

```
 +------------------+
 |    Simulator     |   (a real sensor device could replace this)
 +--------+---------+
          | MQTT: iotfault/turbine/wt01/telemetry
          v
 +------------------+
 |   MQTT broker    |   Mosquitto (Docker) or HiveMQ Cloud
 +--------+---------+
          |
          v
 +------------------+        +-------------------------+
 |    Subscriber    |------->|  Analyzer               |
 |  (receives,      |        |  limits + knowledge     |
 |   stores,        |<-------|  -> status, symptoms,   |
 |   publishes)     |        |     ranked faults       |
 +----+--------+----+        +-------------------------+
      |        | MQTT: iotfault/turbine/wt01/diagnosis
      v        v
 +---------+  (any listener, for example the broker web client)
 | SQLite  |
 | readings|<------------------+
 | diagnoses                   |
 +---------+            +------+--------------+
                        |     Dashboard       |
                        |     (Streamlit)     |
                        +------+--------------+
                               | on button click
                               v
                        +---------------------+      +-----------------+
                        |  RAG                |----->|  Local LLM      |
                        |  ChromaDB +         |      |  Ollama         |
                        |  embeddings         |<-----|  llama3.2:3b    |
                        +---------------------+      +-----------------+
```

## 2. Components and responsibilities

| Component | File | Responsibility | Does not do |
|---|---|---|---|
| Simulator | `simulators/sim1.py` | Produces one realistic reading per second, injects faults, publishes over MQTT | Detect anything or touch the database |
| MQTT broker | Mosquitto container, or HiveMQ Cloud | Receives messages and delivers them to subscribers | Understand the messages |
| Subscriber | `subscriber/subscriber.py` | Receives readings, saves them, runs the analyzer, saves and publishes diagnoses | Decide the limits or hold knowledge |
| Analyzer | `analyzers/analyzer.py` | Compares readings with limits, ranks faults from the knowledge base | Talk to MQTT, the database or the LLM |
| Machine profile | `profiles/wind_turbine.json` | Parameter names, units and limits | Contain logic |
| Fault knowledge | `analyzers/knowledge.json` | Fault entries: symptoms, causes, checks, severity | Contain logic |
| Database | `iot_data.db` (SQLite) | Stores readings and diagnoses | Compute anything |
| RAG index builder | `rag/build_index.py` | Splits the knowledge document into sections and stores their embeddings | Run at diagnosis time |
| Explainer | `rag/explain.py` | Retrieves relevant sections, asks the LLM for an explanation, returns it with sources | Decide whether a fault exists |
| Dashboard | `dashboard/app.py` | Shows status, charts, diagnosis and history, and triggers the explanation | Write to the database |
| Local LLM | Ollama, model llama3.2:3b | Writes the explanation from the retrieved text | See raw sensor streams |

## 3. Data flow for one reading

1. The simulator builds a JSON reading and publishes it on the telemetry topic.
2. The broker delivers it to the subscriber.
3. The subscriber inserts it into the `readings` table.
4. The subscriber calls `full_analysis(reading)`.
5. The analyzer classifies each parameter as normal, warning or critical, using the profile.
6. The analyzer lists the out-of-range parameters as symptoms and ranks the faults in the knowledge base by how many of their symptoms are present.
7. If the status is not normal, the subscriber inserts a row into `diagnoses` and publishes the diagnosis on the diagnosis topic.
8. The dashboard reads the latest readings and diagnoses every 2 seconds and redraws the page.
9. When the user clicks **Explain with AI**, the dashboard builds a symptom sentence from the current symptoms, and the explainer retrieves the two best-matching knowledge sections and asks the LLM to answer using only those sections.
10. The explanation and the section names (the sources) are shown on the page.

## 4. Two ways to run it

The same code runs in two settings. The difference is only configuration, supplied through environment variables.

| | On a laptop (development) | In Docker Compose |
|---|---|---|
| Broker | HiveMQ Cloud, with TLS and a username and password from an ignored local file | Mosquitto container, no login, no TLS |
| Database | `iot_data.db` in the project folder | A shared volume mounted at `/app/data` |
| Ollama | On the host | On the host, reached through `host.docker.internal` |
| Start | Several terminals | `docker compose up --build` |

In Docker, the simulator, subscriber and dashboard all use the **same image**. Compose starts it three times with a different command each time, so there is only one image to build and maintain.

## 5. Design principles

**Loose coupling through MQTT.** Producers and consumers never talk to each other directly. The simulator does not know the subscriber exists. This is what lets a real device replace the simulator, and what allows more consumers to be added later.

**One job per component.** Detection is separate from storage, which is separate from display. The analyzer is a pure function from a reading to a result, which makes it easy to test on its own.

**Detection and explanation are separate.** Rules decide whether something is wrong. The LLM is only asked to explain, and only after the rules have found a problem. The LLM can never raise or cancel an alarm.

**Data, not code.** Limits, fault knowledge and RAG documents are files. Changing them does not require editing Python.

**Replaceable parts.** Each component has a narrow interface, so it can be swapped:

| Today | Possible replacement |
|---|---|
| Simulator | Real sensor device publishing the same JSON |
| Rule-based analyzer | Trained ML model behind the same `full_analysis` function |
| SQLite | PostgreSQL |
| Mosquitto | HiveMQ Cloud or another broker |
| Streamlit | Another dashboard tool reading the same database |

**Configuration from the environment.** Broker address, port, TLS, credentials and the database path come from environment variables, with sensible defaults. This is how one codebase runs both on a laptop and in containers without edits.

## 6. Why the explanation runs on request

A local LLM takes seconds to produce an answer, and much longer on its first call while the models load. Running it on every reading would make the system slow and would repeat the same explanation hundreds of times for one ongoing fault. So the dashboard shows the instant rule-based diagnosis immediately, and the AI explanation is produced on demand. This also gives the user control during a demonstration.

## 7. Failure behaviour

- Services are set to restart automatically in Docker Compose, so a service that starts before the broker is ready simply retries.
- If Ollama is not running, only the **Explain with AI** feature is affected. Detection, storage and the rule-based diagnosis continue to work.
- If the broker is unreachable, no new readings arrive, and the dashboard keeps showing the last stored data.

## 8. Project structure

```
IOT-fault-assistant/
|-- analyzers/        analyzer.py, knowledge.json
|-- dashboard/        app.py
|-- docs/             project documents
|-- knowledge/        wind_turbine_faults.md  (text for RAG)
|-- mosquitto/config/ mosquitto.conf
|-- profiles/         wind_turbine.json
|-- rag/              build_index.py, explain.py
|-- simulators/       sim1.py
|-- subscriber/       subscriber.py
|-- config.py         broker settings, topics
|-- mqtt_client.py    shared MQTT connection helper
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
```

Files that are generated or secret are not committed: `venv/`, `iot_data.db`, `rag_store/` and `local_secrets.py`.

## 9. Known architectural limits

- The system handles one turbine. Supporting several requires turbine-specific topics (for example `iotfault/turbine/+/telemetry`), a turbine identifier in every table and a fleet view on the dashboard.
- SQLite suits a single writer. A larger fleet would call for a database server.
- Ollama runs outside the containers, so it must be installed separately on the host.