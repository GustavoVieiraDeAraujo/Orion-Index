#!/usr/bin/env python3
"""
Orion Index: rastreia as linguagens de programacao mais usadas no mundo,
combinando 3 fontes com metodologias diferentes (de proposito, ver README):

- PYPL: buscado automaticamente todo mes (dado aberto, CC-BY, atualizado
  pelos mantenedores em pypl/pypl.github.io).
- Stack Overflow Developer Survey: buscado automaticamente todo mes, direto
  do CSV oficial publicado pela propria Stack Exchange no GitHub
  (StackExchange/Survey). So muda de verdade 1x/ano, quando sai pesquisa
  nova, mas a busca em si nao precisa de nenhuma acao manual.
- GitHub Octoverse: fixo no codigo, atualizado manualmente quando sai um
  relatorio novo. Unica das tres sem nenhum jeito de automatizar: nao ha
  API nem dataset estruturado, so um relatorio esporadico em prosa (testado
  e confirmado: nem octoverse.github.com nem o post do blog tem qualquer
  endpoint de dado por tras).

TIOBE foi excluido de proposito: o termo de uso deles proibe copiar ou
republicar o conteudo sem consentimento previo, e eles vendem o dataset
completo. Nao faz sentido raspar o que e vendido como produto.
"""
import csv
import datetime
import io
import os
import re
import sys
import urllib.error
import urllib.request

csv.field_size_limit(sys.maxsize)

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
PYPL_URL = "https://raw.githubusercontent.com/pypl/pypl.github.io/master/PYPL/All.js"

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

# --- GitHub Octoverse 2025 -------------------------------------------------
# Contribuidores mensais distintos no GitHub, agosto/2025. Fonte:
# https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/
# TypeScript, Python e JavaScript: numero absoluto divulgado pelo GitHub,
# conferido em duas fontes independentes.
# Java e C#: o GitHub so divulgou o ganho no ano e o % de crescimento, nao
# o total. Valor = ganho / crescimento + ganho (os dois numeros oficiais).
#   Java: ganho ~174.705, +20,73% -> anterior ~842.761 -> atual ~1.017.466
#   C#:   ganho ~136.735, +22,22% -> anterior ~615.369 -> atual ~752.104
# Marcados como estimativa no grafico (nao e numero que o GitHub deu pronto).
OCTOVERSE_2025 = {
    "TypeScript": 2_636_006,
    "Python": 2_600_000,
    "JavaScript": 2_150_000,
    "Java": 1_017_000,
    "C#": 752_000,
}
OCTOVERSE_ESTIMATED = {"Java", "C#"}
OCTOVERSE_DATE = "ago/2025"
OCTOVERSE_DATE_FULL = "dados de agosto/2025, relatório publicado em outubro/2025"
# Numeros vieram deste relatorio (nao mude so por causa do check de frescor).
OCTOVERSE_REPORT_SOURCE = "https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/"
# Ultimo post da categoria Octoverse que eu (ou uma sessao de IA) ja revisei
# e confirmei que nao tem numero novo de linguagem. O check_octoverse_freshness.py
# le esta constante — atualize pra URL do post revisado toda vez que checar um
# novo aviso, mesmo que a conclusao seja "sem novidade", pra nao alertar de novo.
# Revisado em 07/08/2026: post so reforça o crescimento de 66% do relatorio
# original, sem numero absoluto novo.
OCTOVERSE_SOURCE = "https://github.blog/ai-and-ml/generative-ai/how-ai-is-reshaping-developer-choice-and-octoverse-data-proves-it/"

# --- Stack Overflow Developer Survey -----------------------------------
# Buscado automaticamente do CSV oficial (respostas individuais, coluna
# "LanguageHaveWorkedWith") publicado pela propria Stack Exchange:
# https://github.com/StackExchange/Survey/tree/main/packages/archive
# raw.githubusercontent.com so devolve o ponteiro Git LFS pra esse arquivo
# (ele e grande, ~140MB); a URL abaixo (github.com/.../raw/...) resolve o
# LFS de verdade e devolve o CSV completo.
STACKOVERFLOW_CSV_URL = "https://github.com/StackExchange/Survey/raw/refs/heads/main/packages/archive/{year}/results.csv"


def fetch_pypl():
    """Baixa o dataset publico do PYPL e retorna {linguagem: fatia} do mes mais recente."""
    with urllib.request.urlopen(PYPL_URL, timeout=30) as resp:
        text = resp.read().decode("utf-8")

    header_match = re.search(r"'Date',(.*?)\]", text, re.DOTALL)
    if not header_match:
        raise RuntimeError("Nao consegui achar o cabecalho de linguagens no PYPL")
    langs = [x.strip().strip("'") for x in header_match.group(1).split(",") if x.strip()]

    rows = re.findall(r"\[new Date\((\d+),(\d+),\d+\),([^\]]*)\]", text)
    if not rows:
        raise RuntimeError("Nao consegui achar nenhuma linha de dados no PYPL")
    year, month, values_raw = rows[-1]
    values = [float(v) for v in values_raw.split(",") if v.strip() != ""]

    data = dict(zip(langs, values))
    date_label = f"{int(month) + 1:02d}/{year}"
    return data, date_label


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
    pypl_data, pypl_date = fetch_pypl()
    print(f"PYPL: dados de {pypl_date}, {len(pypl_data)} linguagens")

    so_data, so_date = fetch_stackoverflow()
    print(f"Stack Overflow Survey: {so_date}, {len(so_data)} linguagens")

    paths = {
        "pypl": os.path.join(DOCS_DIR, "pypl.svg"),
        "octoverse": os.path.join(DOCS_DIR, "octoverse.svg"),
        "stackoverflow": os.path.join(DOCS_DIR, "stackoverflow.svg"),
    }

    build_source_svg(
        pypl_data, "PYPL", "interesse de busca por tutorial", pypl_date,
        paths["pypl"], unit="pct_frac", grad_id="gradPypl",
    )
    build_source_svg(
        OCTOVERSE_2025, "GitHub Octoverse", "contribuidores mensais", OCTOVERSE_DATE,
        paths["octoverse"], unit="M", estimated=OCTOVERSE_ESTIMATED, grad_id="gradOctoverse",
    )
    build_source_svg(
        so_data, "Stack Overflow Survey", "% de respondentes", so_date,
        paths["stackoverflow"], unit="%", grad_id="gradStackoverflow",
    )

    build_combined_svg(
        [paths["pypl"], paths["octoverse"], paths["stackoverflow"]],
        os.path.join(DOCS_DIR, "orion-index.svg"),
    )

    print("SVGs gerados em docs/.")


if __name__ == "__main__":
    main()
