# 02. Project Overview

**Project:** Knowledge-Driven IoT Fault Diagnosis Assistant for Wind Turbines
**Stack:** MQTT, Python, Local LLM, RAG (with Docker for deployment)

This document explains what the project is, why it was shaped the way it was, and what it deliberately does not do. Later documents go into each part in detail.

---

## 1. The problem

A wind turbine produces a constant stream of sensor readings: gearbox temperatures, generator temperatures, vibration, rotor speed, power output. When one value drifts out of range, a monitoring screen can show an alarm. But an alarm alone does not help the person who has to respond. The technician still has to answer three questions:

1. What is probably wrong?
2. Why might it be happening?
3. What should I check first?

The answers usually sit in maintenance manuals and in the experience of senior engineers. They are not connected to the live data. The result is slow diagnosis, and a lot of depends-who-is-on-shift.

## 2. The goal

Build a system that connects live IoT telemetry to maintenance knowledge, so that an abnormal reading produces not just an alarm but an **explained diagnosis**: the likely fault, the reason, the probable causes and the recommended checks, with the source of that advice shown.

In one sentence:

> Receive machine data over MQTT, detect abnormal behaviour, look up the likely fault in a knowledge base, and use a local LLM with retrieval (RAG) to explain it in plain language, with sources, on a live dashboard.

## 3. Where the project came from

The project did not start in its final form. Recording the path matters, because each change had a reason.

| Stage | Idea | What changed it |
|---|---|---|
| 1 | A general IoT platform with Node-RED, ML and Grafana | The project sheet was checked again, and the intended row turned out to be row 100, not row 101 |
| 2 | Cold storage or factory pump monitoring | The title "Knowledge-Driven IoT Fault Diagnosis Assistant" put the focus on explaining faults, not just detecting them |
| 3 | A small fan with an ESP32 and sensors | The guide said hardware is not required and that simulated data is acceptable |
| 4 | Wind turbine | The guide suggested it. It has rich public maintenance knowledge and a real public dataset |

The final specification comes from row 100 of the project sheet:

| Field | Value |
|---|---|
| Sub-domain | Industrial Support |
| Tech stack | MQTT + Python + Local LLM + RAG |
| Objective | Provide AI-assisted IoT fault diagnosis |
| Description | Combine IoT telemetry, a searchable knowledge base and a local RAG/LLM system to explain likely faults and recommended checks |

## 4. Why a wind turbine

- **The guide suggested it**, and it fits the assignment well.
- **Faults are well understood.** Gearbox overheating, bearing wear and generator overheating are documented failure modes, so a knowledge base can be written and checked.
- **A real dataset exists.** The CARE to Compare SCADA dataset (Fraunhofer IEE, three wind farms, 36 turbines, labelled anomaly events) shows which sensors a real turbine has and supports later calibration.
- **It is easy to explain** to people who are not engineers.

## 5. Key design decisions

### 5.1 Rules detect, the LLM explains

The system separates two jobs:

- **Detection** (is something wrong?) is done by simple, testable rules: each parameter is compared with warning and critical limits.
- **Explanation** (what, why, what to check?) is done by the knowledge base and the local LLM.

This was a deliberate choice. An LLM can sound confident and be wrong, so it is never allowed to decide whether a fault exists. If the rules say everything is normal, the LLM is not consulted. Because of this, every alarm can be traced to a number and a limit, which makes the system explainable and easy to defend.

### 5.2 No machine learning model in the detector

The project sheet for row 100 lists MQTT, Python, a local LLM and RAG. It does not list an ML model, so none is used. This also keeps the system simple and predictable. The detector is a single function with a fixed input and output, so a trained model could replace it later without changing the rest of the system.

### 5.3 Everything local

The LLM (through Ollama) and the embedding model run on the same machine as the project. No sensor data and no diagnosis is sent to a cloud AI service. This matters for industrial users, whose operating data is often confidential.

### 5.4 Simulated data first, real sensors possible later

No hardware is needed. A simulator publishes turbine readings in the same JSON format a real device would use. Because everything downstream only sees MQTT messages, a real device could replace the simulator without changing the analyzer, the database or the dashboard.

### 5.5 Knowledge is data, not code

Limits live in a machine profile file, fault knowledge lives in a knowledge file, and RAG documents live in a Markdown file. Adding a fault or changing a limit means editing a data file, not rewriting code. This is what makes the assistant "knowledge-driven".

### 5.6 Packaged to run anywhere

The system is packaged with Docker Compose, so anyone who clones the repository can start it with one command, without installing Python packages by hand.

## 6. What the system does, end to end

```
Simulator publishes a reading every second
        |  (MQTT)
        v
Subscriber receives it and saves it to the database
        |
        v
Analyzer compares each parameter with its limits
        |
        v
If a limit is crossed: rank likely faults from the knowledge base,
store the diagnosis and publish it on MQTT
        |
        v
Dashboard shows status, symptoms, causes and checks.
On request, RAG + local LLM write an explanation and cite their sources.
```

## 7. Objectives

| # | Objective | How it is checked |
|---|---|---|
| 1 | Each injected fault is detected within seconds of appearing | Auto-fault mode, observed on the dashboard (to be recorded in the testing document) |
| 2 | Every alarm shows which parameters triggered it and their limits | Visible in the diagnosis panel |
| 3 | Every AI explanation cites its knowledge sources | Visible under the explanation |
| 4 | No data leaves the machine for AI processing | Local Ollama and local embeddings |
| 5 | The system starts with a single command | `docker compose up` |
| 6 | Limits and knowledge can change without code changes | Edit the profile or knowledge files |

## 8. Scope

**In scope:** simulated telemetry for one turbine, MQTT messaging, storage, rule-based detection, knowledge-base ranking, RAG with a local LLM, a web dashboard, and Docker packaging.

**Not in this version:**

- Physical sensors
- A trained ML model
- Automatic control actions on the turbine
- Monitoring several turbines at once (planned, and requested by the guide)
- Cloud-hosted AI

## 9. Honest limitations

- The warning and critical limits are **initial estimates**. They should be calibrated with the real dataset.
- Vibration is **simulated**, because SCADA data has no vibration channel.
- The "symptom match" percentage is a simple ratio of matched symptoms to total symptoms for a fault. It is **not a statistical probability**.
- A rule-based detector only sees faults that push a value past its limit. Faults such as yaw misalignment (low power for the wind speed, with every value in range) need an additional check that is not built yet.
- The knowledge text was written from general maintenance knowledge and should be reviewed against real manuals.

## 10. How the rest of the documents fit

| Document | Covers |
|---|---|
| 03 System Architecture | The components and how data moves between them |
| 04 Technology Choices | Why each tool was chosen, and what was rejected |
| 05 to 09 | Data, messaging, detection, RAG and the dashboard in detail |
| 10 Docker Deployment | Containers and how to run the system |
| 11 to 14 | Testing, setup guide, problems solved, and future work |