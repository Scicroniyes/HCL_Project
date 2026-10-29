import sys, os, json, time, random, threading
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from mqtt_client import make_client

machine_id = "wt01"

FAULTS = {"0": "normal", "1": "gearbox_overheat", "2": "bearing_wear", "3": "generator_overheat"}
FAULT_LIST = ["gearbox_overheat", "bearing_wear", "generator_overheat"]
SWITCH_EVERY = 25          # auto mode: new fault every 25 seconds

auto = os.environ.get("AUTO_FAULTS", "false").lower() == "true"
fault = sys.argv[1] if len(sys.argv) > 1 else "normal"
if auto:
    fault = random.choice(FAULT_LIST)
second = 0

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


def keyboard_listener():
    global fault, second, auto
    while True:
        try:
            choice = input().strip()
        except EOFError:
            return                      # no keyboard (for example detached container)
        if choice == "9":
            auto = True
            fault = random.choice(FAULT_LIST)
            second = 0
            print(">>> Auto mode ON")
        elif choice in FAULTS:
            auto = False
            fault = FAULTS[choice]
            second = 0
            print(f">>> Mode set to: {fault}")
        else:
            print(">>> 0 normal | 1 gearbox | 2 bearing | 3 generator | 9 auto")


def move_towards(current, target, speed):
    difference = target - current
    if abs(difference) <= speed:
        return target
    return current + speed if difference > 0 else current - speed


def generate_new_targets():
    wind = random.uniform(5, 12)
    power = (wind / 12) ** 3 * 1000
    load = power / 1000                         # 0 to 1

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

threading.Thread(target=keyboard_listener, daemon=True).start()
print("Simulator running. 0 normal | 1 gearbox | 2 bearing | 3 generator | 9 auto. Ctrl+C to stop.")
generate_new_targets()

while True:
    second += 1

    if auto and second > SWITCH_EVERY:
        fault = random.choice([f for f in FAULT_LIST if f != fault])
        second = 0

    if random.random() < 0.05:
        generate_new_targets()

    for name in values:
        values[name] = move_towards(values[name], targets[name], speeds[name])

    data = dict(values)

    # fault effects: ramp to full strength in 10 s (auto) or 30 s (manual), then hold
    ramp_seconds = 10 if auto else 30
    ramp = min(second * 30 / ramp_seconds, 30)

    if fault == "gearbox_overheat":
        data["gearbox_oil_temp"] += ramp * 1.0
        data["gearbox_bearing_temp"] += ramp * 1.2
    elif fault == "bearing_wear":
        data["vibration"] += ramp * 0.15
        data["gearbox_bearing_temp"] += ramp * 0.5
    elif fault == "generator_overheat":
        data["gen_bearing_temp"] += ramp * 1.0
        data["stator_temp"] += ramp * 1.8

    data = {k: round(v, 2) for k, v in data.items()}
    data["machine_id"] = machine_id
    data["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data["sim_fault"] = fault            # ground truth, the analyzer must NOT use this

    client.publish(config.TELEMETRY_TOPIC, json.dumps(data))
    print(f"[{fault}] wind {data['wind_speed']} | oil {data['gearbox_oil_temp']:.1f} | "
          f"vib {data['vibration']:.2f} | stator {data['stator_temp']:.1f}")
    time.sleep(1)