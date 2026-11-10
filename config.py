"""Configurações globais do protótipo (APS 2026/2 - Identificação Biométrica Facial 1:N)."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BASE = RAIZ / "base"
DIR_REFERENCIA = BASE / "referencia"      # base/referencia/<id_usuario>/*.jpg  (cadastro)
DIR_TESTE = BASE / "teste"                # base/teste/<id_usuario|desconhecido|invalido>/*.jpg
ARQ_USUARIOS = BASE / "usuarios.json"
ARQ_AMBIENTAL = BASE / "dados_ambientais.json"
ARQ_LIMIAR = BASE / "limiar.json"
DIR_SAIDAS = RAIZ / "saidas"

EXTENSOES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# --- Pipeline ---
LADO_MAX = 640            # redimensionamento máximo (padronização do tamanho)
TAM_ROI = (128, 128)      # tamanho padrão da face (ROI)
GAUSS_KERNEL = (5, 5)     # filtro espacial: Gaussiano
CLAHE_CLIP = 2.0          # melhoria: equalização adaptativa de histograma
CLAHE_GRADE = (8, 8)
HAAR_ESCALA = 1.1
HAAR_VIZINHOS = 5
HAAR_MIN_FACE = (60, 60)

# --- Características (LBP uniforme por células) ---
LBP_P = 8
LBP_R = 1
GRADE_LBP = (8, 8)

# --- Decisão ---
LIMIAR_PADRAO = 0.35      # distância qui-quadrado média; recalibrável pelo menu

NIVEIS = {1: "Nível 1 - Geral", 2: "Nível 2 - Fiscalização", 3: "Nível 3 - Estratégico"}
