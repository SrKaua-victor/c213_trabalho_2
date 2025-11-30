import json
import paho.mqtt.client as mqtt

TOKEN = "BBUS-WwyOU1nsEDFECqPV8bM27l8MLeaLa6"
BROKER = "industrial.api.ubidots.com"
TOPIC = "/v1.6/devices/datacenter"

client = mqtt.Client()
client.username_pw_set(TOKEN, "")
client.connect(BROKER, 1883, 60)

payload = {
    "erro": 10,
    "carga": 55,
    "crac": 77
}

client.publish(TOPIC, json.dumps(payload))
client.disconnect()

print("Enviado!")
