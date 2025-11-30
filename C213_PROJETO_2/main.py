# main.py – BIBLIOTECA MATEMÁTICA
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt
import random

# --- CONFIGURAÇÃO FUZZY ---
erro_univ = np.linspace(-10, 10, 100)
de_univ = np.linspace(-2, 2, 100)
text_univ = np.linspace(10, 35, 100)
qest_univ = np.linspace(0, 100, 100)
pcrac_univ = np.linspace(0, 100, 100)

erro_var = ctrl.Antecedent(erro_univ, 'erro')
de_var = ctrl.Antecedent(de_univ, 'de')
text_var = ctrl.Antecedent(text_univ, 'text')
qest_var = ctrl.Antecedent(qest_univ, 'qest')
pcrac_var = ctrl.Consequent(pcrac_univ, 'pcrac')

# MFs (Funções de Pertinência)
erro_var['neg'] = fuzz.trimf(erro_univ, [-10, -10, 0])
erro_var['zero'] = fuzz.trimf(erro_univ, [-1, 0, 1])
erro_var['pos'] = fuzz.trimf(erro_univ, [0, 16, 16])

de_var['neg'] = fuzz.trimf(de_univ, [-2, -2, 0])
de_var['zero'] = fuzz.trimf(de_univ, [-0.5, 0, 0.5])
de_var['pos'] = fuzz.trimf(de_univ, [0, 2, 2])

text_var['baixa'] = fuzz.trimf(text_univ, [10, 10, 20])
text_var['media'] = fuzz.trimf(text_univ, [15, 22, 30])
text_var['alta'] = fuzz.trimf(text_univ, [25, 35, 35])

qest_var['baixa'] = fuzz.trimf(qest_univ, [0, 0, 40])
qest_var['media'] = fuzz.trimf(qest_univ, [20, 50, 80])
qest_var['alta'] = fuzz.trimf(qest_univ, [60, 100, 100])

pcrac_var['baixa'] = fuzz.trimf(pcrac_univ, [0, 0, 40])
pcrac_var['media'] = fuzz.trimf(pcrac_univ, [20, 50, 80])
pcrac_var['alta'] = fuzz.trimf(pcrac_univ, [60, 100, 100])

# Regras
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

sistema = ctrl.ControlSystem(regras)
simulador = ctrl.ControlSystemSimulation(sistema)

# --- FUNÇÕES LÓGICAS ---
def fuzzy_controller(e, de, Text, Qest, Prev):
    simulador.input['erro'] = e
    simulador.input['de'] = de
    simulador.input['text'] = Text
    simulador.input['qest'] = Qest
    try:
        simulador.compute()
        raw = float(simulador.output['pcrac'])
    except:
        raw = Prev
    return 0.7 * Prev + 0.3 * raw

def modelo_fisico(T_atual, PCRAC, Qest, Text):
    return 0.9*T_atual - 0.08*PCRAC + 0.05*Qest + 0.02*Text + 3.5

def criar_graficos_mf(e, de, ext, c, p):
    fig, axes = plt.subplots(3, 2, figsize=(10, 12))
    plt.subplots_adjust(hspace=0.5)
    # Exemplo simplificado de plotagem para funcionar a chamada
    axes[0,0].plot(erro_univ, erro_var['zero'].mf); axes[0,0].set_title("Erro")
    axes[0,0].axvline(e, color='r')
    return fig

# --- CENÁRIOS DIÁRIOS ---
def get_temp_externa(t):
    t_h = t / 60
    return 25 + 7*np.sin(2*np.pi*(t_h - 9)/24) + random.gauss(0, 0.5)

def get_carga_termica(t):
    t_h = t / 60
    # Interpolando perfil suave
    horas = [0, 6, 12, 18, 24]
    cargas = [20, 30, 80, 70, 20]
    base = np.interp(t_h, horas, cargas)
    return max(0, min(100, base + random.uniform(-2,2)))