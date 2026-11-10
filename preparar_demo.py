"""Monta uma base de demonstração a partir da base pública LFW (via scikit-learn).
Os usuários recebem nomes fictícios; nenhuma identidade real é exibida.
Uso:  python preparar_demo.py
Estrutura gerada:
  base/referencia/usuario_0X/   (5 imagens por usuário cadastrado)
  base/teste/usuario_0X/        (4 imagens distintas por usuário)
  base/teste/desconhecido/      (imagens de pessoas NÃO cadastradas)
  base/teste/invalido/          (imagens sem face: ruído, gradiente, formas)
"""
import json
import shutil

import cv2
import numpy as np
from sklearn.datasets import fetch_lfw_people

import config as cfg
import pipeline as pl

N_CADASTRADOS, N_DESCONHECIDOS, N_REF, N_TESTE = 4, 3, 5, 4
NIVEIS = [1, 2, 3, 2]


def _salvar(pasta, nome, arr):
    arr = arr * 255 if arr.max() <= 1.0 else arr
    bgr = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2BGR)
    pasta.mkdir(parents=True, exist_ok=True)
    pl.salvar_imagem(pasta / nome, bgr)


def main():
    if cfg.BASE.exists():
        if input("A pasta 'base' já existe e será recriada. Continuar? (s/N) ").lower() != "s":
            return
        shutil.rmtree(cfg.BASE)
    print("Baixando/carregando LFW (pode demorar na primeira vez)...")
    lfw = fetch_lfw_people(min_faces_per_person=20, color=True, slice_=None, resize=1.0)
    ids, cont = np.unique(lfw.target, return_counts=True)
    escolhidos = ids[np.argsort(-cont)][:N_CADASTRADOS + N_DESCONHECIDOS]

    usuarios = {}
    for k, pid in enumerate(escolhidos[:N_CADASTRADOS], 1):
        uid = f"usuario_{k:02d}"
        usuarios[uid] = {"nome": f"Usuário Demo {k}", "nivel": NIVEIS[k - 1]}
        idx = np.where(lfw.target == pid)[0][:N_REF + N_TESTE]
        for j, i in enumerate(idx):
            destino = cfg.DIR_REFERENCIA / uid if j < N_REF else cfg.DIR_TESTE / uid
            _salvar(destino, f"{uid}_{j:02d}.jpg", lfw.images[i])
    for pid in escolhidos[N_CADASTRADOS:]:
        for j, i in enumerate(np.where(lfw.target == pid)[0][:N_TESTE]):
            _salvar(cfg.DIR_TESTE / "desconhecido", f"desc_{pid}_{j:02d}.jpg", lfw.images[i])

    # entradas inválidas (sintéticas): ruído, gradiente, formas geométricas, cor lisa
    rng = np.random.default_rng(0)
    inval = [rng.integers(0, 255, (250, 250, 3), dtype=np.uint8),
             np.tile(np.linspace(0, 255, 250, dtype=np.uint8), (250, 1))[..., None].repeat(3, 2),
             np.full((250, 250, 3), 128, np.uint8)]
    formas = np.zeros((250, 250, 3), np.uint8)
    cv2.rectangle(formas, (40, 40), (200, 200), (255, 255, 255), 3)
    cv2.circle(formas, (125, 125), 60, (0, 0, 255), -1)
    inval.append(formas)
    for j, im in enumerate(inval):
        pl.salvar_imagem(cfg.DIR_TESTE / "invalido" / f"invalido_{j}.png", im)

    cfg.BASE.mkdir(parents=True, exist_ok=True)
    cfg.ARQ_USUARIOS.write_text(json.dumps(usuarios, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Base de demonstração criada em:", cfg.BASE)
    print("Agora execute: python main.py  (opção 6 para calibrar, depois 5 para avaliar)")


if __name__ == "__main__":
    main()
