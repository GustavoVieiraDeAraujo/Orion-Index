#!/usr/bin/env python3
"""
Gera as estatisticas do PERFIL de GustavoVieiraDeAraujo (nao e o Orion Index
em si -- e um script separado que so mora aqui pra concentrar toda a
automacao de dashboard num unico lugar, em vez de espalhar em mais um
repositorio). Faz duas coisas:

1. Varre os repositorios publicos do Gustavo (linhas de codigo, repositorios
   mais extensos, commits, topicos) e gera cartoes SVG em docs/profile_*.svg
   aqui neste repositorio.
2. Clona https://github.com/GustavoVieiraDeAraujo/GustavoVieiraDeAraujo,
   atualiza os blocos STATS/SKILLS do README.md de la (marcadores
   <!-- X:START/END -->) e da push -- precisa de um token com permissao de
   escrita naquele outro repositorio (secret PROFILE_PAT), porque o
   GITHUB_TOKEN padrao do Actions so enxerga o repositorio onde ele roda.
   (A secao "Projetos de Exposicao" do README do perfil e curada a mao, nao
   e mais gerada automaticamente -- por isso nao tem mais bloco RECENT.)

O card "Estatisticas do GitHub" (linguagens mais usadas no MUNDO) que entra
no README do perfil e o proprio docs/orion-index.svg gerado por generate.py
-- aqui so lemos a data do ultimo commit dele pra mostrar quando foi
atualizado de verdade.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PROFILE_OWNER = "GustavoVieiraDeAraujo"
PROFILE_REPO_NAME = "GustavoVieiraDeAraujo"
PROFILE_REPO_FULL = f"{PROFILE_OWNER}/{PROFILE_REPO_NAME}"

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")

ORION_INDEX_SVG = "https://raw.githubusercontent.com/GustavoVieiraDeAraujo/Orion-Index/main/docs/orion-index.svg"
ORION_INDEX_REPO = "https://github.com/GustavoVieiraDeAraujo/Orion-Index"

MARKERS = {
    "STATS": ("<!-- STATS:START -->", "<!-- STATS:END -->"),
    "SKILLS": ("<!-- SKILLS:START -->", "<!-- SKILLS:END -->"),
}

# Mesma medida nativa dos cartoes do proprio Orion Index (ver generate.py) --
# de proposito, pra toda fileira (a do perfil e a do mundo) mostrar cada
# cartao do mesmo tamanho quando exibida a 100% da largura no README.
CARD_NATIVE_W = 380
CARD_GAP = 16

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Ruby": "#701516", "Go": "#00ADD8", "Java": "#b07219", "C": "#555555",
    "C++": "#f34b7d", "C#": "#178600", "PHP": "#4F5D95", "HTML": "#e34c26",
    "CSS": "#563d7c", "SQL": "#e38c00", "Shell": "#89e051",
}

# So linguagens de programacao de verdade entram aqui. HTML e CSS ficam de
# fora de proposito: HTML e marcacao, CSS e estilo, nenhum dos dois e
# linguagem de programacao (nao tem logica, controle de fluxo, etc.).
EXT_LANG = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".rb": "Ruby", ".erb": "Ruby",
    ".go": "Go", ".java": "Java", ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++", ".cs": "C#",
    ".php": "PHP", ".sql": "SQL", ".sh": "Shell", ".bash": "Shell",
}

IGNORE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "vendor", "dist", "build",
    "__pycache__", ".next", "target", "bin", "obj", "coverage",
    ".pytest_cache", ".tox", ".yarn",
}

# prefixo comum nos nomes dos repos de trabalho/curso -- tirar deixa o nome
# mais curto e mais facil de reconhecer no card "Repositorios Mais Extensos"
# (mais longo primeiro, senao "Trabalho-" nunca seria removido)
REPO_NAME_PREFIXES = [
    "Trabalhos-Algoritmos-Progamacao-Computadores",
    "Exercicios-Processo-Trainee-Struct", "Exercicios-",
    "Processo-Seletivo-", "Projeto-Final-Struct-", "Trabalho-",
]

TOPIC_BLOCKLIST = {
    "extracurricular-unb", "extracurricular", "trabalho-unb", "trabalho-senac",
    "projeto-pessoal", "processo-seletivo", "senac", "unb",
}

# topico -> nome de exibicao no card de "Ferramentas Mais Usadas". So preciso
# aqui pros topicos que realmente aparecem nos repos; o resto cai no
# fallback (title-case com hifen virando espaco).
TOPIC_DISPLAY_NAMES = {
    "javascript": "JavaScript", "typescript": "TypeScript", "python": "Python",
    "csharp": "C#", "cpp": "C++", "c": "C", "php": "PHP", "ruby": "Ruby",
    "ruby-on-rails": "Ruby on Rails", "html": "HTML", "css": "CSS",
    "nodejs": "Node.js", "golang": "Go", "postgresql": "PostgreSQL",
    "mysql": "MySQL", "sqlite": "SQLite", "mongodb": "MongoDB",
    "dotnet": ".NET", "sdl2": "SDL2", "styled-components": "styled-components",
}

# topico -> codigo do skillicons.dev (so inclui o que o servico realmente suporta)
TOPIC_TO_SKILLICON = {
    "javascript": "js", "typescript": "ts", "python": "py", "java": "java",
    "csharp": "cs", "cpp": "cpp", "c": "c", "php": "php", "ruby": "ruby",
    "ruby-on-rails": "rails", "react": "react", "vue": "vue", "angular": "angular",
    "html": "html", "css": "css", "sass": "sass", "tailwind": "tailwind",
    "bootstrap": "bootstrap", "nodejs": "nodejs", "express": "express",
    "django": "django", "flask": "flask", "golang": "go", "rust": "rust",
    "postgresql": "postgres", "mysql": "mysql", "sqlite": "sqlite",
    "mongodb": "mongodb", "redis": "redis", "docker": "docker", "git": "git",
    "dotnet": "dotnet", "vite": "vite", "graphql": "graphql", "sdl2": "cpp",
    "styled-components": "styledcomponents", "sequelize": "sequelize",
}

# linguagem (medida por linhas de codigo, nao topico manual) -> codigo do
# skillicons.dev. So as que tem icone direto no servico.
LANG_TO_SKILLICON = {
    "Python": "py", "JavaScript": "js", "TypeScript": "ts", "Ruby": "ruby",
    "Go": "go", "Java": "java", "C": "c", "C++": "cpp", "C#": "cs", "PHP": "php",
}

# codigo do skillicons.dev (mesmo codigo usado nos dois mapas acima) ->
# (nome de exibicao, cor da marca em hex, slug do logo no simple-icons via
# shields.io, cor do texto/logo). Usado pra desenhar badge com icone E nome,
# nao so o icone sozinho.
BADGE_INFO = {
    "py": ("Python", "3776AB", "python", "white"),
    "js": ("JavaScript", "F7DF1E", "javascript", "black"),
    "ts": ("TypeScript", "3178C6", "typescript", "white"),
    "ruby": ("Ruby", "CC342D", "ruby", "white"),
    "go": ("Go", "00ADD8", "go", "white"),
    "java": ("Java", "007396", "openjdk", "white"),
    "cs": ("C%23", "239120", "csharp", "white"),
    "c": ("C", "A8B9CC", "c", "black"),
    "cpp": ("C++", "00599C", "cplusplus", "white"),
    "php": ("PHP", "777BB4", "php", "white"),
    "rails": ("Ruby%20on%20Rails", "CC0000", "rubyonrails", "white"),
    "react": ("React", "61DAFB", "react", "black"),
    "vue": ("Vue.js", "4FC08D", "vuedotjs", "white"),
    "angular": ("Angular", "DD0031", "angular", "white"),
    "html": ("HTML5", "E34F26", "html5", "white"),
    "css": ("CSS3", "1572B6", "css3", "white"),
    "sass": ("Sass", "CC6699", "sass", "white"),
    "tailwind": ("Tailwind%20CSS", "06B6D4", "tailwindcss", "white"),
    "bootstrap": ("Bootstrap", "7952B3", "bootstrap", "white"),
    "nodejs": ("Node.js", "339933", "nodedotjs", "white"),
    "express": ("Express", "000000", "express", "white"),
    "django": ("Django", "092E20", "django", "white"),
    "flask": ("Flask", "000000", "flask", "white"),
    "rust": ("Rust", "000000", "rust", "white"),
    "postgres": ("PostgreSQL", "4169E1", "postgresql", "white"),
    "mysql": ("MySQL", "4479A1", "mysql", "white"),
    "sqlite": ("SQLite", "003B57", "sqlite", "white"),
    "mongodb": ("MongoDB", "47A248", "mongodb", "white"),
    "redis": ("Redis", "DC382D", "redis", "white"),
    "docker": ("Docker", "2496ED", "docker", "white"),
    "git": ("Git", "F05032", "git", "white"),
    "dotnet": (".NET", "512BD4", "dotnet", "white"),
    "vite": ("Vite", "646CFF", "vite", "white"),
    "graphql": ("GraphQL", "E10098", "graphql", "white"),
    "styledcomponents": ("styled--components", "DB7093", "styledcomponents", "white"),
    "sequelize": ("Sequelize", "52B0E7", "sequelize", "white"),
}


def list_profile_repos():
    """Usa o endpoint PUBLICO users/{login}/repos (nao user/repos): funciona
    com qualquer token, mesmo o GITHUB_TOKEN deste repositorio (que nao tem
    nenhuma relacao de "usuario autenticado" com a conta do Gustavo) --
    e so retorna repositorio publico mesmo, o que ja e o filtro que queremos."""
    result = subprocess.run(
        ["gh", "api", f"users/{PROFILE_OWNER}/repos?per_page=100&type=owner", "--paginate", "-q", ".[]"],
        capture_output=True, text=True, check=True,
    )
    repos = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    return [r for r in repos if not r["fork"] and r["name"] != PROFILE_REPO_NAME]


def count_lines(repo_full_name):
    """Clona sem autenticacao: sao sempre repositorios publicos."""
    tmp = tempfile.mkdtemp(prefix="stat-")
    url = f"https://github.com/{repo_full_name}.git"
    counts = {}
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, tmp],
            check=True, capture_output=True, text=True, timeout=120,
        )
        for root, dirs, files in os.walk(tmp):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            for fname in files:
                lang = EXT_LANG.get(os.path.splitext(fname)[1].lower())
                if not lang:
                    continue
                try:
                    with open(os.path.join(root, fname), "rb") as fh:
                        n = sum(1 for line in fh if line.strip())
                except OSError:
                    continue
                counts[lang] = counts.get(lang, 0) + n
    except subprocess.CalledProcessError as e:
        print(f"  [aviso] falha ao clonar {repo_full_name}: {e.stderr.strip()[:200]}", file=sys.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return counts


def count_commits(repo_full_name):
    """Numero total de commits do branch padrao: pede so 1 commit por pagina
    e le o numero da ultima pagina no header Link (rel="last")."""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo_full_name}/commits?per_page=1", "-i"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return 0
    headers, _, body = result.stdout.partition("\r\n\r\n")
    if not body:
        headers, _, body = result.stdout.partition("\n\n")
    m = re.search(r'page=(\d+)>;\s*rel="last"', headers)
    if m:
        return int(m.group(1))
    try:
        arr = json.loads(body)
        return len(arr) if isinstance(arr, list) else 0
    except json.JSONDecodeError:
        return 0


def orion_index_last_update():
    """Data do ultimo commit que mexeu no card combinado do Orion Index, via
    API do GitHub (nao da pra confiar no `git log` local aqui: o checkout
    deste workflow e raso -- fetch-depth 1 -- e um repositorio raso so tem
    UM commit de historico, entao "git log -- path" acaba devolvendo a data
    desse unico commit mesmo quando ele nao tocou o arquivo, em vez de
    devolver vazio. A API sempre busca o historico de verdade, direto do
    servidor, sem depender de quanta historia foi baixada localmente)."""
    result = subprocess.run(
        ["gh", "api", "repos/GustavoVieiraDeAraujo/Orion-Index/commits?path=docs/orion-index.svg&per_page=1",
         "-q", ".[0].commit.committer.date"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        dt = datetime.datetime.fromisoformat(result.stdout.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.strftime("%d/%m/%Y")


def shorten_repo_name(name):
    for prefix in REPO_NAME_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):].lstrip("-") or name
    return name


def short_label(text, max_chars=15):
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def render_bar_card(data, title, svg_path, unit="pct", color_map=None,
                     default_color="#60a5fa", top_n=5, order="value", grad_id="cardBg",
                     layout="side", label_w=84, label_chars=13):
    """Cartao de barras padrao: 380px nativo, sempre top N linhas. Sem
    subtitulo de proposito: o titulo tem que ser mnemonico sozinho, o
    detalhe de cada tabela fica explicado no NOTE do README, nao repetido
    dentro do card.

    `layout="side"` (padrao): rotulo a esquerda, barra a direita -- bom pra
    rotulo curto. `layout="stacked"`: rotulo numa linha, barra full-width
    embaixo -- bom pra rotulo longo (nome de repositorio)."""
    color_map = color_map or {}
    items = list(data.items())
    if order == "value":
        items = sorted(items, key=lambda kv: kv[1], reverse=True)
    items = items[:top_n]
    grand_total = sum(data.values()) or 1
    bar_scale = items[0][1] if items else 1

    card_pad = 20
    title_h = 30
    width = CARD_NATIVE_W
    row_h = 50 if layout == "stacked" else 32
    bar_x = card_pad + label_w + 10
    bar_max_w = width - bar_x - card_pad - 56
    stacked_bar_w = width - card_pad * 2 - 54
    height = card_pad * 2 + title_h + row_h * len(items)

    rows = []
    for i, (key, n) in enumerate(items):
        color = color_map.get(key, default_color)
        if unit == "pct":
            val_label = f"{100 * n / grand_total:.1f}%"
        elif unit == "loc":
            val_label = f"{n:,}".replace(",", ".")
        else:
            val_label = f"{n}"
        label = short_label(str(key), label_chars)

        if layout == "stacked":
            row_top = card_pad + title_h + i * row_h
            bar_w = max(3, round(stacked_bar_w * n / bar_scale))
            rows.append(f'''
    <text x="{card_pad}" y="{row_top + 15}" class="lbl">{label}</text>
    <rect x="{card_pad}" y="{row_top + 23}" width="{stacked_bar_w}" height="11" rx="5.5" class="track"/>
    <rect x="{card_pad}" y="{row_top + 23}" width="{bar_w}" height="11" rx="5.5" fill="{color}" class="bar"/>
    <text x="{card_pad + stacked_bar_w + 8}" y="{row_top + 32}" class="val">{val_label}</text>''')
        else:
            bar_w = max(3, round(bar_max_w * n / bar_scale))
            cy = card_pad + title_h + i * row_h + row_h / 2
            rows.append(f'''
    <text x="{card_pad + label_w}" y="{cy + 4}" text-anchor="end" class="lbl">{label}</text>
    <rect x="{bar_x}" y="{cy - 6.5}" width="{bar_max_w}" height="13" rx="6.5" class="track"/>
    <rect x="{bar_x}" y="{cy - 6.5}" width="{bar_w}" height="13" rx="6.5" fill="{color}" class="bar"/>
    <text x="{bar_x + bar_max_w + 10}" y="{cy + 4}" class="val">{val_label}</text>''')

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}">
  <defs>
    <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#D1D5DB"/>
      <stop offset="100%" stop-color="#374151"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 13.5px; }}
    .card {{ fill: url(#{grad_id}); stroke: #4b5563; stroke-width: 1; }}
    .title {{ fill: #1f2937; font-weight: 700; font-size: 15.5px; }}
    .lbl {{ fill: #1f2937; font-weight: 600; }}
    .val {{ fill: #f9fafb; }}
    .track {{ fill: rgba(0,0,0,0.15); }}
    .bar {{ stroke: rgba(255,255,255,0.55); stroke-width: 0.75; }}
  </style>
  <rect x="0" y="0" width="{width}" height="{height}" rx="14" class="card"/>
  <text x="{card_pad}" y="{card_pad + 17}" class="title">{title}</text>
  {"".join(rows)}
</svg>'''

    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)


def build_combined_row(panel_paths, out_path):
    """Junta N SVGs de cartao lado a lado num so arquivo (concatenacao de
    texto, mesma tecnica do generate.py -- evita conflito de namespace/id
    do xml.etree ao mesclar varios documentos SVG independentes)."""
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
        total_w += w + CARD_GAP
        max_h = max(max_h, h)
    total_w -= CARD_GAP

    groups = []
    x_offset = 0.0
    for body, w in inner_bodies:
        groups.append(f'<g transform="translate({x_offset},0)">{body}</g>')
        x_offset += w + CARD_GAP

    combined = (
        f'<svg width="{total_w}" height="{max_h}" viewBox="0 0 {total_w} {max_h}" '
        f'xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(groups) + "\n</svg>\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(combined)


def build_stats_block(grand_total_lines, n_repos):
    linhas_fmt = f"{grand_total_lines:,}".replace(",", ".")
    my_updated = datetime.date.today().strftime("%d/%m/%Y")
    orion_updated = orion_index_last_update() or "veja no repositório do Orion Index"
    return (
        '### 📁 Estatísticas do Meu Repositório\n\n'
        '> [!NOTE]\n'
        f'> Contagem própria — {linhas_fmt} linhas de código analisadas em {n_repos} repositórios públicos meus, '
        f'gerada em [Orion-Index/scripts/generate_profile_stats.py]({ORION_INDEX_REPO}/blob/main/scripts/generate_profile_stats.py), '
        'que clona cada repositório e conta linhas não vazias por extensão de arquivo. HTML e CSS ficam de fora: '
        'são marcação e estilo, não linguagem de programação.\n'
        '> - **Repositórios Mais Extensos** — meus repositórios com mais linhas de código.\n'
        '> - **Linguagens por Linhas** — % de linhas de código por linguagem, somando todos os meus repositórios.\n'
        '> - **Repositórios por Commits** — meus repositórios com mais commits, ou seja, onde mais voltei pra '
        'trabalhar (diferente de "mais extenso": um repositório pode ter poucas linhas e muitos commits, ou o '
        'contrário).\n\n'
        '<p align="center">\n'
        f'<img src="https://raw.githubusercontent.com/GustavoVieiraDeAraujo/Orion-Index/main/docs/profile_row1.svg" alt="repositorios mais extensos, linguagens por linhas de codigo, repositorios por numero de commits" width="100%" />\n'
        '</p>\n\n'
        f'<p align="center"><sub>Última atualização: {my_updated}</sub></p>\n\n'
        '---\n\n'
        '### 🌍 Estatísticas do GitHub\n\n'
        '> [!NOTE]\n'
        f'> Não é sobre mim, é sobre todo mundo — vem do próprio [Orion Index]({ORION_INDEX_REPO}), que busca ao '
        'vivo direto da API oficial do GitHub, sem depender de terceiro nenhum.\n'
        '> - **Repositórios Novos** — quantos foram criados nos últimos 30 dias, por linguagem.\n'
        '> - **Repositórios Totais** — quantos repositórios públicos existem por linguagem no GitHub inteiro, '
        'acumulado histórico.\n'
        '> - **Crescimento Relativo** — novos ÷ totais: qual linguagem está crescendo mais rápido em relação ao '
        'próprio tamanho, não só em número absoluto.\n'
        '>\n'
        f'> Detalhes de cada fonte no [README do Orion Index]({ORION_INDEX_REPO}#readme).\n\n'
        '<p align="center">\n'
        f'<img src="{ORION_INDEX_SVG}" alt="Orion Index: linguagens mais usadas no mundo segundo o GitHub (repositorios novos, totais e crescimento relativo)" width="100%" />\n'
        '</p>\n\n'
        f'<p align="center"><sub>Última atualização: {orion_updated}</sub></p>'
    )


def build_skills_block(topics_count, total_lines):
    """Gera os icones a partir das estatisticas de verdade, nao de uma lista
    escolhida a dedo: primeiro as linguagens medidas por linhas de codigo
    (o dado mais confiavel que temos, ordenado por volume), depois as
    ferramentas/frameworks que so dao pra saber pelos topicos dos repositorios
    (React, Rails, Postgres etc, que uma linguagem sozinha nao revela)."""
    codes = []

    lang_ranked = sorted(total_lines.items(), key=lambda kv: kv[1], reverse=True)
    for lang, _ in lang_ranked:
        code = LANG_TO_SKILLICON.get(lang)
        if code and code not in codes:
            codes.append(code)

    topic_ranked = sorted(topics_count.items(), key=lambda kv: (-kv[1], kv[0]))
    for topic, _ in topic_ranked:
        code = TOPIC_TO_SKILLICON.get(topic)
        if code and code not in codes:
            codes.append(code)

    if not codes:
        return "_nenhuma tecnologia catalogada ainda_"
    codes = codes[:14]

    badges = []
    for code in codes:
        info = BADGE_INFO.get(code)
        if not info:
            continue
        label, color, logo, logo_color = info
        badge_url = f"https://img.shields.io/badge/{label}-{color}?style=for-the-badge&logo={logo}&logoColor={logo_color}"
        alt = label.replace("%20", " ").replace("--", "-").replace("%23", "#")
        badges.append(f'<img src="{badge_url}" alt="{alt}" height="30" />')
    return " ".join(badges)


def push_profile_readme(blocks, pat):
    """Clona o repositorio de perfil com o PAT embutido na URL, substitui os
    3 blocos marcados no README.md, e da commit+push -- unico jeito de um
    workflow deste repositorio (Orion Index) escrever em OUTRO repositorio,
    ja que o GITHUB_TOKEN padrao do Actions so tem permissao aqui dentro."""
    tmp = tempfile.mkdtemp(prefix="profile-")
    url = f"https://x-access-token:{pat}@github.com/{PROFILE_REPO_FULL}.git"
    try:
        subprocess.run(["git", "clone", "--depth", "1", "--quiet", url, tmp], check=True, capture_output=True, text=True)

        readme_path = os.path.join(tmp, "README.md")
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        for key, (start, end) in MARKERS.items():
            pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
            if not pattern.search(content):
                print(f"Marcadores {key} nao encontrados no README do perfil", file=sys.stderr)
                sys.exit(1)
            content = pattern.sub(f"{start}\n{blocks[key]}\n{end}", content)

        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(content)

        subprocess.run(["git", "-C", tmp, "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "-C", tmp, "config", "user.email",
                         "41898282+github-actions[bot]@users.noreply.github.com"], check=True)

        diff = subprocess.run(["git", "-C", tmp, "diff", "--quiet"], capture_output=True)
        if diff.returncode == 0:
            print("Perfil: sem mudancas no README.")
            return

        subprocess.run(["git", "-C", tmp, "add", "README.md"], check=True)
        subprocess.run(["git", "-C", tmp, "commit", "-m", "Atualiza estatisticas do perfil"], check=True)
        subprocess.run(["git", "-C", tmp, "push"], check=True, capture_output=True, text=True)
        print("Perfil: README.md atualizado e enviado.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    pat = os.environ.get("PROFILE_PAT")
    if not pat:
        print("PROFILE_PAT nao configurado (precisa de permissao de escrita no repositorio de perfil)", file=sys.stderr)
        sys.exit(1)

    repos = list_profile_repos()
    print(f"Repositorios do perfil encontrados: {len(repos)}")

    total_lines = {}
    repo_total_lines = {}
    repo_commits = {}
    topics_count = {}

    for repo in repos:
        print(f"- {repo['name']}")
        for topic in repo.get("topics") or []:
            if topic in TOPIC_BLOCKLIST:
                continue
            topics_count[topic] = topics_count.get(topic, 0) + 1

        counts = count_lines(repo["full_name"])
        repo_total = sum(counts.values())
        if repo_total:
            repo_total_lines[shorten_repo_name(repo["name"])] = repo_total
        for lang, n in counts.items():
            total_lines[lang] = total_lines.get(lang, 0) + n

        n_commits = count_commits(repo["full_name"])
        if n_commits:
            repo_commits[shorten_repo_name(repo["name"])] = n_commits

    grand_total = sum(total_lines.values())

    # ordem da esquerda pra direita bate com a ordem dos bullets no NOTE do
    # README (texto mais curto primeiro, mais longo por ultimo)
    row1_paths = []
    p = os.path.join(DOCS_DIR, "profile_biggest_repos.svg")
    render_bar_card(repo_total_lines, "Repositórios Mais Extensos", p,
                     unit="loc", default_color="#38bdf8", grad_id="gradBiggest",
                     layout="stacked", label_chars=28)
    row1_paths.append(p)

    p = os.path.join(DOCS_DIR, "profile_lang_loc.svg")
    render_bar_card(total_lines, "Linguagens por Linhas", p,
                     unit="pct", color_map=LANG_COLORS, grad_id="gradLangLoc",
                     layout="stacked", label_chars=28)
    row1_paths.append(p)

    p = os.path.join(DOCS_DIR, "profile_commits.svg")
    render_bar_card(repo_commits, "Repositórios por Commits", p,
                     unit="count", default_color="#f59e0b", grad_id="gradCommits",
                     layout="stacked", label_chars=28)
    row1_paths.append(p)

    build_combined_row(row1_paths, os.path.join(DOCS_DIR, "profile_row1.svg"))

    blocks = {
        "STATS": build_stats_block(grand_total, len(repos)),
        "SKILLS": build_skills_block(topics_count, total_lines),
    }

    push_profile_readme(blocks, pat)
    print("Cartoes gerados em docs/profile_*.svg.")


if __name__ == "__main__":
    main()
