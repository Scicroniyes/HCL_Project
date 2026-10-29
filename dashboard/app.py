import sys, os, sqlite3
import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analyzers"))
from analyzer import full_analysis

DB = os.environ.get("DB_PATH", os.path.join(ROOT, "iot_data.db"))

st.set_page_config(page_title="Turbine Fault Diagnosis", layout="wide")
st.title("Wind Turbine Fault Diagnosis Assistant")


def query(sql):
    con = sqlite3.connect(DB)
    df = pd.read_sql_query(sql, con)
    con.close()
    return df

@st.cache_resource
def load_explainer():
    sys.path.insert(0, os.path.join(ROOT, "rag"))
    from explain import explain
    return explain

@st.cache_resource
def load_explainer():
    sys.path.insert(0, os.path.join(ROOT, "rag"))
    from explain import explain
    return explain


@st.fragment(run_every=2)
def live():
    readings = query("SELECT * FROM readings ORDER BY id DESC LIMIT 120")
    if readings.empty:
        st.info("No data yet. Start the simulator and the subscriber.")
        return
    readings = readings.iloc[::-1]
    latest = readings.iloc[-1]
    result = full_analysis(latest.to_dict())

    # 1. status banner
    status = result["status"]
    if status == "normal":
        st.success("Status: NORMAL")
    elif status == "warning":
        st.warning("Status: WARNING")
    else:
        st.error("Status: CRITICAL")

    # 2. key numbers
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Wind speed (m/s)", latest["wind_speed"])
    c2.metric("Power (kW)", latest["active_power"])
    c3.metric("Gearbox oil (°C)", latest["gearbox_oil_temp"])
    c4.metric("Vibration (mm/s)", latest["vibration"])

    # 3. charts
    data = readings.set_index("id")
    g1, g2, g3 = st.columns(3)
    g1.caption("Temperatures (°C)")
    g1.line_chart(data[["gearbox_oil_temp", "gearbox_bearing_temp",
                        "gen_bearing_temp", "stator_temp"]])
    g2.caption("Vibration (mm/s)")
    g2.line_chart(data[["vibration"]])
    g3.caption("Wind speed (m/s) and power (kW)")
    g3.line_chart(data[["wind_speed", "active_power"]])

    # 4. diagnosis
    st.subheader("Diagnosis")
    if not result["diagnoses"]:
        st.write("No fault detected. All parameters are within limits.")
    else:
        st.write("**Out-of-range parameters:**")
        for s in result["symptoms"]:
            st.write(f"- {s['label']}: {s['value']} {s['unit']} ({s['status']})")

        top = result["diagnoses"][0]
        st.markdown(f"### Likely fault: {top['name']} ({top['confidence']}% symptom match)")
        a, b = st.columns(2)
        a.markdown("**Probable causes**\n\n" + "\n".join(f"- {x}" for x in top["causes"]))
        b.markdown("**Recommended checks**\n\n" + "\n".join(f"- {x}" for x in top["checks"]))

        others = result["diagnoses"][1:]
        if others:
            st.caption("Also possible: " + ", ".join(
                f"{d['name']} ({d['confidence']}%)" for d in others))
        
        symptom_text = "; ".join(
            f"{s['label']} {s['value']} {s['unit']} ({s['status']})"
            for s in result["symptoms"])
        if st.button("Explain with AI"):
            with st.spinner("Local LLM is writing the explanation..."):
                answer, sources = load_explainer()(symptom_text)
            st.session_state["ai"] = {"answer": answer, "sources": sources}

        ai = st.session_state.get("ai")
        if ai:
            st.markdown("#### AI explanation (local LLM + RAG)")
            st.write(ai["answer"])
            st.caption("Sources: " + ", ".join(ai["sources"]))    

    # 5. history
    st.subheader("Diagnosis history (latest 10)")
    hist = query("SELECT ts, status, top_fault, confidence FROM diagnoses "
                 "ORDER BY id DESC LIMIT 10")
    if hist.empty:
        st.write("No faults recorded yet.")
    else:
        st.dataframe(hist, hide_index=True)


live()