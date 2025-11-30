# main.py – Fuzzy + Modelo Físico + Simulação (SEM MQTT)
# Agora quem envia MQTT é o gui_tk.py (via Ubidots)

import time
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt
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


# ============================================================
# 4) GERAÇÃO DOS GRÁFICOS MF
# ============================================================

def criar_graficos_mf(e_val, de_val, text_val, qest_val, pcrac_val):

    fig, ((ax1, ax2), (ax3, ax4), (ax5, _)) = plt.subplots(3, 2, figsize=(12, 14))
    plt.subplots_adjust(hspace=0.4)

    def marca(ax, val):
        ax.axvline(x=val, color='r', linestyle='--', linewidth=2)

    # ERRO
    ax1.plot(erro_univ, erro_var['neg'].mf, label='Negativo')
    ax1.plot(erro_univ, erro_var['zero'].mf, label='Zero')
    ax1.plot(erro_univ, erro_var['pos'].mf, label='Positivo')
    marca(ax1, e_val)
    ax1.grid(True)
    ax1.set_title("Erro")

    # DELTA ERRO
    ax2.plot(delta_erro_univ, de_var['neg'].mf)
    ax2.plot(delta_erro_univ, de_var['zero'].mf)
    ax2.plot(delta_erro_univ, de_var['pos'].mf)
    marca(ax2, de_val)
    ax2.grid(True)
    ax2.set_title("Delta Erro")

    # TEMP EXT
    ax3.plot(text_univ, text_var['baixa'].mf)
    ax3.plot(text_univ, text_var['media'].mf)
    ax3.plot(text_univ, text_var['alta'].mf)
    marca(ax3, text_val)
    ax3.grid(True)
    ax3.set_title("Temperatura Externa")

    # CARGA
    ax4.plot(qest_univ, qest_var['baixa'].mf)
    ax4.plot(qest_univ, qest_var['media'].mf)
    ax4.plot(qest_univ, qest_var['alta'].mf)
    marca(ax4, qest_val)
    ax4.grid(True)
    ax4.set_title("Carga Térmica")

    # SAÍDA
    ax5.plot(pcrac_univ, pcrac_var['baixa'].mf)
    ax5.plot(pcrac_univ, pcrac_var['media'].mf)
    ax5.plot(pcrac_univ, pcrac_var['alta'].mf)
    marca(ax5, pcrac_val)
    ax5.grid(True)
    ax5.set_title("Saída PCRAC")

    return fig


# ============================================================
# 5) REGRAS
# ============================================================

regras = [
    ctrl.Rule(erro_var['pos'] & de_var['pos'], pcrac_var['alta']),
    ctrl.Rule(erro_var['pos'] & de_var['zero'], pcrac_var['alta']),
    ctrl.Rule(erro_var['pos'] & de_var['neg'], pcrac_var['media']),

    ctrl.Rule(erro_var['zero'] & de_var['pos'], pcrac_var['alta']),
    ctrl.Rule(erro_var['zero'] & de_var['zero'], pcrac_var['media']),
    ctrl.Rule(erro_var['zero'] & de_var['neg'], pcrac_var['baixa']),

    ctrl.Rule(erro_var['neg'] & de_var['pos'], pcrac_var['media']),
    ctrl.Rule(erro_var['neg'] & de_var['zero'], pcrac_var['baixa']),
    ctrl.Rule(erro_var['neg'] & de_var['neg'], pcrac_var['baixa']),

    ctrl.Rule(text_var['alta'], pcrac_var['alta']),
    ctrl.Rule(text_var['baixa'], pcrac_var['baixa']),

    ctrl.Rule(qest_var['alta'], pcrac_var['alta']),
]

sistema_ctrl = ctrl.ControlSystem(regras)


# ============================================================
# 6) CONTROLADOR FUZZY
# ============================================================

def fuzzy_controller(e, de, Text, Qest, PCRAC_prev):
    sim = ctrl.ControlSystemSimulation(sistema_ctrl)
    sim.input['erro'] = e
    sim.input['de'] = de
    sim.input['text'] = Text
    sim.input['qest'] = Qest
    sim.compute()
    raw = float(sim.output['pcrac'])
    suave = 0.7 * PCRAC_prev + 0.3 * raw
    return suave


# ============================================================
# 7) SIMULAÇÃO 24H (SEM MQTT)
# ============================================================

def temperatura_externa(t):
    t_h = t / 60
    return 25 + 7*np.sin(2*np.pi*(t_h - 9)/24) + random.gauss(0, 0.5)

def carga_termica(t):
    t_h = t / 60
    if 8 <= t_h < 18: base = 80
    elif 18 <= t_h < 23: base = 60
    elif 5 <= t_h < 8: base = 40
    else: base = 20
    return max(0, min(100, base + random.uniform(-2,2)))

def simular_24h(modo_lento=False):
    T = 22
    PCRAC_prev = 50
    e_ant = 0

    ts=[]; Ts=[]; Texts=[]; Qests=[]; PCRACs=[]

    for t in range(1440):
        Text = temperatura_externa(t)
        Qest = carga_termica(t)
        e = T - 22
        de = e - e_ant

        PCRAC = fuzzy_controller(
            max(-15, min(15, e)),
            max(-2, min(2, de)),
            max(10, min(35, Text)),
            max(0, min(100, Qest)),
            PCRAC_prev
        )

        T_next = modelo_fisico(T, PCRAC, Qest, Text)

        ts.append(t/60)
        Ts.append(T)
        Texts.append(Text)
        Qests.append(Qest)
        PCRACs.append(PCRAC)

        if modo_lento:
            time.sleep(0.05)

        T = T_next
        e_ant = e
        PCRAC_prev = PCRAC

    return ts, Ts, Texts, Qests, PCRACs
