# -*- coding: utf-8 -*-
"""
Controle Fuzzy MISO + Modelo Físico + Simulação 24h + MQTT (publish)
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt

# ============================================================
# 1) MODELO FÍSICO
# ============================================================

def modelo_fisico(T_atual, PCRAC, Qest, Text):
    return 0.9*T_atual - 0.08*PCRAC + 0.05*Qest + 0.02*Text + 3.5


# ============================================================
# 2) UNIVERSOS
# ============================================================

erro_univ        = np.linspace(-5, 5, 100)
delta_erro_univ  = np.linspace(-2, 2, 100)
text_univ        = np.linspace(10, 35, 100)
qest_univ        = np.linspace(0, 100, 100)
pcrac_univ       = np.linspace(0, 100, 100)

erro_var  = ctrl.Antecedent(erro_univ, 'erro')
de_var    = ctrl.Antecedent(delta_erro_univ, 'de')
text_var  = ctrl.Antecedent(text_univ, 'text')
qest_var  = ctrl.Antecedent(qest_univ, 'qest')
pcrac_var = ctrl.Consequent(pcrac_univ, 'pcrac')


# ============================================================
# 3) MF’s
# ============================================================

erro_var['neg']  = fuzz.trimf(erro_univ, [-5, -5, 0])
erro_var['zero'] = fuzz.trimf(erro_univ, [-1, 0, 1])
erro_var['pos']  = fuzz.trimf(erro_univ, [0, 5, 5])

de_var['neg']  = fuzz.trimf(delta_erro_univ, [-2, -2, 0])
de_var['zero'] = fuzz.trimf(delta_erro_univ, [-0.5, 0, 0.5])
de_var['pos']  = fuzz.trimf(delta_erro_univ, [0, 2, 2])

text_var['baixa'] = fuzz.trimf(text_univ, [10, 10, 20])
text_var['media'] = fuzz.trimf(text_univ, [15, 22, 30])
text_var['alta']  = fuzz.trimf(text_univ, [25, 35, 35])

qest_var['baixa'] = fuzz.trimf(qest_univ, [0, 0, 40])
qest_var['media'] = fuzz.trimf(qest_univ, [20, 50, 80])
qest_var['alta']  = fuzz.trimf(qest_univ, [60, 100, 100])

pcrac_var['baixa'] = fuzz.trimf(pcrac_univ, [0, 0, 40])
pcrac_var['media'] = fuzz.trimf(pcrac_univ, [20, 50, 80])
pcrac_var['alta']  = fuzz.trimf(pcrac_univ, [60, 100, 100])


# ============================================================
# 4) REGRAS
# ============================================================

regras = [
    ctrl.Rule(erro_var['pos']  & de_var['pos'],   pcrac_var['alta']),
    ctrl.Rule(erro_var['pos']  & de_var['zero'],  pcrac_var['alta']),
    ctrl.Rule(erro_var['pos']  & de_var['neg'],   pcrac_var['media']),

    ctrl.Rule(erro_var['zero'] & de_var['pos'],   pcrac_var['alta']),
    ctrl.Rule(erro_var['zero'] & de_var['zero'],  pcrac_var['media']),
    ctrl.Rule(erro_var['zero'] & de_var['neg'],   pcrac_var['baixa']),

    ctrl.Rule(erro_var['neg']  & de_var['pos'],   pcrac_var['media']),
    ctrl.Rule(erro_var['neg']  & de_var['zero'],  pcrac_var['baixa']),
    ctrl.Rule(erro_var['neg']  & de_var['neg'],   pcrac_var['baixa']),

    ctrl.Rule(text_var['alta'],   pcrac_var['alta']),
    ctrl.Rule(text_var['baixa'],  pcrac_var['baixa']),

    ctrl.Rule(qest_var['alta'],   pcrac_var['alta']),
]

sistema_ctrl = ctrl.ControlSystem(regras)


# ============================================================
# 5) CONTROLADOR FUZZY
# ============================================================

def fuzzy_controller(e, de, Text, Qest, PCRAC_prev):
    sim = ctrl.ControlSystemSimulation(sistema_ctrl)

    sim.input['erro'] = e
    sim.input['de']   = de
    sim.input['text'] = Text
    sim.input['qest'] = Qest

    sim.compute()

    PCRAC_raw = float(sim.output['pcrac'])
    PCRAC_suave = 0.7 * PCRAC_prev + 0.3 * PCRAC_raw
    return PCRAC_suave


# ============================================================
# 6) PERFIS
# ============================================================

def temperatura_externa(t_min):
    t_h = t_min / 60
    return 22 + 6 * np.sin(2 * np.pi * (t_h - 15) / 24)

def carga_termica(t_min):
    t_h = t_min / 60
    if 8 <= t_h < 18:  return 80
    if 18 <= t_h < 23: return 60
    if 5 <= t_h < 8:   return 40
    return 20


# ============================================================
# 7) MQTT – PUBLICAÇÃO
# ============================================================

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT   = 1883

MQTT_TOPIC_TEMP   = "datacenter/temperatura"
MQTT_TOPIC_CARGA  = "datacenter/carga_termica"
MQTT_TOPIC_CRAC   = "datacenter/potencia_crac"
MQTT_TOPIC_ALERTA = "datacenter/alertas"

_mqtt_client = None

def _get_mqtt_client():
    global _mqtt_client
    if _mqtt_client is None:
        client = mqtt.Client()
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start()
            print("MQTT conectado (publish).")
        except:
            print("Erro ao conectar MQTT (publish).")
        _mqtt_client = client
    return _mqtt_client


def publicar_mqtt_temperatura(valor):
    _get_mqtt_client().publish(MQTT_TOPIC_TEMP, str(valor))


def publicar_mqtt_carga(valor):
    _get_mqtt_client().publish(MQTT_TOPIC_CARGA, str(valor))


def publicar_mqtt_crac(valor):
    _get_mqtt_client().publish(MQTT_TOPIC_CRAC, str(valor))


def publicar_mqtt_alerta(msg):
    _get_mqtt_client().publish(MQTT_TOPIC_ALERTA, str(msg))


# ============================================================
# 8) SIMULAÇÃO 24H
# ============================================================

def simular_24h():
    minutos  = 1440
    setpoint = 22.0

    T = setpoint
    e_anterior = 0
    PCRAC_prev = 50

    ts, Ts, Texts, Qests, PCRACs = [], [], [], [], []

    for t in range(minutos):
        Text = temperatura_externa(t)
        Qest = carga_termica(t)

        e = T - setpoint
        de = 0.5 * (e - e_anterior)

        PCRAC = fuzzy_controller(e, de, Text, Qest, PCRAC_prev)
        T_next = modelo_fisico(T, PCRAC, Qest, Text)

        ts.append(t/60)
        Ts.append(T)
        Texts.append(Text)
        Qests.append(Qest)
        PCRACs.append(PCRAC)

        publicar_mqtt_temperatura(T)
        publicar_mqtt_carga(Qest)
        publicar_mqtt_crac(PCRAC)
        if T > 28:
            publicar_mqtt_alerta(f"TEMPERATURA ALTA: {T:.2f}°C")

        T = T_next
        e_anterior = e
        PCRAC_prev = PCRAC

    return ts, Ts, Texts, Qests, PCRACs


# ============================================================
# 9) MAIN
# ============================================================

if __name__ == "__main__":
    ts, Ts, Texts, Qests, PCRACs = simular_24h()

    plt.plot(ts, Ts, label="Temperatura Interna")
    plt.plot(ts, Texts, label="Temperatura Externa")
    plt.legend()
    plt.show()
