# 14. Limitations and Future Work

This document lists what the system does not do yet, why that matters, and how each gap could be closed. It is written to be honest about the current state, and to give a clear plan for what comes next.

---

## 1. Limitations

### 1.1 Data

| Limitation | Effect |
|---|---|
| All data is simulated | The pipeline is shown to work, but performance on a real turbine is not demonstrated |
| Vibration is always simulated | The public dataset has no vibration channel, so it would stay simulated even after calibration |
| Limits are initial estimates | They are plausible, but not calibrated against real operating data |
| Simulator readings come every second, real SCADA data every 10 minutes | The timing of real data is very different from the simulated stream |
| The simulated power curve peaks at about 1000 kW, while the profile's normal range goes up to 2000 kW | The simulator and the profile are not fully consistent |
| Only one turbine | The system cannot compare or monitor several machines |

### 1.2 Detection

| Limitation | Effect |
|---|---|
| Only upper limits are checked | A value that is too low, such as rotor speed falling to zero, is not flagged |
| Fixed limits ignore the operating condition | A temperature that is fine at full load may be too high at low load |
| Every reading is judged on its own | One noisy value can raise an alarm, and there is no rule such as "three readings in a row" |
| Faults that leave every value in range are invisible | Yaw misalignment, with low power for the wind speed, cannot be detected |
| Detection is rule-based | It cannot learn new patterns from data |

### 1.3 Diagnosis and knowledge

| Limitation | Effect |
|---|---|
| The symptom match is a ratio, not a probability | A fault with a single symptom always scores 100% when that symptom appears |
| Only four faults are ranked, and five are described in the text | The coverage of real turbine faults is small |
| The knowledge was written from general maintenance knowledge | It should be reviewed against manufacturer manuals and service guides |
| Two forms of the same knowledge | The structured file and the text document are kept in step by hand, and names already differ slightly |
| Severity is stored but not used | It plays no part in ranking or alerting |

### 1.4 AI explanation

| Limitation | Effect |
|---|---|
| A small model (3 billion parameters) | It can misread or add detail, even when told to use only the given text |
| The sources listed are the sections supplied to the model | The system does not check that each statement came from them |
| The explanation and the rule-based ranking are produced separately | They can occasionally name different faults |
| The explanation does not refresh by itself | The user has to click again when the fault changes |
| The first request is slow | Models load on first use |
| Quality was checked on a few cases only | There is no systematic evaluation |

### 1.5 Platform and security

| Limitation | Effect |
|---|---|
| The local broker allows anonymous access and publishes its port | Suitable for a demonstration only |
| MQTT is used with delivery level 0 | A reading or alert can be lost without notice |
| The dashboard has no login | Anyone who can reach the port can view it |
| SQLite supports a single writer | It would not suit a large fleet |
| Ollama runs outside the containers | It must be installed separately, and Linux needs extra settings |
| No notifications | Problems appear on the page, but nobody is told |
| The dashboard can show an error if it starts before the database tables exist | It recovers on its own once the subscriber creates them |
| The wind speed line is flat on its chart | Wind speed and power share one scale |

## 2. Future work

### 2.1 Overview

| # | Improvement | What it adds | Effort (rough) | Priority |
|---|---|---|---|---|
| 1 | Multiple turbines | A fleet view, as requested by the guide | Medium | High |
| 2 | Calibrate limits and the simulator from real data, and replay real events | Realistic ranges, and a demonstration with real data | Medium | High |
| 3 | Link the rule-based diagnosis to the AI explanation | Consistent answers | Small | High |
| 4 | Power curve check | Detects yaw misalignment and underperformance | Small to medium | Medium |
| 5 | Better detection rules | Persistence, low limits, load-aware limits | Small to medium | Medium |
| 6 | Optional ML detector | Learns normal behaviour from data | Medium | Medium |
| 7 | Alert notifications | Someone is told about a problem | Small to medium | Medium |
| 8 | Real sensors | A physical demonstration | Medium to large | Optional |
| 9 | Deployment: container registry, cloud virtual machine, Kubernetes | A deployment beyond one laptop | Medium | As required |
| 10 | Security hardening | Authentication and encryption | Small to medium | Before any real use |
| 11 | Automated tests and a build pipeline | Tests run on every change | Small | Medium |

Effort figures are rough estimates, not measurements.

### 2.2 Details

**1. Multiple turbines.** Each turbine publishes to its own topic (`iotfault/turbine/wt02/telemetry`, and so on). The subscriber listens with a wildcard (`iotfault/turbine/+/telemetry`) and reads the turbine identifier. The database tables get a turbine column, the analyzer runs per turbine, and the dashboard gets a fleet overview with one status tile per turbine and a selector for the detail view. The simulator would run several instances with different identifiers and fault schedules. The message format already contains a machine identifier.

**2. Calibration and replay.** Read the normal-status rows of the public CARE to Compare data for Wind Farm A, and compute typical values, spread and limits for each mapped parameter. Convert power from energy per interval to kilowatts after checking the dataset documentation. Replace the placeholder limits, and fit simple relationships such as temperature as a function of power, so that the simulator produces more realistic data. Then publish a stretch of real, labelled data through the system as a demonstration.

**3. Linking diagnosis and explanation.** Pass the top-ranked fault and its matched symptoms into the language model's prompt, so the explanation is about the same fault the dashboard reports. A further step is to check automatically that the explanation mentions the fault named by the rules.

**4. Power curve check.** Compare actual power with the power expected for the current wind speed, using the curve from the data. A gap that persists while all temperatures are normal would point to yaw misalignment or blade problems. This adds a derived parameter to the profile.

**5. Better detection rules.** Require a limit to be exceeded for several readings in a row. Add low limits where they matter, such as generator speed. Make temperature limits depend on load, for example by comparing the temperature with the expected value for the current power.

**6. Optional ML detector.** An Isolation Forest, or a model that predicts a temperature from the load and flags large differences, trained on normal data only. It would sit behind the same analysis function, so the knowledge base, RAG and dashboard would not change. It is not required by the project sheet, and it should only be added after the simulator has been calibrated, otherwise the model and the simulator disagree about what normal is.

**7. Alerts.** Send a message (for example through email or a messaging service) when the status reaches critical. Because diagnoses are already published on an MQTT topic, a separate small service can subscribe and notify, without changing the core system.

**8. Real sensors.** An ESP32 with temperature and vibration sensors, fixed to a small fan or motor, publishing the same JSON to the telemetry topic. The rest of the system is unchanged. Parameters that the hardware cannot provide would stay simulated.

**9. Deployment.** Publish the built image to the GitHub Container Registry so users can pull it without building. For a full deployment, run the Compose file on a cloud virtual machine with Ollama installed. A Kubernetes deployment needs a deployment per service, a persistent volume, a service for the dashboard, and a way to reach a language model. The database should move from SQLite to a server database first.

**10. Security.** Add a username and password and TLS to the local broker, remove the exposed port, add a login to the dashboard, and use delivery level 1 for alerts.

**11. Automated tests and a pipeline.** The unit tests already exist. A GitHub Actions workflow could run them on every push, and could also build the Docker image to catch problems early.

## 3. Suggested order

```
1. Link diagnosis and explanation          (small, improves consistency)
2. Multiple turbines                       (requested by the guide)
3. Calibration and a real-data replay      (answers "use a dataset")
4. Power curve check and better rules      (closes the main detection gaps)
5. Alerts, security, deployment            (towards real use)
6. Optional ML detector and hardware       (extensions)
```

## 4. What this project demonstrates already

Even with these limits, the system shows a complete, working chain: data over MQTT, storage, rule-based detection, a knowledge base that ranks faults with evidence, a retrieval-grounded local language model that explains the result with sources, a live dashboard, automated unit tests, and a one-command Docker deployment. Every limitation above is either a clear next step or a deliberate choice, and none changes the design of the pipeline.