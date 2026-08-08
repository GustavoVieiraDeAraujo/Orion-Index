#!/usr/bin/env python3
# Automacao pessoal do perfil, nao do Orion Index em si -- mora aqui so pra
# nao espalhar workflow em mais um repositorio. Varre os repos publicos do
# Gustavo, gera os cartoes de docs/profile_*.svg e depois clona o repo de
# perfil (via secret PROFILE_PAT, ja que o token padrao do Actions nao
# enxerga fora deste repositorio) pra atualizar os blocos STATS/SKILLS do
# README de la.
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
    "STATS_MEU_REPO_CARTAO": ("<!-- STATS_MEU_REPO_CARTAO:START -->", "<!-- STATS_MEU_REPO_CARTAO:END -->"),
    "STATS_MUNDO_CARTAO": ("<!-- STATS_MUNDO_CARTAO:START -->", "<!-- STATS_MUNDO_CARTAO:END -->"),
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
# shields.io, cor do texto/logo, site oficial). Usado pra desenhar um badge
# com icone, nome E link clicavel pro site oficial daquela stack -- tudo
# automatico: qualquer linguagem/topico novo que apareca nos repos e ja
# esteja mapeado aqui embaixo entra sozinho na proxima execucao, sem
# precisar mexer em mais nada.
BADGE_INFO = {
    "py": ("Python", "3776AB", "python", "white", "https://www.python.org/"),
    "js": ("JavaScript", "F7DF1E", "javascript", "black", "https://developer.mozilla.org/docs/Web/JavaScript"),
    "ts": ("TypeScript", "3178C6", "typescript", "white", "https://www.typescriptlang.org/"),
    "ruby": ("Ruby", "CC342D", "ruby", "white", "https://www.ruby-lang.org/"),
    "go": ("Go", "00ADD8", "go", "white", "https://go.dev/"),
    "java": ("Java", "007396", "openjdk", "white", "https://openjdk.org/"),
    "cs": ("C%23", "239120", "csharp", "white", "https://learn.microsoft.com/dotnet/csharp/"),
    "c": ("C", "A8B9CC", "c", "black", "https://en.cppreference.com/w/c"),
    "cpp": ("C++", "00599C", "cplusplus", "white", "https://isocpp.org/"),
    "php": ("PHP", "777BB4", "php", "white", "https://www.php.net/"),
    "rails": ("Ruby%20on%20Rails", "CC0000", "rubyonrails", "white", "https://rubyonrails.org/"),
    "react": ("React", "61DAFB", "react", "black", "https://react.dev/"),
    "vue": ("Vue.js", "4FC08D", "vuedotjs", "white", "https://vuejs.org/"),
    "angular": ("Angular", "DD0031", "angular", "white", "https://angular.dev/"),
    "html": ("HTML5", "E34F26", "html5", "white", "https://developer.mozilla.org/docs/Web/HTML"),
    "css": ("CSS3", "1572B6", "css3", "white", "https://developer.mozilla.org/docs/Web/CSS"),
    "sass": ("Sass", "CC6699", "sass", "white", "https://sass-lang.com/"),
    "tailwind": ("Tailwind%20CSS", "06B6D4", "tailwindcss", "white", "https://tailwindcss.com/"),
    "bootstrap": ("Bootstrap", "7952B3", "bootstrap", "white", "https://getbootstrap.com/"),
    "nodejs": ("Node.js", "339933", "nodedotjs", "white", "https://nodejs.org/"),
    "express": ("Express", "000000", "express", "white", "https://expressjs.com/"),
    "django": ("Django", "092E20", "django", "white", "https://www.djangoproject.com/"),
    "flask": ("Flask", "000000", "flask", "white", "https://flask.palletsprojects.com/"),
    "rust": ("Rust", "000000", "rust", "white", "https://www.rust-lang.org/"),
    "postgres": ("PostgreSQL", "4169E1", "postgresql", "white", "https://www.postgresql.org/"),
    "mysql": ("MySQL", "4479A1", "mysql", "white", "https://www.mysql.com/"),
    "sqlite": ("SQLite", "003B57", "sqlite", "white", "https://www.sqlite.org/"),
    "mongodb": ("MongoDB", "47A248", "mongodb", "white", "https://www.mongodb.com/"),
    "redis": ("Redis", "DC382D", "redis", "white", "https://redis.io/"),
    "docker": ("Docker", "2496ED", "docker", "white", "https://www.docker.com/"),
    "git": ("Git", "F05032", "git", "white", "https://git-scm.com/"),
    "dotnet": (".NET", "512BD4", "dotnet", "white", "https://dotnet.microsoft.com/"),
    "vite": ("Vite", "646CFF", "vite", "white", "https://vitejs.dev/"),
    "graphql": ("GraphQL", "E10098", "graphql", "white", "https://graphql.org/"),
    "styledcomponents": ("styled--components", "DB7093", "styledcomponents", "white", "https://styled-components.com/"),
    "sequelize": ("Sequelize", "52B0E7", "sequelize", "white", "https://sequelize.org/"),
}


def list_profile_repos():
    """Endpoint publico users/{login}/repos: funciona com qualquer token,
    ja retorna so o que e publico."""
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
    """Data do ultimo commit que mexeu no card combinado do Orion Index.
    Via API, nao `git log` local: o checkout deste workflow e raso
    (fetch-depth 1), entao um `git log -- path` local devolve a data do
    unico commit baixado mesmo quando ele nao tocou o arquivo."""
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


def short_label(text, max_chars=15):
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def render_bar_card(data, title, svg_path, unit="pct", color_map=None,
                     default_color="#60a5fa", top_n=5, order="value", grad_id="cardBg",
                     layout="side", label_w=84, label_chars=13):
    """Cartao de barras top N. `layout="side"`: rotulo a esquerda, barra a
    direita (rotulo curto). `layout="stacked"`: rotulo em cima, barra
    full-width embaixo (rotulo longo, tipo nome de repositorio)."""
    color_map = color_map or {}
    items = list(data.items())
    if order == "value":
        items = sorted(items, key=lambda kv: kv[1], reverse=True)
    items = items[:top_n]
    grand_total = sum(data.values()) or 1
    bar_scale = max((v for _, v in items), default=1)

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


def build_combined_row(panel_paths, out_path, cols=2):
    """Junta os cartoes numa grade (2 colunas por padrao). Concatena texto
    em vez de xml.etree pra nao esbarrar em conflito de id/namespace."""
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
    total_w = cols * col_w + (cols - 1) * CARD_GAP
    total_h = n_rows * row_h + (n_rows - 1) * CARD_GAP

    groups = []
    for i, (body, w, h) in enumerate(parsed):
        col, row = i % cols, i // cols
        x, y = col * (col_w + CARD_GAP), row * (row_h + CARD_GAP)
        groups.append(f'<g transform="translate({x},{y})">{body}</g>')

    combined = (
        f'<svg width="{total_w}" height="{total_h}" viewBox="0 0 {total_w} {total_h}" '
        f'xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(groups) + "\n</svg>\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(combined)


def build_mine_img_block():
    """So a imagem + data: o texto de nota ao redor fica fixo no README,
    fora de qualquer marcador, pra edicao manual nunca ser sobrescrita."""
    my_updated = datetime.date.today().strftime("%d/%m/%Y")
    return (
        '<p align="center">\n'
        '<img src="https://raw.githubusercontent.com/GustavoVieiraDeAraujo/Orion-Index/main/docs/profile_row1.svg" alt="repositorios mais extensos, linguagens por linhas de codigo, repositorios por ano, repositorios por numero de commits" width="100%" />\n'
        '</p>\n\n'
        f'<p align="center"><sub>Última atualização: {my_updated}</sub></p>'
    )


def build_world_img_block():
    """Mesma ideia de build_mine_img_block, pro card do Orion Index."""
    orion_updated = orion_index_last_update() or "veja no repositório do Orion Index"
    return (
        '<p align="center">\n'
        f'<img src="{ORION_INDEX_SVG}" alt="Orion Index: linguagens mais usadas no mundo segundo o GitHub (repositorios novos, totais, por finalidade e crescimento relativo)" width="100%" />\n'
        '</p>\n\n'
        f'<p align="center"><sub>Última atualização: {orion_updated}</sub></p>'
    )


def build_skills_block(topics_count, total_lines):
    """Ordena por linguagens medidas em LOC primeiro (dado mais confiavel),
    depois ferramentas/frameworks que so os topicos revelam (React, Rails,
    Postgres etc)."""
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
        label, color, logo, logo_color, url = info
        badge_url = f"https://img.shields.io/badge/{label}-{color}?style=for-the-badge&logo={logo}&logoColor={logo_color}"
        alt = label.replace("%20", " ").replace("--", "-").replace("%23", "#")
        badges.append(f'<a href="{url}" target="_blank"><img src="{badge_url}" alt="{alt}" height="30" /></a>')
    return " ".join(badges)


def push_profile_readme(blocks, pat):
    """Clona o repo de perfil com o PAT embutido na URL, substitui os blocos
    marcados no README.md e da commit+push."""
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
    year_count = {}

    for repo in repos:
        print(f"- {repo['name']}")
        for topic in repo.get("topics") or []:
            if topic in TOPIC_BLOCKLIST:
                continue
            topics_count[topic] = topics_count.get(topic, 0) + 1

        year = repo["created_at"][:4]
        year_count[year] = year_count.get(year, 0) + 1

        counts = count_lines(repo["full_name"])
        repo_total = sum(counts.values())
        if repo_total:
            repo_total_lines[repo["name"]] = repo_total
        for lang, n in counts.items():
            total_lines[lang] = total_lines.get(lang, 0) + n

        n_commits = count_commits(repo["full_name"])
        if n_commits:
            repo_commits[repo["name"]] = n_commits

    grand_total = sum(total_lines.values())
    # cronologico (nao por contagem): conta o crescimento do portfolio ao
    # longo do tempo, nao "ano com mais repos primeiro"
    year_count = dict(sorted(year_count.items()))

    # ordem bate com a ordem dos bullets no NOTE do README (texto mais
    # curto primeiro, mais longo por ultimo) -- linha 1: Mais Extensos +
    # Linguagens, linha 2: Por Ano + Por Commits
    row1_paths = []
    p = os.path.join(DOCS_DIR, "profile_biggest_repos.svg")
    render_bar_card(repo_total_lines, "Repositórios Mais Extensos", p,
                     unit="loc", default_color="#38bdf8", grad_id="gradBiggest",
                     layout="stacked", label_chars=40)
    row1_paths.append(p)

    p = os.path.join(DOCS_DIR, "profile_lang_loc.svg")
    render_bar_card(total_lines, "Linguagens por Linhas", p,
                     unit="pct", color_map=LANG_COLORS, grad_id="gradLangLoc",
                     layout="stacked", label_chars=40)
    row1_paths.append(p)

    p = os.path.join(DOCS_DIR, "profile_by_year.svg")
    render_bar_card(year_count, "Repositórios por Ano", p,
                     unit="count", default_color="#a78bfa", grad_id="gradByYear",
                     layout="stacked", label_chars=40, order="key", top_n=10)
    row1_paths.append(p)

    p = os.path.join(DOCS_DIR, "profile_commits.svg")
    render_bar_card(repo_commits, "Repositórios por Commits", p,
                     unit="count", default_color="#f59e0b", grad_id="gradCommits",
                     layout="stacked", label_chars=40)
    row1_paths.append(p)

    build_combined_row(row1_paths, os.path.join(DOCS_DIR, "profile_row1.svg"))

    blocks = {
        "STATS_MEU_REPO_CARTAO": build_mine_img_block(),
        "STATS_MUNDO_CARTAO": build_world_img_block(),
        "SKILLS": build_skills_block(topics_count, total_lines),
    }

    push_profile_readme(blocks, pat)
    print("Cartoes gerados em docs/profile_*.svg.")


if __name__ == "__main__":
    main()
