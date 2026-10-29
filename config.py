import os

try:
    import local_secrets as _s
    _user, _pass = _s.MQTT_USER, _s.MQTT_PASS
except ImportError:
    _user, _pass = None, None

BROKER_HOST = os.environ.get("MQTT_HOST", "d5c4125f981a4cf2a3068e2710e1305d.s1.eu.hivemq.cloud")
BROKER_PORT = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USER = os.environ.get("MQTT_USER", _user)
MQTT_PASS = os.environ.get("MQTT_PASS", _pass)
USE_TLS = os.environ.get("MQTT_TLS", "true").lower() == "true"

TOPIC_PREFIX = "iotfault"
TELEMETRY_TOPIC = "iotfault/turbine/wt01/telemetry"
DIAGNOSIS_TOPIC = "iotfault/turbine/wt01/diagnosis"