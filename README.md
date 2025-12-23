# Análise de Dados de Safra de Soja (IBGE & CONAB)

Este repositório contém os scripts e a documentação referentes à análise comparativa e evolutiva da área plantada de soja no Brasil, utilizando dados públicos do IBGE (PAM) e da CONAB.

## 📋 Visão Geral do Projeto

O projeto consiste na extração, tratamento e visualização de dados agrícolas, focando especificamente na cultura da soja. As principais etapas incluem:

1.  **Coleta de Dados:** Extração de dados do sistema SIDRA (IBGE) e do portal de informações da CONAB.
2.  **Processamento e ETL:** Limpeza, transformação e unificação das bases de dados.
3.  **Cálculos Analíticos:**
    *   Comparativo entre fontes (IBGE vs. CONAB).
    *   Cálculo de representatividade municipal (PAM/IBGE).
    *   Alocação (projeção) da área plantada da safra 21/22 nos municípios baseada na representatividade histórica.
4.  **Visualização:** Desenvolvimento de um Dashboard no Power BI.

## 🛠️ Ferramentas Utilizadas

*   **Linguagem de Programação:** Python 3.13
*   **Visualização de Dados:** Microsoft Power BI
*   **Fontes de Dados:**
    *   [IBGE - Pesquisa Agrícola Municipal (PAM)](https://sidra.ibge.gov.br/pesquisa/pam/tabelas)
    *   [CONAB - Série Histórica de Grãos](https://portaldeinformacoes.conab.gov.br/downloads/arquivos/SerieHistoricaGraos.txt)

## 🗂️ Estrutura do Repositório

```text
.
├── data/                   # Dados brutos e processados
├── scripts/                # Scripts auxiliares utilizados para extração e tratamento (Python)
├── dashboard/              # Arquivo .pbix do Power BI
├── README.md               # Documentação do projeto
├── main.py                 # Script principal para execução do ETL
├── .gitignore              # Arquivo para ignorar arquivos no Git
├── .python-version         # Versão do Python utilizada
├── pyproject.toml          # Configurações do projeto Python 
└── uv.lock                  # Arquivo de bloqueio de dependências
```

## 🚀 Como Executar

### Pré-requisitos
*   Microsoft Power BI Desktop instalado.
*   Python 3.x (caso queira rodar os scripts de ETL).

### Passos
1.  **Scripts de Tratamento:**
    *   Navegue até a pasta `scripts/`.
    *   Execute o arquivo `etl_process.py` (ou equivalente) para gerar as bases consolidadas.
2.  **Dashboard:**
    *   Abra o arquivo localizado em `dashboard/Analise_Soja.pbix`.
    *   O painel contém uma única tela interativa permitindo filtros por escala geográfica (País, Estado, Município).

## 📊 Metodologia Aplicada

### 1. Comparativo IBGE vs. CONAB
Foi realizada uma análise cruzada das áreas plantadas para as safras 18/19, 19/20 e 20/21, normalizando os anos civis do IBGE com os anos-safra da CONAB para garantir a comparabilidade.

### 2. Alocação Municipal (Safra 21/22)
Para estimar a área municipal da safra 21/22 (dado disponível apenas a nível estadual na CONAB no momento da análise), utilizou-se a seguinte lógica:
1.  Calculou-se o *share* (%) de cada município dentro do seu estado utilizando os dados consolidados do IBGE 2021.
2.  Aplicou-se esse percentual sobre o total estadual reportado pela CONAB para a safra 21/22.

## 📝 Análise Específica (Município 5100201)

*O parágrafo analítico solicitado no item 6 das instruções encontra-se no corpo do e-mail de entrega, conforme requisitado, mas também pode ser visualizado através dos filtros do Dashboard.*

---
**Autor:** Yan Prada