# 🎬 CineAI v1.1

<p align="center">
  <strong>Seu assistente de cinema pessoal no terminal.</strong>
</p>

<p align="center">
  CineAI é um sistema de recomendação de filmes e séries inteligente, construído em Python. Desenvolvido como um projeto universitário, ele demonstra os fundamentos de uma IA de recomendação, utilizando uma abordagem baseada em conhecimento, conteúdo e regras para fornecer sugestões personalizadas.
</p>

<p align="center">
  <img width="596" height="112" alt="Captura de tela 2025-10-17 161008" src="https://github.com/user-attachments/assets/faa542f0-db76-4d2b-aedd-97cea2e86452" />
</p>

---

## 📣 O que há de novo na v1.1

A versão 1.1 traz a funcionalidade "Onde Assistir", melhorias na interface e correções de bugs.

* **Recurso "Onde Assistir":** As recomendações agora mostram em quais serviços de streaming (Netflix, HBO Max, etc.) no Brasil o título está disponível.
* **UI Refinada:** O fluxo de perguntas foi melhorado para ser mais claro e intuitivo (ex: opções de "sim/nao" e duração).
* **Correção de Bug:** Resolvido um problema de formatação visual que exibia texto de markup (ex: `[grey50]`) no terminal.

---

## ✨ Funcionalidades

* **Recomendações Personalizadas:** Responda a algumas perguntas sobre seus gostos e a IA irá calcular um "match score" para encontrar os títulos perfeitos para você.
* **Onde Assistir (Streaming BR):** Descubra instantaneamente em qual plataforma de streaming no Brasil (Netflix, HBO Max, etc.) o título recomendado está disponível.
* **Catálogo Amplo e Curado:** Acesso a um catálogo de 2500 títulos, com uma injeção garantida das melhores séries e animes.
* **Busca Inteligente:** Use termos como "heist" ou "espacial" e a IA irá traduzir para os gêneros corretos.
* **Crítico de IA Integrado:** Cada recomendação vem com um comentário único gerado por uma IA local, simulando um crítico de cinema.
* **Refinamento de Busca:** Goste dos resultados? Refine sua busca com ajustes rápidos, como "focar em clássicos" ou "adicionar um gênero".
* **Interface Elegante e Intuitiva:** Uma interface de usuário minimalista e moderna (construída com a biblioteca Rich) com um fluxo de perguntas refinado.
* **Sistema de Cache:** O catálogo de filmes é salvo localmente para inicializações quasi-instantâneas após a primeira execução.

---

## 🚀 Como Executar

Este projeto foi projetado para ser executado em qualquer terminal que suporte Python 3.

**Pré-requisitos:**
- Python 3.6 ou superior

**Passos:**

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/seu-usuario/CineAI.git](https://github.com/seu-usuario/CineAI.git)
    cd CineAI
    ```

2.  **Instale as dependências:**
    O script instala suas próprias dependências na primeira execução. Alternativamente, você pode instalá-las manualmente:
    ```bash
    pip install requests rapidfuzz rich
    ```

3.  **Execute o script:**
    ```bash
    python cineai.py
    ```
    - Na primeira vez, o script irá construir o catálogo, o que pode levar alguns minutos. Nas execuções seguintes, ele será carregado do cache instantaneamente.
    - Para forçar a reconstrução do catálogo, execute: `python cineai.py --rebuild`.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3:** A linguagem principal do projeto.
- **Rich:** Para a criação da interface de usuário elegante no terminal.
- **Requests:** Para comunicação com a API do The Movie Database (TMDB).
- **RapidFuzz:** Para o processamento de texto e correspondência de strings aproximada (fuzzy matching).

---

## 🔮 Próximas Versões (Roadmap)

A versão 1.1 é uma base sólida. As próximas atualizações planejadas podem incluir:

- [ ] Mais opções de refinamento.
- [ ] Suporte a filtros por ator ou diretor.
- [ ] Expansão da base de conhecimento da IA de comentários local.
- [ ] Salvar listas de "assistir mais tarde".

---

## 📜 Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
