import json
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from bs4 import BeautifulSoup

ARQUIVO_DADOS = "vagas.json"

# Cidades permitidas para estágios presenciais/híbridos
CIDADES_ESTAGIO = [
    "rio de janeiro", "duque de caxias", "xerem",
    "belford roxo", "nova iguacu"
]

# Anos antigos para descartar editais/desafios expirados
ANOS_EXPIRADOS = ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]

# Palavras que indicam processo já encerrado
TERMOS_ENCERRADOS = [
    "resultado final", "resultado preliminar", "homologacao", "homologação",
    "inscricoes encerradas", "inscrições encerradas", "gabarito", "convocacao",
    "convocação", "classificacao final", "classificação final", "errata"
]

# Palavras-chave técnicas (Eng. Mecânica + Energia Solar/Eólica + Sistemas Térmicos)
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

# Órgãos Públicos e Agentes Integradores (RJ & Baixada)
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

# Fontes de Bolsas e Fomento (CEFET/UFCIRJ, FAPERJ, CNPq)
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

# Catálogo Curado de Cursos Gratuitos com Certificado (Lattes & Formação Técnica)
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
        "descricao": "Cursos ministrados por professores do ITA (Orientação a Objetos com Java, Controle de Sistemas, Métodos Ágeis).",
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

    cards_oportunidades = ""
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

        cards_oportunidades += f"""
        <article class="glass-card item-dinamico" data-aba="{aba}" data-cat="{cat}" data-city="{v['local']}">
            <div class="card-header">
                <span class="glass-pill {badge_class}">{cat}</span>
                <span class="card-date">{v['data']}</span>
            </div>
            <h3 class="card-title">{v['titulo']}</h3>
            <p class="card-subtitle">{v['empresa']}</p>
            <div class="spec-box">
                <div class="spec-row"><span class="spec-label">Local</span><span class="spec-val">{v['local']}</span></div>
                <div class="spec-row"><span class="spec-label">Prazo</span><span class="spec-val highlight-prazo">{v['prazo']}</span></div>
                <div class="spec-row"><span class="spec-label">Requisito</span><span class="spec-val">{v['periodo']}</span></div>
                <div class="spec-row"><span class="spec-label">Bolsa / Prêmio</span><span class="spec-val">{v['salario']}</span></div>
            </div>
            <a href="{v['link']}" target="_blank" rel="noopener" class="apple-btn">
                <span>Abrir Edital / Inscrição</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7"/><path d="M7 7h10v10"/></svg>
            </a>
        </article>
        """

    if not cards_oportunidades:
        cards_oportunidades = "<div class='glass-card vazio'>Nenhuma oportunidade nova aberta capturada nesta rodada. Utilize os atalhos diretos no dock acima.</div>"

    cards_cursos = ""
    for c in CURSOS_CERTIFICADOS:
        cards_cursos += f"""
        <article class="glass-card card-curso" data-curso-area="{c['area_curso']}">
            <div class="card-header">
                <span class="glass-pill pill-teal">{c['area_curso']}</span>
                <span class="card-date">Certificado Lattes</span>
            </div>
            <h3 class="card-title">{c['titulo']}</h3>
            <p class
