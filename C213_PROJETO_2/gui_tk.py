# gui_tk.py – Tkinter + Ubidots MQTT + Fuzzy + Gráficos (VERSÃO FINAL)
import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import time
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt

from main import (
    fuzzy_controller,
    criar_graficos_mf,
    simular_24h
)

# ==========================================
# CONFIG MQTT UBIDOTS
# ==========================================

UBIDOTS_TOKEN = "BBUS-WwyOU1nsEDFECqPV8bM27l8MLeaLa6"
UBIDOTS_BROKER = "industrial.api.ubidots.com"
UBIDOTS_PORT = 1883

# Cada variável tem SEU PRÓPRIO tópico (correto para atualização)
TOPIC_ERRO = "/v1.6/devices/datacenter/erro"
TOPIC_CARGA = "/v1.6/devices/datacenter/carga"
TOPIC_CRAC = "/v1.6/devices/datacenter/crac"


def publicar_ubidots(erro, carga, crac):
    """Envia valores para o Ubidots SEM criar novas variáveis."""
    try:
        client = mqtt.Client()
        client.username_pw_set(UBIDOTS_TOKEN, "")
        client.connect(UBIDOTS_BROKER, UBIDOTS_PORT, 60)

        # timestamp obrigatório para registrar SEMPRE
        ts = int(time.time() * 1000)

        # Atualiza erro
        client.publish(
            TOPIC_ERRO,
            json.dumps({"value": float(erro), "timestamp": ts})
        )

        # Atualiza carga
        client.publish(
            TOPIC_CARGA,
            json.dumps({"value": float(carga), "timestamp": ts})
        )

        # Atualiza CRAC
        client.publish(
            TOPIC_CRAC,
            json.dumps({"value": float(crac), "timestamp": ts})
        )

        client.disconnect()

        print("[UBIDOTS] ENVIADO:",
              {"erro": erro, "carga": carga, "crac": crac})

    except Exception as e:
        print("[UBIDOTS] ERRO:", e)


# ==========================================
# CONTROLE FUZZY
# ==========================================

PCRAC_prev = 50.0
PCRAC_ultimo = 50.0


def calcular_fuzzy():
    """Calcula fuzzy e envia SEMPRE ao Ubidots."""
    global PCRAC_prev, PCRAC_ultimo

    try:
        erro = erro_slider.get()
        de = de_slider.get()
        text = text_slider.get()
        qest = qest_slider.get()

        # Cálculo fuzzy
        PCRAC = fuzzy_controller(erro, de, text, qest, PCRAC_prev)

        PCRAC_prev = PCRAC
        PCRAC_ultimo = PCRAC

        # Atualiza visual
        resultado_var.set(f"{PCRAC:.2f}%")

        # Envia para Ubidots (SEM criar duplicatas)
        publicar_ubidots(erro, qest, PCRAC)

    except Exception as e:
        print("❌ Erro Fuzzy:", e)


def mostrar_mf():
    """Mostra funções de pertinência."""
    try:
        fig = criar_graficos_mf(
            erro_slider.get(),
            de_slider.get(),
            text_slider.get(),
            qest_slider.get(),
            PCRAC_ultimo
        )
        plt.show()
    except Exception as e:
        messagebox.showerror("Erro MF", str(e))


# ==========================================
# SIMULAÇÃO 24H (THREAD)
# ==========================================

def _thread_simulacao():
    """Roda simulação sem travar interface."""
    try:
        ts, Ts, Texts, Qests, PCRACs = simular_24h()

        def mostrar():
            fig1, ax1 = plt.subplots(figsize=(10, 4))
            ax1.plot(ts, Ts, label="Temperatura Interna")
            ax1.plot(ts, Texts, label="Temperatura Externa")
            ax1.grid(True)
            ax1.legend()

            fig2, ax2 = plt.subplots(figsize=(10, 4))
            ax2.plot(ts, Qests, label="Carga Térmica")
            ax2.plot(ts, PCRACs, label="PCRAC")
            ax2.grid(True)
            ax2.legend()

            plt.show()

        root.after(0, mostrar)

    except Exception as e:
        messagebox.showerror("Erro Simulação", str(e))


def simular_async():
    threading.Thread(target=_thread_simulacao, daemon=True).start()


# ==========================================
# INTERFACE TKINTER
# ==========================================

root = tk.Tk()
root.title("Controle Fuzzy – Ubidots + Tkinter (Versão Final)")
root.geometry("780x420")

titulo = ttk.Label(
    root,
    text="Sistema Fuzzy – Data Center\nTkinter + MQTT Ubidots",
    font=("Segoe UI", 14, "bold")
)
titulo.pack(pady=10)


frame = ttk.LabelFrame(root, text="Entradas do Controlador Fuzzy")
frame.pack(pady=10, fill="x")

erro_slider = tk.Scale(frame, from_=-16, to=16, orient="horizontal",
                       length=180, resolution=0.1, label="Erro")
erro_slider.grid(row=0, column=0, padx=10)

de_slider = tk.Scale(frame, from_=-2, to=2, orient="horizontal",
                     length=180, resolution=0.1, label="Delta Erro")
de_slider.grid(row=0, column=1, padx=10)

text_slider = tk.Scale(frame, from_=10, to=35, orient="horizontal",
                       length=180, resolution=0.5, label="Temp Externa")
text_slider.grid(row=0, column=2, padx=10)

qest_slider = tk.Scale(frame, from_=0, to=100, orient="horizontal",
                       length=180, resolution=1, label="Carga Térmica")
qest_slider.grid(row=0, column=3, padx=10)


# Resultado PCRAC
resultado_var = tk.StringVar(value="--%")

ttk.Label(root, text="Saída Fuzzy (PCRAC):", font=("Segoe UI", 11)).pack()
ttk.Label(root, textvariable=resultado_var,
          font=("Segoe UI", 14, "bold"), foreground="blue").pack()


# Botões
botoes = ttk.Frame(root)
botoes.pack(pady=10)

ttk.Button(botoes, text="Calcular Fuzzy + Enviar Ubidots",
           command=calcular_fuzzy).grid(row=0, column=0, padx=10)

ttk.Button(botoes, text="Ver Funções de Pertinência",
           command=mostrar_mf).grid(row=0, column=1, padx=10)

ttk.Button(botoes, text="Simular 24h",
           command=simular_async).grid(row=0, column=2, padx=10)


root.mainloop()
