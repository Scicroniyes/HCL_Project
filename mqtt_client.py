import paho.mqtt.client as mqtt
import config

def make_client(client_id=""):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if config.MQTT_USER:
        client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
    if config.USE_TLS:
        client.tls_set()
    return client