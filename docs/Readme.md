# Knowledge-Driven IoT Fault Diagnosis Assistant

An IoT fault diagnosis system for wind turbines. Turbine readings arrive over **MQTT**, a rule-based analyzer detects abnormal conditions, a knowledge base ranks the likely faults, and a **local LLM with RAG** explains the diagnosis in plain language, with sources, on a live dashboard. Everything runs on your own machine, and the whole system starts with one command using Docker.

**Stack:** MQTT, Python, Local LLM (Ollama), RAG (ChromaDB), Streamlit, SQLite, Docker.

---

## What it does

1. A **simulator** publishes a wind turbine reading every second (wind speed, power, generator speed, gearbox and generator temperatures, vibration) and can inject faults.
2. An **MQTT broker** carries the messages.
3. A **subscriber** stores every reading in SQLite and runs the **analyzer**.
4. The analyzer compares each value with warning and critical limits, then ranks the likely faults from a knowledge base, with their causes and recommended checks.
5. The **dashboard** shows live charts, the status, the diagnosis and the history.
6. The **Explain with AI** button retrieves the relevant knowledge sections (RAG) and asks a local LLM to write an explanation, and it shows which sections were used as sources.

Detection is rule-based on purpose. The LLM only explains a problem the rules have already found, and it is told to answer only from the retrieved text.

![Architecture](docs/architecture.svg)

## Quick start (Docker)

### Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker with the Compose plugin)
- [Ollama](https://ollama.com/download), with the model downloaded once:

```bash
ollama pull llama3.2:3b
```

- About 16 GB of RAM is recommended. Internet access is needed on the first run only, to download images and a small embedding model.

### Run

```bash
git clone https://github.com/<your-username>/<repository-name>.git
cd <repository-name>
docker compose up --build
```

Then open **http://localhost:8501**.

The first start takes a few minutes while the images are built and the embedding model is downloaded. Stop everything with `Ctrl + C`, then:

```bash
docker compose down
```

No accounts, passwords or API keys are needed. The Docker setup uses a local Mosquitto broker.

## Using the dashboard

| Part of the page | What it shows |
|---|---|
| Status banner | Green (normal), yellow (warning) or red (critical) |
| Key values and charts | Wind speed, power, temperatures and vibration, refreshed every 2 seconds |
| Diagnosis | The out-of-range parameters, the most likely fault with its symptom match, probable causes and recommended checks, and other possible faults |
| **Explain with AI** | A written explanation from the local LLM, with the knowledge sections used as sources. The first click is slow because the models load |
| History | The latest diagnoses |

The "symptom match" percentage is the share of a fault's expected symptoms that are present. It is not a statistical probability.

## Controlling the simulator

The simulator has two modes:

- **Auto mode** switches to a different fault every 25 seconds, so something is almost always visible. It is controlled by the `AUTO_FAULTS` setting in the simulator's environment in `docker-compose.yml` (`"true"` or `"false"`).
- **Manual mode.** Attach to the simulator container, type a number, and press Enter:

| Key | Mode |
|---|---|
| 0 | Normal operation |
| 1 | Gearbox overheating |
| 2 | Bearing wear |
| 3 | Generator overheating |
| 9 | Auto mode |

```bash
docker compose ps                  # find the simulator container name
docker attach <simulator-container-name>
```

Detach with `Ctrl + P` then `Ctrl + Q`. Do not use `Ctrl + C`, which stops the container.

## Running without Docker

Requires Python 3.12 or newer.

```bash
python -m venv venv
venv\Scripts\activate            # Windows. On Linux or macOS: source venv/bin/activate
pip install -r requirements.txt
```

Start a local broker and point the programs at it (PowerShell shown):

```powershell
docker compose up -d mosquitto
$env:MQTT_HOST="localhost"; $env:MQTT_PORT="1883"; $env:MQTT_TLS="false"
```

Build the knowledge index once, then start each program in its own terminal (with the virtual environment active and the same environment variables set):

```bash
python rag/build_index.py
python subscriber/subscriber.py
python simulators/sim1.py
streamlit run dashboard/app.py
```

Ollama must be running for the AI explanation.

## Configuration

Settings come from environment variables, so nothing secret is stored in the code.

| Variable | Meaning | Default in `config.py` |
|---|---|---|
| `MQTT_HOST` | Broker address | A cloud broker. Set it to `localhost` or `mosquitto` for a local broker |
| `MQTT_PORT` | Broker port | 8883 |
| `MQTT_TLS` | `true` or `false` | true |
| `MQTT_USER`, `MQTT_PASS` | Broker login, if any | Read from `local_secrets.py` if present |
| `DB_PATH` | SQLite database file | `iot_data.db` in the project folder |
| `OLLAMA_HOST` | Address of Ollama | Ollama's local default |
| `AUTO_FAULTS` | Simulator auto mode | false |

To use a cloud broker such as HiveMQ Cloud, create a file named `local_secrets.py` in the project folder with two lines, and set `MQTT_HOST`:

```python
MQTT_USER = "your-username"
MQTT_PASS = "your-password"
```

`local_secrets.py` is listed in `.gitignore` and `.dockerignore`, so it is never committed or copied into an image.

Limits and parameters are in `profiles/wind_turbine.json`. Fault knowledge is in `analyzers/knowledge.json` (ranking) and `knowledge/wind_turbine_faults.md` (text used for RAG). Edit these files to change the behaviour, with no code changes.

## Project structure

```
analyzers/        analyzer.py, knowledge.json
dashboard/        app.py (Streamlit)
docs/             project documents
knowledge/        wind_turbine_faults.md (text used for RAG)
mosquitto/config/ mosquitto.conf
profiles/         wind_turbine.json
rag/              build_index.py, explain.py
simulators/       sim1.py
subscriber/       subscriber.py
tests/            unit tests
config.py         settings and topics
mqtt_client.py    shared MQTT connection helper
Dockerfile
docker-compose.yml
requirements.txt
```

## MQTT topics

| Topic | Content |
|---|---|
| `iotfault/turbine/wt01/telemetry` | One sensor reading per second (JSON) |
| `iotfault/turbine/wt01/diagnosis` | A diagnosis, published when the status is not normal |

A real device can replace the simulator by publishing the same JSON to the telemetry topic.

## Tests

```bash
python -m unittest discover -s tests -v     # run the unit tests
python tests/run_tests.py                   # run them and record the results in docs/unit_test_results.md
```

System tests and their results are in [docs/11_Testing_and_Results.md](docs/11_Testing_and_Results.md).

## Documentation

| Document | Content |
|---|---|
| [01_SRS](docs/01_SRS.md) | Software Requirements Specification |
| [02_Project_Overview](docs/02_Project_Overview.md) | Problem, goal and design decisions |
| [03_System_Architecture](docs/03_System_Architecture.md) | Components and data flow |
| [Architecture_Diagram](docs/Architecture_Diagram.md) | Diagrams |
| [04_Technology_Choices](docs/04_Technology_Choices.md) | Why each tool was chosen |
| [05_Data_and_Simulation](docs/05_Data_and_Simulation.md) | Parameters, dataset and simulator |
| [06_MQTT_Messaging](docs/06_MQTT_Messaging.md) | Topics, messages and brokers |
| [07_Fault_Detection_and_Knowledge](docs/07_Fault_Detection_and_Knowledge.md) | Detection and the knowledge base |
| [08_RAG_and_Local_LLM](docs/08_RAG_and_Local_LLM.md) | Retrieval and the local language model |
| [11_Testing_and_Results](docs/11_Testing_and_Results.md) | Test cases and results |

## Troubleshooting

| Problem | What to do |
|---|---|
| Port 8501 or 1883 is already in use | Stop the other program using it, or change the port mapping in `docker-compose.yml` |
| The dashboard shows no data at first | Wait a few seconds, then check `docker compose logs subscriber` |
| **Explain with AI** fails inside Docker | Make sure Ollama is running and the model is downloaded. On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the dashboard service, and start Ollama with `OLLAMA_HOST=0.0.0.0` |
| `FileNotFoundError` for a JSON file in the container | File names are case-sensitive on Linux. Use lowercase names such as `wind_turbine.json` |
| First start is very slow | The embedding model and images are being downloaded, which happens once |

## Known limitations

- One turbine is monitored. Support for several turbines is planned.
- Detection is rule-based, with upper limits only, and the limits are initial estimates that are to be calibrated with real data.
- Vibration is simulated because the public dataset has no vibration channel.
- Yaw misalignment is described in the knowledge text but cannot be detected yet.
- The local broker allows anonymous access, which is for demonstration only.

## Data source and credits

The parameter selection is based on the public **CARE to Compare** wind turbine dataset by Fraunhofer IEE (C. Güück, C. M. A. Roelofs and S. Faulstich), licensed under CC BY-SA 4.0. The dataset itself is not included in this repository.

---

Author: Sujal Kumar