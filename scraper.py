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
        re
