# -*- coding: utf-8 -*-
"""
Controle Fuzzy MISO + Modelo Físico + Simulação 24h + MQTT (publish)
"""
import time
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt
import random

# ============================================================
# 1) MODELO FÍSICO
# ============================================================

def modelo_fisico(T_atual, PCRAC, Qest, Text):
    return 0.9*T_atual - 0.08*PCRAC + 0.05*Qest + 0.02*Text + 3.5


# ============================================================
# 2) UNIVERSOS
# ============================================================

erro_univ        = np.linspace(-16, 16, 100)
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

erro_var['neg']  = fuzz.trimf(erro_univ, [-16, -16, 0])
erro_var['zero'] = fuzz.trimf(erro_univ, [-1, 0, 1])
erro_var['pos']  = fuzz.trimf(erro_univ, [0, 16, 16])

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


def criar_graficos_mf(e_val, de_val, text_val, qest_val, pcrac_val):
    """
    Gera uma figura Matplotlib com todas as funções de pertinência
    e marca os valores atuais com uma linha vertical tracejada.
    """
    # Cria o layout
    fig, ((ax1, ax2), (ax3, ax4), (ax5, ax6)) = plt.subplots(3, 2, figsize=(12, 14))
    plt.subplots_adjust(hspace=0.4)

    # Função auxiliar para plotar a linha do valor atual
    def plot_valor_atual(ax, valor, nome):
        ax.axvline(x=valor, color='r', linestyle='--', linewidth=2, label=f'Atual: {valor:.2f}')
        ax.legend(loc='upper right')

    # --- 1. ERRO ---
    ax1.plot(erro_univ, fuzz.trimf(erro_univ, [-15, -15, 0]), label='Negativo')
    ax1.plot(erro_univ, fuzz.trimf(erro_univ, [-1, 0, 1]),    label='Zero')
    ax1.plot(erro_univ, fuzz.trimf(erro_univ, [0, 15, 15]),   label='Positivo')
    ax1.set_title('Erro de Temperatura (°C)')
    plot_valor_atual(ax1, e_val, 'Erro')
    ax1.grid(True, alpha=0.3)

    # --- 2. DELTA ERRO ---
    ax2.plot(delta_erro_univ, fuzz.trimf(delta_erro_univ, [-2, -2, 0]),    label='Negativo')
    ax2.plot(delta_erro_univ, fuzz.trimf(delta_erro_univ, [-0.5, 0, 0.5]), label='Zero')
    ax2.plot(delta_erro_univ, fuzz.trimf(delta_erro_univ, [0, 2, 2]),      label='Positivo')
    ax2.set_title('Variação do Erro (de)')
    plot_valor_atual(ax2, de_val, 'dE')
    ax2.grid(True, alpha=0.3)

    # --- 3. TEMP EXTERNA ---
    ax3.plot(text_univ, fuzz.trimf(text_univ, [10, 10, 20]), label='Baixa')
    ax3.plot(text_univ, fuzz.trimf(text_univ, [15, 22, 30]), label='Média')
    ax3.plot(text_univ, fuzz.trimf(text_univ, [25, 35, 35]), label='Alta')
    ax3.set_title('Temperatura Externa (°C)')
    plot_valor_atual(ax3, text_val, 'Text')
    ax3.grid(True, alpha=0.3)

    # --- 4. CARGA TÉRMICA ---
    ax4.plot(qest_univ, fuzz.trimf(qest_univ, [0, 0, 40]),    label='Baixa')
    ax4.plot(qest_univ, fuzz.trimf(qest_univ, [20, 50, 80]),  label='Média')
    ax4.plot(qest_univ, fuzz.trimf(qest_univ, [60, 100, 100]), label='Alta')
    ax4.set_title('Carga Térmica (%)')
    plot_valor_atual(ax4, qest_val, 'Qest')
    ax4.grid(True, alpha=0.3)

    # --- 5. SAÍDA (PCRAC) ---
    ax5.plot(pcrac_univ, fuzz.trimf(pcrac_univ, [0, 0, 40]),    label='Baixa')
    ax5.plot(pcrac_univ, fuzz.trimf(pcrac_univ, [20, 50, 80]),  label='Média')
    ax5.plot(pcrac_univ, fuzz.trimf(pcrac_univ, [60, 100, 100]), label='Alta')
    ax5.set_title('Potência CRAC Calculada (Saída %)')
    
    # Aqui a linha vermelha mostra o resultado final "Defuzzificado"
    plot_valor_atual(ax5, pcrac_val, 'PCRAC') 
    ax5.grid(True, alpha=0.3)

    ax6.axis('off')
    return fig


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
    # Base senoidal (Dia começa frio, esquenta ao meio-dia, esfria à noite)
    # Ajustei a fase (-12) para o pico ser por volta das 14h-15h
    T_base = 25 + 7 * np.sin(2 * np.pi * (t_h - 9) / 24)
    
    # Adiciona Ruído Gaussiano (Aleatoriedade) [cite: 152]
    # Média 0, Desvio Padrão 0.5°C
    ruido = random.gauss(0, 0.5) 
    
    return T_base + ruido

def carga_termica(t_min):
    
    t_h = t_min / 60
    
    # Perfil base escalonado
    if 8 <= t_h < 18:   # Horário comercial (pico)
        base = 80
    elif 18 <= t_h < 23: # Noite (médio)
        base = 60
    elif 5 <= t_h < 8:   # Início da manhã (baixo)
        base = 40
    else:                # Madrugada (ocioso)
        base = 20
        
    # Adiciona variação aleatória de +/- 2% (jitter)
    variacao = random.uniform(-2, 2)
    return max(0, min(100, base + variacao))


# ============================================================
# 7) MQTT – PUBLICAÇÃO (Modo WebSocket - Requisito PDF)
# ============================================================

# O requisito pede porta 8000/mqtt. O HiveMQ suporta isso.
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT   = 1883 # Porta padrão (funciona melhor no Python)

MQTT_TOPIC_TEMP   = "datacenter/fuzzy/temp"
MQTT_TOPIC_CRAC   = "datacenter/fuzzy/control"
MQTT_TOPIC_ALERTA = "datacenter/fuzzy/alert"
MQTT_TOPIC_CARGA  = "datacenter/fuzzy/carga"

_mqtt_client = None

def _get_mqtt_client():
    global _mqtt_client
    if _mqtt_client is None:
        client = mqtt.Client() # Padrão TCP
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_start() # Thread em background
            print(f"✅ MQTT Conectado em {MQTT_BROKER}:{MQTT_PORT}")
        except Exception as e:
            print(f"❌ Erro MQTT: {e}")
        _mqtt_client = client
    return _mqtt_client

# Funções de publicação
def publicar_mqtt_temperatura(valor):
    _get_mqtt_client().publish(MQTT_TOPIC_TEMP, f"{valor:.2f}")

def publicar_mqtt_carga(valor):
    _get_mqtt_client().publish(MQTT_TOPIC_CARGA, f"{valor:.2f}")

def publicar_mqtt_crac(valor):
    _get_mqtt_client().publish(MQTT_TOPIC_CRAC, f"{valor:.2f}")

def publicar_mqtt_alerta(msg):
    _get_mqtt_client().publish(MQTT_TOPIC_ALERTA, str(msg))

# Simulação com MODO LENTO OBRIGATÓRIO
def simular_24h(setpoint=22.0, modo_lento=False):
    minutos  = 1440
    T = 22.0          
    PCRAC_prev = 50.0 
    e_anterior = 0

    ts, Ts, Texts, Qests, PCRACs = [], [], [], [], []

    print("Iniciando simulação...")

    for t in range(minutos):
        # ... (Cálculos do Fuzzy e Modelo Físico iguais ao anterior) ...
        Text = temperatura_externa(t)
        Qest = carga_termica(t)
        e = T - setpoint
        de = e - e_anterior
        PCRAC = fuzzy_controller(max(-15, min(15, e)), max(-2, min(2, de)), max(10, min(35, Text)), max(0, min(100, Qest)), PCRAC_prev)
        T_next = modelo_fisico(T, PCRAC, Qest, Text)

        # ARMAZENAMENTO
        ts.append(t/60); Ts.append(T); Texts.append(Text); Qests.append(Qest); PCRACs.append(PCRAC)

        # --- PUBLICAÇÃO MQTT ---
        publicar_mqtt_temperatura(T)
        publicar_mqtt_carga(Qest)
        publicar_mqtt_crac(PCRAC)
        if T > 26 or T < 18:
            publicar_mqtt_alerta(f"ALERTA: Temp {T:.2f}°C")

        # --- O SEGREDO DO SUCESSO ---
        if modo_lento:
            print(f"Enviando... T={T:.2f}") # Debug no terminal
            time.sleep(0.1) # 1 décimo de segundo por passo

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
