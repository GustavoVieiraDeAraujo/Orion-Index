# Orion Index

Rastreia as linguagens de programação mais usadas no mundo, combinando três perspectivas diferentes de propósito, em vez de fingir que existe uma resposta única pra "linguagem mais usada". As três são buscadas ao vivo, sem nenhum número fixo no código, direto de fontes com API oficial ou dataset publicado pela própria organização dona do dado.

![Orion Index](docs/orion-index.svg)

## Por que três perspectivas, e por que elas não concordam

Nenhum índice de popularidade de linguagem mede a mesma coisa que os outros, e este projeto assume isso em vez de esconder:

| Perspectiva | O que mede de verdade | Como é buscado |
| --- | --- | --- |
| **GitHub — Volume Total** | Quantidade de repositórios públicos **já existentes** por linguagem principal — o acumulado histórico | API GraphQL oficial do GitHub (`search(query: "language:X")`), consulta ao vivo |
| **GitHub — Em Alta** | Quantidade de repositórios **criados nos últimos 30 dias** por linguagem — o que está sendo adotado agora, não o que já existe | Mesma API, com o qualificador `created:>DATA`. Janela móvel: muda de verdade a cada execução |
| **[Stack Overflow Developer Survey](https://survey.stackoverflow.co/)** | Autodeclaração de quem já é dev: "em quais linguagens você trabalhou no último ano" | CSV oficial de respostas individuais ([`StackExchange/Survey`](https://github.com/StackExchange/Survey)), recalculado a cada execução |

Volume total mede o que já existe (acumulado de anos), Em Alta mede o que está crescendo agora (janela de 30 dias), Stack Overflow mede autopercepção de profissionais atuantes. Por isso os top 5 de cada uma são diferentes entre si, e isso é o esperado, não um erro — por exemplo, Python lidera disparado em "Em Alta" (boom de IA/ciência de dados puxando projeto novo), mas fica atrás de JavaScript no volume total acumulado.

### Por que não usamos PYPL

O [PYPL](https://pypl.github.io/PYPL.html) (interesse de busca por "[linguagem] tutorial" via Google Trends) é dado real, aberto (CC-BY) e é a referência mais estabelecida pra esse ângulo específico há mais de uma década — mas é um projeto pessoal de terceiro, sem contrato de acesso ou API oficial por trás. Preferimos manter as três perspectivas 100% dentro de fontes com API oficial (GitHub) ou dataset publicado pela própria organização dona do dado (Stack Exchange), então trocamos o ângulo de "interesse de aprendizado" por "o que está sendo criado agora" (GitHub Em Alta), que captura uma ideia parecida (tendência/momentum) sem depender de mais ninguém no meio.

### Por que não usamos o relatório Octoverse do GitHub

O [GitHub Octoverse](https://github.blog/news-insights/octoverse/) mede contribuidores mensais distintos — métrica interessante, mas é só um relatório esporádico em prosa, sem API nem dataset estruturado por trás (testamos: nem `octoverse.github.com` nem os posts do blog têm qualquer endpoint de dado). Sem forma de automatizar de verdade, preferimos usar a própria API do GitHub pra outras duas métricas (volume total e em alta) que medem algo relacionado, mas são 100% automatizáveis.

### Por que o TIOBE Index não está aqui

O [TIOBE Index](https://www.tiobe.com/tiobe-index/) é citado com frequência ao lado desses outros, mas foi excluído de propósito: o [termo de uso deles](https://www.tiobe.com/disclaimer/) proíbe explicitamente copiar, reproduzir ou publicar o conteúdo sem consentimento prévio, e eles vendem o dataset histórico completo como produto pago (US$ 5.000). Raspar e republicar esse dado violaria o próprio termo deles e contornaria um produto que é vendido comercialmente.

### HTML/CSS não entram

Nenhuma das três perspectivas conta HTML ou CSS no gráfico: marcação e estilo não são linguagem de programação (não têm lógica, controle de fluxo, etc.), mesmo quando a fonte original os inclui na lista.

## Como funciona

[`scripts/generate.py`](scripts/generate.py) roda mensalmente (e sob demanda) via GitHub Actions, sem nenhuma dependência externa além da biblioteca padrão do Python e o `GITHUB_TOKEN` automático do Actions:

1. Consulta a API GraphQL do GitHub (`search(query: "language:X", type: REPOSITORY)`) pra cada linguagem candidata e pega a contagem total de repositórios.
2. Repete a mesma consulta com `created:>DATA` (últimos 30 dias) pra medir o que está sendo criado agora.
3. Baixa o CSV oficial da Stack Overflow Survey mais recente (tenta o ano atual, cai pro anterior se ainda não saiu) e calcula o % de respondentes por linguagem a partir das respostas individuais (coluna `LanguageHaveWorkedWith`).
4. Gera um card SVG por perspectiva (`docs/github.svg`, `docs/github_recent.svg`, `docs/stackoverflow.svg`) e um combinado (`docs/orion-index.svg`).
5. Commita os arquivos gerados se algo mudou.

Nenhuma das três perspectivas precisa de ação manual — tudo é buscado do zero a cada execução, sempre com o dado mais recente disponível em cada fonte.

## Usando em outro lugar

Qualquer repositório público pode embutir o card combinado direto, sem precisar rodar nada:

```markdown
![Orion Index](https://raw.githubusercontent.com/GustavoVieiraDeAraujo/Orion-Index/main/docs/orion-index.svg)
```

Ou só um dos três painéis individuais (`docs/github.svg`, `docs/github_recent.svg`, `docs/stackoverflow.svg`), no mesmo formato de URL.

---

> Documentação e código gerados com auxílio de IA.
