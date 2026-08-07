# Orion Index

Rastreia as linguagens de programação mais usadas no mundo, combinando três fontes com metodologias diferentes de propósito, em vez de fingir que existe uma resposta única pra "linguagem mais usada".

![Orion Index](docs/orion-index.svg)

## Por que três fontes, e por que elas não concordam

Nenhum índice de popularidade de linguagem mede a mesma coisa que os outros, e este projeto assume isso em vez de esconder:

| Fonte | O que mede de verdade | Frequência | Automação aqui |
| --- | --- | --- | --- |
| **[PYPL](https://pypl.github.io/PYPL.html)** | Interesse de busca por **"[linguagem] tutorial"** no Google Trends: quem está aprendendo ou querendo aprender agora | Mensal | Automática: busca o dado mais recente a cada execução, direto do [dataset oficial](https://github.com/pypl/pypl.github.io) (CC-BY) |
| **[Stack Overflow Developer Survey](https://survey.stackoverflow.co/)** | Autodeclaração de quem já é dev: "em quais linguagens você trabalhou no último ano" | Anual | Automática: baixa o CSV oficial de respostas individuais ([`StackExchange/Survey`](https://github.com/StackExchange/Survey)) e recalcula o % a cada execução. Só o valor em si muda 1x/ano (quando sai pesquisa nova), mas a busca não precisa de nenhuma ação manual |
| **[GitHub Octoverse](https://github.blog/news-insights/octoverse/)** | Contribuidores mensais distintos que **commitaram código de verdade** no GitHub | Esporádica (~1x/ano) | Manual: fixo no código, atualizado quando sai relatório novo. É a única sem forma de automatizar — confirmei que nem `octoverse.github.com` nem o post do blog têm qualquer endpoint de dado por trás, só texto e imagens estáticas |

PYPL mede interesse de aprendizado, Stack Overflow mede autopercepção de profissionais já atuantes, Octoverse mede uso de produção real. Por isso os top 5 de cada um são diferentes entre si, e isso é o esperado, não um erro.

### Por que o TIOBE Index não está aqui

O [TIOBE Index](https://www.tiobe.com/tiobe-index/) é citado com frequência ao lado desses outros três, mas foi excluído de propósito: o [termo de uso deles](https://www.tiobe.com/disclaimer/) proíbe explicitamente copiar, reproduzir ou publicar o conteúdo sem consentimento prévio, e eles vendem o dataset histórico completo como produto pago (US$ 5.000). Raspar e republicar esse dado violaria o próprio termo deles e contornaria um produto que é vendido comercialmente.

### HTML/CSS não entram

Nenhuma das três fontes conta HTML ou CSS no gráfico: marcação e estilo não são linguagem de programação (não têm lógica, controle de fluxo, etc.), mesmo quando a fonte original os inclui na lista.

## Como funciona

[`scripts/generate.py`](scripts/generate.py) roda mensalmente (e sob demanda) via GitHub Actions, sem nenhuma dependência externa além da biblioteca padrão do Python:

1. Baixa o dataset público do PYPL direto do repositório oficial deles e extrai o mês mais recente.
2. Baixa o CSV oficial da Stack Overflow Survey mais recente (tenta o ano atual, cai pro anterior se ainda não saiu) e calcula o % de respondentes por linguagem a partir das respostas individuais (coluna `LanguageHaveWorkedWith`).
3. Usa os números do GitHub Octoverse já registrados no código (constante `OCTOVERSE_2025`), com a fonte, a data e a conta de qualquer estimativa documentadas ao lado, já que essa fonte não tem como ser buscada automaticamente.
4. Gera um card SVG por fonte (`docs/pypl.svg`, `docs/octoverse.svg`, `docs/stackoverflow.svg`) e um combinado (`docs/orion-index.svg`).
5. Commita os arquivos gerados se algo mudou.

Linguagens marcadas com `*` no gráfico do Octoverse não têm total absoluto divulgado pelo GitHub — são estimadas a partir do ganho de contribuidores e do percentual de crescimento, ambos oficiais (ver comentário no código para a conta exata).

## Atualizando o Octoverse

Quando sair um relatório novo, edite a constante `OCTOVERSE_2025` (e `OCTOVERSE_DATE`/`OCTOVERSE_SOURCE`) em [`scripts/generate.py`](scripts/generate.py) e rode o workflow manualmente (ou espere a próxima execução mensal). PYPL e Stack Overflow não precisam de nenhuma ação: se atualizam sozinhos.

## Usando em outro lugar

Qualquer repositório público pode embutir o card combinado direto, sem precisar rodar nada:

```markdown
![Orion Index](https://raw.githubusercontent.com/GustavoVieiraDeAraujo/Orion-Index/main/docs/orion-index.svg)
```

Ou só um dos três painéis individuais (`docs/pypl.svg`, `docs/octoverse.svg`, `docs/stackoverflow.svg`), no mesmo formato de URL.

---

> Documentação e código gerados com auxílio de IA.
