import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.rcParams["toolbar"] = "none"  # Remove a toolbar
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import paho.mqtt.client as mqtt
import threading
import time
import json
import subprocess
import sys
import os

from main import (
    fuzzy_controller,
    modelo_fisico,
    criar_graficos_mf,
    get_temp_externa,
    get_carga_termica,
    fuzzy_debug,
)

# ==========================================
# CONFIGURAÇÃO MQTT (REMETENTE)
# ==========================================
MQTT_BROKER = "broker.hivemq.com"
client_mqtt = mqtt.Client()

def conectar_mqtt():
    try:
        client_mqtt.connect(MQTT_BROKER, 1883, 60)
        client_mqtt.loop_start()
        try:
            lbl_status_mqtt.config(text="MQTT: ONLINE (Enviando)", foreground="green")
        except:
            pass
    except:
        try:
            lbl_status_mqtt.config(text="MQTT: OFFLINE", foreground="red")
        except:
            pass

def publicar_mqtt(t, temp, crac, carga, erro):
    if not client_mqtt.is_connected():
        return

    base = "datacenter/fuzzy"
    client_mqtt.publish(f"{base}/temp", round(temp, 2))

    payload = json.dumps({
        "minuto": t,
        "pcrac": round(crac, 2),
        "carga": round(carga, 2),
        "erro": round(erro, 2)
    })
    client_mqtt.publish(f"{base}/control", payload)

    if temp < 18 or temp > 26:
        client_mqtt.publish(f"{base}/alert",
            json.dumps({"msg": "TEMP CRITICA", "val": temp})
        )

# ==========================================
# FUNÇÕES DE INTERFACE (MANUAL)
# ==========================================
manual_prev = 50.0

def resetar_valores():
    sld_erro.set(0)
    sld_de.set(0)
    sld_text.set(25)
    sld_qest.set(40)
    var_res_manual.set("-- %")

def calcular_manual():
    global manual_prev
    try:
        e = sld_erro.get()
        de = sld_de.get()
        ext = sld_text.get()
        c = sld_qest.get()

        res = fuzzy_controller(e, de, ext, c, manual_prev)
        manual_prev = res
        var_res_manual.set(f"{res:.2f}%")

    except Exception as e:
        messagebox.showerror("Erro", str(e))


def mostrar_graficos_mf():
    try:
        e = sld_erro.get()
        de = sld_de.get()
        ext = sld_text.get()
        c = sld_qest.get()

        fig = criar_graficos_mf(e, de, ext, c, manual_prev)
        fig.show()

    except Exception as x:
        messagebox.showerror("Erro", str(x))


def mostrar_regras():
    regras_texto = [
        "1) Se erro é POS e de é POS → PCRAC = ALTA",
        "2) Se erro é POS e de é ZERO → PCRAC = ALTA",
        "3) Se erro é POS e de é NEG → PCRAC = MÉDIA",
        "4) Se erro é ZERO e de é POS → PCRAC = ALTA",
        "5) Se erro é ZERO e de é ZERO → PCRAC = MÉDIA",
        "6) Se erro é ZERO e de é NEG → PCRAC = BAIXA",
        "7) Se erro é NEG e de é POS → PCRAC = MÉDIA",
        "8) Se erro é NEG e de é ZERO → PCRAC = BAIXA",
        "9) Se erro é NEG e de é NEG → PCRAC = BAIXA",
        "10) Se Temp Externa é ALTA → PCRAC = ALTA",
        "11) Se Temp Externa é BAIXA → PCRAC = BAIXA",
        "12) Se Carga Térmica é ALTA → PCRAC = ALTA",
    ]

    win = tk.Toplevel()
    win.title("📜 Regras Fuzzy")
    win.geometry("600x400")

    frame = ttk.Frame(win)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    txt = tk.Text(frame, wrap="word", font=("Arial", 12))
    txt.pack(fill="both", expand=True)

    for r in regras_texto:
        txt.insert("end", r + "\n\n")
    txt.config(state="disabled")


def mostrar_inferencia():
    try:
        e = sld_erro.get()
        de = sld_de.get()
        ext = sld_text.get()
        c = sld_qest.get()

        dbg = fuzzy_debug(e, de, ext, c)

        regras_dbg = dbg["regras"]
        agregado = dbg["agregado"]
        universo = dbg["universo"]
        p_defuzz = dbg["p_defuzz"]

        win = tk.Toplevel()
        win.title("🔍 Processo de Inferência Fuzzy")
        win.geometry("900x600")

        # Título
        frm_top = ttk.Frame(win)
        frm_top.pack(fill="x", padx=10, pady=5)

        lbl_info = ttk.Label(
            frm_top,
            text=f"Entradas: Erro={e:.2f}, dErro={de:.2f}, Text={ext:.2f}, Qest={c:.2f}",
            font=("Arial", 11, "bold")
        )
        lbl_info.pack()

        frm_main = ttk.Frame(win)
        frm_main.pack(fill="both", expand=True)

        # Lista de regras
        frm_r = ttk.LabelFrame(frm_main, text="Regras Ativadas")
        frm_r.pack(side="left", fill="both", expand=True, padx=5)

        txt = tk.Text(frm_r, wrap="word", font=("Arial", 10))
        txt.pack(fill="both", expand=True)

        ordenadas = sorted(regras_dbg, key=lambda r: r["alpha"], reverse=True)
        for r in ordenadas:
            if r["alpha"] > 0:
                txt.insert("end", f"[{r['alpha']:.3f}] {r['descricao']}\n\n")
        txt.config(state="disabled")

        # Gráfico
        frm_g = ttk.LabelFrame(frm_main, text="Saída Agregada + Defuzzificação")
        frm_g.pack(side="left", fill="both", expand=True, padx=5)

        fig = plt.Figure(figsize=(5, 3), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(universo, agregado)
        ax.axvline(p_defuzz, color="red", linestyle="--")
        ax.set_title("Agregação Fuzzy da Saída")

        canvas_local = FigureCanvasTkAgg(fig, master=frm_g)
        canvas_local.get_tk_widget().pack(fill="both", expand=True)
        canvas_local.draw()

    except Exception as e:
        messagebox.showerror("Erro", str(e))


def abrir_monitor_externo():
    script = "monitoramento_viewer.py"
    if os.path.exists(script):
        subprocess.Popen([sys.executable, script], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        messagebox.showerror("Erro", "monitoramento_viewer.py não encontrado!")

# ==========================================
# SIMULAÇÃO 24h
# ==========================================

simulando = False
dados_x = []
dados_y1 = []
dados_y2 = []
dados_ext = []

def thread_simulacao():
    global simulando
    simulando = True
    
    # Trava os controles durante a simulação
    btn_sim_start.config(state="disabled")
    cmb_setpoint.config(state="disabled")
    scale_e_init.config(state="disabled") 

    # 1. Pega o Setpoint
    try:
        sp = float(cmb_setpoint.get())
    except:
        sp = 22.0

    # 2. Pega o ERRO Inicial
    try:
        erro_inicial = float(scale_e_init.get())
    except:
        erro_inicial = 0.0

    dados_x.clear()
    dados_y1.clear()
    dados_y2.clear()
    dados_ext.clear()

    ax1.clear()
    ax2.clear()

    # --- DEFINIÇÃO DA TEMPERATURA INICIAL ---
    # Se Erro = T - Setpoint, então T = Setpoint + Erro
    T = sp + erro_inicial
    
    Prev = 50.0
    e_ant = 0

    for t in range(1440):
        if not simulando:
            break

        ext = get_temp_externa(t)
        qest = get_carga_termica(t)

        # CÁLCULO DO ERRO
        erro = T - sp
        dE = erro - e_ant

        # Controlador Fuzzy
        PCRAC = fuzzy_controller(
            max(-10, min(10, erro)),
            max(-2, min(2, dE)),
            max(10, min(35, ext)),
            max(0, min(100, qest)),
            Prev
        )

        T_next = modelo_fisico(T, PCRAC, qest, ext)

        publicar_mqtt(t, T, PCRAC, qest, erro)

        dados_x.append(t/60)
        dados_y1.append(T)
        dados_y2.append(PCRAC)
        dados_ext.append(ext)

        if t % 15 == 0:
            root.after(0, atualizar_grafico_sim, T, PCRAC, ext, sp)
            time.sleep(0.02)

        Prev = PCRAC
        e_ant = erro
        T = T_next

    simulando = False
    # Destrava os controles
    root.after(0, lambda: btn_sim_start.config(state="normal"))
    root.after(0, lambda: cmb_setpoint.config(state="readonly"))
    root.after(0, lambda: scale_e_init.config(state="normal"))


def parar_simulacao():
    global simulando
    simulando = False


def atualizar_grafico_sim(temp, crac, ext, sp):
    ax1.clear()
    ax2.clear()

    # Temperaturas
    ax1.plot(dados_x, dados_y1, 'r-', label="Temp Interna")
    ax1.plot(dados_x, dados_ext, 'g-', label="Temp Externa")
    
    # Linha do Setpoint
    ax1.axhline(sp, color='black', linestyle='--', alpha=0.5, label=f"Setpoint ({sp}°C)")

    ax1.set_ylabel("Temperatura (°C)")
    ax1.set_ylim(10, 40)
    ax1.legend(loc="upper left")

    # CRAC
    ax2.plot(dados_x, dados_y2, 'b-', alpha=0.4)
    ax2.set_ylabel("CRAC (%)", color="blue")
    ax2.set_ylim(0, 100)

    ax1.set_title(
        f"Simulação 24h (Target: {sp}°C | Erro Atual: {temp-sp:.1f})"
    )

    canvas.draw()


# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
root = tk.Tk()
root.title("Sistema Fuzzy Data Center (Completo)")
root.geometry("1000x700")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# ==========================================
# ABA 1 – MANUAL
# ==========================================
tab_manual = ttk.Frame(notebook)
notebook.add(tab_manual, text="🎛️ Manual & MFs")

frm_inputs = ttk.LabelFrame(tab_manual, text="Entradas do Controlador")
frm_inputs.pack(fill="x", padx=10, pady=10)

sld_erro = tk.Scale(frm_inputs, from_=-10, to=10, orient="horizontal",
                    label="Erro (e)", length=400, resolution=0.1)
sld_erro.pack(pady=5)

sld_de = tk.Scale(frm_inputs, from_=-2, to=2, orient="horizontal",
                  label="Delta Erro (de)", length=400, resolution=0.1)
sld_de.pack(pady=5)

sld_text = tk.Scale(frm_inputs, from_=10, to=35, orient="horizontal",
                    label="Temp Externa", length=400, resolution=0.5)
sld_text.pack(pady=5)

sld_qest = tk.Scale(frm_inputs, from_=0, to=100, orient="horizontal",
                    label="Carga Térmica (%)", length=400, resolution=1)
sld_qest.pack(pady=5)

frm_actions = ttk.Frame(tab_manual)
frm_actions.pack(pady=10)

ttk.Button(frm_actions, text="CALCULAR SAÍDA", command=calcular_manual)\
    .pack(side="left", padx=10)

ttk.Button(frm_actions, text="📈 FUNÇÕES DE PERTINÊNCIA",
           command=mostrar_graficos_mf).pack(side="left", padx=10)

ttk.Button(frm_actions, text="📜 MOSTRAR REGRAS",
           command=mostrar_regras).pack(side="left", padx=10)

ttk.Button(frm_actions, text="🔍 VER INFERÊNCIA",
           command=mostrar_inferencia).pack(side="left", padx=10)

ttk.Button(frm_actions, text="🔄 RESETAR",
           command=resetar_valores).pack(side="left", padx=10)

var_res_manual = tk.StringVar(value="-- %")
ttk.Label(tab_manual, text="Saída PCRAC:", font=("Arial", 12)).pack(pady=5)
ttk.Label(tab_manual, textvariable=var_res_manual,
          font=("Arial", 20, "bold"), foreground="blue").pack()

# ==========================================
# ABA 2 – SIMULAÇÃO
# ==========================================
tab_sim = ttk.Frame(notebook)
notebook.add(tab_sim, text="📊 Simulação & MQTT")

frm_head = ttk.Frame(tab_sim)
frm_head.pack(fill="x", padx=10, pady=5)

lbl_status_mqtt = ttk.Label(frm_head, text="MQTT: ...",
                            font=("Arial", 10, "bold"))
lbl_status_mqtt.pack(side="right")

frm_ctrl = ttk.LabelFrame(tab_sim, text="Controle")
frm_ctrl.pack(fill="x", padx=10, pady=5)

# --- SETPOINT ---
ttk.Label(frm_ctrl, text="Setpoint (°C):", font=("Arial", 10, "bold")).pack(side="left", padx=5)
cmb_setpoint = ttk.Combobox(frm_ctrl, values=["16", "22", "26", "32"], width=5, state="readonly")
cmb_setpoint.current(1) # Padrão 22
cmb_setpoint.pack(side="left", padx=5)

# --- ERRO INICIAL ---
ttk.Label(frm_ctrl, text="Erro Inicial:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
scale_e_init = tk.Scale(frm_ctrl, from_=-10, to=10, orient="horizontal", length=150, resolution=0.5)
scale_e_init.set(0) # Começa estabilizado (Erro 0)
scale_e_init.pack(side="left", padx=5)

ttk.Separator(frm_ctrl, orient="vertical").pack(side="left", fill="y", padx=10)

btn_sim_start = ttk.Button(frm_ctrl,
                           text="▶ INICIAR",
                           command=lambda: threading.Thread(
                               target=thread_simulacao, daemon=True).start())
btn_sim_start.pack(side="left", padx=10, pady=10)

ttk.Button(frm_ctrl, text="⏹ PARAR",
           command=parar_simulacao).pack(side="left", padx=10)

ttk.Separator(frm_ctrl, orient="vertical").pack(side="left",
                                                fill="y",
                                                padx=10)

ttk.Button(frm_ctrl, text="📡 MONITOR",
           command=abrir_monitor_externo).pack(side="left", padx=10)

# Gráfico
fig, ax1 = plt.subplots(figsize=(8, 4), dpi=100)
ax2 = ax1.twinx()

canvas = FigureCanvasTkAgg(fig, master=tab_sim)
canvas.get_tk_widget().pack(fill="both", expand=True)

threading.Thread(target=conectar_mqtt, daemon=True).start()

root.mainloop()