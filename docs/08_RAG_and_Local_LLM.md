# 08. RAG and the Local LLM

This document explains how the system turns a diagnosis into a written explanation with sources: what RAG is, how the knowledge is indexed and searched, how the local language model is prompted, and how the design keeps the model from inventing things.

---

## 1. The problem this solves

The rule-based diagnosis already lists the likely fault, causes and checks. But it is a fixed template. A technician benefits from an explanation that connects **these particular symptoms** to the fault in plain language, and that shows where the advice comes from.

A language model can write that explanation. The risk is that a language model on its own may produce text that sounds right and is not. Retrieval-Augmented Generation (RAG) reduces that risk by handing the model the relevant reference text and asking it to answer from that text only.

## 2. What RAG means here

RAG has three steps:

1. **Retrieve** the passages of the knowledge document that best match the current symptoms.
2. **Augment** the prompt by placing those passages in it.
3. **Generate** an answer with the language model, restricted to those passages.

```
symptoms (text)
      |
      v
embed the text --> search the index --> top 2 matching sections
                                              |
                                              v
                      prompt = symptoms + sections + strict instructions
                                              |
                                              v
                                   local LLM writes the answer
                                              |
                                              v
                      answer shown with the names of the sections used
```

## 3. The knowledge document

The text lives in `knowledge/wind_turbine_faults.md`. It has five sections, each starting with `## `:

- Gearbox overheating
- Gearbox bearing wear
- Generator overheating
- Excessive vibration
- Yaw misalignment

Each section follows the same layout: symptoms, probable causes, recommended checks and risk. Keeping the layout fixed helps retrieval, because a section reads like a complete description of one fault.

The content was written from general maintenance knowledge. It should be reviewed against real manuals, and the references added to the report.

## 4. Building the index

`rag/build_index.py` prepares the knowledge for searching:

1. **Split** the document at each `## ` heading. One section becomes one chunk.
2. **Embed** each chunk. An embedding model converts text into a list of numbers that represents its meaning, so texts with similar meaning get similar numbers. The model used is `all-MiniLM-L6-v2`, a small model (about 90 MB) that runs on an ordinary CPU.
3. **Store** the chunks, their embeddings and metadata (source file and section title) in ChromaDB, a vector database that keeps its data in a local folder.

The index is rebuilt from scratch every time the script runs, so it always matches the document. In Docker, the script runs automatically each time the dashboard container starts. The index is generated, so it is not committed to the repository.

**Why one chunk per section.** Each section is a self-contained description of a single fault. Splitting at the headings means a retrieved chunk is a whole fault description, not a fragment. With only five sections, finer chunking would add complexity without benefit.

## 5. Retrieval: search by meaning

At query time, the symptom text is converted to an embedding with the same model, and ChromaDB returns the closest chunks. A smaller distance means a closer match.

This is search by meaning, not by matching words. The query "power is low for the wind speed but temperatures are normal" shares few exact words with the yaw misalignment section, yet it was matched to it.

### Observed results

Three test queries were run after the index was built. Each returned the right section first:

| Query | Top result | Distance | Second result |
|---|---|---|---|
| Gearbox oil and bearing temperature high | Gearbox overheating | 0.65 | Gearbox bearing wear (0.81) |
| Vibration above normal | Excessive vibration | 0.90 | Gearbox bearing wear (1.29) |
| Power low for the wind speed, temperatures normal | Yaw misalignment | 1.05 | Generator overheating (1.13) |

The distance only has meaning relative to the other sections for the same query. The yaw query has a larger distance because it describes a pattern and not a particular sensor, but the right section still ranked first.

**How many sections are retrieved.** Two. This gives the model the best match and one alternative without overloading a small model with text.

## 6. The language model

The explanation is written by `llama3.2:3b`, a small open model run locally through Ollama. Nothing is sent to an outside service. The model needs about 2 GB of storage and, on the development laptop, ran entirely on the graphics card.

### 6.1 The prompt

The prompt contains three parts:

- The role: a wind turbine maintenance assistant.
- The current symptoms and the retrieved reference sections.
- Strict instructions: use **only** the reference text, answer in a fixed format (likely fault, why, probable causes, recommended checks), and **say so instead of guessing** if the text does not match the symptoms.

### 6.2 Settings

The temperature is set low (0.2). A low temperature makes the output more focused and repeatable and reduces creative variation, which is what a diagnostic explanation needs.

### 6.3 The symptom text

The dashboard builds the input from the current symptoms in plain words, for example: *Gearbox oil temperature 85 °C (critical); gearbox bearing temperature 90 °C (critical)*. The model never receives raw data streams. It only receives this short description and the retrieved text.

## 7. Controlling invented content

A small language model can still make mistakes, so several safeguards work together:

| Safeguard | What it does |
|---|---|
| Rules decide whether a fault exists | The model is only consulted after the analyzer found a problem. It cannot raise or cancel an alarm |
| Retrieval limits the context | The model sees only the two relevant sections |
| Strict instruction | It is told to use only that text, and to say when the text does not fit |
| Low temperature | Less variation and less improvisation |
| Fixed answer format | Easier to read and to check |
| Sources attached by the program | The section names come from the retrieval results, written by code, so the model cannot invent a citation |

**What the sources mean.** The sources shown are the sections that were provided to the model. The system does not verify that every statement in the answer was taken from them. This is a known limitation, listed below.

## 8. The explanation in the dashboard

The explanation is produced when the user clicks **Explain with AI**, and it is not computed for every reading. There are two reasons:

- A local model takes seconds to answer, and the first request is much slower because the models have to be loaded into memory.
- A fault lasts many seconds, and the same explanation would otherwise be regenerated for every reading.

During the request a spinner is shown. The answer and its sources then stay on the page. The embedding model and vector store are loaded once and reused for later clicks, so the first click is the slow one.

The rule-based diagnosis is always shown instantly, so the system is useful even before the explanation appears.

## 9. Running it in Docker

The dashboard container has to reach Ollama, which runs on the host machine, not in a container. The container uses the address `host.docker.internal` on Ollama's standard port, supplied through an environment variable. The embedding model is downloaded the first time and stored in a volume, so it is not downloaded again after a restart.

If Ollama is not running, only the **Explain with AI** feature fails. Everything else continues to work.

## 10. Updating the knowledge

Edit `knowledge/wind_turbine_faults.md` and rebuild the index, either by running `python rag/build_index.py` or by restarting the dashboard container. No code changes are needed. Writing each section in the same layout, and using the words a technician would use for symptoms, improves retrieval.

## 11. Limitations

- **Small knowledge base.** Five short sections. Retrieval quality and answer quality depend on how well the text is written.
- **The model may still misstate things.** Nothing automatically checks the answer against the sources.
- **Two sources of knowledge can disagree.** The rule-based diagnosis ranks faults from the structured file, while the language model chooses a fault from the retrieved text. They usually agree, but they are produced separately. Passing the rule-based top fault into the prompt would make them consistent, and is a planned improvement.
- **The explanation does not refresh by itself** when the fault changes. The user clicks again for a new one.
- **Latency.** On the development laptop the first answer takes tens of seconds, and later answers a few seconds.
- **Model size.** A larger model would write better explanations, at the cost of speed and memory. The model name is a single setting.