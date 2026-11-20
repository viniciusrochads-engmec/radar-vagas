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
    """Garante que não seja edital de anos passados (2018-2025) nem resultado encerrado"""
    combinado = normalizar(f"{titulo} {link}")
    if any(ano in combinado for ano in ANOS_EXPIRADOS):
        return False
    if any(termo in combinado for termo in TERMOS_ENCERRADOS):
        return False
    return True


def regiao_permitida_geral(texto):
    """Para bolsas e desafios: aceita RJ, SP, Brasil/Nacional ou Online/Remoto; descarta outros estados"""
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

    # 1. Bolsa / Prêmio
    match_sal = re.search(
        r"(?:bolsa[\s\-auxílio]*|remuneração|salário|prêmio|valor)?\s*(R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?(?:\s*(?:a|até|\-)\s*R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?)?)",
        limpo,
        re.IGNORECASE
    )
    salario = match_sal.group(1).strip() if match_sal else "Consultar no edital"

    # 2. Período mínimo
    match_per = re.search(
        r"((?:a partir do\s*)?\d{1,2}[º°o]\s*(?:ao\s*\d{1,2}[º°o]\s*)?(?:período|periodo|semestre))",
        limpo,
        re
