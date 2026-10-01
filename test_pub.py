from mqtt_client import make_client
import json, time
import config

client = make_client("test-publisher")
client.connect(config.BROKER_HOST, config.BROKER_PORT)
client.loop_start()

for i in range(5):
    msg = {"wind_speed": 8.5 + i, "gearbox_oil_temp": 55.0}
    client.publish(config.TELEMETRY_TOPIC, json.dumps(msg))
    print("sent", msg)
    time.sleep(1)

time.sleep(1)
client.loop_stop()
client.disconnect()