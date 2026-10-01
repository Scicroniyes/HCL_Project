from mqtt_client import make_client
import config

def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected:", reason_code)
    client.subscribe(config.TELEMETRY_TOPIC)

def on_message(client, userdata, msg):
    print(msg.topic, "->", msg.payload.decode())

client = make_client("test-subscriber")
client.on_connect = on_connect
client.on_message = on_message
client.connect(config.BROKER_HOST, config.BROKER_PORT)
client.loop_forever()