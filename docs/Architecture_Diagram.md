# Architecture Diagrams

This file collects the diagrams of the system. The text description of each component is in `03_System_Architecture.md`.

The Mermaid diagrams below are drawn automatically by GitHub and by VS Code's Markdown preview. A ready-made image of the main diagram is in `architecture.svg`, for tools that do not draw Mermaid and for use in reports.

---

## 1. System architecture

![System architecture](architecture.svg)

The same diagram in Mermaid:

```mermaid
flowchart LR
    SIM["Simulator<br/>sim1.py (or real sensors)"]
    BROKER["MQTT broker<br/>Mosquitto / HiveMQ Cloud"]
    SUB["Subscriber service<br/>subscriber.py"]
    AN["Analyzer<br/>limits + fault ranking"]
    CFG[("Profile + knowledge<br/>wind_turbine.json, knowledge.json")]
    DB[("SQLite database<br/>readings, diagnoses")]
    DASH["Dashboard<br/>Streamlit :8501"]
    USER(["User<br/>web browser"])
    RAG["RAG<br/>ChromaDB + embeddings"]
    KB[("Knowledge document<br/>wind_turbine_faults.md")]
    LLM["Local LLM<br/>Ollama, llama3.2:3b"]

    SIM -- "telemetry (JSON, 1 per second)" --> BROKER
    BROKER -- "telemetry" --> SUB
    SUB -- "diagnosis (JSON)" --> BROKER
    SUB -- "reading" --> AN
    AN -- "status, symptoms, ranked faults" --> SUB
    CFG -- "read at start" --> AN
    SUB -- "save" --> DB
    DB -- "read every 2 s" --> DASH
    USER -- "views" --> DASH
    DASH -- "Explain with AI" --> RAG
    KB -- "indexed" --> RAG
    RAG -- "prompt + retrieved text" --> LLM
    LLM -- "explanation" --> RAG
    RAG -- "explanation + sources" --> DASH
```

## 2. Sequence of one diagnosis

```mermaid
sequenceDiagram
    participant S as Simulator
    participant B as MQTT broker
    participant U as Subscriber
    participant A as Analyzer
    participant D as SQLite
    participant W as Dashboard
    participant R as RAG
    participant L as Local LLM

    S->>B: publish telemetry (1 per second)
    B->>U: deliver telemetry
    U->>D: insert reading
    U->>A: full_analysis(reading)
    A-->>U: status, symptoms, ranked faults
    alt status is warning or critical
        U->>D: insert diagnosis
        U->>B: publish diagnosis
    end
    W->>D: read latest data (every 2 s)
    D-->>W: readings and diagnoses
    Note over W: user clicks Explain with AI
    W->>R: symptom description
    R->>R: embed text, find the 2 closest sections
    R->>L: prompt with the retrieved sections
    L-->>R: explanation
    R-->>W: explanation and the section names as sources
```

## 3. Deployment with Docker Compose

```mermaid
flowchart TB
    subgraph HOST["Host machine"]
        OLL["Ollama<br/>llama3.2:3b<br/>port 11434"]
        subgraph COMPOSE["Docker Compose network"]
            MOS["mosquitto<br/>port 1883"]
            SIMC["simulator"]
            SUBC["subscriber"]
            DASHC["dashboard<br/>port 8501"]
            VOL[("shared volume<br/>appdata: iot_data.db")]
            CACHE[("volume hfcache<br/>embedding model")]
        end
    end
    BROWSER(["Browser<br/>localhost:8501"])

    SIMC --> MOS
    MOS --> SUBC
    SUBC --> VOL
    VOL --> DASHC
    CACHE --- DASHC
    DASHC -- "host.docker.internal:11434" --> OLL
    BROWSER --> DASHC
```

The simulator, subscriber and dashboard are started from the same image, each with a different command.

## 4. Components at a glance

| Component | File | Role |
|---|---|---|
| Simulator | `simulators/sim1.py` | Publishes readings and injects faults |
| MQTT broker | Mosquitto container or HiveMQ Cloud | Delivers messages |
| Subscriber | `subscriber/subscriber.py` | Stores readings, runs the analyzer, publishes diagnoses |
| Analyzer | `analyzers/analyzer.py` | Detects abnormal values and ranks faults |
| Database | `iot_data.db` (SQLite) | Stores readings and diagnoses |
| RAG | `rag/build_index.py`, `rag/explain.py` | Indexes and retrieves knowledge, requests the explanation |
| Local LLM | Ollama | Writes the explanation |
| Dashboard | `dashboard/app.py` | Shows everything and triggers the explanation |
