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

# Regras (Mamdani via skfuzzy)
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

# --- FUNÇÃO CONTROLADOR (USADA NA SIMULAÇÃO) ---
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

# --- MODELO FÍSICO ---
def modelo_fisico(T_atual, PCRAC, Qest, Text):
    return 0.9*T_atual - 0.08*PCRAC + 0.05*Qest + 0.02*Text + 3.5

# --- GRÁFICOS DAS FUNÇÕES DE PERTINÊNCIA ---
def criar_graficos_mf(e, de, ext, c, p):
    fig, axes = plt.subplots(5, 1, figsize=(8, 14))
    fig.suptitle("Funções de Pertinência - Controlador Fuzzy", fontsize=14)

    # 1. Erro
    axes[0].plot(erro_univ, erro_var['neg'].mf, label="Negativo")
    axes[0].plot(erro_univ, erro_var['zero'].mf, label="Zero")
    axes[0].plot(erro_univ, erro_var['pos'].mf, label="Positivo")
    axes[0].axvline(e, color='red', linestyle='--', label="Entrada Atual")
    axes[0].set_title("Erro (e)")
    axes[0].legend()

    # 2. Delta Erro
    axes[1].plot(de_univ, de_var['neg'].mf, label="Negativo")
    axes[1].plot(de_univ, de_var['zero'].mf, label="Zero")
    axes[1].plot(de_univ, de_var['pos'].mf, label="Positivo")
    axes[1].axvline(de, color='red', linestyle='--')
    axes[1].set_title("Delta do Erro (de)")
    axes[1].legend()

    # 3. Temperatura Externa
    axes[2].plot(text_univ, text_var['baixa'].mf, label="Baixa")
    axes[2].plot(text_univ, text_var['media'].mf, label="Média")
    axes[2].plot(text_univ, text_var['alta'].mf, label="Alta")
    axes[2].axvline(ext, color='red', linestyle='--')
    axes[2].set_title("Temperatura Externa")
    axes[2].legend()

    # 4. Carga Térmica
    axes[3].plot(qest_univ, qest_var['baixa'].mf, label="Baixa")
    axes[3].plot(qest_univ, qest_var['media'].mf, label="Média")
    axes[3].plot(qest_univ, qest_var['alta'].mf, label="Alta")
    axes[3].axvline(c, color='red', linestyle='--')
    axes[3].set_title("Carga Térmica (%)")
    axes[3].legend()

    # 5. Saída PCRAC
    axes[4].plot(pcrac_univ, pcrac_var['baixa'].mf, label="Baixa")
    axes[4].plot(pcrac_univ, pcrac_var['media'].mf, label="Média")
    axes[4].plot(pcrac_univ, pcrac_var['alta'].mf, label="Alta")
    axes[4].axvline(p, color='red', linestyle='--')
    axes[4].set_title("Ação do CRAC (%)")
    axes[4].legend()

    plt.tight_layout()
    return fig

# --- DEBUG / VISUALIZAÇÃO DO PROCESSO DE INFERÊNCIA ---
# Definição textual das regras para depuração
_REGRAS_DEBUG = [
    {
        "desc": "Se erro é POS e de é POS então PCRAC é ALTA",
        "ants": [("erro", "pos"), ("de", "pos")],
        "out": "alta",
    },
    {
        "desc": "Se erro é POS e de é ZERO então PCRAC é ALTA",
        "ants": [("erro", "pos"), ("de", "zero")],
        "out": "alta",
    },
    {
        "desc": "Se erro é POS e de é NEG então PCRAC é MÉDIA",
        "ants": [("erro", "pos"), ("de", "neg")],
        "out": "media",
    },
    {
        "desc": "Se erro é ZERO e de é POS então PCRAC é ALTA",
        "ants": [("erro", "zero"), ("de", "pos")],
        "out": "alta",
    },
    {
        "desc": "Se erro é ZERO e de é ZERO então PCRAC é MÉDIA",
        "ants": [("erro", "zero"), ("de", "zero")],
        "out": "media",
    },
    {
        "desc": "Se erro é ZERO e de é NEG então PCRAC é BAIXA",
        "ants": [("erro", "zero"), ("de", "neg")],
        "out": "baixa",
    },
    {
        "desc": "Se erro é NEG e de é POS então PCRAC é MÉDIA",
        "ants": [("erro", "neg"), ("de", "pos")],
        "out": "media",
    },
    {
        "desc": "Se erro é NEG e de é ZERO então PCRAC é BAIXA",
        "ants": [("erro", "neg"), ("de", "zero")],
        "out": "baixa",
    },
    {
        "desc": "Se erro é NEG e de é NEG então PCRAC é BAIXA",
        "ants": [("erro", "neg"), ("de", "neg")],
        "out": "baixa",
    },
    {
        "desc": "Se Temperatura Externa é ALTA então PCRAC é ALTA",
        "ants": [("text", "alta")],
        "out": "alta",
    },
    {
        "desc": "Se Temperatura Externa é BAIXA então PCRAC é BAIXA",
        "ants": [("text", "baixa")],
        "out": "baixa",
    },
    {
        "desc": "Se Carga Térmica é ALTA então PCRAC é ALTA",
        "ants": [("qest", "alta")],
        "out": "alta",
    },
]

def fuzzy_debug(e, de, Text, Qest):
    """
    Calcula manualmente:
      - grau de ativação de cada regra (min dos antecedentes)
      - função de saída agregada (max das contribuições)
      - ponto de defuzzificação (centróide)
    Retorna um dicionário para visualização no GUI.
    """
    # Cálculo dos graus de pertinência das entradas
    mus = {
        "erro": {
            "neg": fuzz.interp_membership(erro_univ, erro_var["neg"].mf, e),
            "zero": fuzz.interp_membership(erro_univ, erro_var["zero"].mf, e),
            "pos": fuzz.interp_membership(erro_univ, erro_var["pos"].mf, e),
        },
        "de": {
            "neg": fuzz.interp_membership(de_univ, de_var["neg"].mf, de),
            "zero": fuzz.interp_membership(de_univ, de_var["zero"].mf, de),
            "pos": fuzz.interp_membership(de_univ, de_var["pos"].mf, de),
        },
        "text": {
            "baixa": fuzz.interp_membership(text_univ, text_var["baixa"].mf, Text),
            "media": fuzz.interp_membership(text_univ, text_var["media"].mf, Text),
            "alta": fuzz.interp_membership(text_univ, text_var["alta"].mf, Text),
        },
        "qest": {
            "baixa": fuzz.interp_membership(qest_univ, qest_var["baixa"].mf, Qest),
            "media": fuzz.interp_membership(qest_univ, qest_var["media"].mf, Qest),
            "alta": fuzz.interp_membership(qest_univ, qest_var["alta"].mf, Qest),
        },
    }

    saidas_mf = {
        "baixa": pcrac_var["baixa"].mf,
        "media": pcrac_var["media"].mf,
        "alta": pcrac_var["alta"].mf,
    }

    agregado = np.zeros_like(pcrac_univ)
    debug_regras = []

    for reg in _REGRAS_DEBUG:
        # Grau de ativação = min dos antecedentes
        graus = []
        for (var, termo) in reg["ants"]:
            graus.append(mus[var][termo])
        if len(graus) == 0:
            alpha = 0.0
        else:
            alpha = min(graus)

        # Armazena para visualização textual
        debug_regras.append({
            "descricao": reg["desc"],
            "alpha": float(alpha),
        })

        # Saída da regra (clipping na MF da saída)
        if alpha > 0:
            mf_saida = saidas_mf[reg["out"]]
            contrib = np.fmin(alpha, mf_saida)
            agregado = np.fmax(agregado, contrib)

    # Defuzzificação (centróide)
    if agregado.sum() > 0:
        p_defuzz = float(np.sum(agregado * pcrac_univ) / np.sum(agregado))
    else:
        p_defuzz = 0.0

    return {
        "regras": debug_regras,
        "agregado": agregado,
        "universo": pcrac_univ,
        "p_defuzz": p_defuzz,
        "mus_entrada": mus,
    }

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
