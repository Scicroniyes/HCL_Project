
# 05. Data and Simulation

This document explains what data the system works with, where the parameters come from, and how the simulator produces realistic normal readings and gradual faults.

---

## 1. Why a simulator

The project needs a steady supply of turbine readings, including faults that can be triggered on demand. A real turbine cannot be made to overheat for a demonstration, and the guide confirmed that hardware is not required. A simulator solves both problems:

- Readings arrive at a steady rate, every second.
- Any fault can be started at any moment, so every part of the system can be tested.
- Each reading carries a label (`sim_fault`) saying which fault was active. This ground truth lets the analyzer's answer be checked against the truth, which supports testing and explainability work.
- The simulator publishes the same JSON a real device would, so real sensors can replace it later with no change to the rest of the system.

## 2. The turbine profile

The machine is described in `profiles/wind_turbine.json`. It lists each parameter with a label, unit, normal range, warning limit and critical limit, and the name of the matching column in the real dataset. The analyzer and the dashboard read their limits from this file, so nothing about the turbine is hard-coded in the analysis code.

## 3. The eight parameters

| Parameter | Unit | Normal range | Warning at | Critical at | Dataset column |
|---|---|---|---|---|---|
| wind_speed | m/s | 3 to 15 | 20 | 25 | `wind_speed_3_avg` |
| active_power | kW | 0 to 2000 | 2200 | 2400 | `sensor_45_avg` + `sensor_46_avg` |
| generator_rpm | rpm | 0 to 1700 | 1800 | 1900 | `sensor_18_avg` |
| gearbox_oil_temp | °C | 35 to 65 | 70 | 80 | `sensor_12_avg` |
| gearbox_bearing_temp | °C | 40 to 70 | 78 | 88 | `sensor_11_avg` |
| gen_bearing_temp | °C | 35 to 70 | 80 | 90 | `sensor_13_avg` |
| stator_temp | °C | 40 to 100 | 120 | 140 | `sensor_15_avg` |
| vibration | mm/s | 0.3 to 2.5 | 4.5 | 7.0 | none (simulated) |

**Important:** the limits are initial estimates chosen to be plausible for a megawatt-class turbine. They have not yet been calibrated against the real data. This is listed as future work.

## 4. The real dataset: CARE to Compare

**What it is.** A public wind turbine anomaly detection dataset published by Fraunhofer IEE (C. Güück, C. M. A. Roelofs and S. Faulstich), under the licence CC BY-SA 4.0. It contains real operating data from 36 turbines in three wind farms, recorded every 10 minutes, with labelled anomaly events.

**How it was used so far.**

- **Choosing the parameters.** The dataset's feature description file lists what each anonymised column (such as `sensor_12`) measures. From it, the eight parameters above were chosen and mapped to real columns: wind speed, generator speed, gearbox oil temperature, gearbox bearing temperature, generator bearing temperature, stator winding temperature and active power.
- **Deriving active power.** The dataset has separate active power columns for the generator connected in star and in delta configuration. These two columns are to be combined into one `active_power` value.

**Points to confirm when the data is processed.**

- The dataset reports power as energy per 10-minute interval (watt-hours). The conversion to average kilowatts has to be checked against the dataset documentation.
- Only Wind Farm A has been examined, because the sensors differ between farms.
- The dataset has no vibration column, so vibration stays simulated. This is stated openly in the project.

**How it will be used next.**

1. Calibrate the limits and normal ranges from the normal-status rows.
2. Check how temperatures change with power, to make the simulator more faithful.
3. Replay a real labelled event through the system as a demonstration with real data.

## 5. How the simulator creates normal behaviour

The simulator avoids random jumps. Real turbine values drift smoothly, so each value moves a small step per second towards a target, and new targets are chosen from time to time.

**Smooth movement.** Every second, each parameter moves towards its target by at most a fixed step (for example 0.3 °C for gearbox temperatures, 0.15 m/s for wind speed). With a 5% chance each second, a new set of targets is chosen, which models a change in operating conditions.

**New targets** are generated like this:

| Parameter | How its target is chosen |
|---|---|
| wind_speed | Random between 5 and 12 m/s |
| active_power | A cubic function of wind speed, as in a real power curve: `(wind / 12)^3 × 1000` kW |
| load | Power divided by 1000, a value between 0 and 1 |
| generator_rpm | Random between 1400 and 1600 |
| gearbox_oil_temp | `48 + 15 × load` |
| gearbox_bearing_temp | `55 + 14 × load` |
| gen_bearing_temp | `50 + 15 × load` |
| stator_temp | `60 + 20 × load` |
| vibration | Random between 0.8 and 2.0 |

**Why temperatures depend on load.** In a real turbine, temperatures rise when it works harder. If they did not, a normal high-wind period would look the same as a fault. Tying temperatures to load makes the data more realistic and the diagnosis task more meaningful.

**Simplifications.**

- The power curve is a plain cubic, so power peaks at about 1000 kW rather than levelling off at rated power.
- Vibration is random and does not depend on load.
- No measurement noise is added beyond the smooth drift.

## 6. How faults are injected

A fault is applied on top of the normal values, and it grows gradually, as real faults do. A **ramp** value rises from 0 to 30 over a ramp period, and each fault adds its effect multiplied by the ramp.

| Fault | Effect at full ramp (ramp = 30) |
|---|---|
| gearbox_overheat | Gearbox oil temperature +30 °C, gearbox bearing temperature +36 °C |
| bearing_wear | Vibration +4.5 mm/s, gearbox bearing temperature +15 °C |
| generator_overheat | Generator bearing temperature +30 °C, stator temperature +54 °C |

**Ramp period.** The ramp takes 30 seconds in manual mode and 10 seconds in auto mode, so that auto mode shows a fault quickly.

**What this means for detection.** Because the effects are gradual, the dashboard shows a progression: normal, then warning, then (for faults strong enough) critical. In the expected behaviour:

- Gearbox overheating crosses the warning limit within a few seconds in auto mode. Reaching the critical limit depends on the current load.
- Bearing wear raises vibration to between about 5.3 and 6.5 mm/s. This is above the warning limit (4.5) but below the critical limit (7.0), so bearing wear produces **warnings only**.
- Generator overheating reaches the warning limit for generator bearing temperature at or near full ramp, and the stator temperature crosses its limit at higher loads.

These timings are approximate and are to be confirmed in the testing document.

**Overlapping symptoms.** Bearing wear also raises the gearbox bearing temperature, which is one of the two symptoms of gearbox overheating. As a result, a bearing wear case can show gearbox overheating as a weaker second candidate. This overlap is realistic, and it is useful for explainability, because it shows why the system reports a ranked list and not a single answer.

## 7. Simulator modes

| Mode | How to start it | Behaviour |
|---|---|---|
| Normal | Run with no options | No fault |
| Fixed fault | Pass a fault name when starting | That fault, ramping up over 30 seconds |
| Manual switching | Type 0 (normal), 1 (gearbox), 2 (bearing) or 3 (generator) while it runs | Changes mode immediately and restarts the ramp |
| Auto | Set the environment variable `AUTO_FAULTS=true`, or type 9 | A random fault, changed every 25 seconds, with a 10-second ramp |

Auto mode exists so that a fault is visible almost all the time, for example when another person needs a continuous supply of diagnoses to examine.

## 8. Message format

The simulator publishes one JSON message per second on `iotfault/turbine/wt01/telemetry`:

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

**The ground-truth rule.** The `sim_fault` field exists only so results can be checked afterwards. The analyzer is written to ignore it, so its diagnoses are based on the sensor values alone, exactly as they would be with a real turbine.

## 9. Limitations of the simulated data

- It is generated from simple rules, so it shows the pipeline works, but it does not prove how the system would perform on a real turbine.
- The limits are estimates until calibrated.
- Only three fault patterns are simulated. The knowledge base also describes excessive vibration and yaw misalignment, but the simulator does not produce yaw misalignment, and the detector cannot find it yet.
- Real SCADA data is averaged over 10 minutes, whereas the simulator produces a reading every second. Values and timing are therefore not directly comparable.