# 09. Dashboard

This document describes the web dashboard: what it shows, how its data gets to the page, how the AI explanation is triggered, and why it was built this way.

---

## 1. Purpose

The dashboard is where a technician or supervisor sees the turbine's state and acts on it. It answers four questions in order:

1. Is the turbine healthy right now? (status banner)
2. What are the values doing? (key numbers and charts)
3. What is probably wrong, and what should I check? (diagnosis)
4. Can you explain it? (Explain with AI)

It only reads data. It never writes to the database and never sends commands to the turbine.

## 2. Technology

The dashboard is a **Streamlit** application in `dashboard/app.py`. Streamlit turns a Python script into a web page with charts, metrics, tables and buttons, so the whole interface is written in Python with no separate front end. It runs at port 8501 (`http://localhost:8501`).

## 3. Layout

The page is a single screen, read from top to bottom:

| Section | Content |
|---|---|
| Title | Wind Turbine Fault Diagnosis Assistant |
| Status banner | Green **NORMAL**, yellow **WARNING** or red **CRITICAL** |
| Key values | Wind speed, power, gearbox oil temperature and vibration (latest reading) |
| Charts | Temperatures (four lines), vibration, and wind speed with power |
| Diagnosis | Out-of-range parameters, the most likely fault with its symptom match, probable causes, recommended checks, other possible faults, and the **Explain with AI** button |
| AI explanation | The written explanation and its sources, once requested |
| History | The latest ten diagnoses (time, status, top fault, symptom match) |

## 4. How data reaches the page

```
simulator -> MQTT -> subscriber -> SQLite database -> dashboard
```

The dashboard does not subscribe to MQTT. It reads the SQLite database that the subscriber fills. This keeps the dashboard simple, and it means the page shows history as well as live data, and still works if it is opened later.

Every 2 seconds, one function (`live`) runs again and does the following:

1. Reads the latest 120 readings from the `readings` table, which is about two minutes of data.
2. Takes the newest reading and runs the analyzer on it (`full_analysis`), the same function the subscriber uses, so the page and the stored diagnoses always agree.
3. Draws the banner, numbers, charts and diagnosis.
4. Reads the latest ten rows from the `diagnoses` table for the history.

Only this function refreshes, so the title and the rest of the page do not flicker. The database location comes from the `DB_PATH` environment variable, which is how the dashboard and the subscriber share one file in Docker.

If there is no data yet, the page shows a message asking for the simulator and the subscriber to be started.

## 5. The sections in detail

### 5.1 Status banner

The overall status from the analyzer: the most severe status of any parameter. It is the quickest signal on the page, and it is colour-coded for a glance from a distance.

### 5.2 Key values and charts

The four numbers are the latest values of the parameters that matter most for the main faults. The charts show the last 120 readings:

- **Temperatures:** gearbox oil, gearbox bearing, generator bearing and stator, on one chart so that a rising line is easy to spot.
- **Vibration.**
- **Wind speed and power,** on one chart.

### 5.3 Diagnosis

When the status is not normal, this section shows:

- The **out-of-range parameters**, with value, unit and status. This is the evidence.
- The **most likely fault**, with its symptom match percentage. The label says "symptom match" and not "confidence", because the number is a simple ratio and not a probability.
- **Probable causes** and **recommended checks** from the knowledge base, side by side.
- **Also possible:** the other ranked faults. Faults share symptoms, so showing the runner-up tells the technician what else to rule out.

When everything is within limits, the section simply says that no fault was detected.

### 5.4 Explain with AI

A button under the diagnosis. When clicked:

1. The page builds a short description of the current symptoms in plain words.
2. A spinner is shown while the retrieval and the local language model work.
3. The answer is shown under **AI explanation (local LLM + RAG)**, with the names of the knowledge sections used as sources.

The explanation stays on the page after it appears, even though the page keeps refreshing, because it is kept in the session. It does not update by itself when the fault changes, so the user clicks again for a new one.

The models are loaded the first time the button is clicked and reused afterwards, which is why the first click takes tens of seconds and later clicks only a few.

### 5.5 History

A table of the latest ten diagnoses. Because the subscriber stores a diagnosis for every abnormal reading, a fault that lasts a minute produces many rows. The table is useful for seeing how a fault developed, for example the symptom match rising from 50% to 100% as a second parameter crosses its limit.

## 6. Design decisions

| Decision | Reason |
|---|---|
| Read from the database, not from MQTT | Simpler, shows history, and works whenever the page is opened |
| Run the analyzer on the latest reading in the page | One function is the single source of truth for detection and diagnosis |
| Show the rule-based diagnosis immediately, AI explanation on request | The language model is slow, and a fault lasts many seconds. This also keeps the AI optional and under the user's control |
| Refresh only the live section every 2 seconds | Responsive without reloading the whole page |
| Keep the explanation in the session | Otherwise the next refresh would erase it |
| Show the evidence before the conclusion | A diagnosis that can be checked is more trustworthy |
| Label the percentage "symptom match" | Avoids implying statistical certainty |

## 7. Example: what a gearbox fault looks like

1. **Normal:** the banner is green, lines are flat, and the diagnosis section says no fault.
2. **First parameter crosses its limit:** the banner turns yellow. One symptom appears, such as gearbox oil temperature, and the top fault is Gearbox overheating at 50%.
3. **Second parameter crosses its limit:** gearbox bearing temperature joins, and the symptom match rises to 100%. Depending on the load, the banner may turn red when a critical limit is crossed.
4. **Explain with AI** produces a short written explanation naming the fault, the reason, the causes and the checks, with the sections used listed as sources.
5. **The fault ends:** the banner returns to green. The history keeps the rows.

## 8. Limitations and possible improvements

- **Chart scale.** Wind speed (about 8) and power (hundreds) share one chart, so the wind speed line looks flat. Separate charts, or a second axis, would fix this.
- **One turbine.** There is no turbine selector or fleet overview yet. These are planned with multi-turbine support.
- **Start-up timing.** If the page opens before the subscriber has created the database tables, it can show an error until the tables exist. Catching that case and showing a "waiting for data" message makes start-up smoother.
- **No automatic refresh of the explanation** when the fault changes.
- **No authentication.** Anyone who can reach port 8501 can view the page. This is acceptable for a demonstration, not for production.
- **No alerts.** The page shows problems but does not send notifications.
- **Screenshots** of the dashboard in normal, warning and critical states should be added to the report.