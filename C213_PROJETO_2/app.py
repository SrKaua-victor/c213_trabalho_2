import time
import matplotlib.pyplot as plt
import streamlit as st
import paho.mqtt.client as mqtt

from main import (
    fuzzy_controller,
    simular_24h,
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

    erro  = col1.slider("Erro (°C)", -5.0, 5.0, 0.0, 0.1)
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

    st.header("📈 Simulação Completa de 24 Horas")

    if st.button("Rodar Simulação 24h"):
        with st.spinner("Simulando 24h e publicando via MQTT..."):
            ts, Ts, Texts, Qests, PCRACs = simular_24h()

        st.success("Simulação concluída!")

        # Gráfico 1: Temperaturas
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(ts, Ts,  label="Temperatura Interna (°C)")
        ax1.plot(ts, Texts, '--', label="Temperatura Externa (°C)")
        ax1.set_xlabel("Tempo (h)")
        ax1.set_ylabel("Temperatura (°C)")
        ax1.grid(True)
        ax1.legend()
        st.pyplot(fig1)

        # Gráfico 2: Carga x CRAC
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(ts, Qests,  label="Carga térmica (%)")
        ax2.plot(ts, PCRACs, '--', label="Potência CRAC (%)")
        ax2.set_xlabel("Tempo (h)")
        ax2.set_ylabel("Percentual (%)")
        ax2.grid(True)
        ax2.legend()
        st.pyplot(fig2)

    st.write("---")
    st.write("Desenvolvido por **Kauã Victor Garcia Siecola** ✨")


# ============================================
# PÁGINA 2 — MONITOR MQTT (SIMPLIFICADO, SEM THREAD)
# ============================================
if pagina == "Monitor MQTT":
    st.header("📡 Monitoramento MQTT – Data Center")

    st.write(f"Broker: **{MQTT_BROKER}** — Porta: **{MQTT_PORT}**")

    MQTT_TOPICS = [
        "datacenter/temperatura",
        "datacenter/carga_termica",
        "datacenter/potencia_crac",
        "datacenter/alertas",
    ]

    # ------------------------------
    # Inicializa sessão (apenas uma vez)
    # ------------------------------
    if "mqtt_data" not in st.session_state:
        st.session_state["mqtt_data"] = {
            "temperatura": [],
            "carga": [],
            "crac": [],
            "alertas": [],
        }

    if "mqtt_client" not in st.session_state:
        # Vamos criar o cliente MQTT, com callbacks,
        # mas NÃO vamos usar loop_start (sem thread separada)
        client = mqtt.Client()

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("MQTT monitor conectado.")
                for top in MQTT_TOPICS:
                    client.subscribe(top)
            else:
                print("Falha ao conectar MQTT monitor. Código:", rc)

        def on_message(client, userdata, msg):
            # Essa função roda no MESMO THREAD do Streamlit
            # porque usamos client.loop() dentro do script.
            try:
                payload = msg.payload.decode()
                t = time.time()

                if msg.topic.endswith("temperatura"):
                    st.session_state["mqtt_data"]["temperatura"].append((t, float(payload)))
                elif msg.topic.endswith("carga_termica"):
                    st.session_state["mqtt_data"]["carga"].append((t, float(payload)))
                elif msg.topic.endswith("potencia_crac"):
                    st.session_state["mqtt_data"]["crac"].append((t, float(payload)))
                elif msg.topic.endswith("alertas"):
                    st.session_state["mqtt_data"]["alertas"].append((t, payload))
            except Exception as e:
                print("Erro ao processar mensagem MQTT:", e)

        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
        except Exception as e:
            st.error(f"Erro ao conectar MQTT monitor: {e}")

        # guarda no session_state
        st.session_state["mqtt_client"] = client

    # Pega o cliente
    client = st.session_state["mqtt_client"]

    # Botão para rodar o loop e puxar mensagens novas
    if st.button("Atualizar dados MQTT"):
        # Processa eventos de rede por 0.5 segundo
        start = time.time()
        while time.time() - start < 0.5:
            client.loop(timeout=0.1)  # NÃO cria thread, roda no mesmo fluxo

    # --------------- MÉTRICAS RÁPIDAS ---------------
    temp_val  = st.session_state["mqtt_data"]["temperatura"][-1][1] if st.session_state["mqtt_data"]["temperatura"] else None
    carga_val = st.session_state["mqtt_data"]["carga"][-1][1]        if st.session_state["mqtt_data"]["carga"] else None
    crac_val  = st.session_state["mqtt_data"]["crac"][-1][1]         if st.session_state["mqtt_data"]["crac"] else None

    colA, colB, colC = st.columns(3)
    colA.metric("Temperatura interna (°C)", f"{temp_val:.2f}" if temp_val is not None else "—")
    colB.metric("Carga térmica (%)", f"{carga_val:.1f}" if carga_val is not None else "—")
    colC.metric("Potência CRAC (%)", f"{crac_val:.1f}" if crac_val is not None else "—")

    st.write("")

    # --------------- HISTÓRICO EM GRÁFICO ---------------
    if len(st.session_state["mqtt_data"]["temperatura"]) >= 2:
        tempos_temp = [x[0] for x in st.session_state["mqtt_data"]["temperatura"]]
        vals_temp   = [x[1] for x in st.session_state["mqtt_data"]["temperatura"]]

        figT, axT = plt.subplots(figsize=(10, 3))
        axT.plot(tempos_temp, vals_temp, label="Temperatura (°C)")
        axT.set_xlabel("Tempo (epoch)")
        axT.set_ylabel("°C")
        axT.grid(True)
        axT.legend()
        st.pyplot(figT)

    if len(st.session_state["mqtt_data"]["crac"]) >= 2:
        tempos_crac = [x[0] for x in st.session_state["mqtt_data"]["crac"]]
        vals_crac   = [x[1] for x in st.session_state["mqtt_data"]["crac"]]

        figC, axC = plt.subplots(figsize=(10, 3))
        axC.plot(tempos_crac, vals_crac, label="Potência CRAC (%)")
        axC.set_xlabel("Tempo (epoch)")
        axC.set_ylabel("%")
        axC.grid(True)
        axC.legend()
        st.pyplot(figC)

    # --------------- ALERTAS ---------------
    st.subheader("Alertas recebidos:")
    if st.session_state["mqtt_data"]["alertas"]:
        for t_alert, msg in reversed(st.session_state["mqtt_data"]["alertas"][-10:]):
            st.error(f"{time.ctime(t_alert)} — {msg}")
    else:
        st.info("Nenhum alerta recebido ainda.")

    st.write("---")
    st.write("Monitorando tópicos: `datacenter/temperatura`, `datacenter/carga_termica`, `datacenter/potencia_crac`, `datacenter/alertas`.")
