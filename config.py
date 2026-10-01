import os


USE_CLOUD = True

try:
    import local_secrets as _s          # your laptop: reads local_secrets.py
    _user, _pass = _s.MQTT_USER, _s.MQTT_PASS
except ImportError:                      # cloud / Docker: reads environment variables
    _user = os.environ.get("MQTT_USER")
    _pass = os.environ.get("MQTT_PASS")

if USE_CLOUD:
    BROKER_HOST = "d5c4125f981a4cf2a3068e2710e1305d.s1.eu.hivemq.cloud"
    
    BROKER_PORT = 8883
    
    MQTT_USER = _user
    
    MQTT_PASS = _pass
    USE_TLS = True
    
  
else:
    BROKER_HOST = "localhost"
    BROKER_PORT = 1883
    MQTT_USER = None
    MQTT_PASS = None
    USE_TLS = False
    
    
   
TOPIC_PREFIX = "iotfault"
TELEMETRY_TOPIC = "iotfault/turbine/wt01/telemetry"
DIAGNOSIS_TOPIC = "iotfault/turbine/wt01/diagnosis"
