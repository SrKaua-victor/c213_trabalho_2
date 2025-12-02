# Sistema de Controle Fuzzy para Data Center  
Interface Gráfica, Simulação 24h, Debug de Inferência e Monitoramento via MQTT

Este projeto implementa um controlador fuzzy MISO para regular a temperatura de um Data Center através da atuação do sistema de resfriamento (CRAC).  
Inclui interface gráfica completa em Tkinter, sistema de simulação de 24 horas, visualização das funções de pertinência, análise do processo de inferência e envio contínuo de dados via MQTT.

---

## Estrutura do Projeto
```
C213_PROJETO_2/
├── gui_tk.py                # Interface gráfica principal
├── main.py                  # Motor fuzzy + modelo físico + regras
├── monitoramento_viewer.py  # Monitor remoto MQTT
└── README.md
```

---

## Como Executar

### 1. Instale as dependências
```bash
pip install numpy matplotlib scikit-fuzzy paho-mqtt
```

### 2. Inicie a interface principal
```bash
python gui_tk.py
```

---

# Documentação Técnica

## 1. Relatório de Design

### 1.1 Justificativa do Design das Funções de Pertinência

As funções de pertinência foram definidas utilizando MFs triangulares por serem simples, eficientes e adequadas para sistemas térmicos com variação gradual.

Entradas definidas no sistema:

| Variável | Intervalo | Conjuntos |
|---------|-----------|-----------|
| Erro (e) | −10 a 10 | neg, zero, pos |
| Delta Erro (de) | −2 a 2 | neg, zero, pos |
| Temperatura Externa | 10 a 35 | baixa, média, alta |
| Carga Térmica | 0 a 100 | baixa, média, alta |

Saída:

| Variável | Intervalo | Conjuntos |
|---------|-----------|-----------|
| Ação do CRAC (%) | 0 a 100 | baixa, média, alta |

A modelagem considerou:
- Faixa ideal de operação do Data Center (18 a 26 °C).  
- Relação não linear entre carga térmica e resposta do sistema.  
- Influência direta da temperatura externa na carga térmica interna.  

Esses critérios permitiram criar um controlador suave, estável e que evita oscilações indesejadas.

---

### 1.2 Explicação da Base de Regras Desenvolvida

A base fuzzy foi construída com 12 regras Mamdani que combinam as quatro entradas para determinar a ação apropriada do CRAC.

Exemplos:

- Se erro é positivo e delta erro é positivo, então CRAC = alta  
- Se erro é zero e delta erro é negativo, então CRAC = baixa  
- Se temperatura externa é alta, então CRAC = alta  
- Se carga térmica é alta, então CRAC = alta  

Essas regras foram pensadas para:

- Aumentar a refrigeração quando a temperatura interna está acima do ideal.  
- Reduzir o esforço de refrigeração quando o erro é negativo ou a tendência é de queda.  
- Aumentar proporcionalmente a resposta em condições de carga e ambiente desfavoráveis.  

---

### 1.3 Estratégia de Controle Implementada

O controlador fuzzy fornece um valor bruto defuzzificado.  
Para evitar oscilações no sistema e garantir estabilidade, é aplicado um filtro suavizador:

```python
return 0.7 * Prev + 0.3 * rawMarkdown Preview Enhanced
```

Onde:
- `Prev` = saída anterior (filtro de memória)  
- `raw` = saída fuzzy defuzzificada  

Esse método reduz variações bruscas e torna o controlador mais robusto a perturbações, tanto do ambiente externo quanto do modelo físico.

---

## 2. Análise de Resultados

### 2.1 Testes de Validação

Foram conduzidos testes utilizando simulação de 24 horas que inclui:
- Variação de temperatura externa baseada em função senoidal  
- Carga térmica dinâmica  
- Ruído aleatório nas leituras  

Os testes demonstraram:
- Estabilidade da temperatura interna próximo ao setpoint  
- Ação adequada do CRAC conforme condições externas  
- Ausência de comportamento oscilatório excessivo  

---

### 2.2 Análise da Resposta em Diferentes Cenários

Foram avaliados múltiplos contextos:
- Ambientes frios (10 a 15 °C)  
- Picos de calor (até 35 °C)  
- Carga térmica baixa (20%)  
- Período de pico de carga térmica (80%)  

O algoritmo respondeu de modo coerente, aumentando a atuação do CRAC em cargas pesadas e diminuindo quando o ambiente externo favorecia o resfriamento natural.

---

### 2.3 Comparação com Controladores Tradicionais

| Critério | PID Tradicional | Fuzzy |
|---------|-----------------|--------|
| Lidar com não linearidades | Fraco | Forte |
| Robustez | Média | Alta |
| Oscilações | Comuns | Reduzidas |
| Ajuste | Exige tuning complexo | Regras intuitivas |
| Resposta a distúrbios | Razoável | Muito boa |

O fuzzy se mostra superior principalmente devido ao comportamento não linear do ambiente do Data Center.

---

### 2.4 Avaliação de Robustez e Estabilidade

O controlador fuzzy se mantém estável mesmo quando sujeito a:
- Ruídos gaussianos  
- Cargas abruptamente variáveis  
- Mudanças de setpoint  

O sistema operou sem overshoots perigosos, manteve estabilidade prolongada e respondeu de maneira eficiente a mudanças externas.

---

# Comunicação MQTT

Durante a simulação, os seguintes tópicos são publicados:

```
datacenter/fuzzy/temp
datacenter/fuzzy/control
datacenter/fuzzy/alert
```

Esses dados podem ser monitorados externamente por ferramentas MQTT ou pelo arquivo `monitoramento_viewer.py`.

---

# Autores

**Kauã Victor Garcia Siecola**  
**Davi Padula Rabelo**
