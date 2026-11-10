"""Pipeline de PDI/VC: aquisição -> pré-processamento -> detecção da ROI -> características (LBP)."""
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from skimage.feature import local_binary_pattern

import config as cfg


class ErroPipeline(Exception):
    """Entrada inválida ou sem padrão biométrico detectável. 'parcial' guarda imagens intermediárias."""

    def __init__(self, mensagem, parcial=None):
        super().__init__(mensagem)
        self.parcial = parcial or {}


@dataclass
class ResultadoPipeline:
    original: np.ndarray        # BGR já padronizada
    cinza: np.ndarray
    preprocessada: np.ndarray
    caixa: tuple                # (x, y, w, h)
    roi: np.ndarray             # 128x128 em tons de cinza
    lbp_img: np.ndarray         # mapa LBP da ROI (visualização)
    vetor: np.ndarray           # descritor LBP em células


# ---------- 1. Aquisição e preparação ----------
def ler_imagem(caminho):
    """Lê imagem (aceita caminhos com acentos no Windows)."""
    try:
        img = cv2.imdecode(np.fromfile(str(caminho), dtype=np.uint8), cv2.IMREAD_COLOR)
    except OSError:
        img = None
    if img is None:
        raise ErroPipeline(f"Não foi possível ler a imagem: {caminho}")
    return img


def salvar_imagem(caminho, img):
    ok, buf = cv2.imencode(Path(caminho).suffix or ".jpg", img)
    if not ok:
        raise ErroPipeline(f"Falha ao salvar imagem: {caminho}")
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    buf.tofile(str(caminho))


def padronizar(img):
    """Redimensiona (mantendo proporção) e converte para escala de cinza."""
    h, w = img.shape[:2]
    maior = max(h, w)
    if maior > cfg.LADO_MAX:
        f = cfg.LADO_MAX / maior
        img = cv2.resize(img, (int(w * f), int(h * f)), interpolation=cv2.INTER_AREA)
    return img, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# ---------- 2. Pré-processamento (filtro Gaussiano + CLAHE) ----------
def preprocessar(cinza):
    suave = cv2.GaussianBlur(cinza, cfg.GAUSS_KERNEL, 0)                       # filtragem espacial
    clahe = cv2.createCLAHE(clipLimit=cfg.CLAHE_CLIP, tileGridSize=cfg.CLAHE_GRADE)
    return clahe.apply(suave)                                                  # melhoria de contraste


# ---------- 3. Detecção da ROI (Haar Cascade) ----------
_cascata = None


def _carregar_cascata():
    global _cascata
    if _cascata is None:
        _cascata = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if _cascata.empty():
            raise RuntimeError("Classificador Haar não encontrado na instalação do OpenCV.")
    return _cascata


def detectar_face(pre):
    faces = _carregar_cascata().detectMultiScale(
        pre, scaleFactor=cfg.HAAR_ESCALA, minNeighbors=cfg.HAAR_VIZINHOS, minSize=cfg.HAAR_MIN_FACE)
    if len(faces) == 0:
        return None
    return tuple(int(v) for v in max(faces, key=lambda f: f[2] * f[3]))  # maior face


def recortar_roi(pre, caixa):
    x, y, w, h = caixa
    return cv2.resize(pre[y:y + h, x:x + w], cfg.TAM_ROI, interpolation=cv2.INTER_AREA)


# ---------- 4. Características (LBP uniforme em grade) ----------
def extrair_lbp(roi):
    P = cfg.LBP_P
    lbp = local_binary_pattern(roi, P, cfg.LBP_R, method="uniform")
    gy, gx = cfg.GRADE_LBP
    ch, cw = lbp.shape[0] // gy, lbp.shape[1] // gx
    hists = []
    for i in range(gy):
        for j in range(gx):
            cel = lbp[i * ch:(i + 1) * ch, j * cw:(j + 1) * cw]
            h, _ = np.histogram(cel, bins=np.arange(P + 3))
            hists.append(h / (h.sum() + 1e-9))
    mapa = (lbp / (P + 1) * 255).astype(np.uint8)
    return np.concatenate(hists).astype(np.float32), mapa


def distancia_chi2(a, b):
    """Distância qui-quadrado média por célula (0 = idêntico)."""
    nb = cfg.LBP_P + 2
    a, b = a.reshape(-1, nb), b.reshape(-1, nb)
    return float((0.5 * ((a - b) ** 2 / (a + b + 1e-9)).sum(axis=1)).mean())


# ---------- Pipeline completo ----------
def processar_imagem(origem):
    """origem: caminho ou array BGR. Retorna ResultadoPipeline ou levanta ErroPipeline."""
    img = origem if isinstance(origem, np.ndarray) else ler_imagem(origem)
    original, cinza = padronizar(img)
    pre = preprocessar(cinza)
    parcial = {"original": original, "cinza": cinza, "preprocessada": pre}
    caixa = detectar_face(pre)
    if caixa is None:
        raise ErroPipeline("Nenhum padrão biométrico (face) detectado na imagem.", parcial)
    roi = recortar_roi(pre, caixa)
    vetor, mapa = extrair_lbp(roi)
    return ResultadoPipeline(original, cinza, pre, caixa, roi, mapa, vetor)
