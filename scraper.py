import json
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from bs4 import BeautifulSoup

ARQUIVO_DADOS = "vagas.json"

CIDADES_ESTAGIO = ["rio de janeiro", "duque de caxias", "xerem", "belford roxo", "nova iguacu"]
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
    {"nome": "Prefeitura do Rio (IplanRio)", "url": "https://iplanrio.prefeitura.rio/", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "Prefeitura de Duque de Caxias", "url": "https://portal.duquedecaxias.rj.gov.br/", "cidade": "Duque de Caxias - RJ"},
    {"nome": "INMETRO (Campus Xerém)", "url": "https://www.gov.br/inmetro/pt-br/acesso-a-informacao/servidores/estagio", "cidade": "Duque de Caxias - RJ (Xerém)"},
    {"nome": "CEPEL (Pesquisa de Energia Elétrica)", "url": "https://www.cepel.br/trabalhe-conosco/", "cidade": "Rio de Janeiro - RJ (Fundão)"},
    {"nome": "EPE (Empresa de Pesquisa Energética)", "url": "https://www.epe.gov.br/pt/a-epe/trabalhe-na-epe", "cidade": "Rio de Janeiro - RJ (Centro)"},
    {"nome": "CIEE (Processos Seletivos Públicos)", "url": "https://portal.ciee.org.br/processos-seletivos-especiais/", "cidade": "Rio de Janeiro - RJ"},
    {"nome": "MUDES (Estágios RJ)", "url": "https://www.mudes.org.br/", "cidade": "Rio de Janeiro / Baixada"}
]

FONTES_BOLSAS = [
    {"nome": "CEFET/RJ (UFCIRJ) — Editais & SRI Intercâmbio", "url": "https://www.cefet-rj.br/index.php/editais-e-processos-seletivos", "cidade": "CEFET/RJ / Portugal"},
    {"nome": "DIPPG CEFET/RJ — PIBIC & Pesquisa", "url": "https://dippg.cefet-rj.br/", "cidade": "CEFET/RJ (UFCIRJ)"},
    {"nome": "FAPERJ — Editais IC & Inovação (ITI)", "url": "https://www.faperj.br/?id=28.5.7", "cidade": "Estado do Rio de Janeiro"},
    {"nome": "CNPq — Bolsas & Chamadas Públicas", "url": "https://www.gov.br/cnpq/pt-br/acesso-a-informacao/acoes-e-programas/programas/programas-ict", "cidade": "Governo Federal / RJ"},
    {"nome": "CAPES — Mobilidade & Editais Internacionais", "url": "https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/bolsas/bolsas-e-auxilios-internacionais", "cidade": "Exterior / Portugal"}
]

EMPRESAS_GUPY = [
    "braskem", "vibraenergia", "raizen", "engiebrasil", "enel",
    "edf-renewables", "equinor", "ternium", "whitemartins",
    "eletrobras", "light", "naturgy", "subsea7", "technipfmc", "modec"
]

# Apenas certificações de alto peso no Lattes, oficiais de fabricantes ou com Credly Badge
CERTIFICACOES_LATTES = [
    {"area": "Credly & Fabricantes", "selo": "Badge Oficial ANSYS", "titulo": "ANSYS Innovation Courses — CFD (Fluent), Heat Transfer & FEA", "inst": "ANSYS Inc. (Oficial)", "mod": "EAD • Gratuito com Badge Verificado", "desc": "Física computacional de fluidos, transferência de calor e elementos finitos — base direta para pesquisa e Europa.", "link": "https://courses.ansys.com/"},
    {"area": "Credly & Fabricantes", "selo": "Credly Badge", "titulo": "Autodesk Learn & Certification — Inventor / Fusion (CAD/CAE)", "inst": "Autodesk (Oficial)", "mod": "EAD • Gratuito (Trilhas + Badge Credly)", "desc": "Modelagem paramétrica 3D, montagens mecânicas e preparação para credenciais oficiais Autodesk.", "link": "https://www.autodesk.com/learn"},
    {"area": "Credly & Fabricantes", "selo": "Certificado Oficial", "titulo": "MATLAB & Simulink Onramp + Métodos Numéricos", "inst": "MathWorks (Oficial)", "mod": "EAD • Gratuito com Certificado Verificável", "desc": "Aplicação direta em Cálculo Numérico, matrizes, EDOs e modelagem de sistemas térmicos/dinâmicos.", "link": "https://matlabacademy.mathworks.com/"},
    {"area": "Credly & Fabricantes", "selo": "Credencial CSWA", "titulo": "MySolidWorks — Trilha Oficial de CAD 3D & Preparação CSWA", "inst": "Dassault Systèmes / SolidWorks", "mod": "EAD • Conta Estudante", "desc": "Projeto de peças, chapas, montagens e certificação industrial globalmente reconhecida (CSWA).", "link": "https://my.solidworks.com/training"},
    {"area": "Programação (Credly)", "selo": "Credly Badge", "titulo": "Python Essentials 1 & 2 (Python Institute / Cisco NetAcad)", "inst": "Cisco Networking Academy + OpenEDG", "mod": "EAD • 100% Gratuito com Badge Credly", "desc": "Fundamentos sólidos de Python com insígnia digital verificável no Credly e LinkedIn.", "link": "https://www.netacad.com/courses/python-essentials-1"},
    {"area": "Programação (Credly)", "selo": "Certificado Harvard", "titulo": "CS50's Introduction to Programming with Python (CS50P)", "inst": "Harvard University (EUA)", "mod": "EAD • Gratuito com Certificado Oficial CS50", "desc": "Automação, tratamento de dados, regex e testes unitários em Python com peso internacional no Lattes.", "link": "https://cs50.harvard.edu/python/"},
    {"area": "Instituições de Elite", "selo": "Certificado ITA", "titulo": "Cursos de Engenharia, Controle e Programação do ITA", "inst": "ITA — Inst. Tecnológico de Aeronáutica (Coursera)", "mod": "EAD • Gratuito via Auxílio Financeiro", "desc": "Cursos oficiais de professores do ITA com certificado nominal verificável para o Lattes.", "link": "https://www.coursera.org/ita"},
    {"area": "Instituições de Elite", "selo": "Universidade Europeia", "titulo": "Solar Energy & Wind Energy Engineering (TU Delft / Polimi)", "inst": "TU Delft (Holanda) • Politecnico di Milano", "mod": "EAD • edX / Polimi Open Knowledge", "desc": "Dimensionamento fotovoltaico, aerodinâmica de turbinas eólicas e transição energética europeia.", "link": "https://www.edx.org/school/delftx"}
]


def normalizar(texto):
    if not texto:
        return ""
    mapa = str.maketrans("áàãâéêíóôõúüçÁÀÃÂÉÊÍÓÔÕÚÜÇ", "aaaaeeiooouucAAAAEEIOOOUUC")
    return texto.translate(mapa).lower()


def eh_atual_e_aberto(titulo, link=""):
    comb = normalizar(f"{titulo} {link}")
    return not any(a in comb for a in ANOS_EXPIRADOS) and not any(t in comb for t in TERMOS_ENCERRADOS)


def regiao_permitida_geral(texto):
    norm = normalizar(texto)
    outros = ["minas gerais", "belo horizonte", "bahia", "salvador", "parana", "curitiba", "rio grande do sul", "porto alegre", "santa catarina", "florianopolis", "pernambuco", "recife", "ceara", "fortaleza", "goias", "amazonas"]
    if any(e in norm for e in outros) and not any(k in norm for k in ["online", "remoto", "nacional", "brasil", "rio de janeiro", "sao paulo", "portugal", "europa", "internacional"]):
        return False
    return True


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
    m_sal = re.search(r"(?:bolsa[\s\-auxílio]*|remuneração|salário|auxílio|prêmio|valor)?\s*((?:R\$|€|US\$)\s*\d{1,3}(?:[\.,]\d{3})*(?:,\d{2})?)", limpo, re.I)
    m_per = re.search(r"((?:a partir do\s*)?\d{1,2}[º°o]\s*(?:ao\s*\d{1,2}[º°o]\s*)?(?:período|periodo|semestre))", limpo, re.I)
    m_prz = re.search(r"(?:inscrições\s*(?:abertas\s*)?até|prazo(?:\s*final)?[:\s]*|até\s*(?:o\s*dia\s*)?)(\d{1,2}[/\.]\d{1,2}(?:[/\.]\d{2,4})?|\d{1,2}\s*de\s*[a-zç]+)", limpo, re.I)
    return (
        m_sal.group(1).strip() if m_sal else "Consultar no edital",
        m_per.group(1).strip().capitalize() if m_per else "Ver requisitos",
        m_prz.group(1).strip() if m_prz else "Inscrições Abertas"
    )


def eh_titulo_semelhante(titulo_novo, existentes):
    limpo_novo = normalizar(titulo_novo.split(" - ")[0])
    for ev in ["nasa space apps", "schneider go green", "shell eco-marathon", "red bull basement", "edp university", "expin", "santander mobilidade", "santander ibero"]:
        if ev in limpo_novo and any(ev in normalizar(t) for t in existentes):
            return True
    p_novo = {p for p in re.findall(r"\w+", limpo_novo) if len(p) > 3}
    for ex in existentes:
        p_ex = {p for p in re.findall(r"\w+", normalizar(ex.split(" - ")[0])) if len(p) > 3}
        if p_novo and p_ex and (len(p_novo & p_ex) / len(p_novo | p_ex)) >= 0.52:
            return True
    return False


def buscar_nube_mecanica():
    resultados, hoje = [], datetime.now().strftime("%d/%m/%Y")
    try:
        resp = requests.get("https://www.nube.com.br/vagas-de-estagio/engenharia-mecanica", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                if "/detalhes-vaga/" in a["href"]:
                    txt = a.get_text(" | ", strip=True)
                    norm = normalizar(f"{txt} {a['href']}")
                    if any(c in norm for c in CIDADES_ESTAGIO) and eh_atual_e_aberto(txt, a["href"]):
                        sal, per, prz = extrair_metadados(txt)
                        link = a["href"] if a["href"].startswith("http") else f"https://www.nube.com.br{a['href']}"
                        resultados.append({"aba": "estagios", "categoria": "Agentes (Nube/MUDES/CIEE)", "titulo": txt[:120], "empresa": "Nube — Eng. Mecânica", "local": formatar_cidade(norm), "periodo": per, "salario": sal, "prazo": prz, "link": link, "data": hoje})
    except Exception as e:
        print(f"Aviso Nube: {e}")
    return resultados


def buscar_orgaos_publicos():
    resultados, hoje = [], datetime.now().strftime("%d/%m/%Y")
    for f in FONTES_ORGAOS_PUBLICOS:
        try:
            resp = requests.get(f["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                txt = a.get_text(" ", strip=True)
                norm = normalizar(txt)
                href = a["href"] if a["href"].startswith("http") else "/".join(f["url"].split("/")[:3]) + a["href"]
                if 12 <= len(txt) <= 180 and href.startswith("http") and not any(ig in normalizar(f"{txt} {href}") for ig in IGNORAR_LINKS) and any(t in norm for t in ["estagio", "edital", "processo seletivo", "selecao", "engenharia", "mecanica", "inscricoes"]) and eh_atual_e_aberto(txt, href):
                    sal, per, prz = extrair_metadados(txt)
                    resultados.append({"aba": "estagios", "categoria": "Órgãos Públicos & Estatais", "titulo": txt, "empresa": f["nome"], "local": f["cidade"], "periodo": per, "salario": sal, "prazo": prz, "link": href, "data": hoje})
        except Exception as e:
            print(f"Aviso ({f['nome']}): {e}")
    return resultados


def buscar_gupy_rj():
    resultados, hoje = [], datetime.now().strftime("%d/%m/%Y")
    for emp in EMPRESAS_GUPY:
        try:
            resp = requests.get(f"https://portal.api.gupy.io/api/job?jobName=estagio&subdomain={emp}&limit=30", headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
            if resp.status_code == 200:
                for v in resp.json().get("data", []):
                    titulo, desc = v.get("name", ""), v.get("description", "")
                    cid = f"{v.get('city', '')} {v.get('state', '')}"
                    busca = normalizar(f"{titulo} {desc}")
                    if "estagio" in normalizar(titulo) and any(c in normalizar(cid) for c in CIDADES_ESTAGIO) and any(t in busca for t in TERMOS_AREA):
                        sal, per, prz = extrair_metadados(desc)
                        eh_ren = any(k in busca for k in ["solar", "eolica", "renovavel", "renovaveis", "eficiencia energetica", "hidrogenio"])
                        resultados.append({"aba": "estagios", "categoria": "Energia Solar & Eólica" if eh_ren else "Indústria & Engenharia", "titulo": titulo, "empresa": emp.upper(), "local": formatar_cidade(cid), "periodo": per, "salario": sal, "prazo": prz, "link": v.get("jobUrl", f"https://{emp}.gupy.io/"), "data": hoje})
        except Exception as e:
            print(f"Aviso Gupy ({emp}): {e}")
    return resultados


def buscar_bolsas_e_subsistencia():
    """Monitora bolsas PIBIC/FAPERJ/CNPq + Auxílio Subsistência/Mobilidade (Santander, Governo, CAPES, Portugal/Europa)"""
    resultados, hoje = [], datetime.now().strftime("%d/%m/%Y")

    # 1. Varredura direta nas agências e no CEFET/UFCIRJ (somente abertura)
    for f in FONTES_BOLSAS:
        try:
            resp = requests.get(f["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                txt = a.get_text(" ", strip=True)
                norm = normalizar(txt)
                href = a["href"] if a["href"].startswith("http") else "/".join(f["url"].split("/")[:3]) + a["href"]
                tem_tema = any(p in norm for p in ["pibic", "pibiti", "iniciacao tecnologica", "faperj", "cnpq", "capes", "iniciacao cientifica", "bolsa", "intercambio", "dupla diplomacao", "mobilidade", "portugal", "assistencia estudantil"])
                tem_abertura = any(k in norm for k in ["edital", "chamada", "abertura", "inscricoes", "selecao", "2026", "2027"])
                if 14 <= len(txt) <= 190 and href.startswith("http") and not any(ig in normalizar(f"{txt} {href}") for ig in IGNORAR_LINKS) and tem_tema and tem_abertura and eh_atual_e_aberto(txt, href):
                    sal, _, prz = extrair_metadados(txt)
                    eh_mob = any(m in norm for m in ["intercambio", "dupla diplomacao", "mobilidade", "portugal", "capes", "exterior"])
                    cat = "Mobilidade & Subsistência Exterior" if eh_mob else "PIBIC / FAPERJ / CNPq"
                    resultados.append({"aba": "bolsas", "categoria": cat, "titulo": txt, "empresa": f["nome"], "local": f["cidade"], "periodo": "Graduação / CRA ≥ 7,0", "salario": sal if ("R$" in sal or "€" in sal) else "Bolsa / Auxílio Institucional", "prazo": prz, "link": href, "data": hoje})
        except Exception as e:
            print(f"Aviso Bolsas ({f['nome']}): {e}")

    # 2. Radar de Abertura (últimos 21 dias): Santander Universidades, Bolsas Governo, Subsistência Portugal/Europa, FAPERJ/CNPq
    consultas_bolsas = [
        {
            "q": '("Santander Universidades" OR "Santander Open Academy" OR "Bolsas Ibero-Americanas" OR "Fundação Estudar" OR "IAESTE") ("bolsa" OR "auxílio" OR "intercâmbio" OR "mobilidade") ("inscrições abertas" OR "edital") when:21d',
            "cat": "Mobilidade & Subsistência Exterior",
            "org": "Fomento Externo / Mobilidade",
            "loc": "Brasil / Portugal / Europa"
        },
        {
            "q": '("CAPES" OR "BRAFITEC" OR "Erasmus" OR "bolsa de subsistência" OR "bolsa mobilidade") ("graduação" OR "engenharia" OR "Portugal" OR "Europa") ("inscrições abertas" OR "edital") when:21d',
            "cat": "Mobilidade & Subsistência Exterior",
            "org": "Bolsas Governo / Cooperação Internacional",
            "loc": "Portugal / Europa"
        },
        {
            "q": '("PIBIC" OR "FAPERJ" OR "CNPq" OR "iniciação tecnológica") ("inscrições abertas" OR "edital" OR "chamada") ("Rio de Janeiro" OR "CEFET" OR "UFRJ" OR "UFF") when:21d',
            "cat": "PIBIC / FAPERJ / CNPq",
            "org": "Fomento à Pesquisa RJ / Governo",
            "loc": "Rio de Janeiro - RJ"
        }
    ]

    for c in consultas_bolsas:
        try:
            resp = requests.get(f"https://news.google.com/rss/search?q={urllib.parse.quote(c['q'])}&hl=pt-BR&gl=BR&ceid=BR:pt-419", timeout=15)
            if resp.status_code == 200:
                for item in ET.fromstring(resp.content).findall(".//item")[:8]:
                    t = item.findtext("title", "").split(" - ")[0]
                    l = item.findtext("link", "")
                    if eh_atual_e_aberto(t, l) and regiao_permitida_geral(t):
                        sal, _, prz = extrair_metadados(t)
                        resultados.append({"aba": "bolsas", "categoria": c["cat"], "titulo": t, "empresa": c["org"], "local": c["loc"], "periodo": "Estudantes de Graduação", "salario": sal if ("R$" in sal or "€" in sal) else "Auxílio / Subsistência", "prazo": prz, "link": l, "data": hoje})
        except Exception as e:
            print(f"Aviso RSS Bolsas: {e}")

    return resultados


def buscar_desafios_abertos():
    resultados, hoje = [], datetime.now().strftime("%d/%m/%Y")
    consultas = [
        '("Schneider Go Green" OR "NASA Space Apps" OR "Shell Eco-marathon" OR "Red Bull Basement" OR "EDP University Challenge" OR "EXPIN") ("inscrições abertas" OR "inscrições" OR "abertas") when:21d',
        '("hackathon" OR "desafio de inovação") ("energia limpa" OR "energia renovável" OR "energia solar" OR "energia eólica") ("inscrições abertas" OR "online" OR "Rio de Janeiro" OR "São Paulo") when:21d'
    ]
    for q in consultas:
        try:
            resp = requests.get(f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=pt-BR&gl=BR&ceid=BR:pt-419", timeout=15)
            if resp.status_code == 200:
                for item in ET.fromstring(resp.content).findall(".//item")[:10]:
                    t = item.findtext("title", "").split(" - ")[0]
                    l = item.findtext("link", "")
                    if eh_atual_e_aberto(t, l) and regiao_permitida_geral(t):
                        norm = normalizar(t)
                        loc = "Rio de Janeiro - RJ" if "rio de janeiro" in norm else ("São Paulo - SP" if "sao paulo" in norm else "Online / Nacional / Global")
                        _, _, prz = extrair_metadados(t)
                        resultados.append({"aba": "desafios", "categoria": "Desafios & Hackathons", "titulo": t, "empresa": "Competição / Inovação Aberta", "local": loc, "periodo": "Universitários", "salario": "Premiação / Lattes", "prazo": prz, "link": l, "data": hoje})
        except Exception as e:
            print(f"Aviso Desafios: {e}")
    return resultados


def enviar_telegram(novas):
    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id or not novas:
        return
    for v in novas[:8]:
        t = v["titulo"].replace("*", "").replace("_", "").replace("[", "(").replace("]", ")")
        msg = f"🚨 *Nova Oportunidade ({v['categoria']})*\n\n📌 *{t}*\n🏢 {v['empresa']}\n📍 {v['local']}\n⏳ Prazo: {v['prazo']}\n💰 Valor: {v['salario']}\n\n🔗 [Acessar Oficial]({v['link']})"
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        except Exception as e:
            print(f"Erro Telegram: {e}")


def gerar_html(itens):
    atualizacao = datetime.now().strftime("%d/%m/%Y às %H:%M")
    cores = {
        "Mobilidade & Subsistência Exterior": "p-tel",
        "PIBIC / FAPERJ / CNPq": "p-org",
        "Desafios & Hackathons": "p-pnk",
        "Órgãos Públicos & Estatais": "p-amb",
        "Energia Solar & Eólica": "p-grn",
        "Agentes (Nube/MUDES/CIEE)": "p-pur"
    }

    cards_op = [
        f'<article class="glass-card item-din" data-aba="{v["aba"]}" data-cat="{v["categoria"]}" data-city="{v["local"]}">'
        f'<div class="c-top"><span class="pill {cores.get(v["categoria"], "p-blu")}">{v["categoria"]}</span><span class="dt">{v["data"]}</span></div>'
        f'<h3>{v["titulo"]}</h3><p class="sub-c">{v["empresa"]}</p>'
        f'<div class="spec"><div><span>Local</span><b>{v["local"]}</b></div><div><span>Prazo</span><b class="prz">{v["prazo"]}</b></div><div><span>Requisito</span><b>{v["periodo"]}</b></div><div><span>Bolsa/Auxílio</span><b>{v["salario"]}</b></div></div>'
        f'<a href="{v["link"]}" target="_blank" rel="noopener" class="btn">Abrir Edital / Inscrição ↗</a></article>'
        for v in itens
    ]
    html_op = "\n".join(cards_op) if cards_op else '<div class="glass-card vazio">Nenhuma abertura nova capturada nesta rodada. Use os portais oficiais acima.</div>'

    cards_cur = [
        f'<article class="glass-card card-cur" data-area="{c["area"]}">'
        f'<div class="c-top"><span class="pill p-tel">{c["selo"]}</span><span class="dt">{c["area"]}</span></div>'
        f'<h3>{c["titulo"]}</h3><p class="sub-c">{c["inst"]}</p>'
        f'<div class="spec"><div><span>Credencial</span><b>{c["mod"]}</b></div><p class="desc">{c["desc"]}</p></div>'
        f'<a href="{c["link"]}" target="_blank" rel="noopener" class="btn btn-g">Acessar Plataforma Oficial ↗</a></article>'
        for c in CERTIFICACOES_LATTES
    ]
    html_cur = "\n".join(cards_cur)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Radar Engenharia Mecânica • Apple Glass</title>
<style>
:root{{--bg:#070b14;--tx:rgba(255,255,255,.94);--tx2:rgba(255,255,255,.62);--gl:rgba(255,255,255,.06);--glh:rgba(255,255,255,.1);--bd:rgba(255,255,255,.15);--hi:rgba(255,255,255,.3);--sp:rgba(0,0,0,.3);--ac:#0a84ff;--o1:rgba(10,132,255,.35);--o2:rgba(94,92,230,.28);--o3:rgba(48,209,88,.2)}}
body.light{{--bg:#eef2f8;--tx:rgba(15,23,42,.92);--tx2:rgba(15,23,42,.64);--gl:rgba(255,255,255,.65);--glh:rgba(255,255,255,.85);--bd:rgba(255,255,255,.8);--hi:#fff;--sp:rgba(241,245,249,.75);--ac:#007aff;--o1:rgba(0,122,255,.22);--o2:rgba(88,86,214,.18);--o3:rgba(52,199,89,.18)}}
*{{box-sizing:border-box;-webkit-font-smoothing:antialiased}}
body{{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display",Inter,sans-serif;background:var(--bg);color:var(--tx);margin:0;padding:24px 18px 60px;min-height:100vh;transition:.3s}}
.bg-orbs{{position:fixed;inset:0;z-index:-1;overflow:hidden;pointer-events:none}}
.orb{{position:absolute;border-radius:50%;filter:blur(90px);animation:flt 16s ease-in-out infinite alternate}}
.o1{{width:500px;height:500px;background:var(--o1);top:-100px;left:-80px}}.o2{{width:460px;height:460px;background:var(--o2);top:25%;right:-90px;animation-delay:-5s}}.o3{{width:440px;height:440px;background:var(--o3);bottom:-120px;left:30%;animation-delay:-10s}}
@keyframes flt{{to{{transform:translate(35px,25px) scale(1.08)}}}}
.wrap{{max-width:1160px;margin:0 auto}}
.hero,.seg,.glass-card,.dock a,.fpill,.tbtn{{background:var(--gl);backdrop-filter:blur(26px) saturate(180%);-webkit-backdrop-filter:blur(26px) saturate(180%);border:1px solid var(--bd);box-shadow:0 18px 38px -14px rgba(0,0,0,.45),inset 0 1px 0 var(--hi)}}
.hero{{border-radius:24px;padding:24px 28px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}}
.badge-live{{display:inline-flex;align-items:center;gap:7px;font-size:.75rem;font-weight:600;text-transform:uppercase;color:var(--ac);background:rgba(10,132,255,.15);padding:4px 12px;border-radius:99px;margin-bottom:8px}}
.dot{{width:7px;height:7px;border-radius:50%;background:#30d158;box-shadow:0 0 8px #30d158}}
h1{{margin:0 0 5px;font-size:1.65rem;letter-spacing:-.02em}}.sub{{margin:0;color:var(--tx2);font-size:.9rem}}
.tbtn{{color:var(--tx);padding:9px 15px;border-radius:99px;font-weight:600;font-size:.83rem;cursor:pointer}}
.seg{{display:flex;flex-wrap:wrap;gap:6px;padding:6px;border-radius:18px;margin-bottom:22px}}
.tab{{flex:1 1 auto;background:transparent;border:1px solid transparent;color:var(--tx2);padding:10px 14px;border-radius:13px;font-weight:600;font-size:.86rem;cursor:pointer;transition:.2s}}
.tab.active,.tab:hover{{background:var(--glh);color:var(--tx);border-color:var(--hi)}}
.lbl{{font-size:.75rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--tx2);margin:14px 0 8px 4px}}
.dock,.frow{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}}
.dock a{{color:var(--tx);padding:7px 13px;border-radius:12px;text-decoration:none;font-size:.82rem;font-weight:500;transition:.2s}}
.dock a:hover,.glass-card:hover{{background:var(--glh);transform:translateY(-3px)}}
.fpill{{color:var(--tx2);padding:6px 14px;border-radius:99px;font-size:.82rem;font-weight:600;cursor:pointer}}
.fpill.active{{background:var(--ac);color:#fff;border-color:transparent}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}}
.glass-card{{border-radius:22px;padding:20px;display:flex;flex-direction:column;justify-content:space-between;transition:.25s}}
.c-top{{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px}}
.pill{{padding:4px 10px;border-radius:99px;font-size:.72rem;font-weight:700}}
.p-amb{{background:rgba(255,214,10,.18);color:#ffd60a}}.p-grn{{background:rgba(48,209,88,.18);color:#32d74b}}.p-pur{{background:rgba(191,90,242,.2);color:#bf5af2}}.p-org{{background:rgba(255,159,10,.2);color:#ff9f0a}}.p-pnk{{background:rgba(255,55,95,.2);color:#ff375f}}.p-blu{{background:rgba(10,132,255,.2);color:#64d2ff}}.p-tel{{background:rgba(100,210,255,.2);color:#5ac8fa}}
body.light .p-amb{{color:#9a6700}}body.light .p-grn{{color:#1a7f37}}body.light .p-pur{{color:#8250df}}body.light .p-org{{color:#bc4c00}}body.light .p-pnk{{color:#cf222e}}body.light .p-blu{{color:#0969da}}body.light .p-tel{{color:#0550ae}}
.dt{{font-size:.74rem;color:var(--tx2)}}h3{{margin:0 0 5px;font-size:1.02rem;line-height:1.35}}.sub-c{{margin:0 0 12px;font-size:.84rem;color:var(--tx2)}}
.spec{{background:var(--sp);border-radius:14px;padding:11px 13px;margin-bottom:14px;display:flex;flex-direction:column;gap:6px;font-size:.81rem}}
.spec div{{display:flex;justify-content:space-between;gap:8px}}.spec span{{color:var(--tx2)}}.spec b{{text-align:right;font-weight:500}}.prz{{color:#64d2ff!important;font-weight:600!important}}.desc{{margin:2px 0 0;color:var(--tx2);line-height:1.4}}
.btn{{display:block;text-align:center;background:var(--ac);color:#fff;text-decoration:none;padding:10px;border-radius:12px;font-weight:600;font-size:.85rem}}.btn-g{{background:#28a745}}
.hidden{{display:none!important}}.vazio{{grid-column:1/-1;text-align:center;color:var(--tx2)}}
</style></head>
<body>
<div class="bg-orbs"><div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div></div>
<div class="wrap">
<header class="hero"><div><div class="badge-live"><span class="dot"></span> Ativo • {atualizacao}</div><h1>Radar Engenharia Mecânica</h1><p class="sub">Estágios RJ/Baixada • Bolsas Subsistência &amp; Mobilidade (Santander/Governo/Portugal) • Certificações Credly/Lattes</p></div><button class="tbtn" onclick="toggleTheme()" id="tbtn">☀️ Modo Claro</button></header>
<nav class="seg">
<button class="tab active" onclick="setAba('todas',this)">Todas ({len(itens)})</button>
<button class="tab" onclick="setAba('estagios',this)">Estágios RJ &amp; Baixada</button>
<button class="tab" onclick="setAba('bolsas',this)">Bolsas &amp; Auxílio Exterior</button>
<button class="tab" onclick="setAba('desafios',this)">Desafios &amp; Hackathons</button>
<button class="tab" onclick="setAba('cursos',this)">Certificações &amp; Credly (Lattes)</button>
</nav>
<div id="p-op">
<div class="lbl">Portais Oficiais — Mobilidade, Bolsas de Subsistência &amp; Estágios</div>
<div class="dock">
<a href="https://www.santanderopenacademy.com/pt_br/index.html" target="_blank">🌍 Santander Open Academy</a>
<a href="https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/bolsas/bolsas-e-auxilios-internacionais" target="_blank">✈️ CAPES Internacional</a>
<a href="https://www.cefet-rj.br/index.php/editais-e-processos-seletivos" target="_blank">🎓 CEFET/UFCIRJ &amp; SRI</a>
<a href="https://www.faperj.br/?id=28.5.7" target="_blank">🔬 FAPERJ (IC / ITI)</a>
<a href="https://www.trf2.jus.br/trf2/institucional/estagio" target="_blank">⚖️ TRF2 Estágios</a>
<a href="https://www.nube.com.br/vagas-de-estagio/engenharia-mecanica" target="_blank">📋 Nube Mecânica</a>
<a href="https://www.mudes.org.br/" target="_blank">📋 MUDES RJ</a>
<a href="https://portal.ciee.org.br/processos-seletivos-especiais/" target="_blank">📋 CIEE Editais</a>
<a href="https://iaeste.org.br/" target="_blank">🇪🇺 IAESTE Brasil</a>
</div>
<div id="c-est"><div class="lbl">Filtrar Cidade (Estágios)</div><div class="frow" id="fcity">
<button class="fpill active" onclick="setCity('todas',this)">Todas</button>
<button class="fpill" onclick="setCity('Rio de Janeiro',this)">Rio de Janeiro</button>
<button class="fpill" onclick="setCity('Duque de Caxias',this)">Duque de Caxias</button>
<button class="fpill" onclick="setCity('Nova Iguaçu',this)">Nova Iguaçu</button>
<button class="fpill" onclick="setCity('Belford Roxo',this)">Belford Roxo</button>
</div></div>
<div id="c-bol" class="hidden"><div class="lbl">Filtrar Tipo de Bolsa</div><div class="frow" id="fbol">
<button class="fpill active" onclick="setBolsa('todas',this)">Todas as Bolsas</button>
<button class="fpill" onclick="setBolsa('Mobilidade & Subsistência Exterior',this)">Mobilidade &amp; Subsistência (Santander/Governo/Portugal)</button>
<button class="fpill" onclick="setBolsa('PIBIC / FAPERJ / CNPq',this)">Pesquisa (PIBIC / FAPERJ / CNPq)</button>
</div></div>
<div class="grid">{html_op}</div>
</div>
<div id="p-cur" class="hidden">
<div class="lbl">Credenciais Reconhecidas (Fabricantes, Universidades de Elite &amp; Credly Badges)</div>
<div class="frow" id="fcur">
<button class="fpill active" onclick="setArea('todas',this)">Todas ({len(CERTIFICACOES_LATTES)})</button>
<button class="fpill" onclick="setArea('Credly & Fabricantes',this)">ANSYS / MathWorks / Autodesk / SolidWorks</button>
<button class="fpill" onclick="setArea('Programação (Credly)',this)">Python (Credly &amp; Harvard CS50P)</button>
<button class="fpill" onclick="setArea('Instituições de Elite',this)">ITA &amp; Universidades Europeias</button>
</div>
<div class="grid">{html_cur}</div>
</div></div>
<script>
let aba='todas',city='todas',bolsa='todas';
function toggleTheme(){{document.body.classList.toggle('light');document.getElementById('tbtn').textContent=document.body.classList.contains('light')?'🌙 Modo Escuro':'☀️ Modo Claro'}}
function setAba(a,b){{aba=a;document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.getElementById('p-op').classList.toggle('hidden',a==='cursos');document.getElementById('p-cur').classList.toggle('hidden',a!=='cursos');document.getElementById('c-est').style.display=(a==='estagios'||a==='todas')?'block':'none';document.getElementById('c-bol').classList.toggle('hidden',a!=='bolsas');filtrar()}}
function setCity(c,b){{city=c;document.querySelectorAll('#fcity .fpill').forEach(x=>x.classList.remove('active'));b.classList.add('active');filtrar()}}
function setBolsa(bl,b){{bolsa=bl;document.querySelectorAll('#fbol .fpill').forEach(x=>x.classList.remove('active'));b.classList.add('active');filtrar()}}
function filtrar(){{document.querySelectorAll('.item-din').forEach(x=>{{const okAba=(aba==='todas'||x.dataset.aba===aba);const okCity=(city==='todas'||aba!=='estagios'&&aba!=='todas'||x.dataset.aba!=='estagios'||x.dataset.city.includes(city));const okBol=(aba!=='bolsas'||bolsa==='todas'||x.dataset.cat===bolsa);x.style.display=(okAba&&okCity&&okBol)?'flex':'none'}})}}
function setArea(ar,b){{document.querySelectorAll('#fcur .fpill').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.querySelectorAll('.card-cur').forEach(x=>{{x.style.display=(ar==='todas'||x.dataset.area===ar)?'flex':'none'}})}}
</script></body></html>"""

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
    brutas = buscar_orgaos_publicos() + buscar_nube_mecanica() + buscar_gupy_rj() + buscar_bolsas_e_subsistencia() + buscar_desafios_abertos()

    vistos, titulos, unicas, ineditas = set(), [], [], []
    for v in brutas:
        if v["link"] not in vistos and not eh_titulo_semelhante(v["titulo"], titulos):
            vistos.add(v["link"])
            titulos.append(v["titulo"])
            unicas.append(v)
            if v["link"] not in links_antigos:
                ineditas.append(v)

    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(unicas, f, ensure_ascii=False, indent=2)

    gerar_html(unicas)
    enviar_telegram(ineditas)
    print(f"Concluído! {len(unicas)} oportunidades abertas ({len(ineditas)} novas).")


if __name__ == "__main__":
    main()
