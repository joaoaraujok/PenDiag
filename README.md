# ⚡ PenDiag - CLI de Diagnóstico Rápido de Hardware e Rede em Pendrive

> **Suíte portátil de terminal para técnicos de suporte e infraestrutura.** Extrai métricas de saúde do hardware (S.M.A.R.T. de discos, integridade e desgaste de bateria, latência de rede/DNS e testes de estresse de memória RAM e blocos de disco com conferência de integridade SHA-256).

Gera relatórios completos exportáveis em **HTML standalone (moderno e 100% offline)** e **JSON estruturado**, além de suportar envio automático para servidores via **Webhook HTTP POST**.

---

## 🎯 Destaques e Diferenciais

- **🚀 100% Portátil para Pendrive:** Pode ser executado via interpretador Python portátil, Python do sistema ou compilado em um único arquivo executável autônomo (`pendiag.exe`), sem requerer instalação de dependências na máquina cliente.
- **🎨 Interface Visual de Alto Impacto (Rich):** Tabelas formatadas, medidores de uso, badges de status coloridos (`SAUDÁVEL`, `ATENÇÃO`, `CRÍTICO`) e barras de progresso dinâmicas em tempo real.
- **💼 Parecer Técnico Comercial (Laudo Executivo para Cliente):** Conclusões e recomendações comerciais automáticas em linguagem clara e acessível para clientes leigos (ex: indicação de upgrade de RAM, alerta preventivo de troca de bateria ou atestado de saúde de armazenamento).
- **🛡️ Detecção de Segurança & Antivírus:** Identificação do antivírus ativo (via WMI SecurityCenter2 no Windows e agentes de segurança no Linux), status da proteção em tempo real e atualização das definições de vacinas.
- **🌡️ Sensores Térmicos:** Monitoramento de temperatura da CPU e dos discos rígidos/SSDs.
- **💽 Diagnóstico S.M.A.R.T. & Descoberta Portátil:** Identificação de discos físicos (NVMe, SSD, HDD), status operacional, temperatura, desgaste, partições e localização automática de utilitários como `smartctl` embutidos na pasta `tools/` do pendrive.
- **🔋 Integridade & Degradação de Bateria (Wear Level):** Extração de capacidade de fábrica (Design Capacity), capacidade máxima atual (Full Charge Capacity), porcentagem de desgaste (*wear level*), ciclos de recarga e estimativa de autonomia.
- **🌐 Rede Inteligente sem Falsos Positivos:** Verificação de Camada 2 via tabela ARP e fallback para portas de roteador (`80`, `8080`, `443`, `53`), eliminando alertas falsos quando o roteador bloqueia ICMP mas a navegação externa funciona com sucesso.
- **⚡ Testes de Estresse com Zero Thrashing:**
  - **Memória RAM:** Pré-alocação segura de buffer único com fatiamento via `memoryview` (sem cópias redundantes no heap) e redimensionamento preventivo automático em máquinas com baixa memória livre remanescente.
  - **Bloco de Disco (I/O):** Gravação forçada em disco físico com `fsync` e leitura com conferência de integridade de checksum SHA-256, medindo vazão real de escrita e leitura sequencial.
- **📊 Relatório HTML Premium Standalone:** Design escuro moderno com visualização clara de gauges de pontuação de saúde (0 a 100), laudo executivo comercial, tabelas de recursos, lista de alertas críticos identificados, botão para impressão/PDF (`Ctrl+P`) e visualizador/copiador de JSON integrado. Não depende de internet nem de CDNs externos.

---

## 📁 Estrutura do Projeto

```text
cli-python-hardware/
├── pendiag/
│   ├── __init__.py               # Inicialização e configuração UTF-8 universal
│   ├── cli.py                    # Interface de Linha de Comando (Typer + Rich)
│   ├── models.py                 # Dataclasses de diagnóstico, segurança e alertas
│   ├── utils.py                  # Avaliação inteligente de saúde e parecer executivo
│   ├── collectors/
│   │   ├── system.py             # CPU, RAM, SO, BIOS, Antivírus e Temperatura
│   │   ├── disk.py               # Discos físicos, S.M.A.R.T., smartctl portátil
│   │   ├── battery.py            # Bateria, desgaste, capacidades e ciclos
│   │   └── network.py            # Interfaces, ARP Camada 2, Ping/ICMP, DNS e HTTP
│   ├── benchmarks/
│   │   ├── memory_test.py        # Teste de RAM com memoryview e segurança preventiva
│   │   └── disk_test.py          # Teste de blocos com fsync e SHA-256 em disco
│   ├── exporters/
│   │   ├── json_exporter.py      # Serialização e salvamento em JSON
│   │   ├── html_exporter.py      # Renderização do relatório HTML com Jinja2
│   │   └── webhook.py            # Transmissão HTTP POST para API / Webhook
│   └── templates/
│       └── report_template.html  # Template HTML Dark Mode com Laudo Executivo
├── tests/
│   ├── test_collectors.py        # Testes dos coletores, gateway e laudo
│   ├── test_benchmarks.py        # Testes de integridade de RAM e ajuste automático
│   └── test_exporters.py         # Testes de exportação JSON e HTML
├── main.py                       # Ponto de entrada direto
├── build_exe.py                  # Compilador PyInstaller para pendiag.exe
├── run_pendiag.bat               # Launcher com duplo-clique para Windows
├── run_pendiag.sh                # Launcher para Linux / macOS
├── requirements.txt              # Dependências do projeto
└── pyproject.toml                # Metadados de empacotamento
```

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.9+** (compatível com Python 3.14+)
- **[psutil](https://github.com/giampaolo/psutil):** Coleta de métricas do sistema operacional, memória, discos e rede.
- **[typer](https://typer.tiangolo.com/):** Criação da interface CLI tipada e moderna.
- **[rich](https://rich.readthedocs.io/):** Renderização visual no terminal com cores, caixas, spinners e tabelas.
- **[jinja2](https://jinja.palletsprojects.com/):** Mecanismo de templates para geração do relatório HTML.
- **[pyinstaller](https://pyinstaller.org/):** Empacotamento em executável único independente para pendrives.

---

## 🚀 Como Executar

### 1. Execução Rápida via Pendrive (Windows)
Basta dar **duplo clique** em:
```text
run_pendiag.bat
```
O script detecta automaticamente se existe o executável compilado (`pendiag.exe`), um interpretador Python na pasta `tools\python` do pendrive ou o Python do Windows, executando a bateria de testes e abrindo o relatório no navegador.

### 2. Execução Direta via Terminal (Python)
Instale as dependências:
```bash
pip install -r requirements.txt
```

Execute o diagnóstico completo:
```bash
python main.py all
```

---

## 📖 Comandos Disponíveis

| Comando | Descrição |
| :--- | :--- |
| `python main.py all` | Executa diagnóstico completo (Hardware, Discos, Bateria, Rede e Benchmarks) e gera relatórios. |
| `python main.py sys` | Exibe dados de identificação da máquina, processador, memória RAM, BIOS e Antivírus. |
| `python main.py disk` | Analisa a saúde S.M.A.R.T. dos discos físicos e volumes montados. |
| `python main.py battery` | Mostra nível de desgaste da bateria (*wear level*), ciclos e capacidades. |
| `python main.py net` | Testa adaptadores, resolução de gateway via ARP, ping, servidores DNS e HTTP. |
| `python main.py bench` | Executa testes de velocidade e integridade com SHA-256 na RAM e no disco. |

### Opções do Comando `all`

```bash
# Diagnóstico rápido (reduz amostras dos benchmarks de escrita)
python main.py all --quick

# Definir pasta de saída dos relatórios
python main.py all --output-dir ./meus_relatorios

# Exportar apenas em formato específico (all, html, json ou none)
python main.py all --format html

# Abrir automaticamente o relatório gerado no navegador padrão
python main.py all --open-browser

# Identificar o técnico e o número do chamado
python main.py all --technician "João Silva" --ticket "CH-94821"

# Enviar o diagnóstico em JSON diretamente para um webhook ou API
python main.py all --send-url "https://api.meusuporte.com/v1/diagnosticos"
```

---

## 📦 Como Compilar o Executável Portátil (`.exe`)

Para gerar o arquivo `pendiag.exe` standalone para levar no pendrive (sem depender de Python instalado nas máquinas dos clientes):

```bash
python build_exe.py
```

O executável final estará disponível em:
```text
dist/pendiag.exe
```

Copie este arquivo para a raiz do seu pendrive junto com `run_pendiag.bat`.

---

## 🧪 Executando os Testes Automatizados

O projeto conta com suíte de testes com cobertura para coletores, benchmarks, resiliência de rede e exportadores:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 📄 Licença
Distribuído sob a licença MIT. Livre para uso pessoal, técnico e comercial.
