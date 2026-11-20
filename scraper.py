import json
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from bs4 import BeautifulSoup

ARQUIVO_DADOS = "vagas.json"

# Cidades permitidas para estágios presenciais/híbridos (normalizadas sem acento)
CIDADES_PERMITIDAS = [
    "rio de janeiro", "duque de caxias", "xerem",
    "belford roxo", "nova iguacu"
]

# Palavras-chave técnicas para estágios
TERMOS_AREA = [
    "engenharia mecanica", "eng. mecanica", "mecanica", "mechanical",
    "energia solar", "fotovoltaica", "energia eolica", "eolica", "wind",
    "energias renovaveis", "energia renovavel", "eficiencia energetica",
    "termofluidos", "climatizacao", "refrigeracao", "hvac", "ar condicionado",
    "manutencao mecanica", "projetos mecanicos", "metrologia", "cfd", "hidrogenio"
]

# Palavras para descartar menus e redes sociais
IGNORAR = [
    "facebook", "instagram", "youtube", "bluesky", "twitter", "x.com",
    "linkedin.com/company", "socioambiental", "cultural", "investidor",
    "logo", "imprensa", "ouvidoria", "fale conosco", "politica de privacidade",
    "acessibilidade", "mapa do site", "login", "entrar", "esqueci minha senha"
]

# 1. Órgãos Públicos (Federal, Estadual RJ, Prefeituras Rio e Caxias) e Agentes
FONTES_ORGAOS_PUBLICOS = [
    {"nome": "TRF2 (Tribunal Regional Federal 2ª Região)", "url": "https://www.trf2.jus.br/trf2/institucional/estagio", "cidade": "Rio de Janeiro - RJ (Centro)"},
    {"nome": "TJRJ (Tribunal de Justiça RJ)", "url": "https://www.tjrj.jus.br/web/guest/institucional/estagio", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "TRT-1 (Tribunal Regional do Trabalho RJ)", "url": "https://www.trt1.jus.br/web/guest/estagio", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "Governo do Estado RJ (Trabalho e Estágio)", "url": "https://www.rj.gov.br/cidadao/servicos/trabalho-e-estagio/categoria/20", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "CGE-RJ (Controladoria Geral do Estado)", "url": "https://cge.rj.gov.br/programa-de-estagio/", "cidade": "Rio de Janeiro - RJ (Centro)"},
    {"nome": "Prefeitura do Rio (IplanRio / Órgãos Municipais)", "url": "https://iplanrio.prefeitura.rio/", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "Prefeitura de Duque de Caxias", "url": "https://portal.duquedecaxias.rj.gov.br/", "cidade": "Duque de Caxias - RJ"},
    {"nome": "INMETRO (Campus Xerém)", "url": "https://www.gov.br/inmetro/pt-br/acesso-a-informacao/servidores/estagio", "cidade": "Duque de Caxias - RJ (Xerém)"},
    {"nome": "Fiocruz (Manguinhos)", "url": "https://portal.fiocruz.br/estagio", "cidade": "Rio de Janeiro - RJ (Manguinhos)"},
    {"nome": "CEPEL (Pesquisa de Energia Elétrica)", "url": "https://www.cepel.br/trabalhe-conosco/", "cidade": "Rio de Janeiro - RJ (Ilha do Fundão)"},
    {"nome": "EPE (Empresa de Pesquisa Energética)", "url": "https://www.epe.gov.br/pt/a-epe/trabalhe-na-epe", "cidade": "Rio de Janeiro - RJ (Centro)"},
    {"nome": "Petrobras Carreiras", "url": "https://petrobras.com.br/quem-somos/carreiras", "cidade": "Rio de Janeiro / Duque de Caxias"},
    {"nome": "CIEE (Processos Seletivos Públicos)", "url": "https://portal.ciee.org.br/processos-seletivos-especiais/", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "MUDES (Estágios RJ)", "url": "https://www.mudes.org.br/", "cidade": "Rio de Janeiro / Baixada"},
    {"nome": "ISBET (Parceiro Governo RJ)", "url": "https://isbet.org.br/", "cidade": "Rio de Janeiro - RJ"}
]

# 2. Portais Acadêmicos CEFET/RJ (UFCIRJ) e Fomento
FONTES_BOLSAS_CEFET = [
    {"nome": "CEFET/RJ (UFCIRJ) — Editais e Processos Seletivos", "url": "https://www.cefet-rj.br/index.php/editais-e-processos-seletivos", "cidade": "Maracanã / Nova Iguaçu"},
    {"nome": "DIPPG CEFET/RJ — Pesquisa, PIBIC e Eventos", "url": "https://dippg.cefet-rj.br/", "cidade": "CEFET/RJ (UFCIRJ)"},
    {"nome": "CEFET/RJ — Extensão (PBEXT / EXPIN)", "url": "https://www.cefet-rj.br/index.php/extensao", "cidade": "CEFET/RJ (UFCIRJ)"}
]

# 3. Empresas Privadas / Mistas de Energia, Óleo & Gás e Indústria no RJ e Caxias
EMPRESAS_GUPY = [
    "braskem", "vibraenergia", "raizen", "engiebrasil", "enel",
    "edf-renewables", "equinor", "ternium", "whitemartins",
    "eletrobras", "light", "naturgy", "subsea7", "technipfmc", "modec"
]


def normalizar(texto):
    if not texto:
        return ""
    mapa = str.maketrans("áàãâéêíóôõúüçÁÀÃÂÉÊÍÓÔÕÚÜÇ", "aaaaeeiooouucAAAAEEIOOOUUC")
    return texto.translate(mapa).lower()


def cidade_valida(texto_local):
    norm = normalizar(texto_local)
    return any(c in norm for c in CIDADES_PERMITIDAS)


def formatar_cidade(texto_local):
    norm = normalizar(texto_local)
    if "duque de caxias" in norm or "xerem" in norm:
        return "Duque de Caxias - RJ"
    if "nova iguacu" in norm:
        return "Nova Iguaçu - RJ"
    if "belford roxo" in norm:
        return "Belford Roxo - RJ"
    if "rio de janeiro" in norm:
        return "Rio de Janeiro - RJ"
    return texto_local


def extrair_metadados(texto_completo):
    limpo = BeautifulSoup(texto_completo or "", "html.parser").get_text(" ", strip=True)

    match_sal = re.search(
        r"(?:bolsa[\s\-auxílio]*|remuneração|salário|prêmio|valor)?\s*(R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?(?:\s*(?:a|até|\-)\s*R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?)?)",
        limpo,
        re.IGNORECASE
    )
    salario = match_sal.group(1).strip() if match_sal else "Consultar no edital"

    match_per = re.search(
        r"((?:a partir do\s*)?\d{1,2}[º°o]\s*(?:ao\s*\d{1,2}[º°o]\s*)?(?:período|periodo|semestre))",
        limpo,
        re.IGNORECASE
    )
    periodo = match_per.group(1).strip().capitalize() if match_per else "Consultar no edital"

    return salario, periodo


def buscar_nube_mecanica():
    resultados = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    hoje = datetime.now().strftime("%d/%m/%Y")
    url_nube = "https://www.nube.com.br/vagas-de-estagio/engenharia-mecanica"

    try:
        resp = requests.get(url_nube, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/detalhes-vaga/" in href:
                    bloco_texto = a.get_text(" | ", strip=True)
                    norm = normalizar(f"{bloco_texto} {href}")
                    if cidade_valida(norm):
                        link_completo = href if href.startswith("http") else f"https://www.nube.com.br{href}"
                        salario, periodo = extrair_metadados(bloco_texto)
                        cidade_fmt = formatar_cidade(norm)
                        resultados.append({
                            "categoria": "Agentes (Nube / MUDES / CIEE)",
                            "titulo": bloco_texto[:120],
                            "empresa": "Nube — Estágio Eng. Mecânica",
                            "local": cidade_fmt,
                            "periodo": periodo,
                            "salario": salario,
                            "link": link_completo,
                            "data": hoje
                        })
    except Exception as e:
        print(f"Aviso Nube: {e}")

    return resultados


def buscar_orgaos_publicos():
    resultados = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    hoje = datetime.now().strftime("%d/%m/%Y")

    for fonte in FONTES_ORGAOS_PUBLICOS:
        try:
            resp = requests.get(fonte["url"], headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                texto = a.get_text(" ", strip=True)
                norm = normalizar(texto)
                href = a["href"]
                if href.startswith("/"):
                    base = "/".join(fonte["url"].split("/")[:3])
                    href = base + href

                eh_relevante = any(t in norm for t in [
                    "estagio", "edital", "processo seletivo", "selecao",
                    "engenharia", "mecanica", "inscricoes", "vagas", "resultado"
                ])

                if (
                    10 <= len(texto) <= 190
                    and href.startswith("http")
                    and not any(ig in normalizar(f"{texto} {href}") for ig in IGNORAR)
                    and eh_relevante
                ):
                    salario, periodo = extrair_metadados(texto)
                    resultados.append({
                        "categoria": "Órgãos Públicos & Estatais",
                        "titulo": texto,
                        "empresa": fonte["nome"],
                        "local": fonte["cidade"],
                        "periodo": periodo,
                        "salario": salario,
                        "link": href,
                        "data": hoje
                    })
        except Exception as e:
            print(f"Aviso ao acessar {fonte['nome']}: {e}")

    return resultados


def buscar_bolsas_cefet():
    """Varre editais de bolsas, PIBIC, extensão, EXPIN e intercâmbio no CEFET/RJ (UFCIRJ)"""
    resultados = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    hoje = datetime.now().strftime("%d/%m/%Y")

    palavras_bolsa = [
        "bolsa", "pibic", "pibiti", "pbext", "extensao", "iniciacao cientifica",
        "monitoria", "intercambio", "dupla diplomacao", "expin", "jipp", "jic",
        "sepex", "edital", "faperj", "cnpq", "ufci", "ufcirj"
    ]

    for fonte in FONTES_BOLSAS_CEFET:
        try:
            resp = requests.get(fonte["url"], headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                texto = a.get_text(" ", strip=True)
                norm = normalizar(texto)
                href = a["href"]
                if href.startswith("/"):
                    base = "/".join(fonte["url"].split("/")[:3])
                    href = base + href

                if (
                    10 <= len(texto) <= 200
                    and href.startswith("http")
                    and not any(ig in normalizar(f"{texto} {href}") for ig in IGNORAR)
                    and any(p in norm for p in palavras_bolsa)
                ):
                    salario, _ = extrair_metadados(texto)
                    resultados.append({
                        "categoria": "Bolsas & Editais CEFET/UFCIRJ",
                        "titulo": texto,
                        "empresa": fonte["nome"],
                        "local": fonte["cidade"],
                        "periodo": "Ver regras do edital",
                        "salario": salario if "R$" in salario else "Bolsa / Auxílio Institucional",
                        "link": href,
                        "data": hoje
                    })
        except Exception as e:
            print(f"Aviso CEFET ({fonte['nome']}): {e}")

    return resultados


def buscar_desafios_e_radar_web():
    """Monitora editais públicos no RJ e desafios de energia limpa, hackathons, EXPIN, Shell, Red Bull, NASA e Schneider"""
    resultados = []
    hoje = datetime.now().strftime("%d/%m/%Y")

    consultas = [
        {
            "q": '"estágio" "engenharia mecânica" ("TRF2" OR "Governo do Estado" OR "Prefeitura do Rio" OR "Duque de Caxias" OR "Petrobras")',
            "cat": "Órgãos Públicos & Estatais",
            "local": "Rio de Janeiro / Caxias"
        },
        {
            "q": '("CEFET/RJ" OR "CEFET-RJ" OR "UFCI" OR "UFCIRJ" OR "UFCI/RJ") ("edital" OR "bolsa" OR "PIBIC" OR "EXPIN" OR "FAPERJ")',
            "cat": "Bolsas & Editais CEFET/UFCIRJ",
            "local": "CEFET/RJ (UFCIRJ)"
        },
        {
            "q": '("Schneider Go Green" OR "NASA Space Apps" OR "Shell Eco-marathon" OR "Red Bull Basement" OR "EDP University Challenge" OR "EXPIN") ("inscrições" OR "desafio" OR "hackathon" OR "energia")',
            "cat": "Desafios & Hackathons",
            "local": "Online / Nacional / Global"
        },
        {
            "q": '("hackathon" OR "desafio de inovação") ("energia limpa" OR "energia renovável" OR "energia solar" OR "energia eólica" OR "transição energética")',
            "cat": "Desafios & Hackathons",
            "local": "Online / Brasil"
        }
    ]

    for item_q in consultas:
        url_rss = f"https://news.google.com/rss/search?q={urllib.parse.quote(item_q['q'])}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        try:
            resp = requests.get(url_rss, timeout=15)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item")[:8]:
                    titulo = item.findtext("title", "")
                    link = item.findtext("link", "")
                    resultados.append({
                        "categoria": item_q["cat"],
                        "titulo": titulo,
                        "empresa": "Radar de Editais & Competições",
                        "local": item_q["local"],
                        "periodo": "Estudantes de Graduação",
                        "salario": "Bolsa / Premiação",
                        "link": link,
                        "data": hoje
                    })
        except Exception as e:
            print(f"Aviso Radar Web: {e}")

    return resultados


def buscar_gupy_rj():
    resultados = []
    headers = {"User-Agent": "Mozilla/5.0"}
    hoje = datetime.now().strftime("%d/%m/%Y")

    for empresa in EMPRESAS_GUPY:
        url_api = f"https://portal.api.gupy.io/api/job?jobName=estagio&subdomain={empresa}&limit=30"
        try:
            resp = requests.get(url_api, headers=headers, timeout=12)
            if resp.status_code != 200:
                continue

            for vaga in resp.json().get("data", []):
                titulo = vaga.get("name", "")
                descricao = vaga.get("description", "")
                cidade_raw = f"{vaga.get('city', '')} {vaga.get('state', '')}"
                texto_busca = normalizar(f"{titulo} {descricao}")

                eh_estagio = "estagio" in normalizar(titulo)
                eh_area = any(t in texto_busca for t in TERMOS_AREA)

                if eh_estagio and cidade_valida(cidade_raw) and eh_area:
                    salario, periodo = extrair_metadados(descricao)
                    cidade_fmt = formatar_cidade(cidade_raw)
                    eh_renovavel = any(k in texto_busca for k in ["solar", "eolica", "renovavel", "renovaveis", "eficiencia energetica", "hidrogenio"])
                    cat = "Energia Solar & Eólica" if eh_renovavel else "Indústria & Engenharia"

                    resultados.append({
                        "categoria": cat,
                        "titulo": titulo,
                        "empresa": empresa.upper(),
                        "local": cidade_fmt,
                        "periodo": periodo,
                        "salario": salario,
                        "link": vaga.get("jobUrl", f"https://{empresa}.gupy.io/"),
                        "data": hoje
                    })
        except Exception as e:
            print(f"Aviso Gupy ({empresa}): {e}")

    return resultados


def enviar_telegram(novas_vagas):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id or not novas_vagas:
        return

    for v in novas_vagas[:10]:
        titulo_limpo = v["titulo"].replace("*", "").replace("_", "").replace("[", "(").replace("]", ")")
        mensagem = (
            f"🚨 *Nova Oportunidade ({v['categoria']})*\n\n"
            f"📌 *{titulo_limpo}*\n"
            f"🏢 {v['empresa']}\n"
            f"📍 {v['local']}\n"
            f"🎓 Requisito: {v['periodo']}\n"
            f"💰 Valor/Prêmio: {v['salario']}\n\n"
            f"🔗 [Acessar Link Oficial]({v['link']})"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(
                url,
                json={"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"},
                timeout=10
            )
        except Exception as e:
            print(f"Erro ao enviar Telegram: {e}")


def gerar_html(vagas):
    atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M (UTC)")
    cards_html = ""

    for v in vagas:
        cat = v["categoria"]
        if "Órgãos" in cat:
            badge_class = "badge-estatal"
        elif "Solar" in cat:
            badge_class = "badge-energia"
        elif "Agentes" in cat:
            badge_class = "badge-agente"
        elif "Bolsas" in cat:
            badge_class = "badge-bolsa"
        elif "Desafios" in cat:
            badge_class = "badge-desafio"
        else:
            badge_class = "badge-ind"

        cards_html += f"""
        <div class="card" data-cat="{cat}" data-city="{v['local']}">
            <div class="card-top">
                <span class="badge {badge_class}">{cat}</span>
                <span class="date">{v['data']}</span>
            </div>
            <h3>{v['titulo']}</h3>
            <p class="empresa">{v['empresa']}</p>
            <ul class="detalhes">
                <li><strong>📍 Local:</strong> {v['local']}</li>
                <li><strong>🎓 Requisito:</strong> {v['periodo']}</li>
                <li><strong>💰 Bolsa/Prêmio:</strong> {v['salario']}</li>
            </ul>
            <a href="{v['link']}" target="_blank" rel="noopener" class="btn">Acessar Edital / Desafio →</a>
        </div>
        """

    if not cards_html:
        cards_html = "<p style='color:#94a3b8'>Nenhuma oportunidade nova capturada nesta execução. Utilize os atalhos diretos acima.</p>"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Radar Eng. Mecânica | Estágios, Bolsas UFCIRJ & Desafios</title>
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --muted: #94a3b8; --accent: #38bdf8; }}
        body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        .container {{ max-width: 1160px; margin: 0 auto; }}
        header {{ border-bottom: 1px solid #334155; padding-bottom: 16px; margin-bottom: 20px; }}
        h1 {{ margin: 0 0 6px 0; font-size: 1.55rem; color: var(--accent); }}
        .sub {{ color: var(--muted); font-size: 0.9rem; margin: 0; }}
        .secao-titulo {{ font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin: 16px 0 8px 0; }}
        .atalhos {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }}
        .atalhos a {{ background: #1e293b; border: 1px solid #334155; color: #e2e8f0; padding: 7px 11px; border-radius: 8px; text-decoration: none; font-size: 0.82rem; }}
        .atalhos a:hover {{ border-color: var(--accent); color: var(--accent); }}
        .filtros {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }}
        button {{ background: var(--card); color: var(--text); border: 1px solid #475569; padding: 7px 14px; border-radius: 20px; cursor: pointer; font-weight: 600; font-size: 0.84rem; }}
        button.active, button:hover {{ background: var(--accent); color: #0f172a; border-color: var(--accent); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 16px; margin-top: 18px; }}
        .card {{ background: var(--card); border: 1px solid #334155; border-radius: 12px; padding: 18px; display: flex; flex-direction: column; justify-content: space-between; }}
        .card-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 0.76rem; gap: 6px; }}
        .badge {{ padding: 4px 10px; border-radius: 12px; font-weight: 700; }}
        .badge-estatal {{ background: #fef08a; color: #854d0e; }}
        .badge-energia {{ background: #bbf7d0; color: #166534; }}
        .badge-agente {{ background: #e9d5ff; color: #6b21a8; }}
        .badge-bolsa {{ background: #fed7aa; color: #9a3412; }}
        .badge-desafio {{ background: #fbcfe8; color: #9d174d; }}
        .badge-ind {{ background: #bae6fd; color: #075985; }}
        .date {{ color: var(--muted); white-space: nowrap; }}
        h3 {{ margin: 0 0 4px 0; font-size: 1.02rem; line-height: 1.35; }}
        .empresa {{ color: var(--accent); font-weight: 600; font-size: 0.88rem; margin: 0 0 12px 0; }}
        .detalhes {{ list-style: none; padding: 0; margin: 0 0 16px 0; font-size: 0.85rem; color: #cbd5e1; line-height: 1.6; background: #0f172a; padding: 10px 12px; border-radius: 8px; }}
        .btn {{ display: inline-block; text-align: center; background: #0284c7; color: white; text-decoration: none; padding: 10px; border-radius: 8px; font-weight: 600; font-size: 0.9rem; }}
        .btn:hover {{ background: #0369a1; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Radar Pessoal — Eng. Mecânica, Bolsas UFCIRJ & Desafios de Energia</h1>
            <p class="sub">Estágios (Rio, Caxias, Nova Iguaçu, Belford Roxo) • Bolsas CEFET/UFCIRJ • Desafios Globais | Atualizado em {atualizacao}</p>
        </header>

        <div class="secao-titulo">Acesso Rápido — Estágios, Bolsas CEFET/UFCIRJ & Competições</div>
        <div class="atalhos">
            <a href="https://www.cefet-rj.br/index.php/editais-e-processos-seletivos" target="_blank">🎓 Editais CEFET/UFCIRJ</a>
            <a href="https://dippg.cefet-rj.br/" target="_blank">🔬 DIPPG (PIBIC / JIPP)</a>
            <a href="https://www.trf2.jus.br/trf2/institucional/estagio" target="_blank">⚖️ TRF2 Estágios</a>
            <a href="https://www.nube.com.br/vagas-de-estagio/engenharia-mecanica" target="_blank">📋 Nube Mecânica</a>
            <a href="https://www.mudes.org.br/" target="_blank">📋 MUDES RJ</a>
            <a href="https://portal.ciee.org.br/processos-seletivos-especiais/" target="_blank">📋 CIEE Editais</a>
            <a href="https://www.spaceappschallenge.org/" target="_blank">🚀 NASA Space Apps</a>
            <a href="https://gogreen.se.com/" target="_blank">🌱 Schneider Go Green</a>
            <a href="https://www.makethefuture.shell/en-gb/shell-eco-marathon" target="_blank">⚡ Shell Eco-marathon</a>
            <a href="https://www.redbull.com/br-pt/projects/red-bull-basement" target="_blank">🐂 Red Bull Basement</a>
        </div>

        <div class="secao-titulo">Filtrar por Categoria</div>
        <div class="filtros" id="filtro-cat">
            <button class="active" onclick="setCat('todas', this)">Todas ({len(vagas)})</button>
            <button onclick="setCat('Bolsas & Editais CEFET/UFCIRJ', this)">Bolsas & Editais CEFET/UFCIRJ</button>
            <button onclick="setCat('Desafios & Hackathons', this)">Desafios & Hackathons</button>
            <button onclick="setCat('Órgãos Públicos & Estatais', this)">Órgãos Públicos & Estatais</button>
            <button onclick="setCat('Agentes (Nube / MUDES / CIEE)', this)">Agentes (Nube / MUDES / CIEE)</button>
            <button onclick="setCat('Energia Solar & Eólica', this)">Energia Solar & Eólica</button>
            <button onclick="setCat('Indústria & Engenharia', this)">Indústria & Engenharia</button>
        </div>

        <div class="secao-titulo">Filtrar Estágios por Cidade</div>
        <div class="filtros" id="filtro-city">
            <button class="active" onclick="setCity('todas', this)">Todas</button>
            <button onclick="setCity('Rio de Janeiro', this)">Rio de Janeiro</button>
            <button onclick="setCity('Duque de Caxias', this)">Duque de Caxias</button>
            <button onclick="setCity('Nova Iguaçu', this)">Nova Iguaçu</button>
            <button onclick="setCity('Belford Roxo', this)">Belford Roxo</button>
        </div>

        <div class="grid">
            {cards_html}
        </div>
    </div>

    <script>
        let catAtual = 'todas';
        let cityAtual = 'todas';

        function aplicarFiltros() {{
            document.querySelectorAll('.card').forEach(card => {{
                const matchCat = (catAtual === 'todas' || card.dataset.cat === catAtual);
                const matchCity = (cityAtual === 'todas' || card.dataset.city.includes(cityAtual));
                card.style.display = (matchCat && matchCity) ? 'flex' : 'none';
            }});
        }}

        function setCat(cat, btn) {{
            catAtual = cat;
            document.querySelectorAll('#filtro-cat button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            aplicarFiltros();
        }}

        function setCity(city, btn) {{
            cityAtual = city;
            document.querySelectorAll('#filtro-city button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            aplicarFiltros();
        }}
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


def main():
    antigas = []
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                antigas = json.load(f)
        except Exception:
            antigas = []

    links_antigos = {v["link"] for v in antigas}
    vagas = (
        buscar_bolsas_cefet()
        + buscar_orgaos_publicos()
        + buscar_nube_mecanica()
        + buscar_desafios_e_radar_web()
        + buscar_gupy_rj()
    )

    vistos = set()
    unicas = []
    ineditas = []
    for v in vagas:
        if v["link"] not in vistos:
            vistos.add(v["link"])
            unicas.append(v)
            if v["link"] not in links_antigos:
                ineditas.append(v)

    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(unicas, f, ensure_ascii=False, indent=2)

    gerar_html(unicas)
    enviar_telegram(ineditas)
    print(f"Concluído! {len(unicas)} oportunidades no site ({len(ineditas)} novas enviadas ao Telegram).")


if __name__ == "__main__":
    main()
