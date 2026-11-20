import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

ARQUIVO_DADOS = "vagas.json"

# Palavras-chave para filtrar vagas relevantes
PALAVRAS_ESTATAIS = [
    "petrobras", "transpetro", "epe", "bndes", "eletronuclear",
    "finep", "inmetro", "estágio", "estagio", "edital", "engenharia"
]

PALAVRAS_ENG_RENOVAVEIS = [
    "mecânica", "mecanica", "mechanical", "energia", "energy",
    "solar", "eólica", "eolica", "wind", "renovável", "renovavel",
    "renewable", "cfd", "simulação", "simulacao", "estágio", "estagio", "intern"
]

# Fontes públicas monitoradas automaticamente
FONTES_EDITAIS = [
    {"nome": "Portal CIEE", "url": "https://portal.ciee.org.br/processos-seletivos-especiais/"},
    {"nome": "MUDES (Estágios RJ)", "url": "https://www.mudes.org.br/"},
    {"nome": "EPE (Empresa de Pesquisa Energética)", "url": "https://www.epe.gov.br/pt/a-epe/trabalhe-na-epe"},
    {"nome": "Petrobras Carreiras", "url": "https://petrobras.com.br/quem-somos/carreiras"}
]

# Empresas de Energia para consulta via API pública da Gupy
EMPRESAS_GUPY = [
    "engiebrasil", "enel", "voltalia", "casadosventos",
    "omegaenergia", "edf-renewables", "raizen", "vibraenergia"
]


def carregar_vagas_salvas():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def buscar_editais_estatais():
    resultados = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    hoje = datetime.now().strftime("%d/%m/%Y")

    for fonte in FONTES_EDITAIS:
        try:
            resp = requests.get(fonte["url"], headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                texto = a.get_text(" ", strip=True)
                texto_lower = texto.lower()
                if 12 <= len(texto) <= 180 and any(p in texto_lower for p in PALAVRAS_ESTATAIS):
                    href = a["href"]
                    if href.startswith("/"):
                        base = "/".join(fonte["url"].split("/")[:3])
                        href = base + href
                    if href.startswith("http"):
                        resultados.append({
                            "id": f"est-{hash(href)}",
                            "categoria": "Estatais & Editais",
                            "titulo": texto,
                            "empresa": fonte["nome"],
                            "local": "Brasil / RJ",
                            "link": href,
                            "data": hoje
                        })
        except Exception as e:
            print(f"Aviso ao ler {fonte['nome']}: {e}")
    return resultados


def buscar_renovaveis_gupy():
    resultados = []
    headers = {"User-Agent": "Mozilla/5.0"}
    hoje = datetime.now().strftime("%d/%m/%Y")

    for empresa in EMPRESAS_GUPY:
        url_api = f"https://portal.api.gupy.io/api/job?name=estagio&subdomain={empresa}&limit=20"
        try:
            resp = requests.get(url_api, headers=headers, timeout=12)
            if resp.status_code == 200:
                dados = resp.json().get("data", [])
                for vaga in dados:
                    titulo = vaga.get("name", "")
                    if "estágio" in titulo.lower() or "estagio" in titulo.lower():
                        resultados.append({
                            "id": f"gupy-{vaga.get('id')}",
                            "categoria": "Energias Renováveis",
                            "titulo": titulo,
                            "empresa": empresa.upper(),
                            "local": f"{vaga.get('city', 'Remoto')} - {vaga.get('state', '')}".strip(" -"),
                            "link": vaga.get("jobUrl", f"https://{empresa}.gupy.io/"),
                            "data": hoje
                        })
        except Exception as e:
            print(f"Aviso Gupy ({empresa}): {e}")
    return resultados


def buscar_internacional_remoto():
    resultados = []
    hoje = datetime.now().strftime("%d/%m/%Y")
    try:
        resp = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
        if resp.status_code == 200:
            for vaga in resp.json().get("data", []):
                titulo = vaga.get("title", "")
                titulo_lower = titulo.lower()
                if vaga.get("remote") and ("intern" in titulo_lower or "working student" in titulo_lower):
                    if any(k in titulo_lower for k in ["engineer", "energy", "solar", "wind", "mechanical", "cad", "simulation", "data"]):
                        resultados.append({
                            "id": f"intl-{vaga.get('slug')}",
                            "categoria": "Internacional Remoto",
                            "titulo": titulo,
                            "empresa": vaga.get("company_name", "Empresa Internacional"),
                            "local": "Remoto (Europa / Global)",
                            "link": vaga.get("url", "#"),
                            "data": hoje
                        })
    except Exception as e:
        print(f"Aviso Internacional: {e}")
    return resultados


def gerar_html(vagas):
    atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M (UTC)")
    cards_html = ""

    for v in vagas:
        cat = v["categoria"]
        badge_class = "badge-estatal" if "Estatais" in cat else ("badge-renovavel" if "Renováveis" in cat else "badge-intl")
        cards_html += f"""
        <div class="card" data-cat="{cat}">
            <div class="card-top">
                <span class="badge {badge_class}">{cat}</span>
                <span class="date">Capturada em {v['data']}</span>
            </div>
            <h3>{v['titulo']}</h3>
            <p class="meta"><strong>{v['empresa']}</strong> • {v['local']}</p>
            <a href="{v['link']}" target="_blank" rel="noopener" class="btn">Acessar Vaga / Edital →</a>
        </div>
        """

    if not cards_html:
        cards_html = "<p class='empty'>Nenhuma vaga nova encontrada nesta varredura. Use os atalhos diretos acima ou aguarde a próxima execução.</p>"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Radar de Estágios | Engenharia & Energia</title>
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --muted: #94a3b8; --accent: #38bdf8; }}
        body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        .container {{ max-width: 1050px; margin: 0 auto; }}
        header {{ border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 24px; }}
        h1 {{ margin: 0 0 6px 0; font-size: 1.7rem; color: var(--accent); }}
        .sub {{ color: var(--muted); font-size: 0.9rem; margin: 0; }}
        .atalhos {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 24px; }}
        .atalhos a {{ background: #1e293b; border: 1px solid #334155; color: #e2e8f0; padding: 8px 14px; border-radius: 8px; text-decoration: none; font-size: 0.85rem; }}
        .atalhos a:hover {{ border-color: var(--accent); color: var(--accent); }}
        .filtros {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
        button {{ background: var(--card); color: var(--text); border: 1px solid #475569; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-weight: 600; }}
        button.active, button:hover {{ background: var(--accent); color: #0f172a; border-color: var(--accent); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }}
        .card {{ background: var(--card); border: 1px solid #334155; border-radius: 12px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between; }}
        .card-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 0.78rem; }}
        .badge {{ padding: 4px 10px; border-radius: 12px; font-weight: 700; }}
        .badge-estatal {{ background: #fef08a; color: #854d0e; }}
        .badge-renovavel {{ background: #bbf7d0; color: #166534; }}
        .badge-intl {{ background: #bae6fd; color: #075985; }}
        .date {{ color: var(--muted); }}
        h3 {{ margin: 0 0 8px 0; font-size: 1.05rem; line-height: 1.4; }}
        .meta {{ color: var(--muted); font-size: 0.88rem; margin: 0 0 16px 0; }}
        .btn {{ display: inline-block; text-align: center; background: #0284c7; color: white; text-decoration: none; padding: 10px; border-radius: 8px; font-weight: 600; font-size: 0.9rem; }}
        .btn:hover {{ background: #0369a1; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Radar Pessoal de Estágios — Engenharia & Energia</h1>
            <p class="sub">Última varredura automática: {atualizacao} | Total monitorado: {len(vagas)} oportunidades</p>
        </header>

        <div class="atalhos">
            <a href="https://petrobras.com.br/quem-somos/carreiras" target="_blank">🔎 Petrobras Carreiras</a>
            <a href="https://portal.ciee.org.br/processos-seletivos-especiais/" target="_blank">🔎 Editais CIEE</a>
            <a href="https://www.epe.gov.br/pt/a-epe/trabalhe-na-epe" target="_blank">🔎 EPE Energia</a>
            <a href="https://www.mudes.org.br/" target="_blank">🔎 Portal MUDES</a>
            <a href="https://www.linkedin.com/jobs/search/?keywords=estagio%20engenharia%20energia%20renovavel&location=Brasil" target="_blank">🔎 LinkedIn Renováveis</a>
            <a href="https://www.euraxess.ec.europa.eu/jobs/search" target="_blank">🔎 Europa / Euraxess</a>
        </div>

        <div class="filtros">
            <button class="active" onclick="filtrar('todas', this)">Todas ({len(vagas)})</button>
            <button onclick="filtrar('Estatais & Editais', this)">Estatais & Editais</button>
            <button onclick="filtrar('Energias Renováveis', this)">Energias Renováveis</button>
            <button onclick="filtrar('Internacional Remoto', this)">Internacional Remoto</button>
        </div>

        <div class="grid" id="lista-vagas">
            {cards_html}
        </div>
    </div>

    <script>
        function filtrar(categoria, btn) {{
            document.querySelectorAll('.filtros button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.card').forEach(card => {{
                if (categoria === 'todas' || card.dataset.cat === categoria) {{
                    card.style.display = 'flex';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


def main():
    antigas = carregar_vagas_salvas()
    novas = buscar_editais_estatais() + buscar_renovaveis_gupy() + buscar_internacional_remoto()

    # Evita duplicadas mantendo as mais recentes no topo
    vistos = set()
    combinadas = []
    for v in novas + antigas:
        if v["link"] not in vistos:
            vistos.add(v["link"])
            combinadas.append(v)

    combinadas = combinadas[:120]  # Mantém as 120 oportunidades mais recentes
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(combinadas, f, ensure_ascii=False, indent=2)

    gerar_html(combinadas)
    print(f"Concluído! {len(combinadas)} vagas salvas no site.")


if __name__ == "__main__":
    main()
