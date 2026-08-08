# Orion Index

Rastreia as linguagens de programação mais usadas no mundo, combinando quatro perspectivas diferentes de propósito em vez de assumir que existe uma resposta única pra "linguagem mais usada". As quatro vêm exclusivamente da API GraphQL oficial do GitHub, buscadas ao vivo a cada execução, sem nenhum número fixo no código e sem depender de terceiro.

> **Usado por:** o [README de perfil](https://github.com/GustavoVieiraDeAraujo/GustavoVieiraDeAraujo) do autor embute o card combinado gerado aqui.

---

## Sumário

- [Autor](#autor)
- [Tecnologias](#tecnologias)
- [Perspectivas](#perspectivas)
- [Por que não outras fontes](#por-que-não-outras-fontes)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Requisitos](#requisitos)
- [Como Executar](#como-executar)
- [Automação](#automação)
- [Usando em Outro Lugar](#usando-em-outro-lugar)

---

## Autor

| Nome | GitHub |
|---|---|
| Gustavo Vieira de Araújo | [@GustavoVieiraDeAraujo](https://github.com/GustavoVieiraDeAraujo) |

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3 (biblioteca padrão apenas) | Busca dos dados e geração dos cartões SVG, sem nenhuma dependência externa |
| API GraphQL do GitHub | Fonte de dados ao vivo: contagem de repositórios por linguagem/tópico, calendário de contribuições |
| SVG + SMIL | Desenho e animação dos cartões (nave espacial), sem JavaScript |
| GitHub Actions | Agendamento e execução automática dos três scripts |

---

## Perspectivas

Nenhum ângulo de popularidade de linguagem mede a mesma coisa que os outros, e este projeto assume isso em vez de esconder:

| Perspectiva | O que mede de verdade | Como é calculada |
| --- | --- | --- |
| **Repositórios Novos** | Quantidade de repositórios **criados** nos últimos 30 dias por linguagem — volume absoluto do que está sendo adotado agora | `language:X created:>DATA` |
| **Repositórios Totais** | Quantidade de repositórios públicos **já existentes** por linguagem principal — o acumulado histórico, tamanho do ecossistema | `language:X` |
| **Repositórios por Finalidade** | Quantidade de repositórios por **tópico de propósito** (IA, APIs, automação, dados...), sem olhar linguagem nenhuma — pra que o código está sendo usado agora | `topic:X` |
| **Crescimento Relativo** | **Novos ÷ Totais**, em % — não é uma busca nova, é a razão entre as duas primeiras. Mede velocidade de crescimento **relativa ao próprio tamanho** | derivado, sem chamada extra à API |

Todas partem da mesma API GraphQL (`search(query: "...", type: REPOSITORY)`). Repositórios Novos favorece linguagem já grande, porque tem mais gente usando. Repositórios Totais também favorece linguagem grande e estabelecida. Repositórios por Finalidade muda de eixo por completo: compara propósito entre si, não linguagem (é a única das quatro que não rankeia linguagem). Crescimento Relativo neutraliza o viés de tamanho das duas primeiras — uma linguagem pequena mas em expansão rápida (ex: Rust, Dart) pode aparecer na frente de uma gigante estabelecida que cresce bastante em número absoluto mas pouco proporcionalmente. Por isso os top 5 de cada perspectiva são diferentes entre si, e isso é o esperado, não um erro.

HTML e CSS ficam de fora de todas as quatro: marcação e estilo não são linguagem de programação.

---

## Por que não outras fontes

| Fonte | Motivo |
|---|---|
| [PYPL](https://pypl.github.io/PYPL.html) | Dado real e referência estabelecida, mas é projeto pessoal de terceiro, sem API oficial |
| [Stack Overflow Developer Survey](https://survey.stackoverflow.co/) | Chegou a ser usada (CSV oficial da Stack Exchange). Trocada pela perspectiva Crescimento Relativo pra ficar 100% dentro de uma única fonte/API/token, em vez de misturar busca ao vivo com CSV anual de outra organização |
| [GitHub Octoverse](https://github.blog/news-insights/octoverse/) | Relatório esporádico em prosa, sem API nem dataset estruturado (testado: nem o site nem os posts do blog têm endpoint de dado) |
| [TIOBE Index](https://www.tiobe.com/tiobe-index/) | O [termo de uso deles](https://www.tiobe.com/disclaimer/) proíbe copiar/republicar sem consentimento prévio, e vendem o dataset histórico como produto pago |

A primeira versão da quarta perspectiva era "repositórios com push nos últimos 30 dias" (`pushed:>DATA`), mas na prática o top 5 saía quase idêntico ao de Repositórios Novos — as duas métricas absolutas são dominadas pelas mesmas linguagens grandes. Trocada por Repositórios por Finalidade, que muda de eixo em vez de só filtrar diferente.

---

## Estrutura do Projeto

| Diretório / Arquivo | Descrição |
|---|---|
| `scripts/generate.py` | As 4 perspectivas do Orion Index: busca na API do GitHub e gera `docs/orion-index.svg` |
| `scripts/generate_profile_stats.py` | Automação pessoal do perfil (não é o Orion Index): estatísticas dos repositórios do autor, publicadas no README de outro repositório |
| `scripts/generate_spaceship.py` | Automação pessoal: nave espacial animada sobre o calendário de contribuições, publicada no mesmo README de perfil |
| `.github/workflows/atualiza_orion_index.yml` | Roda `generate.py` uma vez por dia, dispara o próximo da cadeia ao terminar |
| `.github/workflows/atualiza_estatisticas_perfil.yml` | Roda `generate_profile_stats.py` quando o workflow anterior termina |
| `.github/workflows/gera_nave_espacial.yml` | Roda `generate_spaceship.py` quando o workflow anterior termina |
| `docs/orion-index.svg` | Card combinado das 4 perspectivas, em grade 2x2 |
| `docs/github_*.svg` | Os 4 painéis individuais que compõem o combinado |
| `docs/profile_*.svg` | Cartões de estatísticas do perfil (não fazem parte do Orion Index) |
| `docs/spaceship.svg` | Animação da nave espacial (não faz parte do Orion Index) |

---

## Requisitos

- Python 3.9 ou superior (sem dependências externas, só biblioteca padrão)
- Um `GITHUB_TOKEN` com leitura pública (o token automático do GitHub Actions já serve; localmente, `gh auth token` funciona)
- Pra `generate_profile_stats.py`: também um token com permissão de escrita no repositório de perfil (`PROFILE_PAT`)

---

## Como Executar

```bash
git clone https://github.com/GustavoVieiraDeAraujo/Orion-Index.git
cd Orion-Index

export GITHUB_TOKEN=$(gh auth token)
python3 scripts/generate.py
```

Os cartões são escritos em `docs/`. Pra rodar os outros dois scripts localmente, defina também `PROFILE_PAT` (ver [Requisitos](#requisitos)):

```bash
export PROFILE_PAT=$(gh auth token)
python3 scripts/generate_profile_stats.py
python3 scripts/generate_spaceship.py
```

---

## Automação

| Workflow | Dispara quando | Script |
|---|---|---|
| `atualiza_orion_index.yml` | Todo dia, 06:00 UTC (cron) | `generate.py` |
| `atualiza_estatisticas_perfil.yml` | `atualiza_orion_index.yml` termina (`workflow_run`) | `generate_profile_stats.py` |
| `gera_nave_espacial.yml` | `atualiza_estatisticas_perfil.yml` termina (`workflow_run`) | `generate_spaceship.py` |

Os três formam uma corrente: só o primeiro tem agenda fixa, os outros dois disparam via `workflow_run` assim que o anterior termina — evita dois workflows commitando ao mesmo tempo no mesmo repositório, sem precisar chutar um intervalo de segurança entre horários fixos. Todos também rodam sob demanda (`workflow_dispatch`) e ao detectar push no próprio script. Nenhuma das quatro perspectivas do Orion Index precisa de ação manual — tudo é buscado do zero a cada execução, sempre com o dado mais recente disponível.

---

## Usando em Outro Lugar

Qualquer repositório público pode embutir o card combinado direto, sem precisar rodar nada:

```markdown
![Orion Index](https://raw.githubusercontent.com/GustavoVieiraDeAraujo/Orion-Index/main/docs/orion-index.svg)
```

Ou só um dos quatro painéis individuais (`docs/github_new.svg`, `docs/github_total.svg`, `docs/github_purpose.svg`, `docs/github_growth.svg`), no mesmo formato de URL. Nenhum dos SVGs traz data de atualização embutida — quem for exibir isso decide o formato (por exemplo, puxando a data do último commit deste repositório via API do GitHub).

---

> Documentacao gerada com auxilio de IA.
