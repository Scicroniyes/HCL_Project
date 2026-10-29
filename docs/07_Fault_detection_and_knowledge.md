# 07. Fault Detection and Knowledge Base

This document explains how the system decides that something is wrong, how it works out which fault is the most likely, and how the knowledge base is organised. This is the "knowledge-driven" core of the project.

---

## 1. Two questions, two steps

| Question | Answered by | Based on |
|---|---|---|
| Is something wrong right now? | **Detection** | Limits in the machine profile |
| What is it probably, and what should be checked? | **Diagnosis** | The fault knowledge base |

Both steps are plain, deterministic code, so the same reading always gives the same result. The language model is not involved here. It is used afterwards, only to explain a diagnosis that has already been made.

All of this lives in `analyzers/analyzer.py`, which has no knowledge of MQTT, the database or the dashboard. It takes a reading and returns a result, which makes it easy to test on its own and easy to replace later.

## 2. Detection

For every parameter in the machine profile, the analyzer compares the current value with two limits:

| Condition | Parameter status |
|---|---|
| Value at or above the critical limit | **critical** |
| Value at or above the warning limit | **warning** |
| Otherwise | normal |

**Overall status.** The overall status is the most severe status of any parameter: one critical parameter makes the turbine critical, one warning makes it a warning, and no out-of-range parameters means normal.

**Symptoms.** Each parameter that is not normal becomes a *symptom*, recorded with its name, label, value, unit and status. The symptom list is the evidence that every later step builds on.

**Why warning and critical.** The two levels mirror how maintenance works. A warning means "look at this soon", and a critical level means "act now". The dashboard shows the overall status as a green, yellow or red banner.

### Properties and limits of this method

- **Transparent.** Every alarm can be traced to a value and a limit.
- **Only upper limits are checked.** A reading that is abnormally low, for example generator speed dropping to zero, is not flagged. The normal ranges in the profile are descriptive and are not used for detection yet.
- **Each reading is judged on its own.** One noisy reading above a limit raises an alarm. A future improvement is to require several consecutive readings.
- **Fixed limits ignore context.** A temperature that is fine at full load may be too high at low load. A model of expected values given the current load would improve this.
- **Limits are estimates** until they are calibrated with real data.

## 3. The knowledge base

The expert knowledge is stored as data, in `analyzers/knowledge.json`, not written into the code. Each entry describes one fault:

| Field | Meaning |
|---|---|
| `id` and `name` | Identifier and display name |
| `symptoms` | The parameters that tend to be out of range when this fault happens |
| `causes` | Probable causes |
| `checks` | Recommended checks for a technician |
| `severity` | How serious the fault is (stored for display and future use, not used for ranking) |

### The four faults

| Fault | Symptom parameters | Severity |
|---|---|---|
| Gearbox overheating | gearbox_oil_temp, gearbox_bearing_temp | high |
| Bearing wear | vibration, gearbox_bearing_temp | high |
| Generator overheating | gen_bearing_temp, stator_temp | high |
| Excessive vibration | vibration | medium |

**Adding a fault** means adding an entry to the file. No code changes are needed. This is what makes the assistant knowledge-driven: its expertise is data that can be reviewed, corrected and extended by someone who is not a programmer.

### A second form of the same knowledge

The same fault knowledge also exists as readable text in `knowledge/wind_turbine_faults.md`, with five sections (the four above plus yaw misalignment). This text is what the RAG component searches (see document 08). The structured file is used for ranking, and the text file is used for explanation.

**Consistency note.** The two files have to be kept in step by hand. Some names differ slightly (for example "Bearing wear" in the structured file and "Gearbox bearing wear" in the text), and yaw misalignment exists only in the text, because the detector cannot find it yet.

## 4. Diagnosis: ranking the faults

Given the list of symptoms, the analyzer compares it with every fault in the knowledge base:

1. For each fault, count how many of its symptom parameters are currently out of range. These are the **matched symptoms**.
2. Ignore faults with no matches.
3. Compute the **symptom match** for each remaining fault: matched symptoms divided by the total symptoms for that fault, as a percentage.
4. Sort the faults by number of matched symptoms first, and by symptom match second.

The first fault in the list is the **most likely fault**, and the others are shown as "also possible". The output for each candidate includes its name, symptom match, matched parameters, causes, checks and severity.

### Worked examples

These come from the analyzer's built-in self-test, which uses made-up readings:

| Reading | Status | Result |
|---|---|---|
| Oil 55 °C, vibration 1.2 | normal | No fault |
| Oil 85 °C, gearbox bearing 90 °C | critical | 1. Gearbox overheating, 100% (two of two symptoms). 2. Bearing wear, 50% (one of two) |
| Vibration 5.0 mm/s only | warning | 1. Excessive vibration, 100%. 2. Bearing wear, 50% |

A further case, a bearing wear fault where both vibration and gearbox bearing temperature are out of range, would rank Bearing wear first (two matches), Excessive vibration second (one match, 100%) and Gearbox overheating third (one match, 50%).

**Why a ranked list.** Faults share symptoms. The gearbox bearing temperature belongs to two of them. Showing a ranked list with its evidence is more honest than naming a single answer, and it shows the technician what else to rule out.

## 5. What the symptom match means, and what it does not

The percentage is the share of a fault's expected symptoms that are present. It is **not a probability**, and it should not be described as accuracy or confidence in the statistical sense. In particular:

- A fault with only one symptom parameter (such as Excessive vibration) always scores 100% when that parameter is out of range, even though the evidence is weak.
- It does not consider how far past the limit a value is.
- It does not consider how common each fault is.

For this reason the dashboard labels it "symptom match", and the matched parameters are always shown beside it, so the number can be checked against the evidence.

## 6. Explainability

Every diagnosis can answer the question "why?":

- Which parameters were out of range, with their values, units and limits (the symptoms).
- Which of each fault's symptoms matched, and how the ranking was reached.
- Which causes and checks the knowledge base lists for it.

All of this is stored with the diagnosis in the database (symptoms and ranked faults as JSON), together with the simulator's ground-truth label. That stored record is what makes later analysis possible, such as examining where the diagnosis agreed or disagreed with the true fault.

## 7. Flow of one reading

```
reading
   |
   v
analyze():  compare each parameter with its limits
   |        -> overall status + list of symptoms
   v
diagnose(): compare symptoms with each fault in the knowledge base
   |        -> ranked list of faults with causes and checks
   v
full_analysis() returns: status, symptoms, ranked diagnoses
```

The subscriber stores a diagnosis row for every reading that is not normal, so a fault that lasts a minute produces about sixty rows. The dashboard shows the latest ten.

## 8. Extending the system

| Change | What to edit |
|---|---|
| New limit or a different turbine | The profile file |
| New fault | An entry in the knowledge file, plus a section in the text document for RAG |
| New parameter | The profile file, plus the database columns and the list of stored fields in the subscriber, because storage has a fixed set of columns |
| A different detection method, for example a trained ML model | Replace the inside of `analyze()` while keeping the same inputs and outputs |

## 9. Known gaps

- **Yaw misalignment cannot be detected.** Its signature is power that is too low for the wind speed while every sensor value looks normal. It needs a power curve check, for example comparing power with the expected power for the current wind speed. This is planned.
- **Low values are not checked**, and there is no persistence rule against noise.
- **The knowledge content** was written from general maintenance knowledge and should be reviewed against manufacturer manuals and service guides.