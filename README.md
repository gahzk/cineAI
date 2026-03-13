<div align="center">

# 🎬 CineAI

### Recomendador Inteligente de Filmes e Séries

[![Python](https://img.shields.io/badge/Python-3.7+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Google Colab](https://img.shields.io/badge/Google_Colab-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white)](https://colab.research.google.com/)
[![TMDB API](https://img.shields.io/badge/TMDB_API-01D277?style=for-the-badge&logo=themoviedatabase&logoColor=white)](https://www.themoviedb.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br>

*Sistema inteligente de recomendação com busca dupla (Cache + API), interface TUI rica e comentários gerados por IA local.*

---

</div>

## 📋 Sobre o Projeto

O **CineAI** é um sistema de recomendação de filmes e séries desenvolvido em Python, projetado para rodar no **Google Colab**. Ele combina um catálogo local de **2500+ títulos** com consultas em tempo real à API do TMDB, oferecendo recomendações personalizadas através de uma interface de terminal estilizada com a biblioteca `rich`.

O projeto foi desenvolvido como trabalho acadêmico, explorando conceitos de consumo de APIs REST, processamento de dados, cache inteligente e interfaces de usuário em terminal.

## ✨ Funcionalidades

### 🔍 Busca Dupla

- **Busca Normal (Cache Local)** — Recomendações rápidas a partir de um catálogo local pré-construído com 2500+ títulos. Ideal para descobertas baseadas em gênero, foco (nota vs. popularidade) e duração.

- **Busca Específica (API ao Vivo)** — Consulta a API do TMDB em tempo real com filtros granulares: palavras-chave, ator/atriz, diretor(a), ano, produtora, rede/streaming, classificação indicativa e nota mínima.

### 📊 Detalhes Completos

Cada resultado inclui: sinopse, elenco, diretor/criador, onde assistir (streaming no Brasil), classificação indicativa (BR), produtoras, palavras-chave, temporadas (séries) e recomendações similares.

### 🎨 Interface TUI

Interface gráfica de terminal construída com `rich`, com tema de cores personalizado, cards com painéis arredondados e prompts interativos com correspondência fuzzy.

### 🧠 Motor de Pontuação

Sistema de scoring que calcula compatibilidade baseado nas preferências do usuário, com suporte a busca fuzzy de gêneros e temas (ex: digitar "espacial" mapeia para "Ficção Científica").

### 💬 Comentários IA

Geração local de comentários personalizados para cada recomendação, baseados em gênero, nota, popularidade e ano.

## 🚀 Como Executar

### Pré-requisitos

1. Obtenha um **Bearer Token** (v4 Auth) gratuito no [TMDB](https://www.themoviedb.org/settings/api)

### Google Colab (Recomendado)

1. Abra o notebook `CineAI.ipynb` no Google Colab
2. Clique no ícone de **chave (🔑)** na barra lateral esquerda
3. Adicione um secret chamado `TMDB_BEARER_TOKEN` com seu token
4. Ative o acesso do notebook ao secret
5. Execute todas as células com `Ctrl+F9`

> **🔒 Segurança:** O token é carregado via [Google Colab Secrets](https://colab.research.google.com/), sem necessidade de expor credenciais no código.

## 📁 Estrutura do Projeto

```
cineAI/
├── CineAI.ipynb    # Notebook principal (Google Colab)
├── LICENSE          # Licença MIT
└── README.md        # Documentação
```

## 🛠️ Tecnologias

| Tecnologia | Uso |
|:---:|:---|
| **Python 3** | Linguagem principal |
| **Rich** | Interface gráfica de terminal (TUI) |
| **Requests** | Comunicação com a API TMDB |
| **RapidFuzz** | Correspondência fuzzy de texto |
| **Google Colab** | Ambiente de execução |
| **TMDB API** | Base de dados de filmes e séries |

## 🔒 Segurança

Este projeto utiliza o sistema de **Secrets do Google Colab** para gerenciar o token da API TMDB de forma segura. O token nunca é exposto no código-fonte do notebook, eliminando riscos de vazamento de credenciais.

## 📜 Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).

---

<div align="center">

Desenvolvido por [**Gabriel Oliveira Santos**](https://github.com/gahzk)

</div>
