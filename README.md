# Orion Index

Rastreia as linguagens de programação mais usadas no mundo, combinando três fontes com metodologias diferentes de propósito, em vez de fingir que existe uma resposta única pra "linguagem mais usada". As três são buscadas ao vivo, sem nenhum número fixo no código.

![Orion Index](docs/orion-index.svg)

## Por que três fontes, e por que elas não concordam

Nenhum índice de popularidade de linguagem mede a mesma coisa que os outros, e este projeto assume isso em vez de esconder:

| Fonte | O que mede de verdade | Como é buscado |
| --- | --- | --- |
| **[PYPL](https://pypl.github.io/PYPL.html)** | Interesse de busca por **"[linguagem] tutorial"** no Google Trends: quem está aprendendo ou querendo aprender agora | Direto do [dataset oficial](https://github.com/pypl/pypl.github.io) (CC-BY), mês mais recente |
| **[Stack Overflow Developer Survey](https://survey.stackoverflow.co/)** | Autodeclaração de quem já é dev: "em quais linguagens você trabalhou no último ano" | CSV oficial de respostas individuais ([`StackExchange/Survey`](https://github.com/StackExchange/Survey)), recalculado a cada execução |
| **GitHub** | Quantidade de repositórios públicos por linguagem principal | API GraphQL oficial do GitHub (`search(query: "language:X")`), consulta ao vivo |

PYPL mede interesse de aprendizado, Stack Overflow mede autopercepção de profissionais já atuantes, GitHub mede volume de repositórios existentes. Por isso os top 5 de cada um são diferentes entre si, e isso é o esperado, não um erro.

### Por que não é o relatório Octoverse do GitHub

O [GitHub Octoverse](https://github.blog/news-insights/octoverse/) mede contribuidores mensais distintos, uma métrica diferente da usada aqui (quantidade de repositórios). A troca foi deliberada: o Octoverse é só um relatório esporádico em prosa, sem API nem dataset estruturado por trás (testamos: nem `octoverse.github.com` nem os posts do blog têm qualquer endpoint de dado), então não tinha como automatizar de verdade sem admitir uma fonte diferente. A busca por `language:X` na API do GitHub mede outra coisa, mas é 100% automatizável, oficial, e ao vivo — trade-off que preferimos a manter uma métrica "melhor" que precisa de atualização manual pra sempre.

### Por que o TIOBE Index não está aqui

O [TIOBE Index](https://www.tiobe.com/tiobe-index/) é citado com frequência ao lado desses outros, mas foi excluído de propósito: o [termo de uso deles](https://www.tiobe.com/disclaimer/) proíbe explicitamente copiar, reproduzir ou publicar o conteúdo sem consentimento prévio, e eles vendem o dataset histórico completo como produto pago (US$ 5.000). Raspar e republicar esse dado violaria o próprio termo deles e contornaria um produto que é vendido comercialmente.

### HTML/CSS não entram

Nenhuma das três fontes conta HTML ou CSS no gráfico: marcação e estilo não são linguagem de programação (não têm lógica, controle de fluxo, etc.), mesmo quando a fonte original os inclui na lista.

## Como funciona

[`scripts/generate.py`](scripts/generate.py) roda mensalmente (e sob demanda) via GitHub Actions, sem nenhuma dependência externa além da biblioteca padrão do Python e o `GITHUB_TOKEN` automático do Actions:

1. Baixa o dataset público do PYPL direto do repositório oficial deles e extrai o mês mais recente.
2. Baixa o CSV oficial da Stack Overflow Survey mais recente (tenta o ano atual, cai pro anterior se ainda não saiu) e calcula o % de respondentes por linguagem a partir das respostas individuais (coluna `LanguageHaveWorkedWith`).
3. Consulta a API GraphQL do GitHub (`search(query: "language:X", type: REPOSITORY)`) pra cada linguagem candidata e pega a contagem de repositórios.
4. Gera um card SVG por fonte (`docs/pypl.svg`, `docs/github.svg`, `docs/stackoverflow.svg`) e um combinado (`docs/orion-index.svg`).
5. Commita os arquivos gerados se algo mudou.

Nenhuma das três fontes precisa de ação manual — tudo é buscado do zero a cada execução.

## Usando em outro lugar

Qualquer repositório público pode embutir o card combinado direto, sem precisar rodar nada:

```markdown
![Orion Index](https://raw.githubusercontent.com/GustavoVieiraDeAraujo/Orion-Index/main/docs/orion-index.svg)
```

Ou só um dos três painéis individuais (`docs/pypl.svg`, `docs/github.svg`, `docs/stackoverflow.svg`), no mesmo formato de URL.

---

> Documentação e código gerados com auxílio de IA.
