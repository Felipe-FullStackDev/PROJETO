"""Identificação biométrica 1:N por distância qui-quadrado entre descritores LBP."""
import itertools
import json
from dataclasses import dataclass, field

import config as cfg
from pipeline import distancia_chi2


@dataclass
class Decisao:
    reconhecido: bool
    id_usuario: str | None
    distancia: float | None
    ranking: list = field(default_factory=list)   # [(id, menor_distancia), ...] ordenado


def identificar(vetor, referencias, limiar):
    """Compara a amostra com TODOS os cadastrados (1:N). Usa a menor distância por usuário."""
    if not referencias:
        return Decisao(False, None, None)
    ranking = sorted(((uid, min(distancia_chi2(vetor, v) for v in vs)) for uid, vs in referencias.items()),
                     key=lambda t: t[1])
    melhor_id, melhor_d = ranking[0]
    return Decisao(melhor_d <= limiar, melhor_id, melhor_d, ranking)


# ---------- Limiar ----------
def carregar_limiar():
    if cfg.ARQ_LIMIAR.exists():
        return json.loads(cfg.ARQ_LIMIAR.read_text(encoding="utf-8"))["limiar"]
    return cfg.LIMIAR_PADRAO


def salvar_limiar(limiar):
    cfg.BASE.mkdir(parents=True, exist_ok=True)
    cfg.ARQ_LIMIAR.write_text(json.dumps({"limiar": limiar}), encoding="utf-8")


def calibrar_limiar(referencias):
    """Usa SOMENTE as imagens de referência (sem tocar nas de teste): pares do mesmo usuário (genuínos)
    x pares de usuários diferentes (impostores). Escolhe o limiar de maior acurácia balanceada.
    Retorna (limiar, media_genuinos, media_impostores) ou None se não houver dados suficientes."""
    gen, imp = [], []
    ids = list(referencias)
    for uid in ids:
        gen += [distancia_chi2(a, b) for a, b in itertools.combinations(referencias[uid], 2)]
    for u1, u2 in itertools.combinations(ids, 2):
        imp += [distancia_chi2(a, b) for a in referencias[u1] for b in referencias[u2]]
    if not gen or not imp:
        return None
    candidatos = sorted(set(gen + imp))
    melhor_t, melhor_s = candidatos[0], -1.0
    for t in candidatos:
        s = (sum(g <= t for g in gen) / len(gen) + sum(i > t for i in imp) / len(imp)) / 2
        if s > melhor_s:
            melhor_t, melhor_s = t, s
    # ponto médio entre o limiar escolhido e o próximo candidato (margem)
    prox = next((c for c in candidatos if c > melhor_t), melhor_t)
    limiar = (melhor_t + prox) / 2
    return limiar, sum(gen) / len(gen), sum(imp) / len(imp)
