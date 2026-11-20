import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

ARQUIVO_DADOS = "vagas.json"

# Cidades permitidas (normalizadas sem acento para comparação)
CIDADES_PERMITIDAS = [
    "rio de janeiro", "duque de caxias", "xerem",
    "belford roxo", "nova iguacu"
]

# Termos obrigatórios de curso/área
TERMOS_MECANICA = [
    "engenharia mecânica", "engenharia mecanica", "eng. mecânica", "eng. mecanica",
    "mecânica", "mecanica", "mechanical", "manutenção", "manutencao",
    "projetos mecânicos", "energia", "renovável", "renovavel", "metrologia", "fluidos"
]

# Palavras para descartar links de redes sociais/menus
IGNORAR = [
    "facebook", "instagram", "youtube", "bluesky", "twitter", "x.com",
    "linkedin.com/company", "socioambiental", "cultural", "investidor",
    "logo", "imprensa", "ouvidoria", "fale conosco", "política de privacidade"
]

# Portais públicos e centros de pesquisa no RJ / Baixada
FONTES_EDITAIS = [
    {"nome": "MUDES (Estágios RJ)", "url": "https://www.mudes.org.br/", "cidade_padrao": "Rio de Janeiro / Baixada"},
    {"nome": "Portal CIEE", "url": "https://portal.ciee.org.br/processos-seletivos-especiais/", "cidade_padrao": "Rio de Janeiro - RJ"},
    {"nome": "EPE (Pesquisa Energética)", "url": "https://www.epe.gov.br/pt/a-epe/trabalhe-na-epe", "cidade_padrao": "Rio de Janeiro (Centro)"},
    {"nome": "Petrobras Carreiras", "url": "https://petrobras.com.br/quem-somos/carreiras", "cidade_padrao": "Rio de Janeiro / Duque de Caxias"},
    {"nome": "CEPEL (Pesquisa Energia)", "url": "https://www.cepel.br/trabalhe-conosco/", "cidade_padrao": "Rio de Janeiro (Fundão)"},
    {"nome": "INT (Inst. Nac. Tecnologia)", "url": "https://www.gov.br/int/pt-br/acesso-a-informacao/servidores/estagio", "cidade_padrao": "Rio de Janeiro (Centro)"}
]

# Empresas com operação no RJ, Caxias (REDUC/Polo) e Energia na plataforma Gupy
EMPRESAS_GUPY = [
    "braskem", "vibraenergia", "raizen", "engiebrasil", "enel",
    "edf-renewables", "equinor", "ternium", "whitemartins",
    "saint-gobain", "loreal", "ambev", "eletrobras", "light"
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

    # 1. Busca faixa salarial / bolsa-auxílio
    match_sal = re.search(
        r"(?:bolsa[\s\-auxílio]*|remuneração|salário|valor)?\s*(R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?(?:\s*(?:a|até|\-)\s*R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?)?)",
        limpo,
        re.IGNORECASE
    )
    salario = match_sal.group(1).strip() if match_sal else "Não divulgado no resumo"

    # 2. Busca período mínimo
    match_per = re.search(
        r"((?:a partir do\s*)
