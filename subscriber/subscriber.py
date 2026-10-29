import sys, os, json, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "analyzers"))
import config
from mqtt_client import make_client
from analyzer import full_analysis

DB_PATH = os.environ.get("DB_PATH", os.path.join(ROOT, "iot_data.db"))
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id TEXT, ts TEXT,
        wind_speed REAL, active_power REAL, generator_rpm REAL,
        gearbox_oil_temp REAL, gearbox_bearing_temp REAL,
        gen_bearing_temp REAL, stator_temp REAL, vibration REAL,
        sim_fault TEXT
    )
""")
db.execute("""
    CREATE TABLE IF NOT EXISTS diagnoses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id TEXT, ts TEXT, status TEXT,
        top_fault TEXT, confidence INTEGER,
        symptoms TEXT, diagnoses TEXT, sim_fault TEXT
    )
""")
db.commit()

COLUMNS = ["machine_id", "ts", "wind_speed", "active_power", "generator_rpm",
           "gearbox_oil_temp", "gearbox_bearing_temp", "gen_bearing_temp",
           "stator_temp", "vibration", "sim_fault"]
count = 0


def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected:", reason_code)
    client.subscribe(config.TELEMETRY_TOPIC)


def on_message(client, userdata, msg):
    global count
    data = json.loads(msg.payload.decode())

    # 1. save the reading
    values = [data.get(c) for c in COLUMNS]
    db.execute(
        f"INSERT INTO readings ({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})",
        values,
    )
    count += 1

    # 2. analyze it
    result = full_analysis(data)

    # 3. if something is wrong, save and publish the diagnosis
    if result["status"] != "normal":
        top = result["diagnoses"][0] if result["diagnoses"] else None
        db.execute(
            "INSERT INTO diagnoses (machine_id, ts, status, top_fault, confidence, "
            "symptoms, diagnoses, sim_fault) VALUES (?,?,?,?,?,?,?,?)",
            (data.get("machine_id"), data.get("ts"), result["status"],
             top["name"] if top else "Unknown",
             top["confidence"] if top else 0,
             json.dumps(result["symptoms"]),
             json.dumps(result["diagnoses"]),
             data.get("sim_fault")),
        )
        message = {
            "machine_id": data.get("machine_id"),
            "ts": data.get("ts"),
            "status": result["status"],
            "symptoms": result["symptoms"],
            "diagnoses": result["diagnoses"],
        }
        client.publish(config.DIAGNOSIS_TOPIC, json.dumps(message))
        print(f"#{count} {result['status'].upper()} -> {top['name'] if top else 'Unknown'}"
              f" ({top['confidence'] if top else 0}%)")
    else:
        print(f"#{count} normal")

    db.commit()


client = make_client("turbine-subscriber")
client.on_connect = on_connect
client.on_message = on_message
client.connect(config.BROKER_HOST, config.BROKER_PORT)
print("Subscriber running. Ctrl+C to stop.")
client.loop_forever()