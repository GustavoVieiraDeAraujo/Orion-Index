#!/usr/bin/env python3
"""
Gera uma animacao SVG ORIGINAL (nave espacial atirando nos commits do
grafico de contribuicoes do Gustavo) a partir dos dados reais de
contribuicao, buscados ao vivo via GraphQL do GitHub. Nao usa nenhuma
action, biblioteca ou gerador pronto de terceiro pra isso -- so a API
oficial do GitHub pros dados, e SVG + SMIL (animacao nativa do proprio
formato SVG, sem JS) escritos aqui do zero.

Como a animacao e construida:
- Cada semana do ano vira uma coluna, cada dia da semana uma linha -- mesma
  grade do grafico de contribuicoes de verdade do GitHub.
- A nave percorre a grade em zigue-zague (varre a linha de domingo da
  esquerda pra direita, desce, varre a linha de segunda da direita pra
  esquerda, e assim por diante) via <animateMotion> com um path calculado,
  virando de verdade (rotate="auto") conforme a direcao do trecho.
- Quadrado com contribuicao de verdade (count > 0) "explode" quando a nave
  passa: flash branco, leve estouro de escala, e particulas que saem
  voando do centro do quadrado. Quadrado vazio (sem commit naquele dia) so
  desaparece rapido, sem efeito, porque nunca foi um alvo de verdade.
- O instante exato de cada explosao ("begin") e calculado a partir da
  posicao real da nave no path naquele momento, pra ela atingir o quadrado
  bem na hora que passa por cima.
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
BURST = 0.16  # duracao da explosao (fracao curta dentro do ciclo)


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
    # linha 1 (segunda) dir->esq, etc. -- caminho continuo da nave.
    cells = []
    for day_idx in range(7):
        week_range = range(n_weeks) if day_idx % 2 == 0 else range(n_weeks - 1, -1, -1)
        for order, week_idx in enumerate(week_range):
            days = weeks[week_idx]["contributionDays"]
            count = days[day_idx]["contributionCount"] if day_idx < len(days) else 0
            cells.append((week_idx, day_idx, count, order))

    row_len = (n_weeks - 1) * STEP
    step_len = STEP
    total_len = 7 * row_len + 6 * step_len

    def cell_center(week_idx, day_idx):
        cx = PAD + week_idx * STEP + CELL / 2
        cy = PAD + TITLE_H + day_idx * STEP + CELL / 2
        return cx, cy

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

    # angulos fixos (mas variados por celula) pra dispersao das particulas,
    # sem depender de random pra manter o resultado determinístico
    burst_angles_by_mod = [(20, 160, 260), (60, 200, 320), (0, 130, 240)]

    cell_rows = []
    for week_idx, day_idx, count, order in cells:
        cx, cy = cell_center(week_idx, day_idx)
        cumulative = day_idx * (row_len + step_len) + order * STEP
        t = cumulative / total_len
        t = max(0.0, min(0.995, t))
        color = color_for(count, max_count)
        rx0, ry0 = cx - CELL / 2, cy - CELL / 2

        if count == 0:
            cell_rows.append(f'''
    <rect x="{rx0:.1f}" y="{ry0:.1f}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}">
      <animate attributeName="opacity" dur="{DURATION}s" repeatCount="indefinite"
        keyTimes="0;{t:.4f};{min(t + 0.006, 1):.4f};1" values="1;1;0;0" />
    </rect>''')
            continue

        t_flash = min(t + 0.012, 1)
        t_gone = min(t + 0.05, 1)
        cell_rows.append(f'''
    <rect x="{rx0:.1f}" y="{ry0:.1f}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}">
      <animate attributeName="fill" dur="{DURATION}s" repeatCount="indefinite"
        keyTimes="0;{t:.4f};{t_flash:.4f};1" values="{color};{color};#f8fafc;{color}" />
      <animate attributeName="opacity" dur="{DURATION}s" repeatCount="indefinite"
        keyTimes="0;{t:.4f};{t_flash:.4f};{t_gone:.4f};1" values="1;1;1;0;0" />
    </rect>''')

        angles = burst_angles_by_mod[(week_idx + day_idx) % len(burst_angles_by_mod)]
        t_burst_end = min(t + BURST, 1)
        for angle in angles:
            rad = math.radians(angle)
            dx, dy = 9 * math.cos(rad), 9 * math.sin(rad)
            cell_rows.append(f'''
    <circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.4" fill="#fde68a" opacity="0">
      <animate attributeName="opacity" dur="{DURATION}s" repeatCount="indefinite"
        keyTimes="0;{t:.4f};{t_flash:.4f};{t_burst_end:.4f};1" values="0;0;1;0;0" />
      <animateTransform attributeName="transform" type="translate" dur="{DURATION}s" repeatCount="indefinite"
        keyTimes="0;{t:.4f};{t_burst_end:.4f};1" values="0,0;0,0;{dx:.1f},{dy:.1f};{dx:.1f},{dy:.1f}"/>
    </circle>''')

    # nave: corpo prateado + chama do motor atras, apontando pra +x (o
    # rotate="auto" do animateMotion cuida da orientacao no percurso)
    ship_body = "M9,0 L-6,-4.5 L-2,0 L-6,4.5 Z"
    flame_open = "M-6,-2 L-13,0 L-6,2 Z"
    flame_closed = "M-6,-0.7 L-9,0 L-6,0.7 Z"

    total = calendar["totalContributions"]
    title = f"{total} contribuições no último ano · nave atira nos commits, semana a semana"

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Nave espacial atirando nos meus commits">
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
    <path d="{flame_open}" fill="#f97316">
      <animate attributeName="d" dur="0.15s" repeatCount="indefinite"
        keyTimes="0;0.5;1" values="{flame_open};{flame_closed};{flame_open}"/>
    </path>
    <path d="{ship_body}" fill="#e2e8f0" stroke="#94a3b8" stroke-width="0.6"/>
  </g>
</svg>'''
    return svg


def main():
    calendar = fetch_contribution_calendar()
    svg = build_svg(calendar)
    out_path = os.path.join(DOCS_DIR, "spaceship.svg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Nave gerada em docs/spaceship.svg ({calendar['totalContributions']} contribuições).")


if __name__ == "__main__":
    main()
