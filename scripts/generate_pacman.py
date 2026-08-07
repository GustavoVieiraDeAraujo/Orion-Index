#!/usr/bin/env python3
"""
Gera uma animacao SVG ORIGINAL (Pac-Man comendo o grafico de contribuicoes
do Gustavo) a partir dos dados reais de contribuicao, buscados ao vivo via
GraphQL do GitHub. Nao usa nenhuma action, biblioteca ou gerador pronto de
terceiro pra isso -- so a API oficial do GitHub pros dados, e SVG + SMIL
(animacao nativa do proprio formato SVG, sem JS) escritos aqui do zero.

Como a animacao e construida:
- Cada semana do ano vira uma coluna, cada dia da semana uma linha -- mesma
  grade do grafico de contribuicoes de verdade do GitHub.
- O Pac-Man percorre a grade em zigue-zague (varre a linha de domingo da
  esquerda pra direita, desce, varre a linha de segunda da direita pra
  esquerda, e assim por diante) via <animateMotion> com um path calculado.
- Cada quadradinho tem sua propria animacao de opacidade, com o instante
  exato ("begin") calculado a partir da posicao real do Pac-Man no path
  naquele momento -- pra ele "comer" o quadrado bem na hora que passa por
  cima, nao antes nem depois.
- No fim do ciclo tudo reaparece e recomeca (repeatCount indefinite).
"""
import json
import math
import os
import subprocess

PROFILE_OWNER = "GustavoVieiraDeAraujo"
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")

CELL = 11
GAP = 3
STEP = CELL + GAP
PAD = 22
TITLE_H = 26
DURATION = 26  # segundos por volta completa


def fetch_contribution_calendar():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays { date contributionCount }
            }
          }
        }
      }
    }
    """
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}", "-f", f"login={PROFILE_OWNER}"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def color_for(count, max_count):
    if count == 0:
        return "#2d3748"
    ratio = count / max_count if max_count else 0
    if ratio > 0.75:
        return "#22d3ee"
    if ratio > 0.5:
        return "#38bdf8"
    if ratio > 0.25:
        return "#60a5fa"
    return "#3b82f6"


def pacman_path(d, r):
    """Corpo do Pac-Man (circulo com uma fatia cortada = boca), boca
    apontando pra +x. `d` e o meio-angulo de abertura da boca em graus."""
    a = math.radians(d)
    x1, y1 = r * math.cos(a), r * math.sin(a)
    x2, y2 = r * math.cos(-a), r * math.sin(-a)
    return f"M0,0 L{x1:.2f},{y1:.2f} A{r},{r} 0 1,0 {x2:.2f},{y2:.2f} Z"


def build_svg(calendar):
    weeks = calendar["weeks"]
    n_weeks = len(weeks)
    max_count = max(
        (day["contributionCount"] for week in weeks for day in week["contributionDays"]),
        default=1,
    ) or 1

    grid_w = n_weeks * STEP - GAP
    grid_h = 7 * STEP - GAP
    width = grid_w + PAD * 2
    height = grid_h + PAD * 2 + TITLE_H

    # ordem em zigue-zague (boustrophedon): linha 0 (domingo) esq->dir,
    # linha 1 (segunda) dir->esq, etc. -- da o caminho continuo do Pac-Man.
    cells = []  # (week_idx, day_idx, count, order_index_within_row)
    for day_idx in range(7):
        week_range = range(n_weeks) if day_idx % 2 == 0 else range(n_weeks - 1, -1, -1)
        for order, week_idx in enumerate(week_range):
            count = weeks[week_idx]["contributionDays"][day_idx]["contributionCount"] if day_idx < len(weeks[week_idx]["contributionDays"]) else 0
            cells.append((week_idx, day_idx, count, order))

    row_len = (n_weeks - 1) * STEP  # distancia horizontal de uma varredura
    step_len = STEP  # distancia do pulo vertical entre linhas
    total_len = 7 * row_len + 6 * step_len

    def cell_center(week_idx, day_idx):
        cx = PAD + week_idx * STEP + CELL / 2
        cy = PAD + TITLE_H + day_idx * STEP + CELL / 2
        return cx, cy

    # path de movimento do Pac-Man: liga o centro de cada extremo de linha
    move_points = []
    for day_idx in range(7):
        y = PAD + TITLE_H + day_idx * STEP + CELL / 2
        x_left = PAD + CELL / 2
        x_right = PAD + (n_weeks - 1) * STEP + CELL / 2
        if day_idx % 2 == 0:
            move_points.append((x_left, y))
            move_points.append((x_right, y))
        else:
            move_points.append((x_right, y))
            move_points.append((x_left, y))
    motion_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in move_points)

    cell_rows = []
    for week_idx, day_idx, count, order in cells:
        cx, cy = cell_center(week_idx, day_idx)
        cumulative = day_idx * (row_len + step_len) + order * STEP
        t = cumulative / total_len
        t_fade = max(0.0, min(0.999, t))
        color = color_for(count, max_count)
        cell_rows.append(f'''
    <rect x="{cx - CELL / 2:.1f}" y="{cy - CELL / 2:.1f}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}">
      <animate attributeName="opacity" dur="{DURATION}s" repeatCount="indefinite"
        keyTimes="0;{t_fade:.4f};{min(t_fade + 0.006, 1):.4f};1" values="1;1;0;0" />
    </rect>''')

    pac_r = CELL * 0.85
    d_open = pacman_path(32, pac_r)
    d_closed = pacman_path(4, pac_r)

    total = calendar["totalContributions"]
    title = f"{total} contribuições no último ano · Pac-Man come em ordem, semana a semana"

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Pac-Man comendo meus commits">
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 12px; }}
    .card {{ fill: #1f2937; stroke: #4b5563; stroke-width: 1; }}
    .title {{ fill: #9ca3af; }}
  </style>
  <rect x="0" y="0" width="{width}" height="{height}" rx="14" class="card"/>
  <text x="{PAD}" y="{PAD + 4}" class="title">{title}</text>
  {"".join(cell_rows)}
  <g>
    <animateMotion dur="{DURATION}s" repeatCount="indefinite" rotate="auto" path="{motion_d}"/>
    <path fill="#fbbf24">
      <animate attributeName="d" dur="0.28s" repeatCount="indefinite"
        keyTimes="0;0.5;1" values="{d_open};{d_closed};{d_open}"/>
    </path>
  </g>
</svg>'''
    return svg


def main():
    calendar = fetch_contribution_calendar()
    svg = build_svg(calendar)
    out_path = os.path.join(DOCS_DIR, "pacman.svg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Pac-Man gerado em docs/pacman.svg ({calendar['totalContributions']} contribuições).")


if __name__ == "__main__":
    main()
