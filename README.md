# Controle de Horas

Aplicação Streamlit para acompanhamento de horas trabalhadas por profissional e cliente, com integração ao Google Sheets e armazenamento local via DuckDB.

## Requisitos

- **Python** 3.11.5
- Arquivo `credentials.json` com credenciais de Service Account do Google (não versionado)

## Estrutura do projeto

```
src/
├── streamlit_app.py          # App principal (entry point)
├── modules/
│   ├── data_store.py         # Camada de persistência (DuckDB)
│   ├── google_auth.py        # Autenticação Google (Service Account)
│   ├── google_sheets.py      # Cliente Google Sheets (gspread)
│   ├── google_drive.py       # Cliente Google Drive (não implementado)
│   └── gs_integrations.py    # Orquestrador de integração
├── templates/
│   └── relatorio.html        # Template CSS do relatório HTML
└── data_horas/
    └── horas.duckdb           # Banco de dados local (gerado automaticamente)
```

## Instalação

```bash
# Clone o repositório
git clone <url-do-repo>
cd prj_horas

# Crie e ative o ambiente virtual
python3.11 -m venv .venv
source .venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

## Configuração do Google Sheets

1. Crie um projeto no [Google Cloud Console](https://console.cloud.google.com/)
2. Ative as APIs **Google Sheets** e **Google Drive**
3. Crie uma **Service Account** e baixe o JSON de credenciais
4. Renomeie o arquivo para `credentials.json` e coloque na raiz do projeto
5. Compartilhe a planilha do Google Sheets com o e-mail da Service Account

## Como rodar

```bash
# A partir da raiz do projeto
streamlit run src/streamlit_app.py
```

O app abre no navegador em `http://localhost:8501`.

## Funcionalidades

### Painel
- Dashboard com KPIs (registros, horas totais, profissionais)
- Gráficos: horas por profissional, cliente, período, área e profissional x cliente
- Comparativo de alocação vs realizado (quando dados de alocação estão carregados)
- Filtros na sidebar: profissional, cliente e período

### Atualização de Dados
- Importação de horas do Google Sheets
- Upload de CSV de alocação

### Explorador de Dados
- Visualização de todas as tabelas do DuckDB
- Filtros dinâmicos por coluna (texto e numérico)

### Relatório
- Geração de relatório HTML estático com dados reais
- Filtros de período e profissional
- Download do HTML e preview inline
- Suporte a impressão/PDF via navegador (Ctrl+P)

## Principais dependências

| Pacote     | Versão  | Uso                          |
|------------|---------|------------------------------|
| streamlit  | 1.53.1  | Interface web                |
| duckdb     | 1.4.4   | Banco de dados local         |
| pandas     | 2.3.3   | Manipulação de dados         |
| altair     | 6.0.0   | Gráficos                    |
| gspread    | 6.2.1   | Cliente Google Sheets        |
| google-auth| 2.48.0  | Autenticação Google          |

## Banco de dados

O DuckDB armazena os dados localmente em `src/data_horas/horas.duckdb` com as tabelas:

- **horas** — registros de horas importados do Google Sheets
- **alocacao** — dados de alocação importados via CSV
- **metadata** — controle de última atualização
