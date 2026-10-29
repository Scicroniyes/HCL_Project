# 13. Problems and Decisions Log

This document records the main decisions made during the project and the problems that came up, with the reasoning behind each. It shows how the final design was reached and what was learned along the way.

---

## Part 1. Decisions

| # | Decision | Alternatives | Reasoning |
|---|---|---|---|
| D1 | Use **wind turbines** as the machine | Cold storage, a factory pump, a small fan with real sensors | The guide suggested it. Wind turbine faults are well documented, so a knowledge base can be written, and a real public dataset exists |
| D2 | Follow **row 100** of the project sheet: MQTT + Python + Local LLM + RAG | The earlier plan used Node-RED, Grafana and a trained ML model (row 101) | The requirement was rechecked and row 100 was the correct one. This removed Node-RED, Grafana and the need for an ML model, and made the knowledge base and the explanation the centre of the project |
| D3 | **No hardware**, simulated data | An ESP32 with sensors and a small fan | The guide confirmed hardware was not required. The message format is the same as a real device would use, so hardware can be added later without changing the rest |
| D4 | **Rules detect, the LLM explains** | Let the LLM decide whether a fault exists, or use an ML model | An LLM can sound sure and be wrong, so it never decides whether there is a fault. Rules are testable and every alarm traces to a value and a limit |
| D5 | **No ML model** for detection, for now | An Isolation Forest trained on the real dataset | It is not in the row 100 stack. A model trained on real data could also disagree with the simulator's estimated numbers and flag healthy simulated readings, unless the simulator was calibrated first. That risk was judged too high close to a demonstration (it was assessed, not tested) |
| D6 | Use the **CARE to Compare** dataset to choose and map parameters | Collect no real data, or clean the whole dataset immediately | The guide asked for a dataset. Mapping the sensors gives real parameter names and units now, and calibration is kept as a clearly stated next step |
| D7 | **SQLite** for storage | PostgreSQL, a time-series database | Nothing to install, one file, and easy to inspect. Only one program writes to it |
| D8 | **Streamlit** for the dashboard | Grafana, Node-RED dashboard | Pure Python, and it can show a button, an explanation and sources, which Grafana cannot do easily |
| D9 | **Two brokers:** HiveMQ Cloud for development, Mosquitto in Docker as the default | Only the cloud, or the public test broker | The local broker means a clone needs no account. The cloud broker shows a managed service. The public test broker was rejected, because anyone can read it |
| D10 | **Secrets kept out of the repository** | Keep credentials in `config.py` | A `.gitignore`d `local_secrets.py` locally, environment variables elsewhere, and `.dockerignore` so credentials are never baked into an image |
| D11 | **AI explanation on a button,** not on every reading | Run the LLM continuously | The local model is slow, and a fault lasts many seconds. The rule-based diagnosis appears instantly, and the AI part is optional |
| D12 | **Low temperature and strict prompt;** sources attached by code | Trust the model to cite | The model cannot invent a citation if the program supplies the section names itself |
| D13 | **One chunk per knowledge section,** retrieve two | Fine-grained chunks, more results | Each section describes one whole fault. With five sections, more complexity would add nothing |
| D14 | **One image,** three services | A separate image per service | One build, one set of libraries, and quick rebuilds |
| D15 | **CPU-only PyTorch** and Python 3.12 in the image | The default PyTorch build, Python 3.13 | Much smaller image, and better library availability on Linux |
| D16 | **Ollama stays on the host** | Run it in a container | It can use the GPU directly, and the model files are already there |
| D17 | **Auto fault mode** and a ground-truth label in the simulator | Only manual fault injection | A continuous supply of diagnoses was needed for explainability work, and the label lets results be checked against the truth |
| D18 | **Defer multi-turbine support and Kubernetes** | Do them immediately | The core pipeline had to work first. The topic design and the profile already allow multi-turbine later |
| D19 | Write all documents in **Markdown** | Word or PDF | It shows on GitHub, lives in the repository, and converts to Word or PDF later |

### How the idea changed

```
General IoT alert platform (Node-RED, ML, Grafana)
        |  project sheet rechecked: row 100, not row 101
        v
Knowledge-driven fault diagnosis (MQTT, Python, local LLM, RAG)
        |  domain changed to wind turbines at the guide's suggestion
        v
Rule-based detection + knowledge base + RAG explanation, simulated data
        |  guide asked for a container on GitHub and a deployment
        v
Dockerised system, one command to run
```

## Part 2. Problems and fixes

| # | Problem | Cause | Fix | Lesson |
|---|---|---|---|---|
| P1 | Python errors when the broker settings were imported | Indentation was mixed in `config.py`, and the setting names did not match the names the other files used | One consistent set of names and correct indentation | Keep shared settings in one file and use identical names everywhere |
| P2 | A broker password appeared in a screenshot | Files were shared while asking for help | Treat the password as exposed and replace it. Credentials moved to an ignored file | Never share files with secrets. Hide them first |
| P3 | Messages did not appear in the HiveMQ web client | The topic was typed as `#iotfault`, which is invalid, and the web client has its own connect step | Subscribe to `iotfault/#` after connecting with the MQTT credentials | In MQTT, `#` must be the last part of a topic |
| P4 | Subscriber stopped with "unable to open database file" | The script sat outside its folder, so the project root was worked out wrongly and the database was created at the drive root | The script was moved into its folder | Paths computed from a file's location depend on where the file is |
| P5 | Old output kept appearing after the code was changed | The previous subscriber was still running, and a running script keeps its old code | Stop it and start it again | Restart a program after editing it |
| P6 | `cannot import name 'full_analysis'` | The import named the folder, and the file had a different name | Import from the file name, and name the file consistently | Python imports from files, not from folders |
| P7 | A yellow warning and an orange folder in VS Code | The editor's checker does not follow the dynamic search path used by the code | Ignored. It can be silenced with an `extraPaths` setting | A warning in the editor is not always an error. Run the code to find out |
| P8 | `ollama` was not recognised | Ollama was not installed, and later the terminal was opened before the installer updated the path | Install it, then open a new terminal | New terminals are needed after installing command-line tools |
| P9 | The first language model request seemed stuck | The model and embedding model load on first use | Waited. Later requests are fast. The design already runs the model only on a button click | The first call to a local model is the slow one |
| P10 | Docker build cancelled while fetching the base image | A temporary network problem | Pulled the base image first, then rebuilt | Split a failing step to see which part fails |
| P11 | Compose could not start the broker | The broker's configuration folder was missing | Created `mosquitto/config/mosquitto.conf` | A mounted folder must exist |
| P12 | `FileNotFoundError` for the machine profile in the container | The file extension was in capitals (`.JSON`). Windows ignores case, Linux does not | Renamed to lowercase | Use lowercase file names so code works on every system |
| P13 | "Not authorized" from the subscriber in Docker | The container used the cloud defaults, because the configuration did not read environment variables | `config.py` reads the variables | Configuration must be able to change without editing code |
| P14 | Dashboard error "no such table: readings" | The subscriber and the dashboard were using two different database files inside their containers | A shared `DB_PATH` on a shared volume | Containers do not share a file system unless a volume is shared |
| P15 | Typing a fault number in the simulator did nothing | An older version of the simulator had no keyboard listener, and in Docker the terminal must be attached | A listener was added, and the README explains `docker attach` | Check which version of a file is actually running |
| P16 | A draft simulator from another source only printed data | It did not publish to MQTT, had no faults, its temperatures ignored the load, and vibration could exceed the normal range | The smooth-drift idea was kept and the missing parts were added | Review generated code against the requirements before using it |
| P17 | The wind speed line looks flat on its chart | Wind speed and power share one scale | Recorded as a known limitation. Separate charts would fix it | Mixing very different scales hides small signals |

## Part 3. Lessons learned

1. **Check the specification early.** Rereading the project sheet changed the stack and saved effort.
2. **Keep detection and explanation separate.** It made the system explainable and easy to test.
3. **Make configuration external.** Environment variables allowed one codebase to run on a laptop and in Docker.
4. **Build the pipeline end to end first,** with the simplest parts, then improve each part. A working demonstration existed at every stage.
5. **Be honest about what is estimated or simulated.** The limits, the vibration data and the symptom match are all labelled for what they are.
6. **Test on a second system.** Several problems (case-sensitive names, separate file systems) only appeared once the system ran in containers.