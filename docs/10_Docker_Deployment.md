# 10. Docker Deployment

This document explains how the system is packaged and run with Docker: the image, the four containers, how they are connected, and why each choice was made.

---

## 1. Goal

Anyone who clones the repository should be able to run the whole system with one command, with no Python setup, no accounts and no secrets:

```
docker compose up --build
```

## 2. The pieces

| Piece | File | Role |
|---|---|---|
| Image recipe | `Dockerfile` | Builds one image that contains Python, the libraries and the project code |
| Exclusions | `.dockerignore` | Keeps files out of the image |
| Orchestration | `docker-compose.yml` | Starts four containers from that image and the broker, and connects them |
| Broker settings | `mosquitto/config/mosquitto.conf` | Configuration for the broker container |

## 3. The image (`Dockerfile`)

The steps, in order:

1. **Start from `python:3.12-slim`,** a small Python image. Python 3.12 was chosen because more of the libraries publish ready-made builds for it on Linux than for 3.13, which is the version used on the development laptop.
2. **Install a CPU-only build of PyTorch first.** The embedding model needs PyTorch. The default Linux build downloads large GPU libraries that are not needed here, so the CPU build is installed explicitly, which keeps the image much smaller.
3. **Install the libraries** from `requirements.txt`.
4. **Copy the project code.**
5. **Set a default command** (the simulator). Compose overrides it for each service.

The libraries are installed before the code is copied. Docker caches each step, so when only the code changes, a rebuild reuses the installed libraries and takes seconds, not minutes.

### What is kept out of the image (`.dockerignore`)

| Excluded | Why |
|---|---|
| `venv/`, `__pycache__/`, `*.pyc` | Local Python files, useless in the image |
| `iot_data.db` | Local data. The container creates its own |
| `local_secrets.py` | **Credentials must never be baked into an image**, because anyone who pulls the image could read them |
| `rag_store/` | The index is generated inside the container at start-up |
| `.vscode/`, `.git/` | Editor and version-control files |

## 4. The containers (`docker-compose.yml`)

| Service | Built from | Command | Purpose |
|---|---|---|---|
| `mosquitto` | `eclipse-mosquitto:2` | (default) | MQTT broker on port 1883 |
| `simulator` | the project image | `python -u simulators/sim1.py` | Publishes turbine readings |
| `subscriber` | the project image | `python -u subscriber/subscriber.py` | Stores readings, runs the analyzer, publishes diagnoses |
| `dashboard` | the project image | builds the RAG index, then starts Streamlit | Web page on port 8501 |

The simulator, subscriber and dashboard use the **same image** and differ only in the command they run. That means one build and one set of libraries serve three services.

### 4.1 Environment variables

Each service gets its settings from environment variables, which the project's `config.py` reads. This is the mechanism that lets one codebase run both on a laptop and in containers without editing files.

| Variable | Value in Compose | Meaning |
|---|---|---|
| `MQTT_HOST` | `mosquitto` | The broker, found by its service name on the Compose network |
| `MQTT_PORT` | `1883` | Standard unencrypted MQTT port |
| `MQTT_TLS` | `false` | No encryption for the local broker |
| `DB_PATH` | `/app/data/iot_data.db` | Where the database lives, on a shared volume |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Where to find the language model |
| `AUTO_FAULTS` | `true` or `false` | Simulator auto mode |

### 4.2 Volumes

| Volume | Used by | Holds |
|---|---|---|
| `appdata` | subscriber (writes) and dashboard (reads) | The SQLite database, so both containers see the same file |
| `hfcache` | dashboard | The downloaded embedding model, so it is not downloaded again after a restart |

Data in a volume survives `docker compose down`. It is removed by `docker compose down -v`, which gives a clean start.

### 4.3 Start-up behaviour

- The dashboard container first runs the index builder, which converts the knowledge document into the searchable index, and only then starts Streamlit. Nobody has to run the indexing step by hand.
- `depends_on` only controls the order in which containers start, not whether the broker is ready to accept connections. A service that starts a moment too early simply fails and is restarted automatically, because every service has `restart: unless-stopped`. The system settles within a few seconds.
- The first start needs internet access to pull images and download the embedding model (about 90 MB). Later starts do not.

### 4.4 The simulator's keyboard

The simulator container is started with an open input stream and a terminal, so the keyboard control still works. Attach to the container to switch modes:

```
docker compose ps
docker attach <simulator-container-name>
```

Type 0 to 3 or 9, then press Enter. Detach with `Ctrl + P` then `Ctrl + Q`. Pressing `Ctrl + C` would stop the container. Alternatively, `AUTO_FAULTS=true` keeps a fault active automatically.

## 5. Why the language model stays outside Docker

Ollama runs on the host machine and the dashboard container calls it over the network, using the special address `host.docker.internal`.

| Reason | Detail |
|---|---|
| GPU use | Ollama on the host can use the laptop's graphics card directly, which makes answers much faster than a CPU-only container |
| Model files | The models are large and already downloaded on the host. Putting them in an image would make it huge |
| Simplicity | One Ollama installation is shared by every project |

**Consequence:** the machine running the system must have Ollama installed and the model downloaded (`ollama pull llama3.2:3b`). If it is missing, only the **Explain with AI** feature fails.

**On Linux,** the address `host.docker.internal` is not defined by default. Add this to the dashboard service:

```
extra_hosts:
  - "host.docker.internal:host-gateway"
```

and start Ollama so that it listens on all interfaces (`OLLAMA_HOST=0.0.0.0`).

## 6. Everyday commands

| Command | What it does |
|---|---|
| `docker compose up --build` | Build and start everything, showing the logs |
| `docker compose up -d` | Start in the background |
| `docker compose ps` | List the containers |
| `docker compose logs <service>` | Show a service's log, for example `subscriber` |
| `docker compose down` | Stop and remove the containers, keeping the volumes |
| `docker compose down -v` | Also delete the volumes, for a clean start |

## 7. Security notes

- The local broker allows anonymous connections and publishes port 1883 on the host. This is fine on a personal laptop for a demonstration. For anything else, remove the port mapping, or add authentication and TLS to the broker.
- No credential appears in the Dockerfile, the compose file or the image. The cloud broker password is read from an ignored file or from environment variables set outside the repository.
- The dashboard has no login.

## 8. Sharing the container on GitHub

There are two ways, and the first is already complete.

1. **Share the source with the compose file.** Anyone who clones the repository builds the image on their own machine with `docker compose up --build`. This is what the README describes.
2. **Publish the built image to the GitHub Container Registry (optional, not yet done).** The steps, in outline:
   - Create a personal access token with permission to write packages.
   - Log in to `ghcr.io` with Docker.
   - Tag the local image as `ghcr.io/<username>/iot-fault-assistant:latest` and push it.
   - Change the compose file's `image:` lines to that name, so that users pull it and skip the build.

   Check GitHub's current documentation for the exact commands before doing this.

## 9. Further deployment (not done)

| Target | What it would need |
|---|---|
| A cloud virtual machine | Install Docker and Ollama on the machine, clone the repository, run Compose. The simplest full deployment |
| Kubernetes | One deployment per service, a persistent volume for the database, a service for the dashboard, and a way for the dashboard to reach a language model. SQLite on several pods would need to be replaced by a database server |
| Streamlit Community Cloud | Can host only the dashboard. It cannot run the simulator and subscriber continuously, and it has no access to a local Ollama, so it does not give an end-to-end deployment |

## 10. Problems met while containerising

| Problem | Cause | Fix |
|---|---|---|
| Subscriber showed "Not authorized" | The containers were using the cloud broker defaults, because the configuration ignored environment variables | `config.py` reads the variables |
| `FileNotFoundError` for the machine profile | The file was saved with the extension in capitals, and Linux file names are case-sensitive | Renamed to lowercase |
| Dashboard error "no such table: readings" | The subscriber and the dashboard used different database files | Shared `DB_PATH` on a shared volume |
| Build cancelled while fetching the base image | Temporary network problem | Pulled the base image first, then rebuilt |

These and other problems are described further in `13_Problems_and_Decisions_Log.md`.