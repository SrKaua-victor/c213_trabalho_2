# monitoramento_viewer.py – GUI DE MONITORAMENTO REMOTO
import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

# Configuração MQTT
BROKER = "broker.hivemq.com"
TOPIC_ROOT = "datacenter/fuzzy/#"

# Variáveis Globais de Dados
historico_t = []
historico_temp = []
historico_crac = []

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📡 Dashboard Remoto - Data Center (MQTT)")
        self.root.geometry("800x600")
        
        # Estilos
        style = ttk.Style()
        style.configure("Card.TFrame", relief="ridge", borderwidth=2)
        style.configure("Big.TLabel", font=("Arial", 24, "bold"))
        style.configure("Title.TLabel", font=("Arial", 12))

        # --- HEADER ---
        self.lbl_status = ttk.Label(root, text="Aguardando conexão MQTT...", foreground="orange", font=("Arial", 10, "bold"))
        self.lbl_status.pack(pady=5)

        # --- CARDS DE VALORES ---
        frm_cards = ttk.Frame(root)
        frm_cards.pack(fill="x", pady=10, padx=10)

        # Card Temperatura
        self.card_temp = ttk.LabelFrame(frm_cards, text="Temperatura Interna")
        self.card_temp.pack(side="left", expand=True, fill="x", padx=5)
        self.lbl_temp = ttk.Label(self.card_temp, text="-- °C", style="Big.TLabel", foreground="#d9534f")
        self.lbl_temp.pack(pady=10)

        # Card CRAC
        self.card_crac = ttk.LabelFrame(frm_cards, text="Potência CRAC")
        self.card_crac.pack(side="left", expand=True, fill="x", padx=5)
        self.lbl_crac = ttk.Label(self.card_crac, text="-- %", style="Big.TLabel", foreground="#0275d8")
        self.lbl_crac.pack(pady=10)

        # Card Status
        self.card_stat = ttk.LabelFrame(frm_cards, text="Estado do Sistema")
        self.card_stat.pack(side="left", expand=True, fill="x", padx=5)
        self.lbl_alert = ttk.Label(self.card_stat, text="AGUARDANDO", font=("Arial", 14, "bold"), foreground="gray")
        self.lbl_alert.pack(pady=15)

        # --- GRÁFICO ---
        self.fig, self.ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.ax2 = self.ax.twinx()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        # Iniciar MQTT
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Thread para não travar a GUI
        threading.Thread(target=self.start_mqtt, daemon=True).start()

    def start_mqtt(self):
        try:
            self.client.connect(BROKER, 1883, 60)
            self.client.loop_forever()
        except Exception as e:
            self.lbl_status.config(text=f"Erro MQTT: {e}", foreground="red")

    def on_connect(self, client, userdata, flags, rc):
        self.root.after(0, lambda: self.lbl_status.config(text="✅ Conectado ao Broker MQTT", foreground="green"))
        client.subscribe(TOPIC_ROOT)

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            
            if "control" in topic:
                data = json.loads(payload)
                # Atualiza Gráficos
                minuto = data.get('minuto', 0)
                crac = data.get('pcrac', 0)
                
                # Adiciona ao histórico (limitando a 100 pontos para performance)
                historico_t.append(minuto/60) # Horas
                historico_crac.append(crac)
                if len(historico_t) > 100: 
                    historico_t.pop(0); historico_crac.pop(0)

                # Atualiza GUI na thread principal
                self.root.after(0, lambda: self.update_crac(crac))
                
            elif "temp" in topic:
                temp = float(payload)
                historico_temp.append(temp)
                if len(historico_temp) > 100: historico_temp.pop(0)
                
                self.root.after(0, lambda: self.update_temp(temp))
                self.root.after(0, self.update_plot)
                
            elif "alert" in topic:
                data = json.loads(payload)
                msg_alerta = data.get('msg', 'ALERTA')
                self.root.after(0, lambda: self.trigger_alert(msg_alerta))
                
        except Exception as e:
            print(f"Erro decode: {e}")

    def update_temp(self, val):
        self.lbl_temp.config(text=f"{val:.1f} °C")
        # Resetar alerta se normal
        if 18 <= val <= 26:
            self.lbl_alert.config(text="NORMAL", foreground="green")

    def update_crac(self, val):
        self.lbl_crac.config(text=f"{val:.1f} %")

    def trigger_alert(self, msg):
        self.lbl_alert.config(text=f"⚠️ {msg}", foreground="red")

    def update_plot(self):
        # Redesenha o gráfico se os dados estiverem sincronizados
        if len(historico_t) == len(historico_temp) and len(historico_t) > 0:
            self.ax.clear(); self.ax2.clear()
            
            self.ax.plot(historico_t, historico_temp, 'r-', label="Temp")
            self.ax.set_ylim(15, 30)
            self.ax.set_ylabel("Temp (°C)", color='r')
            
            self.ax.axhline(22, color='g', linestyle='--', alpha=0.3)
            self.ax.axhline(26, color='orange', linestyle=':', alpha=0.5)
            self.ax.axhline(18, color='orange', linestyle=':', alpha=0.5)

            self.ax2.plot(historico_t, historico_crac, 'b-', alpha=0.3, label="CRAC")
            self.ax2.set_ylim(0, 100)
            self.ax2.set_ylabel("CRAC (%)", color='b')
            
            self.ax.set_title(f"Monitoramento em Tempo Real (Últimos {len(historico_t)} min)")
            self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = DashboardApp(root)
    root.mainloop()