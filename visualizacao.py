"""Visualização das etapas do pipeline (original, pré-processada, ROI e mapa LBP)."""
import cv2
import matplotlib.pyplot as plt

import config as cfg


def _rgb(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def _mostrar(ax, img, titulo, gray=False):
    ax.set_title(titulo, fontsize=10)
    ax.axis("off")
    if img is None:
        ax.text(0.5, 0.5, "não disponível", ha="center", va="center")
    else:
        ax.imshow(img, cmap="gray" if gray else None)


def figura_pipeline(res=None, parcial=None, texto="", cor="black"):
    """res: ResultadoPipeline (sucesso) ou parcial: dict com imagens intermediárias (falha)."""
    d = res.__dict__ if res is not None else (parcial or {})
    fig, ax = plt.subplots(2, 3, figsize=(13, 8))
    orig = d.get("original")
    if orig is not None:
        orig = orig.copy()
        if d.get("caixa"):
            x, y, w, h = d["caixa"]
            cv2.rectangle(orig, (x, y), (x + w, y + h), (0, 255, 0), 2)
    _mostrar(ax[0, 0], _rgb(orig) if orig is not None else None, "1. Imagem original (face detectada)")
    _mostrar(ax[0, 1], d.get("cinza"), "2. Escala de cinza (padronizada)", gray=True)
    _mostrar(ax[0, 2], d.get("preprocessada"), "3. Pré-processada (Gaussiano + CLAHE)", gray=True)
    _mostrar(ax[1, 0], d.get("roi"), "4. ROI biométrica (128x128)", gray=True)
    _mostrar(ax[1, 1], d.get("lbp_img"), "5. Mapa LBP uniforme", gray=True)
    ax[1, 2].axis("off")
    ax[1, 2].text(0.5, 0.5, texto, ha="center", va="center", fontsize=11, color=cor, wrap=True,
                  bbox=dict(boxstyle="round", fc="white", ec=cor))
    fig.tight_layout()
    return fig


def exibir(fig, salvar_em=None, mostrar=True):
    if salvar_em:
        cfg.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
        fig.savefig(salvar_em, dpi=120)
    if mostrar:
        plt.show()
    plt.close(fig)


def painel_exemplos(resultados, titulos, salvar_em, mostrar=False):
    """Painel para o relatório: uma linha por imagem (mín. 4): original | pré-processada | ROI | LBP."""
    n = len(resultados)
    fig, ax = plt.subplots(n, 4, figsize=(11, 2.8 * n), squeeze=False)
    for i, (r, t) in enumerate(zip(resultados, titulos)):
        orig = r.original.copy()
        x, y, w, h = r.caixa
        cv2.rectangle(orig, (x, y), (x + w, y + h), (0, 255, 0), 2)
        _mostrar(ax[i, 0], _rgb(orig), f"{t}\nOriginal")
        _mostrar(ax[i, 1], r.preprocessada, "Pré-processada", gray=True)
        _mostrar(ax[i, 2], r.roi, "ROI", gray=True)
        _mostrar(ax[i, 3], r.lbp_img, "Mapa LBP", gray=True)
    fig.tight_layout()
    exibir(fig, salvar_em, mostrar)
