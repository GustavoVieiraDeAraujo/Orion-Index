#!/usr/bin/env python3
"""
Orion Index: rastreia as linguagens de programacao mais usadas no mundo,
combinando 3 perspectivas diferentes de proposito (ver README), todas
buscadas ao vivo, sem nenhum numero fixo no codigo:

- GitHub, volume total: quantidade de repositorios publicos existentes por
  linguagem principal — o que ja existe, acumulado desde sempre.
- GitHub, criados recentemente: quantidade de repositorios criados nos
  ultimos 30 dias por linguagem — o que esta sendo adotado agora. Janela
  movel, muda de verdade a cada execucao (as duas metricas do GitHub usam
  a mesma API GraphQL oficial, search + language:X).
- Stack Overflow Developer Survey: % de respondentes que usaram cada
  linguagem no ultimo ano, calculado a partir do CSV oficial de respostas
  individuais publicado pela propria Stack Exchange no GitHub. Sempre busca
  o ano mais recente disponivel (tenta o atual, cai pro anterior se ainda
  nao saiu).

Nao usamos o relatorio Octoverse do GitHub (mede contribuidores mensais):
e so um relatorio esporadico em prosa, sem API nem dataset estruturado por
tras (confirmado testando octoverse.github.com e o post do blog, nenhum
dos dois tem endpoint de dado). E nao usamos o PYPL (interesse de busca via
Google Trends): apesar de ser dado real e a fonte mais estabelecida pra
esse angulo, e um projeto pessoal de terceiro sem contrato de acesso —
preferimos ficar 100% dentro de fontes com API oficial ou dataset publicado
pela propria organizacao dona do dado.

TIOBE foi excluido de proposito: o termo de uso deles proibe copiar ou
republicar o conteudo sem consentimento previo, e eles vendem o dataset
completo. Nao faz sentido raspar o que e vendido como produto.
"""
import csv
import datetime
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

csv.field_size_limit(sys.maxsize)

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")

# Linguagens que sao marcacao/estilo/consulta, nao linguagem de programacao
# de proposito geral. Ficam de fora do top 5 de qualquer fonte.
NOT_PROGRAMMING_LANGUAGES = {"HTML/CSS", "HTML", "CSS"}

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Ruby": "#701516", "Go": "#00ADD8", "Java": "#b07219", "C": "#555555",
    "C++": "#f34b7d", "C/C++": "#f34b7d", "C#": "#178600", "PHP": "#4F5D95",
    "SQL": "#e38c00", "Shell": "#89e051", "Bash/Shell": "#89e051", "R": "#198CE7",
    "Rust": "#dea584", "Swift": "#F05138", "Kotlin": "#A97BFF",
}

# raw.githubusercontent.com so devolve o ponteiro Git LFS pra esse arquivo
# (ele e grande, ~140MB); a URL abaixo (github.com/.../raw/...) resolve o
# LFS de verdade e devolve o CSV completo.
STACKOVERFLOW_CSV_URL = "https://github.com/StackExchange/Survey/raw/refs/heads/main/packages/archive/{year}/results.csv"

# Linguagens comparadas na busca por repositorio no GitHub. Precisam bater
# com o nome que o GitHub usa no qualificador `language:` da busca.
GITHUB_SEARCH_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C", "C#", "Go",
    "Rust", "PHP", "Ruby", "Kotlin", "Swift", "Scala", "Shell", "R", "Dart",
    "Elixir", "Haskell", "Objective-C",
]


def fetch_stackoverflow():
    """Baixa o CSV oficial (respostas individuais) da pesquisa mais recente
    disponivel e conta quantos % de respondentes usaram cada linguagem
    (coluna LanguageHaveWorkedWith, resposta multipla separada por ';').
    Tenta o ano atual primeiro; se a pesquisa daquele ano ainda nao saiu,
    cai pro ano anterior."""
    current_year = datetime.date.today().year
    for year in (current_year, current_year - 1, current_year - 2):
        url = STACKOVERFLOW_CSV_URL.format(year=year)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "orion-index"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        text = raw.decode("utf-8-sig")
        break
    else:
        raise RuntimeError("Nao encontrei CSV da Stack Overflow Survey em nenhum ano recente")

    from collections import Counter
    counts = Counter()
    total = 0
    reader = csv.DictReader(io.StringIO(text))
    col = "LanguageHaveWorkedWith"
    for row in reader:
        val = row.get(col)
        if not val or val == "NA":
            continue
        total += 1
        for lang in val.split(";"):
            lang = lang.strip()
            if not lang:
                continue
            lang = lang.replace("Bash/Shell (all shells)", "Bash/Shell")
            counts[lang] += 1

    data = {lang: 100 * n / total for lang, n in counts.items()}
    total_fmt = f"{total:,}".replace(",", ".")
    return data, f"pesquisa de {year}, {total_fmt} respondentes"


def _github_repo_count(lang, qualifiers, token):
    query = f'{{ search(query: "language:{lang}{qualifiers}", type: REPOSITORY) {{ repositoryCount }} }}'
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if "errors" in body:
        raise RuntimeError(f"Erro na busca do GitHub pra {lang}: {body['errors']}")
    return body["data"]["search"]["repositoryCount"]


def fetch_github_repo_counts():
    """Conta quantos repositorios publicos existem por linguagem principal
    (volume total acumulado), via API GraphQL oficial do GitHub
    (`search(query: "language:X")`). Precisa de um token (o GITHUB_TOKEN
    automatico do Actions serve, so precisa de acesso de leitura publico)."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN/GH_TOKEN nao configurado")

    data = {lang: _github_repo_count(lang, "", token) for lang in GITHUB_SEARCH_LANGUAGES}
    today = datetime.date.today().strftime("%d/%m/%Y")
    return data, f"busca ao vivo, {today}"


def fetch_github_recent_repo_counts(days=30):
    """Conta quantos repositorios publicos foram CRIADOS nos ultimos `days`
    dias por linguagem principal — janela movel, muda de verdade a cada
    execucao (ao contrario do total acumulado). Mesma API, so acrescenta o
    qualificador `created:>DATA`."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN/GH_TOKEN nao configurado")

    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    qualifiers = f" created:>{cutoff}"
    data = {lang: _github_repo_count(lang, qualifiers, token) for lang in GITHUB_SEARCH_LANGUAGES}
    today = datetime.date.today().strftime("%d/%m/%Y")
    cutoff_fmt = f"{cutoff.split('-')[2]}/{cutoff.split('-')[1]}"
    return data, f"últimos {days} dias ({cutoff_fmt} a {today})"


def build_source_svg(data, title, source_label, date_label, svg_path,
                      unit="%", estimated=frozenset(), gradient=("#D1D5DB", "#374151"), top_n=5, grad_id="cardBg"):
    filtered = {k: v for k, v in data.items() if k not in NOT_PROGRAMMING_LANGUAGES}
    ranked = sorted(filtered.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    bar_scale = ranked[0][1] if ranked else 1

    row_h = 32
    card_pad = 20
    title_h = 44
    width = 380
    label_w = 84
    bar_x = card_pad + label_w + 10
    bar_max_w = width - bar_x - card_pad - 56
    height = card_pad * 2 + title_h + row_h * len(ranked)

    rows = []
    for i, (lang, val) in enumerate(ranked):
        bar_w = max(3, round(bar_max_w * val / bar_scale))
        cy = card_pad + title_h + i * row_h + row_h / 2
        color = LANG_COLORS.get(lang, "#8a8a8a")
        star = " *" if lang in estimated else ""
        if unit == "%":
            label = f"{val:.1f}%"
        elif unit == "pct_frac":
            label = f"{val * 100:.1f}%"
        elif unit == "M":
            label = f"{'~' if lang in estimated else ''}{val / 1_000_000:.2f}M"
        elif unit == "k":
            label = f"{val / 1_000:.1f}k" if val >= 1000 else f"{val:.0f}"
        else:
            label = f"{val:.3f}"
        rows.append(f'''
    <text x="{card_pad + label_w}" y="{cy + 4}" text-anchor="end" class="lbl">{lang}{star}</text>
    <rect x="{bar_x}" y="{cy - 6}" width="{bar_max_w}" height="12" rx="6" class="track"/>
    <rect x="{bar_x}" y="{cy - 6}" width="{bar_w}" height="12" rx="6" fill="{color}"/>
    <text x="{bar_x + bar_max_w + 10}" y="{cy + 4}" class="val">{label}</text>''')

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title} ({source_label})">
  <defs>
    <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{gradient[0]}"/>
      <stop offset="100%" stop-color="{gradient[1]}"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 11.5px; }}
    .card {{ fill: url(#{grad_id}); stroke: #4b5563; stroke-width: 1; }}
    .title {{ fill: #1f2937; font-weight: 700; font-size: 13.5px; }}
    .subtitle {{ fill: #374151; font-size: 10.5px; }}
    .lbl {{ fill: #1f2937; font-weight: 600; }}
    .val {{ fill: #f9fafb; }}
    .track {{ fill: rgba(0,0,0,0.15); }}
  </style>
  <rect x="0" y="0" width="{width}" height="{height}" rx="14" class="card"/>
  <text x="{card_pad}" y="{card_pad + 15}" class="title">{title}</text>
  <text x="{card_pad}" y="{card_pad + 30}" class="subtitle">{source_label} · {date_label}</text>
  {"".join(rows)}
</svg>'''

    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)


def build_combined_svg(panel_paths, out_path):
    """Junta os 3 SVGs individuais lado a lado num so arquivo, via manipulacao
    de texto simples (evita os problemas de namespace do xml.etree ao mesclar
    varios documentos SVG independentes)."""
    gap = 16
    inner_bodies = []
    total_w = 0.0
    max_h = 0.0

    for path in panel_paths:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        w = float(re.search(r'width="([\d.]+)"', content).group(1))
        h = float(re.search(r'height="([\d.]+)"', content).group(1))
        body = re.search(r"<svg[^>]*>(.*)</svg>", content, re.DOTALL).group(1)
        inner_bodies.append((body, w))
        total_w += w + gap
        max_h = max(max_h, h)
    total_w -= gap

    groups = []
    x_offset = 0.0
    for body, w in inner_bodies:
        groups.append(f'<g transform="translate({x_offset},0)">{body}</g>')
        x_offset += w + gap

    combined = (
        f'<svg width="{total_w}" height="{max_h}" viewBox="0 0 {total_w} {max_h}" '
        f'xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(groups) + "\n</svg>\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(combined)


def main():
    gh_data, gh_date = fetch_github_repo_counts()
    print(f"GitHub (total): {gh_date}, {len(gh_data)} linguagens")

    gh_recent_data, gh_recent_date = fetch_github_recent_repo_counts()
    print(f"GitHub (recentes): {gh_recent_date}, {len(gh_recent_data)} linguagens")

    so_data, so_date = fetch_stackoverflow()
    print(f"Stack Overflow Survey: {so_date}, {len(so_data)} linguagens")

    paths = {
        "github": os.path.join(DOCS_DIR, "github.svg"),
        "github_recent": os.path.join(DOCS_DIR, "github_recent.svg"),
        "stackoverflow": os.path.join(DOCS_DIR, "stackoverflow.svg"),
    }

    build_source_svg(
        gh_data, "GitHub — Volume Total", "repositórios por linguagem", gh_date,
        paths["github"], unit="M", grad_id="gradGithub",
    )
    build_source_svg(
        gh_recent_data, "GitHub — Em Alta", "repositórios criados", gh_recent_date,
        paths["github_recent"], unit="k", grad_id="gradGithubRecent",
    )
    build_source_svg(
        so_data, "Stack Overflow Survey", "% de respondentes", so_date,
        paths["stackoverflow"], unit="%", grad_id="gradStackoverflow",
    )

    build_combined_svg(
        [paths["github"], paths["github_recent"], paths["stackoverflow"]],
        os.path.join(DOCS_DIR, "orion-index.svg"),
    )

    print("SVGs gerados em docs/.")


if __name__ == "__main__":
    main()
