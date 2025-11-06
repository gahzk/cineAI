# CineAI (Estável)

> Um sistema de recomendação de filmes e séries no terminal com modo de busca duplo (Cache e API Ao Vivo), construído em Python e `rich`.

## ✨ Funcionalidades Principais

Este projeto utiliza uma arquitetura de busca dupla para otimizar velocidade e precisão.

### 1. Modo de Busca Duplo

* **Busca Normal (Rápida, via Cache):**
    * Utiliza um catálogo local pré-construído de 2500+ títulos.
    * Ideal para recomendações genéricas baseadas em Gênero, Foco (Nota vs. Popularidade) e Duração.
    * Resultados quasi-instantâneos após a primeira execução.
* **Busca Específica (Precisa, via API Ao Vivo):**
    * Ativada quando o usuário necessita de filtros granulares.
    * Consulta a API do TMDB em tempo real para obter os resultados mais precisos.
    * Permite filtrar por:
        * Palavras-chave (ex: "cyberpunk", "viagem no tempo")
        * Ator ou Atriz
        * Diretor(a)
        * Ano de Lançamento Específico
        * Produtora ou Estúdio (ex: "A24", "Ghibli")
        * Rede ou Streaming (ex: "HBO", "Netflix")
        * Classificação Indicativa (BR)
        * Nota Mínima

### 2. Extração Máxima de Detalhes

Cada resultado é enriquecido com o máximo de informações relevantes da API:

* **Onde Assistir:** Lista de serviços de streaming no Brasil.
* **Detalhes Principais:** Elenco principal, Diretor (Filme) ou Criador (Série).
* **Metadados:** Tagline, Classificação Indicativa (BR), Produtoras e Nº de Temporadas (para séries).
* **Contexto:** Palavras-chave associadas e Recomendações Similares.

### 3. Interface Gráfica de Terminal (TUI)

* Construída inteiramente com a biblioteca `rich`.
* Um tema de design centralizado para consistência visual.
* Resultados exibidos em "cards" com painéis arredondados.
* Prompts de usuário estáveis e claros, à prova de bugs de renderização do Colab.

### 4. Motor de Pontuação e Cache

* **Motor de Pontuação (Busca Normal):** Calcula um "match score" para cada item no cache baseado nas preferências do usuário (gênero, nota, popularidade, ano).
* **Busca "Fuzzy":** Permite que o usuário digite termos como "espacial" ou "suspense", que são traduzidos internamente para os gêneros corretos (ex: "Ficção Científica", "Thriller").
* **Cache Inteligente:** O catálogo principal e a lista de gêneros são cacheados localmente para inicializações rápidas.

---

## 🚀 Como Executar

O projeto é otimizado para execução no Google Colab, mas também funciona em qualquer terminal local.

### Opção 1: Google Colab (Recomendado)

1.  **Chave da API:** Obtenha uma Chave de API "Bearer Token" (v4 Auth) gratuita no [The Movie Database (TMDB)](https://www.themoviedb.org/settings/api).
2.  **Configurar o Script:** Abra o notebook `.ipynb` no Google Colab. Encontre a variável `TMDB_BEARER` no topo do script e cole sua chave.
    ```python
    TMDB_BEARER = "eyJhbGciOiJuz..."
    ```
3.  **Executar:** Execute todas as células do notebook.

### Opção 2: Terminal Local

1.  **Pré-requisitos:** Python 3.7 ou superior.
2.  **Clonar o Repositório:**
    ```bash
    git clone [https://github.com/seu-usuario/CineAI.git](https://github.com/seu-usuario/CineAI.git)
    cd CineAI
    ```
3.  **Instalar Dependências:**
    ```bash
    pip install requests rapidfuzz rich
    ```
4.  **Configurar o Script:** Abra o arquivo `.py` em um editor. Encontre a variável `TMDB_BEARER` no topo do script e cole sua chave de API.
5.  **Executar:**
    ```bash
    python cineai.py
    ```

### Nota sobre o Cache

Na **primeira execução**, o script irá construir o catálogo local (`catalog.json`), o que pode levar alguns minutos. Nas execuções seguintes, ele carregará instantaneamente do cache.

* Para forçar a reconstrução do catálogo, execute: `python cineai.py --rebuild`

---

## 🛠️ Tecnologias Utilizadas

* **Python 3:** Linguagem principal.
* **Rich:** Para a criação da interface gráfica de usuário no terminal (TUI).
* **Requests:** Para comunicação com a API do The Movie Database (TMDB).
* **RapidFuzz:** Para o processamento de texto e correspondência "fuzzy".

---

## 📜 Licença

Este projeto está licenciado sob a Licença MIT.
