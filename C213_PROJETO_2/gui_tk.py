import tkinter as tk
from tkinter import ttk, messagebox
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
    criar_graficos_mf,  # Importando a função restaurada
    get_temp_externa,
    get_carga_termica
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
        lbl_status_mqtt.config(text="MQTT: ONLINE (Enviando)", foreground="green")
    except:
        lbl_status_mqtt.config(text="MQTT: OFFLINE", foreground="red")

def publicar_mqtt(t, temp, crac, carga, erro):
    if not client_mqtt.is_connected(): return
    
    # Tópicos conforme PDF
    base = "datacenter/fuzzy"
    client_mqtt.publish(f"{base}/temp", round(temp, 2))
    
    payload = json.dumps({"minuto": t, "pcrac": round(crac,2), "carga": round(carga,2), "erro": round(erro,2)})
    client_mqtt.publish(f"{base}/control", payload)
    
    if temp < 18 or temp > 26:
        client_mqtt.publish(f"{base}/alert", json.dumps({"msg": "TEMP CRITICA", "val": temp}))

# ==========================================
# FUNÇÕES DE INTERFACE (MANUAL)
# ==========================================
manual_prev = 50.0

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
        # Usa o valor calculado atual ou o anterior
        pcrac = manual_prev
        
        fig = criar_graficos_mf(e, de, ext, c, pcrac)
        plt.show() # Abre em janela separada do Matplotlib para melhor visualização
    except Exception as x:
        messagebox.showerror("Erro", str(x))

def abrir_monitor_externo():
    script = "monitoramento_viewer.py"
    if not os.path.exists(script):
        messagebox.showerror("Erro", f"Arquivo {script} não encontrado!")
        return
    try:
        if os.name == 'nt':
            subprocess.Popen([sys.executable, script], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(["x-terminal-emulator", "-e", sys.executable, script])
    except Exception as e:
        messagebox.showerror("Erro", str(e))

# ==========================================
# FUNÇÕES DE SIMULAÇÃO (THREAD)
# ==========================================
simulando = False
dados_x, dados_y1, dados_y2 = [], [], []

def thread_simulacao():
    global simulando
    simulando = True
    btn_sim_start.config(state="disabled")
    
    dados_x.clear(); dados_y1.clear(); dados_y2.clear()
    ax1.clear(); ax2.clear()
    
    T = 22.0
    Prev = 50.0
    e_ant = 0
    
    for t in range(1440):
        if not simulando: break
        
        ext = get_temp_externa(t)
        qest = get_carga_termica(t)
        erro = T - 22.0
        de = erro - e_ant
        
        PCRAC = fuzzy_controller(
            max(-16, min(16, erro)), max(-2, min(2, de)),
            max(10, min(35, ext)), max(0, min(100, qest)), Prev
        )
        
        T_next = modelo_fisico(T, PCRAC, qest, ext)
        
        # Envia MQTT
        publicar_mqtt(t, T, PCRAC, qest, erro)
        
        # Atualiza GUI
        dados_x.append(t/60)
        dados_y1.append(T)
        dados_y2.append(PCRAC)
        
        if t % 15 == 0: # Atualiza visual a cada 15 min simulados
            root.after(0, atualizar_grafico_sim, T, PCRAC)
            time.sleep(0.02)
            
        T = T_next
        e_ant = erro
        Prev = PCRAC
        
    simulando = False
    root.after(0, lambda: btn_sim_start.config(state="normal"))

def parar_simulacao():
    global simulando
    simulando = False

def atualizar_grafico_sim(temp, crac):
    ax1.clear(); ax2.clear()
    
    ax1.plot(dados_x, dados_y1, 'r-', label="Temp")
    ax1.axhline(22, color='g', linestyle='--', alpha=0.5)
    ax1.axhline(26, color='orange', linestyle=':')
    ax1.axhline(18, color='orange', linestyle=':')
    ax1.set_ylabel("Temp (°C)", color='r')
    ax1.set_ylim(16, 28)
    
    ax2_twin = ax1.twinx()
    ax2_twin.plot(dados_x, dados_y2, 'b-', label="CRAC", alpha=0.3)
    ax2_twin.set_ylim(0, 100)
    ax2_twin.set_ylabel("CRAC (%)", color='b')
    
    ax1.set_title(f"Simulação 24h (T: {temp:.1f}°C)")
    canvas.draw()

# ==========================================
# INTERFACE GRÁFICA PRINCIPAL
# ==========================================
root = tk.Tk()
root.title("Sistema Fuzzy Data Center (Completo)")
root.geometry("950x650")

# Conecta MQTT no início
threading.Thread(target=conectar_mqtt, daemon=True).start()

# --- SISTEMA DE ABAS ---
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

# ==========================================
# ABA 1: CONTROLE MANUAL & GRÁFICOS MF
# ==========================================
tab_manual = ttk.Frame(notebook)
notebook.add(tab_manual, text="🎛️ Manual & MFs")

frm_inputs = ttk.LabelFrame(tab_manual, text="Entradas do Controlador")
frm_inputs.pack(padx=20, pady=20, fill="x")

# Sliders (Inputs)
sld_erro = tk.Scale(frm_inputs, from_=-16, to=16, orient="horizontal", label="Erro (e)", length=400, resolution=0.1)
sld_erro.pack(pady=5)

sld_de = tk.Scale(frm_inputs, from_=-2, to=2, orient="horizontal", label="Delta Erro (de)", length=400, resolution=0.1)
sld_de.pack(pady=5)

sld_text = tk.Scale(frm_inputs, from_=10, to=35, orient="horizontal", label="Temp. Externa", length=400, resolution=0.5)
sld_text.pack(pady=5)

sld_qest = tk.Scale(frm_inputs, from_=0, to=100, orient="horizontal", label="Carga Térmica %", length=400, resolution=1)
sld_qest.pack(pady=5)

# Botões e Resultado
frm_actions = ttk.Frame(tab_manual)
frm_actions.pack(pady=10)

ttk.Button(frm_actions, text="CALCULAR SAÍDA", command=calcular_manual).pack(side="left", padx=10)
ttk.Button(frm_actions, text="📈 VER GRÁFICOS DE PERTINÊNCIA", command=mostrar_graficos_mf).pack(side="left", padx=10)

var_res_manual = tk.StringVar(value="-- %")
ttk.Label(tab_manual, text="Saída PCRAC:", font=("Arial", 12)).pack(pady=5)
ttk.Label(tab_manual, textvariable=var_res_manual, font=("Arial", 20, "bold"), foreground="blue").pack()


# ==========================================
# ABA 2: SIMULAÇÃO 24H & MQTT
# ==========================================
tab_sim = ttk.Frame(notebook)
notebook.add(tab_sim, text="📊 Simulação & MQTT")

# Header Status
frm_head = ttk.Frame(tab_sim)
frm_head.pack(fill="x", padx=10, pady=5)
lbl_status_mqtt = ttk.Label(frm_head, text="MQTT: ...", font=("Arial", 10, "bold"))
lbl_status_mqtt.pack(side="right")

# Botões de Simulação
frm_ctrl_sim = ttk.LabelFrame(tab_sim, text="Controle")
frm_ctrl_sim.pack(fill="x", padx=10, pady=5)

btn_sim_start = ttk.Button(frm_ctrl_sim, text="▶ INICIAR SIMULAÇÃO 24H", command=lambda: threading.Thread(target=thread_simulacao, daemon=True).start())
btn_sim_start.pack(side="left", padx=10, pady=10)

ttk.Button(frm_ctrl_sim, text="⏹ PARAR", command=parar_simulacao).pack(side="left", padx=10)

ttk.Separator(frm_ctrl_sim, orient="vertical").pack(side="left", fill="y", padx=10, pady=5)

ttk.Button(frm_ctrl_sim, text="📡 ABRIR MONITOR EXTERNO", command=abrir_monitor_externo).pack(side="left", padx=10)

# Gráfico
fig, ax1 = plt.subplots(figsize=(8, 4), dpi=100)
ax2 = ax1.twinx()
canvas = FigureCanvasTkAgg(fig, master=tab_sim)
canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

root.mainloop()