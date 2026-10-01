import sys, os, json, time, random
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from mqtt_client import make_client

machine_id = "wt01"
fault = sys.argv[1] if len(sys.argv) > 1 else "normal"

values = {
    "wind_speed": 8.0, "active_power": 500.0, "generator_rpm": 1500.0,
    "gearbox_oil_temp": 55.0, "gearbox_bearing_temp": 60.0,
    "gen_bearing_temp": 58.0, "stator_temp": 65.0, "vibration": 1.2,
}
targets = values.copy()
speeds = {
    "wind_speed": 0.15, "active_power": 20, "generator_rpm": 8,
    "gearbox_oil_temp": 0.3, "gearbox_bearing_temp": 0.3,
    "gen_bearing_temp": 0.3, "stator_temp": 0.4, "vibration": 0.08,
}


def move_towards(current, target, speed):
    difference = target - current
    if abs(difference) <= speed:
        return target
    return current + speed if difference > 0 else current - speed


def generate_new_targets():
    wind = random.uniform(5, 12)
    power = (wind / 12) ** 3 * 1000
    load = power / 1000                      # 0 to 1

    targets["wind_speed"] = wind
    targets["active_power"] = power
    targets["generator_rpm"] = random.uniform(1400, 1600)
    targets["gearbox_oil_temp"] = 48 + 15 * load        # temperatures follow load
    targets["gearbox_bearing_temp"] = 55 + 14 * load
    targets["gen_bearing_temp"] = 50 + 15 * load
    targets["stator_temp"] = 60 + 20 * load
    targets["vibration"] = random.uniform(0.8, 2.0)


client = make_client("turbine-simulator")
client.connect(config.BROKER_HOST, config.BROKER_PORT)
client.loop_start()

generate_new_targets()
second = 0

while True:
    second += 1
    if random.random() < 0.05:
        generate_new_targets()

    for name in values:
        values[name] = move_towards(values[name], targets[name], speeds[name])

    data = {k: round(v, 2) for k, v in values.items()}

    # fault effects grow for 30 seconds, then hold
    ramp = min(second, 30)
    if fault == "gearbox_overheat":
        data["gearbox_oil_temp"] += ramp * 1.0
        data["gearbox_bearing_temp"] += ramp * 1.2
    elif fault == "bearing_wear":
        data["vibration"] += ramp * 0.12
        data["gearbox_bearing_temp"] += ramp * 0.5

    data["machine_id"] = machine_id
    data["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data["sim_fault"] = fault            # ground truth, the analyzer must NOT use this

    client.publish(config.TELEMETRY_TOPIC, json.dumps(data))
    print(f"[{fault}] wind {data['wind_speed']} | oil {data['gearbox_oil_temp']:.1f} | vib {data['vibration']:.2f}")
    time.sleep(1)