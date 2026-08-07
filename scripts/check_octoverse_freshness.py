#!/usr/bin/env python3
"""
Nao automatiza a EXTRACAO dos numeros do Octoverse (isso continua manual de
proposito, ver README: o conteudo e texto corrido, nao dado estruturado, e
raspar prosa com regex ja deu resultado ambiguo nos testes que fizemos).

Automatiza a DETECCAO: confere o feed RSS oficial da categoria Octoverse do
blog do GitHub, e se aparecer um post mais novo que o que esta registrado
em OCTOVERSE_SOURCE (generate.py), abre uma issue nesse repositorio
avisando. Assim ninguem precisa lembrar de checar manualmente.
"""
import re
import sys
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

FEED_URL = "https://github.blog/news-insights/octoverse/feed/"
GENERATE_PY = __file__.replace("check_octoverse_freshness.py", "generate.py")


def current_source():
    with open(GENERATE_PY, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'OCTOVERSE_SOURCE\s*=\s*"([^"]+)"', content)
    if not match:
        raise RuntimeError("Nao achei OCTOVERSE_SOURCE em generate.py")
    return match.group(1)


def latest_feed_item():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "orion-index"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    item = root.find(".//item")
    if item is None:
        raise RuntimeError("Feed do Octoverse veio sem nenhum item")
    return item.find("title").text, item.find("link").text


def main():
    known_url = current_source()
    latest_title, latest_url = latest_feed_item()

    if latest_url == known_url:
        print("Nada novo no feed do Octoverse.")
        return

    print(f"Post novo encontrado: {latest_title} ({latest_url})")
    body = (
        f"O feed do GitHub Blog (categoria Octoverse) tem um post mais novo que o "
        f"registrado em `OCTOVERSE_SOURCE`:\n\n"
        f"- **{latest_title}**\n{latest_url}\n\n"
        f"Registrado atualmente: {known_url}\n\n"
        f"Se tiver numero novo de linguagem mais usada, atualize `OCTOVERSE_2025` "
        f"(nome da constante, data, fonte) em `scripts/generate.py` e feche esta issue."
    )
    subprocess.run(
        ["gh", "issue", "create", "--title", f"Octoverse: possível atualização — {latest_title}",
         "--body", body, "--label", "octoverse-update"],
        check=True,
    )


if __name__ == "__main__":
    main()
