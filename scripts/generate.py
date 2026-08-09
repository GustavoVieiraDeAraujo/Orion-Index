#!/usr/bin/env python3
# Busca as 4 perspectivas do Orion Index na API GraphQL do GitHub e gera os
# cartoes SVG em docs/. Por que essas 4 (e nao PYPL/TIOBE/Octoverse) esta
# explicado no README, nao repetido aqui.
import datetime
import json
import os
import re
import urllib.error
import urllib.request

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")

# Linguagens que sao marcacao/estilo/consulta, nao linguagem de programacao
# de proposito geral. Ficam de fora do top 5 de qualquer fonte.
NOT_PROGRAMMING_LANGUAGES = {"HTML/CSS", "HTML", "CSS"}

# Tema escuro dos cartoes -- mesma paleta usada em generate_profile_stats.py,
# pra manter o padrao visual identico entre os cartoes do perfil e os do
# Orion Index.
CARD_BG_FROM = "#161b22"
CARD_BG_TO = "#0d1117"
CARD_STROKE = "#30363d"
CARD_TITLE_COLOR = "#f0f6fc"
CARD_LABEL_COLOR = "#e6edf3"
CARD_VALUE_COLOR = "#8b949e"
CARD_TRACK_COLOR = "#21262d"

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Ruby": "#701516", "Go": "#00ADD8", "Java": "#b07219", "C": "#555555",
    "C++": "#f34b7d", "C/C++": "#f34b7d", "C#": "#178600", "PHP": "#4F5D95",
    "SQL": "#e38c00", "Shell": "#89e051", "Bash/Shell": "#89e051", "R": "#198CE7",
    "Rust": "#dea584", "Swift": "#F05138", "Kotlin": "#A97BFF",
}

# Linguagens comparadas na busca por repositorio no GitHub. Precisam bater
# com o nome que o GitHub usa no qualificador `language:` da busca.
GITHUB_SEARCH_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C", "C#", "Go",
    "Rust", "PHP", "Ruby", "Kotlin", "Swift", "Scala", "Shell", "R", "Dart",
    "Elixir", "Haskell", "Objective-C",
]

# finalidade/proposito -> topico usado no GitHub pra marcar repositorios
# daquele tipo. Candidatos curados; o card mostra o top 5 por contagem real,
# igual a lista de linguagens acima (nem toda finalidade cabe no top 5).
GITHUB_PURPOSE_TOPICS = {
    "IA / Machine Learning": "machine-learning",
    "APIs": "api",
    "Automação": "automation",
    "Ciência de Dados": "data-science",
    "DevOps": "devops",
    "Jogos": "game-development",
    "Segurança": "cybersecurity",
    "Aplicações Web": "webapp",
    "Mobile": "mobile-app",
}


def _github_search_count(query_str, token):
    query = f'{{ search(query: "{query_str}", type: REPOSITORY) {{ repositoryCount }} }}'
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if "errors" in body:
        raise RuntimeError(f"Erro na busca do GitHub pra '{query_str}': {body['errors']}")
    return body["data"]["search"]["repositoryCount"]


def _github_repo_count(lang, qualifiers, token):
    return _github_search_count(f"language:{lang}{qualifiers}", token)


def fetch_github_repo_counts():
    """Repositorios publicos existentes por linguagem, acumulado historico."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN/GH_TOKEN nao configurado")

    data = {lang: _github_repo_count(lang, "", token) for lang in GITHUB_SEARCH_LANGUAGES}
    today = datetime.date.today().strftime("%d/%m/%Y")
    return data, f"busca ao vivo, {today}"


def fetch_github_recent_repo_counts(days=30):
    """Repositorios criados nos ultimos `days` dias por linguagem. Janela
    movel: o corte de data muda a cada execucao."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN/GH_TOKEN nao configurado")

    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    qualifiers = f" created:>{cutoff}"
    data = {lang: _github_repo_count(lang, qualifiers, token) for lang in GITHUB_SEARCH_LANGUAGES}
    today = datetime.date.today().strftime("%d/%m/%Y")
    cutoff_fmt = f"{cutoff.split('-')[2]}/{cutoff.split('-')[1]}"
    return data, f"últimos {days} dias ({cutoff_fmt} a {today})"


def compute_growth_rates(total_data, new_data):
    """Novos ÷ total por linguagem -- normaliza pelo tamanho, entao uma
    linguagem pequena crescendo rapido pode superar uma gigante estabelecida
    aqui mesmo perdendo nas duas metricas absolutas."""
    return {
        lang: 100 * new_data[lang] / total_data[lang]
        for lang in total_data
        if lang in new_data and total_data[lang]
    }


def fetch_github_purpose_counts():
    """Repositorios por topico de proposito (`topic:X`), sem filtro de
    linguagem -- pra que o codigo esta sendo usado, nao em qual linguagem."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN/GH_TOKEN nao configurado")

    data = {
        purpose: _github_search_count(f"topic:{topic}", token)
        for purpose, topic in GITHUB_PURPOSE_TOPICS.items()
    }
    today = datetime.date.today().strftime("%d/%m/%Y")
    return data, f"busca ao vivo, {today}"


def short_label(text, max_chars=22):
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def build_source_svg(data, title, svg_path, unit="%", estimated=frozenset(),
                      gradient=(CARD_BG_FROM, CARD_BG_TO), top_n=5, grad_id="cardBg",
                      default_color="#8a8a8a"):
    """Renderiza um cartao de barras: rotulo em cima, barra full-width embaixo."""
    filtered = {k: v for k, v in data.items() if k not in NOT_PROGRAMMING_LANGUAGES}
    ranked = sorted(filtered.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    bar_scale = ranked[0][1] if ranked else 1

    card_pad = 20
    title_h = 30
    row_h = 50
    width = 380
    bar_w_full = width - card_pad * 2 - 54
    height = card_pad * 2 + title_h + row_h * len(ranked)

    rows = []
    for i, (lang, val) in enumerate(ranked):
        bar_w = max(3, round(bar_w_full * val / bar_scale))
        row_top = card_pad + title_h + i * row_h
        color = LANG_COLORS.get(lang, default_color)
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
    <text x="{card_pad}" y="{row_top + 15}" class="lbl">{short_label(str(lang))}{star}</text>
    <rect x="{card_pad}" y="{row_top + 23}" width="{bar_w_full}" height="11" rx="5.5" class="track"/>
    <rect x="{card_pad}" y="{row_top + 23}" width="{bar_w}" height="11" rx="5.5" fill="{color}" class="bar"/>
    <text x="{card_pad + bar_w_full + 8}" y="{row_top + 32}" class="val">{label}</text>''')

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}">
  <defs>
    <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{gradient[0]}"/>
      <stop offset="100%" stop-color="{gradient[1]}"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 13.5px; }}
    .card {{ fill: url(#{grad_id}); stroke: {CARD_STROKE}; stroke-width: 1; }}
    .title {{ fill: {CARD_TITLE_COLOR}; font-weight: 700; font-size: 15.5px; }}
    .lbl {{ fill: {CARD_LABEL_COLOR}; font-weight: 600; }}
    .val {{ fill: {CARD_VALUE_COLOR}; }}
    .track {{ fill: {CARD_TRACK_COLOR}; }}
    .bar {{ stroke: rgba(255,255,255,0.2); stroke-width: 0.75; }}
  </style>
  <rect x="0" y="0" width="{width}" height="{height}" rx="14" class="card"/>
  <text x="{card_pad}" y="{card_pad + 17}" class="title">{title}</text>
  {"".join(rows)}
</svg>'''

    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)


def build_combined_svg(panel_paths, out_path, cols=2):
    """Junta os cartoes numa grade e escreve o SVG combinado. Concatena texto
    em vez de usar xml.etree pra nao esbarrar em conflito de id/namespace
    entre os SVGs originais."""
    gap = 16
    parsed = []
    for path in panel_paths:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        w = float(re.search(r'width="([\d.]+)"', content).group(1))
        h = float(re.search(r'height="([\d.]+)"', content).group(1))
        body = re.search(r"<svg[^>]*>(.*)</svg>", content, re.DOTALL).group(1)
        parsed.append((body, w, h))

    col_w = parsed[0][1]
    row_h = max(h for _, _, h in parsed)
    n_rows = -(-len(parsed) // cols)  # ceil sem importar math
    total_w = cols * col_w + (cols - 1) * gap
    total_h = n_rows * row_h + (n_rows - 1) * gap

    groups = []
    for i, (body, w, h) in enumerate(parsed):
        col, row = i % cols, i // cols
        x, y = col * (col_w + gap), row * (row_h + gap)
        groups.append(f'<g transform="translate({x},{y})">{body}</g>')

    combined = (
        f'<svg width="{total_w}" height="{total_h}" viewBox="0 0 {total_w} {total_h}" '
        f'xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(groups) + "\n</svg>\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(combined)


def main():
    gh_data, gh_date = fetch_github_repo_counts()
    print(f"GitHub (total): {gh_date}, {len(gh_data)} linguagens")

    gh_new_data, gh_new_date = fetch_github_recent_repo_counts()
    print(f"GitHub (novos): {gh_new_date}, {len(gh_new_data)} linguagens")

    growth_data = compute_growth_rates(gh_data, gh_new_data)
    print(f"GitHub (crescimento): derivado de total e novos, {len(growth_data)} linguagens")

    purpose_data, purpose_date = fetch_github_purpose_counts()
    print(f"GitHub (finalidade): {purpose_date}, {len(purpose_data)} topicos")

    paths = {
        "github_new": os.path.join(DOCS_DIR, "github_new.svg"),
        "github_total": os.path.join(DOCS_DIR, "github_total.svg"),
        "github_purpose": os.path.join(DOCS_DIR, "github_purpose.svg"),
        "github_growth": os.path.join(DOCS_DIR, "github_growth.svg"),
    }

    # ordem bate com a ordem dos bullets no NOTE do README (texto mais
    # curto primeiro, mais longo por ultimo) -- linha 1: Novos + Totais,
    # linha 2: Finalidade + Crescimento
    build_source_svg(
        gh_new_data, "Repositórios Novos",
        paths["github_new"], unit="k", grad_id="gradGithubNew",
    )
    build_source_svg(
        gh_data, "Repositórios Totais",
        paths["github_total"], unit="M", grad_id="gradGithubTotal",
    )
    build_source_svg(
        purpose_data, "Repositórios por Finalidade",
        paths["github_purpose"], unit="k", grad_id="gradGithubPurpose",
        default_color="#a78bfa",
    )
    build_source_svg(
        growth_data, "Crescimento Relativo",
        paths["github_growth"], unit="%", grad_id="gradGithubGrowth",
    )

    build_combined_svg(
        [paths["github_new"], paths["github_total"], paths["github_purpose"], paths["github_growth"]],
        os.path.join(DOCS_DIR, "orion-index.svg"),
        cols=2,
    )

    print("SVGs gerados em docs/.")


if __name__ == "__main__":
    main()
