#!/usr/bin/env python3
"""
Orion Index: rastreia as linguagens de programacao mais usadas no mundo,
combinando 3 fontes com metodologias diferentes (de proposito, ver README):

- PYPL: buscado automaticamente todo mes (dado aberto, CC-BY, atualizado
  pelos mantenedores em pypl/pypl.github.io).
- GitHub Octoverse: fixo no codigo, atualizado manualmente quando sai um
  relatorio novo (nao ha API, so relatorio esporadico em prosa).
- Stack Overflow Developer Survey: fixo no codigo, atualizado manualmente
  quando sai uma pesquisa nova (anual).

TIOBE foi excluido de proposito: o termo de uso deles proibe copiar ou
republicar o conteudo sem consentimento previo, e eles vendem o dataset
completo. Nao faz sentido raspar o que e vendido como produto.
"""
import datetime
import os
import re
import sys
import urllib.request

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
OCTOVERSE_SOURCE = "https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/"

# --- Stack Overflow Developer Survey 2025 -----------------------------------
# % de respondentes que usaram a linguagem no ultimo ano ("used in the past
# year"). Conferido em duas fontes independentes. HTML/CSS excluido (nao e
# linguagem de programacao).
# Fonte: https://survey.stackoverflow.co/2025/technology/
STACKOVERFLOW_2025 = {
    "JavaScript": 66.0,
    "SQL": 58.6,
    "Python": 57.9,
    "Bash/Shell": 48.7,
    "TypeScript": 43.6,
}
STACKOVERFLOW_DATE = "pesquisa de 2025, ~49 mil respondentes"
STACKOVERFLOW_SOURCE = "https://survey.stackoverflow.co/2025/technology/"


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
        STACKOVERFLOW_2025, "Stack Overflow Survey", "% de respondentes", STACKOVERFLOW_DATE,
        paths["stackoverflow"], unit="%", grad_id="gradStackoverflow",
    )

    build_combined_svg(
        [paths["pypl"], paths["octoverse"], paths["stackoverflow"]],
        os.path.join(DOCS_DIR, "orion-index.svg"),
    )

    print("SVGs gerados em docs/.")


if __name__ == "__main__":
    main()
