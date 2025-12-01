import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import random

# ==========================================
# CONFIGURAÇÕES
# ==========================================
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_ROOT = "datacenter/fuzzy/#"
CLIENT_ID = f"viewer_{random.randint(1000, 9999)}"

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📡 Monitoramento Remoto (Auto-Reset)")
        self.root.geometry("900x650")
        
        # --- DADOS ---
        self.historico_t = []
        self.historico_temp = []
        self.historico_crac = []
        self.latest_temp = 22.0
        self.ultimo_minuto = -1

        # --- ESTILOS ---
        style = ttk.Style()
        style.configure("Big.TLabel", font=("Arial", 24, "bold"))

        # --- HEADER ---
        self.lbl_status = ttk.Label(root, text="Conectando...", foreground="orange", font=("Arial", 10, "bold"))
        self.lbl_status.pack(pady=5)

        # --- CARDS ---
        frm_cards = ttk.Frame(root)
        frm_cards.pack(fill="x", pady=5, padx=10)

        # Temp
        self.card_t = ttk.LabelFrame(frm_cards, text="Temperatura")
        self.card_t.pack(side="left", expand=True, fill="x", padx=5)
        self.lbl_temp = ttk.Label(self.card_t, text="-- °C", style="Big.TLabel", foreground="#d9534f")
        self.lbl_temp.pack(pady=10)

        # CRAC
        self.card_c = ttk.LabelFrame(frm_cards, text="CRAC")
        self.card_c.pack(side="left", expand=True, fill="x", padx=5)
        self.lbl_crac = ttk.Label(self.card_c, text="-- %", style="Big.TLabel", foreground="#0275d8")
        self.lbl_crac.pack(pady=10)

        # Alerta
        self.card_a = ttk.LabelFrame(frm_cards, text="Status")
        self.card_a.pack(side="left", expand=True, fill="x", padx=5)
        self.lbl_alert = ttk.Label(self.card_a, text="AGUARDANDO", font=("Arial", 12, "bold"), foreground="gray")
        self.lbl_alert.pack(pady=15)

        # --- GRÁFICO ---
        self.fig, self.ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.ax2 = self.ax.twinx()
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # --- MQTT ---
        self.client = mqtt.Client(client_id=CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        threading.Thread(target=self.start_mqtt, daemon=True).start()

    def start_mqtt(self):
        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_forever()
        except Exception as e:
            self.lbl_status.config(text=f"Erro: {e}", foreground="red")

    def on_connect(self, client, userdata, flags, rc):
        self.root.after(0, lambda: self.lbl_status.config(text="✅ Monitor Conectado", foreground="green"))
        client.subscribe(TOPIC_ROOT)

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode()

            # 1. TEMPERATURA (Só atualiza variável)
            if "temp" in topic:
                try:
                    self.latest_temp = float(payload)
                    self.root.after(0, lambda: self.update_cards(self.latest_temp, None))
                except: pass

            # 2. CONTROLE (Sincronia e Plotagem)
            elif "control" in topic:
                data = json.loads(payload)
                minuto = data.get('minuto', 0)
                crac = data.get('pcrac', 0)

                # === LÓGICA DE RESET ===
                # Se o minuto atual for MENOR que o último recebido, é uma NOVA simulação.
                if minuto < self.ultimo_minuto:
                    print("Nova simulação detectada! Limpando dados...")
                    self.historico_t.clear()
                    self.historico_temp.clear()
                    self.historico_crac.clear()
                
                self.ultimo_minuto = minuto

                # Adiciona o novo ponto
                self.historico_t.append(minuto/60) # Converter para horas
                self.historico_temp.append(self.latest_temp)
                self.historico_crac.append(crac)

                # Mantém performance (últimos 300 pontos)
                if len(self.historico_t) > 300:
                    self.historico_t.pop(0)
                    self.historico_temp.pop(0)
                    self.historico_crac.pop(0)

                # Atualiza Interface
                self.root.after(0, lambda: self.update_cards(None, crac))
                self.root.after(0, self.update_plot)

            # 3. ALERTA
            elif "alert" in topic:
                d = json.loads(payload)
                self.root.after(0, lambda: self.lbl_alert.config(text=f"⚠️ {d.get('msg')}", foreground="red"))

        except Exception as e:
            print(f"Erro msg: {e}")

    def update_cards(self, temp, crac):
        if temp is not None:
            self.lbl_temp.config(text=f"{temp:.1f} °C")
            if 18 <= temp <= 26:
                self.lbl_alert.config(text="NORMAL", foreground="green")
        if crac is not None:
            self.lbl_crac.config(text=f"{crac:.1f} %")

    def update_plot(self):
        # Limpa TUDO para garantir que não sobrem linhas antigas
        self.ax.clear()
        self.ax2.clear()

        # Se não houver dados, retorna (mas já limpou a tela)
        if not self.historico_t:
            self.canvas.draw()
            return

        # Plota Temperatura (Vermelho)
        self.ax.plot(self.historico_t, self.historico_temp, 'r-', linewidth=1.5, label="Temp")
        self.ax.set_ylim(10, 40)
        self.ax.set_ylabel("Temp (°C)", color='r', fontsize=10)
        self.ax.set_xlabel("Tempo (Horas)", fontsize=10)
        self.ax.grid(True, linestyle=':', alpha=0.6)

        # Linhas de Referência
        self.ax.axhline(22, color='green', linestyle='--', alpha=0.5, linewidth=1)
        self.ax.axhline(26, color='orange', linestyle=':', alpha=0.8)
        self.ax.axhline(18, color='orange', linestyle=':', alpha=0.8)

        # Plota CRAC (Azul)
        self.ax2.plot(self.historico_t, self.historico_crac, 'b-', alpha=0.3, linewidth=1, label="CRAC")
        self.ax2.set_ylim(0, 100)
        self.ax2.set_ylabel("CRAC (%)", color='b', fontsize=10)

        self.ax.set_title(f"Monitoramento: {len(self.historico_t)} min recebidos")
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()