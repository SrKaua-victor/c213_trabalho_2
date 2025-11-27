import time
import matplotlib.pyplot as plt
import streamlit as st
import paho.mqtt.client as mqtt

from main import (
    fuzzy_controller,
    simular_24h,
    criar_graficos_mf,
    publicar_mqtt_temperatura,
    publicar_mqtt_carga,
    publicar_mqtt_crac,
    publicar_mqtt_alerta,
    MQTT_BROKER,
    MQTT_PORT,
)

# ==============================
# CONFIG STREAMLIT
# ==============================
st.set_page_config(
    page_title="Controle Fuzzy – Data Center",
    layout="wide",
)

st.title("❄️ Sistema Fuzzy MISO – Data Center")
st.write("Interface gráfica com simulação, publicação MQTT e (opcionalmente) monitoramento dos tópicos.")


# ==============================
# SIDEBAR – NAVEGAÇÃO
# ==============================
pagina = st.sidebar.radio(
    "Navegação",
    ["Simulação / Controlador", "Monitor MQTT"],
)


# ============================================
# PÁGINA 1 — SIMULAÇÃO / CONTROLADOR
# ============================================
if pagina == "Simulação / Controlador":
    st.header("⚙️ Entradas do Controlador Fuzzy")

    col1, col2, col3, col4 = st.columns(4)

    erro  = col1.slider("Erro (°C)", -16.0, 16.0, 0.0, 0.1)
    de    = col2.slider("Delta Erro (°C/min)", -2.0, 2.0, 0.0, 0.1)
    text  = col3.slider("Temperatura Externa (°C)", 10.0, 35.0, 22.0, 0.5)
    qest  = col4.slider("Carga Térmica (%)", 0.0, 100.0, 50.0, 1.0)

    PCRAC_prev = 50.0

    if st.button("Calcular Fuzzy"):
        PCRAC = fuzzy_controller(erro, de, text, qest, PCRAC_prev)
        st.success(f"Potência do CRAC calculada: **{PCRAC:.2f}%**")

        # Publica também no MQTT (demonstração imediata)
        publicar_mqtt_temperatura(erro)  # aqui poderia ser T real, mas serve p/ teste
        publicar_mqtt_carga(qest)
        publicar_mqtt_crac(PCRAC)
        if erro > 3:
            publicar_mqtt_alerta(f"TEMPERATURA ALTA (modo manual): erro={erro:.2f}°C")

    st.write("---")


    with st.expander("📊 Visualizar Funções de Pertinência"):
        st.write("Clique no botão abaixo para ver o ponto de operação atual nos gráficos.")
    
        if st.button("Gerar Gráficos com Valores Atuais"):
        
        # 1. Primeiro calculamos o Fuzzy com os valores atuais dos sliders
        # Usamos 50 como valor anterior dummy apenas para plotagem instantânea
            pcrac_atual_grafico = fuzzy_controller(erro, de, text, qest, 50.0)
        
        # 2. Chamamos a função passando TODOS os 5 valores
            figura = criar_graficos_mf(erro, de, text, qest, pcrac_atual_grafico)
        
        # 3. Exibimos
            st.pyplot(figura)
        
            st.info(f"Visualizando para: Erro={erro}, dE={de}, Text={text}, Qest={qest} -> Saída PCRAC={pcrac_atual_grafico:.2f}%")

    st.header("📈 Simulação Completa de 24 Horas")

    # Checkbox para ativar o envio lento MQTT
    usar_mqtt = st.checkbox("Ativar Modo Demo MQTT (Simulação lenta para monitoramento)")

    if st.button("Rodar Simulação 24h"):
        with st.spinner("Simulando..."):
            # Passa o valor do checkbox para a função
            ts, Ts, Texts, Qests, PCRACs = simular_24h(modo_lento=usar_mqtt) 
        
        st.success("Simulação concluída!")
        # ... (código dos gráficos continua igual) ...

        # --- GRÁFICO 1: TEMPERATURAS ---
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        
        # Linha Azul: Temperatura Interna
        ax1.plot(ts, Ts, label="Temperatura Interna (°C)", color='blue', linewidth=2)
        
        # Linha Laranja: Temperatura Externa
        ax1.plot(ts, Texts, ':', label="Temp. Externa (°C)", color='orange', linewidth=1)

        # Linhas de referência (Limites)
        ax1.axhline(y=26, color='red', linestyle='-', linewidth=0.8, alpha=0.5, label="Limites (18-26°C)")
        ax1.axhline(y=18, color='red', linestyle='-', linewidth=0.8, alpha=0.5)

        ax1.set_xlabel("Tempo (h)")
        ax1.set_ylabel("Temperatura (°C)")
        ax1.set_title("Histórico de Temperatura (24h) - Setpoint Fixo 22°C")
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right')
        
        st.pyplot(fig1)

        # --- GRÁFICO 2: ESFORÇO ---
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(ts, Qests, label="Carga Térmica (%)", color='orange', linewidth=1.5)
        ax2.plot(ts, PCRACs, label="Potência CRAC (%)", color='blue', linewidth=1.5, linestyle='--')
        
        ax2.set_xlabel("Tempo (h)")
        ax2.set_ylabel("Percentual (%)")
        ax2.set_title("Esforço do Controlador vs Carga")
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        st.pyplot(fig2)

    st.write("---")
    st.write("Desenvolvido por **Kauã Victor Garcia Siecola** ✨")
    st.write("Desenvolvido por **Daví Padula Rabelo** ✨")


# ============================================
# PÁGINA 2 — MONITOR MQTT (CORRIGIDO)
# ============================================
# ============================================
# PÁGINA 2 — MONITOR MQTT (COM CORREÇÃO DE MEMÓRIA)
# ============================================
if pagina == "Monitor MQTT":
    st.header("📡 Monitoramento MQTT (TCP 1883)")
    
    # Configurações idênticas ao main.py
    BROKER = "test.mosquitto.org"
    PORT   = 1883
    
    TOPICS = [
        ("datacenter/fuzzy/temp", 0),
        ("datacenter/fuzzy/control", 0),
        ("datacenter/fuzzy/alert", 0),
        ("datacenter/fuzzy/carga", 0)
    ]

    # --- CORREÇÃO DO ERRO KEYERROR ---
    # Verifica se a memória está "suja" com chaves antigas e recria
    if "mqtt_data" in st.session_state:
        # Se existir "mqtt_data" mas não tiver a chave nova "temp", apaga tudo!
        if "temp" not in st.session_state["mqtt_data"]:
            st.session_state.pop("mqtt_data") # Limpa a memória velha
            st.rerun() # Recarrega a página

    # Inicializa sessão limpa se não existir
    if "mqtt_data" not in st.session_state:
        st.session_state["mqtt_data"] = {
            "temp": [], 
            "carga": [], 
            "crac": [], 
            "alertas": []
        }

    # Inicializa Cliente MQTT
    if "mqtt_client_monitor" not in st.session_state:
        client = mqtt.Client()
        
        def on_connect(c, userdata, flags, rc):
            if rc == 0:
                st.toast("✅ Monitor Conectado!")
                c.subscribe(TOPICS)
            else:
                st.error(f"Erro conexão: {rc}")

        def on_message(c, userdata, msg):
            try:
                topic = msg.topic
                payload = msg.payload.decode()
                t_now = time.time()
                
                # Debug no terminal do Python
                print(f"📥 RECEBIDO: {topic} -> {payload}")

                if "temp" in topic:
                    st.session_state["mqtt_data"]["temp"].append((t_now, float(payload)))
                elif "control" in topic:
                    st.session_state["mqtt_data"]["crac"].append((t_now, float(payload)))
                elif "carga" in topic:
                    st.session_state["mqtt_data"]["carga"].append((t_now, float(payload)))
                elif "alert" in topic:
                    st.session_state["mqtt_data"]["alertas"].append((t_now, payload))
            except Exception as e:
                print(f"Erro processamento: {e}")

        client.on_connect = on_connect
        client.on_message = on_message
        
        try:
            client.connect(BROKER, PORT, 60)
            client.loop_start() 
            st.session_state["mqtt_client_monitor"] = client
        except Exception as e:
            st.error(f"Erro fatal MQTT: {e}")

    st.info(f"Conectado a: {BROKER}:{PORT}. Abra a simulação na outra aba.")

    # Botão para atualizar a TELA
    if st.button("🔄 Atualizar Visualização"):
        pass 

    # --- EXIBIÇÃO ---
    d = st.session_state["mqtt_data"]
    
    # Verifica se as listas têm dados antes de tentar acessar
    val_t = d["temp"][-1][1]  if d["temp"]  else 0.0
    val_c = d["carga"][-1][1] if d["carga"] else 0.0
    val_p = d["crac"][-1][1]  if d["crac"]  else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Temperatura", f"{val_t:.2f} °C")
    c2.metric("Carga Térmica", f"{val_c:.1f} %")
    c3.metric("Potência CRAC", f"{val_p:.1f} %")

    # Gráfico
    if len(d["temp"]) > 1:
        y_vals = [x[1] for x in d["temp"][-50:]] # Últimos 50 pontos
        st.line_chart(y_vals)
    else:
        st.write("Aguardando dados para gerar gráfico...")
    
    # Alertas
    if d["alertas"]:
        st.warning(f"Último alerta: {d['alertas'][-1][1]}")