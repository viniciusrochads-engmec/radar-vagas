import json
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from bs4 import BeautifulSoup

ARQUIVO_DADOS = "vagas.json"

CIDADES_ESTAGIO = [
    "rio de janeiro", "duque de caxias", "xerem",
    "belford roxo", "nova iguacu"
]

ANOS_EXPIRADOS = ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]

TERMOS_ENCERRADOS = [
    "resultado final", "resultado preliminar", "homologacao", "homologação",
    "inscricoes encerradas", "inscrições encerradas", "gabarito", "convocacao",
    "convocação", "classificacao final", "classificação final", "errata"
]

TERMOS_AREA = [
    "engenharia mecanica", "eng. mecanica", "mecanica", "mechanical",
    "energia solar", "fotovoltaica", "energia eolica", "eolica", "wind",
    "energias renovaveis", "energia renovavel", "eficiencia energetica",
    "termofluidos", "climatizacao", "refrigeracao", "hvac", "ar condicionado",
    "manutencao mecanica", "projetos mecanicos", "metrologia", "cfd", "hidrogenio"
]

IGNORAR_LINKS = [
    "facebook", "instagram", "youtube", "bluesky", "twitter", "x.com",
    "linkedin.com/company", "socioambiental", "cultural", "investidor",
    "logo", "imprensa", "ouvidoria", "fale conosco", "politica de privacidade",
    "acessibilidade", "mapa do site", "login", "entrar", "esqueci minha senha"
]

FONTES_ORGAOS_PUBLICOS = [
    {"nome": "TRF2 (Tribunal Regional Federal 2ª Região)", "url": "https://www.trf2.jus.br/trf2/institucional/estagio", "cidade": "Rio de Janeiro - RJ (Centro)"},
    {"nome": "TJRJ (Tribunal de Justiça RJ)", "url": "https://www.tjrj.jus.br/web/guest/institucional/estagio", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "TRT-1 (Tribunal Regional do Trabalho RJ)", "url": "https://www.trt1.jus.br/web/guest/estagio", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "Governo do Estado RJ (Trabalho e Estágio)", "url": "https://www.rj.gov.br/cidadao/servicos/trabalho-e-estagio/categoria/20", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "CGE-RJ (Controladoria Geral do Estado)", "url": "https://cge.rj.gov.br/programa-de-estagio/", "cidade": "Rio de Janeiro - RJ (Centro)"},
    {"nome": "Prefeitura do Rio (IplanRio / Órgãos Municipais)", "url": "https://iplanrio.prefeitura.rio/", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "Prefeitura de Duque de Caxias", "url": "https://portal.duquedecaxias.rj.gov.br/", "cidade": "Duque de Caxias - RJ"},
    {"nome": "INMETRO (Campus Xerém)", "url": "https://www.gov.br/inmetro/pt-br/acesso-a-informacao/servidores/estagio", "cidade": "Duque de Caxias - RJ (Xerém)"},
    {"nome": "CEPEL (Pesquisa de Energia Elétrica)", "url": "https://www.cepel.br/trabalhe-conosco/", "cidade": "Rio de Janeiro - RJ (Ilha do Fundão)"},
    {"nome": "EPE (Empresa de Pesquisa Energética)", "url": "https://www.epe.gov.br/pt/a-epe/trabalhe-na-epe", "cidade": "Rio de Janeiro - RJ (Centro)"},
    {"nome": "CIEE (Processos Seletivos Públicos)", "url": "https://portal.ciee.org.br/processos-seletivos-especiais/", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "MUDES (Estágios RJ)", "url": "https://www.mudes.org.br/", "cidade": "Rio de Janeiro / Baixada"}
]

FONTES_BOLSAS = [
    {"nome": "CEFET/RJ (UFCIRJ) — Editais Abertos", "url": "https://www.cefet-rj.br/index.php/editais-e-processos-seletivos", "cidade": "Rio de Janeiro / Nova Iguaçu"},
    {"nome": "DIPPG CEFET/RJ — PIBIC, Pesquisa e Eventos", "url": "https://dippg.cefet-rj.br/", "cidade": "CEFET/RJ (UFCIRJ)"},
    {"nome": "FAPERJ — Editais e Bolsas RJ", "url": "https://www.faperj.br/?id=28.5.7", "cidade": "Estado do Rio de Janeiro"},
    {"nome": "CNPq — Chamadas Públicas Abertas", "url": "https://www.gov.br/cnpq/pt-br/acesso-a-informacao/acoes-e-programas/programas/programas-ict", "cidade": "Nacional / RJ"}
]

EMPRESAS_GUPY = [
    "braskem", "vibraenergia", "raizen", "engiebrasil", "enel",
    "edf-renewables", "equinor", "ternium", "whitemartins",
    "eletrobras", "light", "naturgy", "subsea7", "technipfmc", "modec"
]

CURSOS_CERTIFICADOS = [
    {
        "area_curso": "CAD / CAE / Simulação",
        "titulo": "ANSYS Innovation Courses — Fluid Dynamics (CFD), Heat Transfer & FEA",
        "instituicao": "ANSYS Inc. (Oficial — Internacional)",
        "modalidade": "EAD • Gratuito com Badge/Certificado",
        "descricao": "Trilhas oficiais de Dinâmica dos Fluidos Computacional (Fluent), Transferência de Calor e Elementos Finitos.",
        "link": "https://courses.ansys.com/"
    },
    {
        "area_curso": "CAD / CAE / Simulação",
        "titulo": "Autodesk Design & Manufacturing — Inventor & Fusion 360 (CAD/CAM/CAE)",
        "instituicao": "Autodesk Academy (Oficial — Internacional)",
        "modalidade": "EAD • Gratuito com Certificado",
        "descricao": "Modelagem paramétrica 3D, montagens mecânicas, desenho técnico e simulação estrutural.",
        "link": "https://www.autodesk.com/learn"
    },
    {
        "area_curso": "CAD / CAE / Simulação",
        "titulo": "MySolidWorks — Trilhas Oficiais de CAD 3D e Simulação",
        "instituicao": "Dassault Systèmes / SolidWorks (Oficial)",
        "modalidade": "EAD • Gratuito (Conta Estudante)",
        "descricao": "Modelagem de peças, chapas metálicas, superfícies aerodinâmicas e preparação para certificação CSWA.",
        "link": "https://my.solidworks.com/training"
    },
    {
        "area_curso": "ITA / IME / Instituições BR",
        "titulo": "Cursos Gratuitos do ITA — Controle, Programação e Engenharia",
        "instituicao": "ITA — Instituto Tecnológico de Aeronáutica (via Coursera)",
        "modalidade": "EAD • Gratuito (Opção Ouvinte / Auxílio Financeiro)",
        "descricao": "Cursos ministrados por professores do ITA (Orientação a Objetos, Controle de Sistemas, Métodos Ágeis).",
        "link": "https://www.coursera.org/ita"
    },
    {
        "area_curso": "ITA / IME / Instituições BR",
        "titulo": "Portal de Extensão e Eventos Científicos do IME",
        "instituicao": "IME — Instituto Militar de Engenharia (Praia Vermelha - RJ)",
        "modalidade": "Presencial (RJ) / Online • Certificados Acadêmicos",
        "descricao": "Simpósios, semanas de engenharia, minicursos de defesa, materiais e energia no IME (Urca - RJ).",
        "link": "https://www.ime.eb.mil.br/"
    },
    {
        "area_curso": "Programação & Dados",
        "titulo": "CS50's Introduction to Programming with Python (CS50P)",
        "instituicao": "Harvard University (EUA)",
        "modalidade": "EAD • Gratuito com Certificado Oficial CS50",
        "descricao": "Fundamentos sólidos de Python, automação, manipulação de arquivos, regex e testes aplicados.",
        "link": "https://cs50.harvard.edu/python/"
    },
    {
        "area_curso": "Energias Renováveis (Exterior)",
        "titulo": "Solar Energy & Wind Energy Engineering Courses",
        "instituicao": "TU Delft (Delft University of Technology — Holanda)",
        "modalidade": "EAD (edX) • Gratuito no modo Auditoria",
        "descricao": "Física de células fotovoltaicas, dimensionamento de sistemas solares e aerodinâmica de turbinas eólicas.",
        "link": "https://www.edx.org/school/delftx"
    },
    {
        "area_curso": "Energias Renováveis (Exterior)",
        "titulo": "Energy Transition, Thermodynamics & Mechanical Engineering",
        "instituicao": "Politecnico di Milano (Itália) & MIT OpenCourseWare (EUA)",
        "modalidade": "EAD • Gratuito (Polimi Open Knowledge / MIT OCW)",
        "descricao": "Cursos abertos de transição energética, ciclos termodinâmicos avançados e mecânica dos fluidos.",
        "link": "https://www.pok.polimi.it/"
    }
]


def normalizar(texto):
    if not texto:
        return ""
    mapa = str.maketrans("áàãâéêíóôõúüçÁÀÃÂÉÊÍÓÔÕÚÜÇ", "aaaaeeiooouucAAAAEEIOOOUUC")
    return texto.translate(mapa).lower()


def eh_atual_e_aberto(titulo, link=""):
    combinado = normalizar(f"{titulo} {link}")
    if any(ano in combinado for ano in ANOS_EXPIRADOS):
        return False
    if any(termo in combinado for termo in TERMOS_ENCERRADOS):
        return False
    return True


def regiao_permitida_geral(texto):
    norm = normalizar(texto)
    outros_estados = [
        "minas gerais", "belo horizonte", "bahia", "salvador", "parana", "curitiba",
        "rio grande do sul", "porto alegre", "santa catarina", "florianopolis",
        "pernambuco", "recife", "ceara", "fortaleza", "goias", "goiania", "amazonas", "manaus"
    ]
    if any(est in norm for est in outros_estados):
        if not any(ok in norm for ok in ["online", "remoto", "nacional", "todo o brasil", "rio de janeiro", "sao paulo"]):
            return False
    return True


def cidade_estagio_valida(texto_local):
    norm = normalizar(texto_local)
    return any(c in norm for c in CIDADES_ESTAGIO)


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
    if "sao paulo" in norm:
        return "São Paulo - SP"
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
    periodo = match_per.group(1).strip().capitalize() if match_per else "Ver requisitos"

    match_prazo = re.search(
        r"(?:inscrições\s*(?:abertas\s*)?até|prazo(?:\s*final)?[:\s]*|até\s*(?:o\s*dia\s*)?)(\d{1,2}[/\.]\d{1,2}(?:[/\.]\d{2,4})?|\d{1,2}\s*de\s*[a-zç]+)",
        limpo,
        re.IGNORECASE
    )
    prazo = match_prazo.group(1).strip() if match_prazo else "Inscrições Abertas (Ver edital)"

    return salario, periodo, prazo


def eh_titulo_semelhante(titulo_novo, titulos_existentes):
    limpo_novo = normalizar(titulo_novo.split(" - ")[0])
    palavras_novo = {p for p in re.findall(r"\w+", limpo_novo) if len(p) > 3}
    if not palavras_novo:
        return False

    eventos_unicos = ["nasa space apps", "schneider go green", "shell eco-marathon", "red bull basement", "edp university", "expin"]
    for ev in eventos_unicos:
        if ev in limpo_novo and any(ev in normalizar(t) for t in titulos_existentes):
            return True

    for existente in titulos_existentes:
        limpo_ex = normalizar(existente.split(" - ")[0])
        palavras_ex = {p for p in re.findall(r"\w+", limpo_ex) if len(p) > 3}
        if not palavras_ex:
            continue
        intersecao = len(palavras_novo & palavras_ex)
        uniao = len(palavras_novo | palavras_ex)
        if uniao > 0 and (intersecao / uniao) >= 0.52:
            return True
    return False


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
                    if cidade_estagio_valida(norm) and eh_atual_e_aberto(bloco_texto, href):
                        link_completo = href if href.startswith("http") else f"https://www.nube.com.br{href}"
                        salario, periodo, prazo = extrair_metadados(bloco_texto)
                        resultados.append({
                            "aba": "estagios",
                            "categoria": "Agentes (Nube / MUDES / CIEE)",
                            "titulo": bloco_texto[:120],
                            "empresa": "Nube — Estágio Eng. Mecânica",
                            "local": formatar_cidade(norm),
                            "periodo": periodo,
                            "salario": salario,
                            "prazo": prazo,
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

                eh_relevante = any(t in norm for t in ["estagio", "edital", "processo seletivo", "selecao", "engenharia", "mecanica", "inscricoes"])
                if (
                    12 <= len(texto) <= 180
                    and href.startswith("http")
                    and not any(ig in normalizar(f"{texto} {href}") for ig in IGNORAR_LINKS)
                    and eh_relevante
                    and eh_atual_e_aberto(texto, href)
                ):
                    salario, periodo, prazo = extrair_metadados(texto)
                    resultados.append({
                        "aba": "estagios",
                        "categoria": "Órgãos Públicos & Estatais",
                        "titulo": texto,
                        "empresa": fonte["nome"],
                        "local": fonte["cidade"],
                        "periodo": periodo,
                        "salario": salario,
                        "prazo": prazo,
                        "link": href,
                        "data": hoje
                    })
        except Exception as e:
            print(f"Aviso ({fonte['nome']}): {e}")
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

                if "estagio" in normalizar(titulo) and cidade_estagio_valida(cidade_raw) and any(t in texto_busca for t in TERMOS_AREA):
                    salario, periodo, prazo = extrair_metadados(descricao)
                    eh_renovavel = any(k in texto_busca for k in ["solar", "eolica", "renovavel", "renovaveis", "eficiencia energetica", "hidrogenio"])
                    resultados.append({
                        "aba": "estagios",
                        "categoria": "Energia Solar & Eólica" if eh_renovavel else "Indústria & Engenharia",
                        "titulo": titulo,
                        "empresa": empresa.upper(),
                        "local": formatar_cidade(cidade_raw),
                        "periodo": periodo,
                        "salario": salario,
                        "prazo": prazo,
                        "link": vaga.get("jobUrl", f"https://{empresa}.gupy.io/"),
                        "data": hoje
                    })
        except Exception as e:
            print(f"Aviso Gupy ({empresa}): {e}")
    return resultados


def buscar_bolsas_abertas():
    resultados = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    hoje = datetime.now().strftime("%d/%m/%Y")

    for fonte in FONTES_BOLSAS:
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

                tem_tema = any(p in norm for p in ["pibic", "pibiti", "faperj", "cnpq", "iniciacao cientifica", "bolsa", "extensao", "intercambio", "dupla diplomacao"])
                tem_abertura = any(a_kw in norm for a_kw in ["edital", "chamada", "abertura", "inscricoes", "selecao", "2026", "2027"])

                if (
                    14 <= len(texto) <= 190
                    and href.startswith("http")
                    and not any(ig in normalizar(f"{texto} {href}") for ig in IGNORAR_LINKS)
                    and tem_tema and tem_abertura
                    and eh_atual_e_aberto(texto, href)
                ):
                    salario, _, prazo = extrair_metadados(texto)
                    resultados.append({
                        "aba": "bolsas",
                        "categoria": "PIBIC / FAPERJ / CNPq",
                        "titulo": texto,
                        "empresa": fonte["nome"],
                        "local": fonte["cidade"],
                        "periodo": "Graduação (Ver CR/Período)",
                        "salario": salario if "R$" in salario else "Bolsa de Fomento",
                        "prazo": prazo,
                        "link": href,
                        "data": hoje
                    })
        except Exception as e:
            print(f"Aviso Bolsas ({fonte['nome']}): {e}")

    q_bolsas = '("PIBIC" OR "FAPERJ" OR "CNPq" OR "iniciação científica") ("inscrições abertas" OR "edital" OR "chamada") ("Rio de Janeiro" OR "CEFET" OR "UFRJ" OR "UFF") when:21d'
    url_rss = f"https://news.google.com/rss/search?q={urllib.parse.quote(q_bolsas)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    try:
        resp = requests.get(url_rss, timeout=15)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:8]:
                titulo = item.findtext("title", "")
                link = item.findtext("link", "")
                if eh_atual_e_aberto(titulo, link) and regiao_permitida_geral(titulo):
                    salario, _, prazo = extrair_metadados(titulo)
                    resultados.append({
                        "aba": "bolsas",
                        "categoria": "PIBIC / FAPERJ / CNPq",
                        "titulo": titulo.split(" - ")[0],
                        "empresa": "Fomento & Pesquisa RJ",
                        "local": "Rio de Janeiro - RJ",
                        "periodo": "Estudantes de Graduação",
                        "salario": salario if "R$" in salario else "Bolsa Institucional / Fomento",
                        "prazo": prazo,
                        "link": link,
                        "data": hoje
                    })
    except Exception as e:
        print(f"Aviso RSS Bolsas: {e}")

    return resultados


def buscar_desafios_abertos():
    resultados = []
    hoje = datetime.now().strftime("%d/%m/%Y")

    consultas = [
        '("Schneider Go Green" OR "NASA Space Apps" OR "Shell Eco-marathon" OR "Red Bull Basement" OR "EDP University Challenge" OR "EXPIN") ("inscrições abertas" OR "inscrições" OR "abertas") when:21d',
        '("hackathon" OR "desafio de inovação") ("energia limpa" OR "energia renovável" OR "energia solar" OR "energia eólica") ("inscrições abertas" OR "online" OR "Rio de Janeiro" OR "São Paulo") when:21d'
    ]

    for q in consultas:
        url_rss = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        try:
            resp = requests.get(url_rss, timeout=15)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item")[:10]:
                    titulo_raw = item.findtext("title", "")
                    titulo_limpo = titulo_raw.split(" - ")[0]
                    link = item.findtext("link", "")

                    if not eh_atual_e_aberto(titulo_limpo, link):
                        continue
                    if not regiao_permitida_geral(titulo_limpo):
                        continue

                    norm = normalizar(titulo_limpo)
                    local_ev = "Rio de Janeiro - RJ" if "rio de janeiro" in norm else ("São Paulo - SP" if "sao paulo" in norm else "Online / Nacional / Global")
                    _, _, prazo = extrair_metadados(titulo_limpo)

                    resultados.append({
                        "aba": "desafios",
                        "categoria": "Desafios & Hackathons",
                        "titulo": titulo_limpo,
                        "empresa": "Competição / Inovação Aberta",
                        "local": local_ev,
                        "periodo": "Universitários / Graduação",
                        "salario": "Premiação / Mentoria / Lattes",
                        "prazo": prazo,
                        "link": link,
                        "data": hoje
                    })
        except Exception as e:
            print(f"Aviso Desafios: {e}")

    return resultados


def enviar_telegram(novas_vagas):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id or not novas_vagas:
        return

    for v in novas_vagas[:8]:
        titulo_limpo = v["titulo"].replace("*", "").replace("_", "").replace("[", "(").replace("]", ")")
        mensagem = (
            f"🚨 *Nova Oportunidade Aberta ({v['categoria']})*\n\n"
            f"📌 *{titulo_limpo}*\n"
            f"🏢 {v['empresa']}\n"
            f"📍 {v['local']}\n"
            f"⏳ Prazo: {v['prazo']}\n"
            f"💰 Bolsa/Prêmio: {v['salario']}\n\n"
            f"🔗 [Acessar Oficial]({v['link']})"
        )
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(
                url,
                json={"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"},
                timeout=10
            )
        except Exception as e:
            print(f"Erro Telegram: {e}")


def gerar_html(itens):
    atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")

    cards_oportunidades = []
    for v in itens:
        cat = v["categoria"]
        aba = v["aba"]
        if aba == "bolsas":
            badge_class = "pill-orange"
        elif aba == "desafios":
            badge_class = "pill-pink"
        elif "Órgãos" in cat:
            badge_class = "pill-amber"
        elif "Solar" in cat:
            badge_class = "pill-green"
        elif "Agentes" in cat:
            badge_class = "pill-purple"
        else:
            badge_class = "pill-blue"

        cards_oportunidades.append(
            f'<article class="glass-card item-dinamico" data-aba="{aba}" data-cat="{cat}" data-city="{v["local"]}">'
            f'<div class="card-header"><span class="glass-pill {badge_class}">{cat}</span><span class="card-date">{v["data"]}</span></div>'
            f'<h3 class="card-title">{v["titulo"]}</h3>'
            f'<p class="card-subtitle">{v["empresa"]}</p>'
            f'<div class="spec-box">'
            f'<div class="spec-row"><span class="spec-label">Local</span><span class="spec-val">{v["local"]}</span></div>'
            f'<div class="spec-row"><span class="spec-label">Prazo</span><span class="spec-val highlight-prazo">{v["prazo"]}</span></div>'
            f'<div class="spec-row"><span class="spec-label">Requisito</span><span class="spec-val">{v["periodo"]}</span></div>'
            f'<div class="spec-row"><span class="spec-label">Bolsa / Prêmio</span><span class="spec-val">{v["salario"]}</span></div>'
            f'</div>'
            f'<a href="{v["link"]}" target="_blank" rel="noopener" class="apple-btn"><span>Abrir Edital / Inscrição</span> ↗</a>'
            f'</article>'
        )

    html_oportunidades = "\n".join(cards_oportunidades) if cards_oportunidades else '<div class="glass-card vazio">Nenhuma oportunidade nova aberta capturada nesta rodada. Utilize os atalhos diretos no dock acima.</div>'

    cards_cursos = []
    for c in CURSOS_CERTIFICADOS:
        cards_cursos.append(
            f'<article class="glass-card card-curso" data-curso-area="{c["area_curso"]}">'
            f'<div class="card-header"><span class="glass-pill pill-teal">{c["area_curso"]}</span><span class="card-date">Certificado Lattes</span></div>'
            f'<h3 class="card-title">{c["titulo"]}</h3>'
            f'<p class="card-subtitle">{c["instituicao"]}</p>'
            f'<div class="spec-box">'
            f'<div class="spec-row"><span class="spec-label">Modalidade</span><span class="spec-val">{c["modalidade"]}</span></div>'
            f'<div class="spec-desc">{c["descricao"]}</div>'
            f'</div>'
            f'<a href="{c["link"]}" target="_blank" rel="noopener" class="apple-btn btn-emerald"><span>Acessar Plataforma Oficial</span> ↗</a>'
            f'</article>'
        )

    html_cursos = "\n".join(cards_cursos)

    pagina = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Radar Engenharia Mecânica • Apple Glass Edition</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #070b14;
            --text-primary: rgba(255, 255, 255, 0.94);
            --text-secondary: rgba(255, 255, 255, 0.62);
            --text-tertiary: rgba(255, 255, 255, 0.42);
            --glass-bg: rgba(255, 255, 255, 0.055);
            --glass-bg-hover: rgba(255, 255, 255, 0.09);
            --glass-border: rgba(255, 255, 255, 0.14);
            --glass-highlight: rgba(255, 255, 255, 0.28);
            --spec-bg: rgba(0, 0, 0, 0.28);
            --shadow-glass: 0 20px 40px -15px rgba(0, 0, 0, 0.65), inset 0 1px 0 0 rgba(255, 255, 255, 0.22);
            --accent-blue: #0a84ff;
            --accent-blue-hover: #409cff;
            --orb-1: rgba(10, 132, 255, 0.34);
            --orb-2: rgba(94, 92, 230, 0.28);
            --orb-3: rgba(48, 209, 88, 0.20);
        }}
        body.light-mode {{
            --bg-base: #eef2f8;
            --text-primary: rgba(15, 23, 42, 0.92);
            --text-secondary: rgba(15, 23, 42, 0.64);
            --text-tertiary: rgba(15, 23, 42, 0.45);
            --glass-bg: rgba(255, 255, 255, 0.62);
            --glass-bg-hover: rgba(255, 255, 255, 0.82);
            --glass-border: rgba(255, 255, 255, 0.75);
            --glass-highlight: rgba(255, 255, 255, 0.95);
            --spec-bg: rgba(241, 245, 249, 0.68);
            --shadow-glass: 0 18px 36px -14px rgba(15, 23, 42, 0.12), inset 0 1px 0 0 rgba(255, 255, 255, 0.9);
            --accent-blue: #007aff;
            --accent-blue-hover: #0062cc;
            --orb-1: rgba(0, 122, 255, 0.22);
            --orb-2: rgba(88, 86, 214, 0.18);
            --orb-3: rgba(52, 199, 89, 0.18);
        }}
        * {{ box-sizing: border-box; -webkit-font-smoothing: antialiased; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif;
            background-color: var(--bg-base);
            color: var(--text-primary);
            margin: 0;
            padding: 28px 20px 60px;
            min-height: 100vh;
            overflow-x: hidden;
            transition: background-color 0.4s ease, color 0.4s ease;
        }}
        .ambient-canvas {{ position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none; }}
        .orb {{ position: absolute; border-radius: 50%; filter: blur(95px); animation: floatOrb 18s ease-in-out infinite alternate; }}
        .orb-1 {{ width: 520px; height: 520px; background: var(--orb-1); top: -120px; left: -80px; }}
        .orb-2 {{ width: 480px; height: 480px; background: var(--orb-2); top: 25%; right: -100px; animation-delay: -6s; }}
        .orb-3 {{ width: 460px; height: 460px; background: var(--orb-3); bottom: -140px; left: 30%; animation-delay: -12s; }}
        @keyframes floatOrb {{ 0% {{ transform: translate(0, 0) scale(1); }} 100% {{ transform: translate(35px, 28px) scale(1.08); }} }}
        .container {{ max-width: 1180px; margin: 0 auto; }}
        .hero-glass {{
            background: var(--glass-bg);
            backdrop-filter: blur(28px) saturate(180%);
            -webkit-backdrop-filter: blur(28px) saturate(180%);
            border: 1px solid var(--glass-border);
            box-shadow: var(--shadow-glass);
            border-radius: 26px;
            padding: 26px 30px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .hero-badge {{
            display: inline-flex; align-items: center; gap: 7px; font-size: 0.76rem; font-weight: 600;
            letter-spacing: 0.03em; text-transform: uppercase; color: var(--accent-blue);
            background: rgba(10, 132, 255, 0.14); border: 1px solid rgba(10, 132, 255, 0.3);
            padding: 5px 12px; border-radius: 999px; margin-bottom: 10px;
        }}
        .pulse-dot {{ width: 7px; height: 7px; border-radius: 50%; background: #30d158; box-shadow: 0 0 10px #30d158; }}
        h1 {{ margin: 0 0 6px 0; font-size: 1.75rem; font-weight: 700; letter-spacing: -0.025em; }}
        .hero-sub {{ margin: 0; color: var(--text-secondary); font-size: 0.92rem; line-height: 1.45; }}
        .theme-toggle {{
            background: var(--glass-bg); border: 1px solid var(--glass-border); color: var(--text-primary);
            padding: 10px 16px; border-radius: 999px; font-size: 0.84rem; font-weight: 600;
            cursor: pointer; backdrop-filter: blur(16px); transition: all 0.25s ease;
        }}
        .theme-toggle:hover {{ background: var(--glass-bg-hover); transform: translateY(-1px); }}
        .segmented-bar {{
            display: flex; flex-wrap: wrap; gap: 6px; background: var(--glass-bg);
            backdrop-filter: blur(24px) saturate(180%); -webkit-backdrop-filter: blur(24px) saturate(180%);
            border: 1px solid var(--glass-border); padding: 6px; border-radius: 18px;
            margin-bottom: 24px; box-shadow: var(--shadow-glass);
        }}
        .tab-btn {{
            flex: 1 1 auto; background: transparent; color: var(--text-secondary);
            border: 1px solid transparent; padding: 11px 16px; border-radius: 13px;
            font-size: 0.88rem; font-weight: 600; cursor: pointer; transition: all 0.25s ease; white-space: nowrap;
        }}
        .tab-btn:hover {{ color: var(--text-primary); background: rgba(255, 255, 255, 0.05); }}
        .tab-btn.active {{
            background: var(--glass-bg-hover); color: var(--text-primary);
            border-color: var(--glass-highlight); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.22);
        }}
        .section-label {{
            font-size: 0.76rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.06em; color: var(--text-tertiary); margin: 18px 0 10px 4px;
        }}
        .dock-links {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
        .dock-links a {{
            background: var(--glass-bg); backdrop-filter: blur(20px) saturate(160%);
            -webkit-backdrop-filter: blur(20px) saturate(160%); border: 1px solid var(--glass-border);
            color: var(--text-primary); padding: 8px 14px; border-radius: 12px;
            text-decoration: none; font-size: 0.82rem; font-weight: 500; transition: all 0.22s ease;
        }}
        .dock-links a:hover {{ background: var(--glass-bg-hover); border-color: var(--glass-highlight); transform: translateY(-2px); }}
        .filter-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }}
        .filter-pill {{
            background: var(--glass-bg); color: var(--text-secondary); border: 1px solid var(--glass-border);
            padding: 7px 15px; border-radius: 999px; font-size: 0.82rem; font-weight: 600;
            cursor: pointer; backdrop-filter: blur(16px); transition: all 0.2s ease;
        }}
        .filter-pill:hover {{ color: var(--text-primary); background: var(--glass-bg-hover); }}
        .filter-pill.active {{
            background: var(--accent-blue); color: #ffffff; border-color: transparent;
            box-shadow: 0 4px 14px rgba(10, 132, 255, 0.38);
        }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 18px; margin-top: 16px; }}
        .glass-card {{
            position: relative; background: var(--glass-bg);
            backdrop-filter: blur(28px) saturate(190%); -webkit-backdrop-filter: blur(28px) saturate(190%);
            border: 1px solid var(--glass-border); border-top-color: var(--glass-highlight);
            box-shadow: var(--shadow-glass); border-radius: 24px; padding: 22px;
            display: flex; flex-direction: column; justify-content: space-between;
            transition: transform 0.28s ease, background 0.28s ease, border-color 0.28s ease;
        }}
        .glass-card:hover {{ transform: translateY(-4px); background: var(--glass-bg-hover); border-color: var(--glass-highlight); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 12px; }}
        .glass-pill {{ padding: 4px 11px; border-radius: 999px; font-size: 0.73rem; font-weight: 600; border: 1px solid rgba(255, 255, 255, 0.16); }}
        .pill-amber {{ background: rgba(255, 214, 10, 0.16); color: #ffd60a; }}
        .pill-green {{ background: rgba(48, 209, 88, 0.16); color: #32d74b; }}
        .pill-purple {{ background: rgba(191, 90, 242, 0.18); color: #bf5af2; }}
        .pill-orange {{ background: rgba(255, 159, 10, 0.18); color: #ff9f0a; }}
        .pill-pink {{ background: rgba(255, 55, 95, 0.18); color: #ff375f; }}
        .pill-blue {{ background: rgba(10, 132, 255, 0.18); color: #64d2ff; }}
        .pill-teal {{ background: rgba(100, 210, 255, 0.18); color: #5ac8fa; }}
        body.light-mode .pill-amber {{ color: #9a6700; background: rgba(255, 204, 0, 0.22); }}
        body.light-mode .pill-green {{ color: #1a7f37; background: rgba(52, 199, 89, 0.2); }}
        body.light-mode .pill-purple {{ color: #8250df; background: rgba(175, 82, 222, 0.16); }}
        body.light-mode .pill-orange {{ color: #bc4c00; background: rgba(255, 149, 0, 0.18); }}
        body.light-mode .pill-pink {{ color: #cf22e; background: rgba(255, 45, 85, 0.16); }}
        body.light-mode .pill-blue {{ color: #0969da; background: rgba(0, 122, 255, 0.15); }}
        body.light-mode .pill-teal {{ color: #0550ae; background: rgba(50, 173, 230, 0.18); }}
        .card-date {{ font-size: 0.75rem; color: var(--text-tertiary); white-space: nowrap; }}
        .card-title {{ margin: 0 0 6px 0; font-size: 1.04rem; font-weight: 600; line-height: 1.38; letter-spacing: -0.01em; }}
        .card-subtitle {{ margin: 0 0 14px 0; font-size: 0.85rem; font-weight: 500; color: var(--text-secondary); }}
        .spec-box {{
            background: var(--spec-bg); border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 15px; padding: 12px 14px; margin-bottom: 16px;
            display: flex; flex-direction: column; gap: 7px;
        }}
        .spec-row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 10px; font-size: 0.82rem; }}
        .spec-label {{ color: var(--text-tertiary); font-weight: 500; flex-shrink: 0; }}
        .spec-val {{ color: var(--text-primary); font-weight: 500; text-align: right; }}
        .highlight-prazo {{ color: #64d2ff; font-weight: 600; }}
        body.light-mode .highlight-prazo {{ color: #007aff; }}
        .spec-desc {{ font-size: 0.81rem; color: var(--text-secondary); line-height: 1.45; margin-top: 2px; }}
        .apple-btn {{
            display: inline-flex; align-items: center; justify-content: center; gap: 6px; width: 100%;
            background: var(--accent-blue); color: #ffffff; text-decoration: none; padding: 11px 16px;
            border-radius: 13px; font-size: 0.86rem; font-weight: 600; transition: all 0.22s ease;
            box-shadow: 0 4px 14px rgba(10, 132, 255, 0.3);
        }}
        .apple-btn:hover {{ background: var(--accent-blue-hover); transform: scale(1.01); }}
        .btn-emerald {{ background: #28a745; box-shadow: 0 4px 14px rgba(40, 167, 69, 0.28); }}
        .btn-emerald:hover {{ background: #2fb94e; }}
        .hidden {{ display: none !important; }}
        .vazio {{ grid-column: 1 / -1; text-align: center; color: var(--text-secondary); }}
    </style>
</head>
<body>
    <div class="ambient-canvas"><div class="orb orb-1"></div><div class="orb orb-2"></div><div class="orb orb-3"></div></div>
    <div class="container">
        <header class="hero-glass">
            <div>
                <div class="hero-badge"><span class="pulse-dot"></span> Monitoramento Ativo • {atualizacao}</div>
                <h1>Radar Engenharia Mecânica</h1>
                <p class="hero-sub">Estágios (RJ & Baixada) • Bolsas PIBIC / FAPERJ / CNPq • Desafios • Certificações Lattes</p>
            </div>
            <button class="theme-toggle" onclick="alternarTema()" id="btn-tema">☀️ Modo Claro</button>
        </header>

        <nav class="segmented-bar">
            <button class="tab-btn active" onclick="mudarAba('todas', this)">Todas ({len(itens)})</button>
            <button class="tab-btn" onclick="mudarAba('estagios', this)">Estágios RJ & Baixada</button>
            <button class="tab-btn" onclick="mudarAba('bolsas', this)">Bolsas PIBIC / FAPERJ / CNPq</button>
            <button class="tab-btn" onclick="mudarAba('desafios', this)">Desafios & Hackathons</button>
            <button class="tab-btn" onclick="mudarAba('cursos', this)">Cursos & Certificados Lattes</button>
        </nav>

        <div id="painel-oportunidades">
            <div class="section-label">Acesso Rápido aos Portais</div>
            <div class="dock-links">
                <a href="https://www.trf2.jus.br/trf2/institucional/estagio" target="_blank">⚖️ TRF2 Estágios</a>
                <a href="https://www.nube.com.br/vagas-de-estagio/engenharia-mecanica" target="_blank">📋 Nube Mecânica</a>
                <a href="https://www.mudes.org.br/" target="_blank">📋 MUDES RJ</a>
                <a href="https://portal.ciee.org.br/processos-seletivos-especiais/" target="_blank">📋 CIEE Editais</a>
                <a href="https://www.faperj.br/?id=28.5.7" target="_blank">🔬 FAPERJ Editais</a>
                <a href="https://www.gov.br/cnpq/pt-br/acesso-a-informacao/acoes-e-programas/programas/programas-ict" target="_blank">🔬 CNPq / PIBIC</a>
                <a href="https://www.cefet-rj.br/index.php/editais-e-processos-seletivos" target="_blank">🎓 CEFET/UFCIRJ</a>
                <a href="https://www.spaceappschallenge.org/" target="_blank">🚀 NASA Space Apps</a>
                <a href="https://gogreen.se.com/" target="_blank">🌱 Schneider Go Green</a>
            </div>

            <div id="controles-estagio">
                <div class="section-label">Filtrar por Localidade</div>
                <div class="filter-row" id="filtro-city">
                    <button class="filter-pill active" onclick="setCity('todas', this)">Todas as Cidades</button>
                    <button class="filter-pill" onclick="setCity('Rio de Janeiro', this)">Rio de Janeiro</button>
                    <button class="filter-pill" onclick="setCity('Duque de Caxias', this)">Duque de Caxias</button>
                    <button class="filter-pill" onclick="setCity('Nova Iguaçu', this)">Nova Iguaçu</button>
                    <button class="filter-pill" onclick="setCity('Belford Roxo', this)">Belford Roxo</button>
                </div>
            </div>

            <div class="grid" id="grid-oportunidades">
                {html_oportunidades}
            </div>
        </div>

        <div id="painel-cursos" class="hidden">
            <div class="section-label">Trilhas Gratuitas com Certificado</div>
            <div class="filter-row" id="filtro-curso">
                <button class="filter-pill active" onclick="setCursoArea('todas', this)">Todos ({len(CURSOS_CERTIFICADOS)})</button>
                <button class="filter-pill" onclick="setCursoArea('CAD / CAE / Simulação', this)">CAD / CAE / ANSYS / SolidWorks</button>
                <button class="filter-pill" onclick="setCursoArea('ITA / IME / Instituições BR', this)">ITA / IME / Brasil</button>
                <button class="filter-pill" onclick="setCursoArea('Energias Renováveis (Exterior)', this)">Energias Renováveis (Exterior)</button>
                <button class="filter-pill" onclick="setCursoArea('Programação & Dados', this)">Python & Dados</button>
            </div>
            <div class="grid">
                {html_cursos}
            </div>
        </div>
    </div>

    <script>
        let abaAtual = 'todas';
        let cityAtual = 'todas';

        function alternarTema() {{
            document.body.classList.toggle('light-mode');
            const btn = document.getElementById('btn-tema');
            btn.textContent = document.body.classList.contains('light-mode') ? '🌙 Modo Escuro' : '☀️ Modo Claro';
        }}

        function mudarAba(aba, btn) {{
            abaAtual = aba;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const painelOp = document.getElementById('painel-oportunidades');
            const painelCursos = document.getElementById('painel-cursos');
            const controlesEstagio = document.getElementById('controles-estagio');
            if (aba === 'cursos') {{
                painelOp.classList.add('hidden');
                painelCursos.classList.remove('hidden');
            }} else {{
                painelCursos.classList.add('hidden');
                painelOp.classList.remove('hidden');
                controlesEstagio.style.display = (aba === 'estagios' || aba === 'todas') ? 'block' : 'none';
                aplicarFiltros();
            }}
        }}

        function aplicarFiltros() {{
            document.querySelectorAll('.item-dinamico').forEach(card => {{
                const matchAba = (abaAtual === 'todas' || card.dataset.aba === abaAtual);
                const matchCity = (cityAtual === 'todas' || abaAtual === 'bolsas' || abaAtual === 'desafios' || card.dataset.city.includes(cityAtual));
                card.style.display = (matchAba && matchCity) ? 'flex' : 'none';
            }});
        }}

        function setCity(city, btn) {{
            cityAtual = city;
            document.querySelectorAll('#filtro-city button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            aplicarFiltros();
        }}

        function setCursoArea(area, btn) {{
            document.querySelectorAll('#filtro-curso button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.card-curso').forEach(card => {{
                card.style.display = (area === 'todas' || card.dataset.cursoArea === area) ? 'flex' : 'none';
            }});
        }}
    </script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(pagina)


def main():
    antigas = []
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                antigas = json.load(f)
        except Exception:
            antigas = []

    links_antigos = {v["link"] for v in antigas}
    brutas = (
        buscar_orgaos_publicos()
        + buscar_nube_mecanica()
        + buscar_gupy_rj()
        + buscar_bolsas_abertas()
        + buscar_desafios_abertos()
    )

    vistos_links = set()
    titulos_aceitos = []
    unicas = []
    ineditas = []

    for v in brutas:
        if v["link"] in vistos_links:
            continue
        if eh_titulo_semelhante(v["titulo"], titulos_aceitos):
            continue

        vistos_links.add(v["link"])
        titulos_aceitos.append(v["titulo"])
        unicas.append(v)

        if v["link"] not in links_antigos:
            ineditas.append(v)

    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(unicas, f, ensure_ascii=False, indent=2)

    gerar_html(unicas)
    enviar_telegram(ineditas)
    print(f"Concluído! {len(unicas)} oportunidades abertas e únicas ({len(ineditas)} novas enviadas ao Telegram).")


if __name__ == "__main__":
    main()
