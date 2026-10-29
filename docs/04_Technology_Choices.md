# 04. Technology Choices

This document explains why each technology was chosen, what alternatives were considered, and what was left out on purpose. The required stack comes from the project sheet (row 100): **MQTT, Python, Local LLM, RAG**. Everything else was chosen to support those four with as little extra complexity as possible.

---

## 1. Summary

| Need | Chosen | Main reason |
|---|---|---|
| Messaging | MQTT | Standard, lightweight protocol for IoT devices (required) |
| Broker | Mosquitto in Docker, HiveMQ Cloud as an option | Local broker needs no account, cloud broker shows real-world use |
| Language | Python | Required, and it has libraries for every part of the system |
| Storage | SQLite | Zero setup, one file, easy to inspect |
| Dashboard | Streamlit | A web page written in pure Python |
| Knowledge search | RAG with ChromaDB and sentence-transformers | Required, runs fully locally |
| Language model | Ollama running llama3.2:3b | Required (local LLM), no cloud and no API cost |
| Packaging | Docker and Docker Compose | One-command start for anyone who clones the repository |

## 2. MQTT (required)

**What it is.** A publish/subscribe protocol. Devices publish messages to named topics, and any program subscribed to a topic receives them.

**Why it fits.**
- It was designed for small devices and unreliable networks, so a real turbine controller or ESP32 can use it.
- Publishers and subscribers do not know each other. This is what lets the simulator be replaced by real sensors without touching the rest of the system.
- A topic name such as `iotfault/turbine/wt01/telemetry` carries meaning: project, machine type, machine id and message type.

**Alternative considered: HTTP/REST.** It would work, but every device would need to know the server's address and call it directly. There is no built-in way to deliver one message to several consumers, and it is heavier for small devices.

## 3. The broker: Mosquitto and HiveMQ Cloud

**MQTT is the protocol, and the broker is the server that runs it.** The project supports both options through configuration.

| | Mosquitto (Docker container) | HiveMQ Cloud |
|---|---|---|
| Account needed | No | Yes (free tier) |
| Security | Anonymous, for local demonstration only | Username, password and TLS |
| Used for | The default in Docker Compose, so anyone can run the project | Development on a laptop, and demonstrating a managed cloud broker |

**Why both.** The local broker makes the repository runnable by anyone with one command and no credentials. The cloud broker shows that the same code works against a real managed service. Switching between them changes only environment variables.

**Honest note.** Anonymous access on the local broker is acceptable for a demonstration, not for production. A production deployment would add authentication and TLS.

## 4. Python

Python is required by the project sheet. It was also the practical choice: libraries exist for MQTT (paho-mqtt), data handling (pandas), the dashboard (Streamlit), vector search (ChromaDB), embeddings (sentence-transformers) and the LLM client (ollama), so the whole system is written in one language.

The containers use Python 3.12 while the development laptop uses 3.13. Version 3.12 was chosen for the image because more of the packages publish ready-made Linux builds for it.

## 5. SQLite

**Why.** It is a single file that needs no server, and Python includes it. The database is created automatically on the first run, and the file can be opened with any SQLite viewer to show stored history.

**Alternatives considered.**

| Option | Why not (for now) |
|---|---|
| PostgreSQL | Better for many writers and large fleets, but needs a server container, credentials and more setup for no benefit at this size |
| InfluxDB or another time-series database | Excellent for sensor data, but it adds a new technology that the project sheet does not ask for |

**Trade-off.** SQLite handles one writer well. In Docker, only the subscriber writes, and the dashboard only reads, so this is fine. A larger fleet would justify moving to PostgreSQL, and only the storage code would change.

## 6. Streamlit

**Why.** It turns a Python script into a live web page with very little code, and it includes charts, metrics, tables and buttons. The dashboard refreshes automatically every 2 seconds.

**Alternatives that were not used.**

| Option | Why not |
|---|---|
| Grafana | Part of the previous (row 101) stack. It is excellent for time-series dashboards, but it cannot easily show an LLM explanation with a button and sources |
| Node-RED dashboard | Same: tied to the previous stack and a poor fit for the explanation panel |
| A custom web app | Far more work for the same result |

## 7. RAG: ChromaDB and sentence-transformers

**What RAG does here.** The maintenance knowledge is split into sections, and each section is converted into an embedding, a list of numbers that represents its meaning. When a fault happens, the symptom description is converted the same way, and the sections closest in meaning are retrieved. Only those sections are given to the LLM.

**Why it matters.** The LLM is told to answer only from the retrieved text. This keeps the answer tied to the knowledge base, and lets the dashboard show exactly which sections were used.

**Choices.**
- **ChromaDB** stores the embeddings in a local folder, with no server.
- **all-MiniLM-L6-v2** (sentence-transformers) is a small embedding model, about 90 MB, that runs on a normal CPU. It is downloaded once and cached.
- **Retrieval depth of 2 sections.** Enough to include a second possible fault without overloading a small model.

**Alternative considered: giving the LLM the whole knowledge file every time.** It works for five short sections, but it does not scale and it removes the retrieval step that the project sheet names.

## 8. Local LLM: Ollama with llama3.2:3b

**Why local.** Industrial operating data is often confidential. Running the model on the same machine means no sensor data, diagnosis or question is sent to an external service. There is also no API cost and no internet requirement at run time.

**Why Ollama.** It downloads and runs open models with one command and exposes a simple local API that Python can call.

**Why llama3.2:3b.** It is small (about 2 GB to download), fast on a laptop, and good enough to write a short structured explanation when it is given the relevant text. Two settings keep it reliable:
- A **low temperature** (0.2), for focused and repeatable answers.
- A prompt that **forbids guessing** and requires a fixed answer format.

The sources are added by the program from the retrieval results, not written by the model, so the model cannot invent a citation.

**Trade-off.** A larger model would write better explanations, at the cost of speed and memory. The model name is one setting, so changing it is easy.

**Alternative rejected: cloud LLM APIs.** They are stronger, but they break the local, private design and add cost.

## 9. Docker and Docker Compose

**Why.** The project has four moving parts (broker, simulator, subscriber, dashboard). Compose starts all four with one command, with the right settings, on any machine that has Docker. A single image is built once and reused by three of the services.

**Details worth knowing.**
- The PyTorch library, needed by the embedding model, is installed in its **CPU-only** build inside the image. This avoids downloading large GPU libraries and keeps the image much smaller.
- A shared **volume** lets the subscriber and the dashboard use the same database file.
- Ollama stays on the host, not in a container, so it can use the laptop's GPU. Containers reach it through `host.docker.internal`.

## 10. Deliberately left out

| Technology | Reason it is not used |
|---|---|
| Node-RED and Grafana | They belong to the previous stack (row 101), not row 100 |
| A trained ML model (for example Isolation Forest) | Not part of the row 100 stack, and rules are easier to explain. A model can replace the analyzer later without changing anything else |
| Real hardware (ESP32 and sensors) | Not required by the guide. The MQTT message format allows real sensors later |
| Kubernetes | Deferred. Docker Compose gives one-command deployment first, and Kubernetes manifests can be added afterwards |
| Streamlit Community Cloud | It can host only the dashboard, and cannot run the simulator and subscriber continuously, so it does not give an end-to-end deployment |