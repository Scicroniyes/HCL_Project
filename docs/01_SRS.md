# Software Requirements Specification

**Knowledge-Driven IoT Fault Diagnosis Assistant for Wind Turbines using MQTT, RAG and a Local LLM**

Version 1.0 | 29 October 2026 | Prepared by: \[Your name\] | Project guide: \[Guide name\]

| Version | Date | Description |
| --- | --- | --- |
| 1.0 | 29 Oct 2026 | First complete draft |

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements of the Knowledge-Driven IoT Fault Diagnosis Assistant. It is written for the project guide, evaluators, developers and anyone who will deploy or maintain the system. It describes what the system shall do, not how the code is organised.

### 1.2 Scope

The system receives wind turbine telemetry over MQTT, stores it, detects abnormal conditions by comparing each reading with configurable limits, matches the symptoms against a fault knowledge base, and uses Retrieval-Augmented Generation (RAG) with a local Large Language Model (LLM) to explain the likely fault, its causes and the recommended checks, citing the knowledge sections used. Results are shown on a live web dashboard. The whole system is packaged as Docker containers so that it can be started with one command.

**In scope**

- Simulated telemetry for one wind turbine (wt01) with injectable faults
- MQTT messaging through a broker
- Storage of readings and diagnoses
- Rule-based fault detection and knowledge-base matching
- RAG plus local LLM explanation with source citations
- Web dashboard and containerised deployment

**Out of scope for this version**

- Physical sensors or hardware (the telemetry format allows them later)
- A trained machine learning model for detection
- Automatic control actions on the turbine
- Simultaneous monitoring of multiple turbines (planned)
- Any use of cloud-hosted LLMs

### 1.3 Definitions and abbreviations

| Term | Meaning |
| --- | --- |
| MQTT | Lightweight publish/subscribe messaging protocol used by IoT devices |
| Broker | Server that receives MQTT messages and forwards them to subscribers (Eclipse Mosquitto or HiveMQ Cloud) |
| Topic | Path-like name that labels an MQTT message, for example iotfault/turbine/wt01/telemetry |
| Telemetry | Sensor readings sent by a machine |
| SCADA | Supervisory control and data acquisition, the system that records turbine data |
| RAG | Retrieval-Augmented Generation: the LLM answers using passages retrieved from a knowledge base |
| LLM | Large Language Model, here a model run locally through Ollama |
| Embedding | Numeric vector that represents the meaning of a text, used for similarity search |
| Symptom | A parameter that is outside its normal limit |
| Symptom match | Matched symptoms divided by the total symptoms listed for a fault (not a statistical probability) |
| SRS | Software Requirements Specification |

### 1.4 References

- IEEE 830 and ISO/IEC/IEEE 29148, guidance on requirements specifications
- OASIS MQTT specification, version 3.1.1
- Documentation of Eclipse Mosquitto, HiveMQ Cloud, Ollama, ChromaDB, sentence-transformers (model all-MiniLM-L6-v2) and Streamlit
- C. Güück, C. M. A. Roelofs, S. Faulstich (Fraunhofer IEE), CARE to Compare: Wind Turbine Anomaly Detection Dataset, Zenodo, licence CC BY-SA 4.0

## 2. Overall Description

### 2.1 Product perspective

The system is a self-contained pipeline. A data source publishes readings to an MQTT broker. A subscriber service receives them, stores them, runs the analyzer and publishes any diagnosis. A dashboard reads the stored data and, on request, calls the RAG and LLM component.

```
Simulator (or future sensors)
      | MQTT telemetry
      v
MQTT broker (Mosquitto / HiveMQ Cloud)
      |
      v
Subscriber service ---> SQLite database (readings, diagnoses)
      |  uses                      ^
      v                            |
Analyzer (limits + knowledge base)  |
      | MQTT diagnosis             |
      v                            |
Dashboard (Streamlit) -------------+
      | on request
      v
RAG (ChromaDB + embeddings) ---> Local LLM (Ollama) ---> explanation + sources
```

### 2.2 Product functions

1. Receive turbine telemetry over MQTT
2. Store every reading with a timestamp
3. Compare each parameter with warning and critical limits
4. Rank candidate faults from a knowledge base
5. Publish and store each diagnosis
6. Explain a diagnosis in natural language with cited sources
7. Display live readings, status, diagnosis and history
8. Run the whole system with a single command

### 2.3 User classes

| User | Description | Main needs |
| --- | --- | --- |
| Maintenance technician | Responds to alerts | Clear fault name, probable causes, what to check |
| Plant supervisor | Oversees turbine health | Live status and fault history |
| System administrator | Deploys and maintains the system | Easy setup, configurable limits and knowledge |
| Evaluator | Reviews the project | Traceable, explainable decisions |

### 2.4 Operating environment

- Docker Desktop (Windows, macOS or Linux) with Docker Compose
- Ollama installed on the host with the model llama3.2:3b
- Recommended 16 GB RAM; a GPU is helpful but not required
- A modern web browser for the dashboard
- Internet access for the first run only, to download images and the embedding model

### 2.5 Design and implementation constraints

- The LLM shall run locally; no operational data is sent to a cloud LLM
- Technology stack: MQTT, Python, local LLM, RAG
- Telemetry is simulated; no physical hardware is required
- Project duration is limited to about one month

### 2.6 Assumptions and dependencies

- The broker is reachable from all services
- Ollama is running on the host before the AI explanation is requested
- The knowledge base content is accurate and reviewed by a domain expert
- Warning and critical limits are initial estimates until calibrated with real SCADA data

## 3. Functional Requirements

### 3.1 Data acquisition

- **FR-1** The system shall subscribe to the MQTT topic iotfault/turbine/wt01/telemetry and receive JSON messages.
- **FR-2** Each telemetry message shall contain machine\_id, a UTC timestamp and the parameters wind\_speed, active\_power, generator\_rpm, gearbox\_oil\_temp, gearbox\_bearing\_temp, gen\_bearing\_temp, stator\_temp and vibration.
- **FR-3** The simulator shall publish one reading per second.
- **FR-4** The simulator shall generate normal operation in which temperatures and vibration follow the load.
- **FR-5** The simulator shall inject the faults gearbox overheating, bearing wear and generator overheating, each developing gradually over a ramp period.
- **FR-6** The simulator shall support an automatic mode that switches between faults at regular intervals so that a fault is always visible.
- **FR-7** The simulator shall include a ground-truth label (sim\_fault) in each message, and the analyzer shall not use it.

### 3.2 Data storage

- **FR-8** The system shall store every received reading in a database table with its timestamp.
- **FR-9** The system shall store each diagnosis (time, status, top fault, symptom match, symptoms and ranked faults) in a separate table.
- **FR-10** The system shall create the database tables automatically on first start.

### 3.3 Fault detection

- **FR-11** The system shall load each parameter's label, unit, normal range, warning limit and critical limit from a machine profile file.
- **FR-12** For every reading the system shall classify each parameter as normal, warning or critical by comparing it with its limits.
- **FR-13** The system shall set the overall status to the most severe parameter status.
- **FR-14** The system shall list every out-of-range parameter as a symptom with its value, unit and status.
- **FR-15** Limits shall be changeable by editing the profile file, without changing source code.

### 3.4 Knowledge-based diagnosis

- **FR-16** The system shall keep fault knowledge (name, symptom parameters, causes, checks, severity) in a data file separate from the source code.
- **FR-17** The system shall compare the current symptoms with each fault and rank the faults by number of matched symptoms and symptom match percentage.
- **FR-18** The system shall return, for each candidate fault, its probable causes and recommended checks.
- **FR-19** When the status is not normal, the system shall publish the diagnosis to the topic iotfault/turbine/wt01/diagnosis and store it in the database.
- **FR-20** A new fault shall be addable by adding a knowledge entry, without changing source code.

### 3.5 RAG explanation

- **FR-21** The system shall split the maintenance knowledge document into sections and store their embeddings in a vector database.
- **FR-22** On user request, the system shall build a symptom description from the current readings and retrieve the most relevant knowledge sections.
- **FR-23** The system shall send the symptom description and the retrieved sections to a local LLM with the instruction to answer only from the provided text.
- **FR-24** The explanation shall state the likely fault, the reason, the probable causes and the recommended checks.
- **FR-25** The system shall display the names of the retrieved knowledge sections as the sources of the explanation.
- **FR-26** The system shall rebuild the vector index automatically when the dashboard container starts.

### 3.6 Dashboard

- **FR-27** The dashboard shall show the current status as Normal, Warning or Critical.
- **FR-28** The dashboard shall show key values: wind speed, power, gearbox oil temperature and vibration.
- **FR-29** The dashboard shall show live charts of temperatures, vibration, and wind speed with power.
- **FR-30** The dashboard shall show the out-of-range parameters, the most likely fault with its symptom match, causes and checks, and other possible faults.
- **FR-31** The dashboard shall provide an Explain with AI action that shows the LLM explanation and its sources.
- **FR-32** The dashboard shall show the latest diagnosis history.
- **FR-33** The dashboard shall refresh automatically every 2 seconds.

### 3.7 Deployment

- **FR-34** The system shall be packaged as Docker containers for the broker, simulator, subscriber and dashboard.
- **FR-35** The system shall start with a single command (docker compose up).
- **FR-36** Broker address, port, credentials and database path shall be configurable through environment variables.

## 4. External Interface Requirements

### 4.1 User interface

A single web page (Streamlit) with a status banner, key values, three charts, a diagnosis panel with the Explain with AI action, and a history table.

### 4.2 Software interfaces

| Interface | Purpose |
| --- | --- |
| MQTT broker (Mosquitto container or HiveMQ Cloud with TLS) | Message transport |
| SQLite | Storage of readings and diagnoses |
| ChromaDB | Vector storage and similarity search |
| sentence-transformers (all-MiniLM-L6-v2) | Embeddings |
| Ollama (llama3.2:3b) | Local LLM |

### 4.3 Communication interfaces

| Topic | Direction | Content |
| --- | --- | --- |
| iotfault/turbine/wt01/telemetry | Simulator to subscriber | Sensor reading (JSON) |
| iotfault/turbine/wt01/diagnosis | Subscriber to any listener | Status, symptoms and ranked faults (JSON) |

### 4.4 Hardware interfaces

None in this version. A physical device shall be able to replace the simulator by publishing the same JSON format to the telemetry topic.

## 5. Non-Functional Requirements

| ID | Category | Requirement |
| --- | --- | --- |
| NFR-1 | Performance | A reading shall be stored and analysed within 2 seconds of arrival |
| NFR-2 | Performance | The dashboard shall show a new status within 5 seconds of a reading arriving |
| NFR-3 | Performance | The AI explanation shall be returned within 60 seconds of the request once the models are loaded |
| NFR-4 | Reliability | Services shall restart automatically if they stop or start before the broker is ready |
| NFR-5 | Reliability | The dashboard shall not crash when the database is not ready yet |
| NFR-6 | Privacy | The LLM and embeddings shall run locally, with no operational data sent to external AI services |
| NFR-7 | Security | Credentials shall not be stored in the repository, and shall be supplied by environment variables or an ignored local file |
| NFR-8 | Explainability | Every diagnosis shall show the symptoms and limits that triggered it, and every AI explanation shall cite its sources |
| NFR-9 | Maintainability | Limits, knowledge entries and knowledge documents shall be editable as data files |
| NFR-10 | Portability | The system shall run on any machine with Docker, apart from the Ollama installation |
| NFR-11 | Usability | A user shall be able to read the status and recommended checks without technical training |

## 6. Data Design

**readings**: id, machine\_id, ts, wind\_speed, active\_power, generator\_rpm, gearbox\_oil\_temp, gearbox\_bearing\_temp, gen\_bearing\_temp, stator\_temp, vibration, sim\_fault

**diagnoses**: id, machine\_id, ts, status, top\_fault, confidence, symptoms (JSON), diagnoses (JSON), sim\_fault

**Machine profile** (profiles/wind\_turbine.json): parameter names, labels, units, dataset column names, normal ranges, warning and critical limits.

**Knowledge files**: analyzers/knowledge.json (structured fault entries used for ranking) and knowledge/wind\_turbine\_faults.md (text sections used for RAG).

## 7. Use Cases

| ID | Use case | Actor | Outcome |
| --- | --- | --- | --- |
| UC-1 | Monitor live status | Supervisor | Sees current status and trends |
| UC-2 | Review a diagnosis | Technician | Sees likely fault, causes and checks |
| UC-3 | Request an AI explanation | Technician | Gets a written explanation with sources |
| UC-4 | Review fault history | Supervisor | Sees past diagnoses |
| UC-5 | Update limits or knowledge | Administrator | Edits data files; behaviour changes without code changes |
| UC-6 | Deploy the system | Administrator | Runs docker compose up |

## 8. Limitations and Future Enhancements

**Current limitations**

- Detection is rule-based, so it can only find faults that push a parameter beyond its limit
- Faults such as yaw misalignment, where power is low for the wind speed while all values look normal, need a power-versus-wind check that is not implemented
- Symptom match is a simple ratio, not a probability
- Limits are initial estimates, and vibration is simulated because SCADA data has no vibration channel
- Only one turbine is handled

**Planned enhancements**

- Calibrate limits and the simulator from the CARE to Compare SCADA data, and replay real labelled events
- Support several turbines at once with a fleet view
- Add a power-curve check for underperformance faults
- Replace the simulator with real sensor devices
- Add broker authentication and TLS for the local broker
- Deploy on Kubernetes or a cloud virtual machine

## Appendix A. Sample telemetry message

```
{"machine_id": "wt01", "ts": "2026-10-29T10:15:00+00:00", "wind_speed": 8.1, "active_power": 312.4, "generator_rpm": 1490, "gearbox_oil_temp": 84.2, "gearbox_bearing_temp": 91.0, "gen_bearing_temp": 56.3, "stator_temp": 66.0, "vibration": 1.4, "sim_fault": "gearbox_overheat"}
```

## Appendix B. Sample diagnosis

- Status: Critical
- Symptoms: gearbox oil temperature 84.2 C (critical); gearbox bearing temperature 91.0 C (critical)
- Likely fault: Gearbox overheating, 100% symptom match
- Probable causes: low oil level or degraded oil; blocked oil cooler or failed cooling fan; excessive friction from worn gears or bearings
- Recommended checks: check oil level and condition; inspect the oil cooler and cooling fan; take an oil sample and look for metal particles
- Sources (AI explanation): Gearbox overheating; Gearbox bearing wear

## Appendix C. Parameters and initial limits

| Parameter | Unit | Dataset column | Warning | Critical |
| --- | --- | --- | --- | --- |
| wind\_speed | m/s | wind\_speed\_3\_avg | 20 | 25 |
| active\_power | kW | sensor\_45\_avg + sensor\_46\_avg | 2200 | 2400 |
| generator\_rpm | rpm | sensor\_18\_avg | 1800 | 1900 |
| gearbox\_oil\_temp | C | sensor\_12\_avg | 70 | 80 |
| gearbox\_bearing\_temp | C | sensor\_11\_avg | 78 | 88 |
| gen\_bearing\_temp | C | sensor\_13\_avg | 80 | 90 |
| stator\_temp | C | sensor\_15\_avg | 120 | 140 |
| vibration | mm/s | simulated | 4.5 | 7.0 |
