"""Base local de usuários fictícios, imagens de referência e dados ambientais fictícios (JSON em disco)."""
import json
import re
import shutil
import unicodedata

import config as cfg
import pipeline as pl

DADOS_AMBIENTAIS_PADRAO = {
    "1": {"titulo": "Informações ambientais gerais (fictícias)",
          "itens": ["Propriedade Fazenda Boa Vista (FICT-001): 120 ha, uso agrícola",
                    "Propriedade Sítio Ribeirão (FICT-002): 35 ha, pecuária",
                    "Consulta pública fictícia nº 07/2026: uso da água na bacia do Rio Exemplo"]},
    "2": {"titulo": "Relatórios de fiscalização e ocorrências (fictícios)",
          "itens": ["Relatório de fiscalização RF-2026-014: APP irregular em FICT-001",
                    "Ocorrência OC-2026-033: suspeita de contaminação por defensivo agrícola em FICT-002",
                    "Análise técnica AT-2026-009: qualidade da água - ponto P3 acima do limite"]},
    "3": {"titulo": "Informações estratégicas e decisões administrativas (fictícias)",
          "itens": ["Relatório consolidado RC-2026-S2: 14 ocorrências abertas na região norte",
                    "Decisão administrativa DA-2026-005: embargo parcial de FICT-001",
                    "Plano estratégico PE-2027: priorização de fiscalização em áreas de nascentes"]},
}


def _slug(nome):
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "usuario"


# ---------- Usuários ----------
def carregar_usuarios():
    if cfg.ARQ_USUARIOS.exists():
        return json.loads(cfg.ARQ_USUARIOS.read_text(encoding="utf-8"))
    return {}


def salvar_usuarios(usuarios):
    cfg.BASE.mkdir(parents=True, exist_ok=True)
    cfg.ARQ_USUARIOS.write_text(json.dumps(usuarios, ensure_ascii=False, indent=2), encoding="utf-8")


def cadastrar_usuario(nome, nivel, caminhos_imagens, id_usuario=None):
    """Copia as imagens válidas (com face detectável) para a base de referência e registra o usuário.
    Retorna (id, aceitas, rejeitadas)."""
    if nivel not in cfg.NIVEIS:
        raise ValueError("Nível de acesso deve ser 1, 2 ou 3.")
    uid = id_usuario or _slug(nome)
    destino = cfg.DIR_REFERENCIA / uid
    destino.mkdir(parents=True, exist_ok=True)
    aceitas, rejeitadas = 0, []
    n = len([p for p in destino.iterdir() if p.suffix.lower() in cfg.EXTENSOES])
    for c in caminhos_imagens:
        try:
            pl.processar_imagem(c)          # só cadastra se o pipeline encontrar uma face
        except pl.ErroPipeline as e:
            rejeitadas.append((str(c), str(e)))
            continue
        n += 1
        shutil.copy2(c, destino / f"ref_{n:02d}{c.suffix.lower()}")
        aceitas += 1
    if aceitas:
        usuarios = carregar_usuarios()
        usuarios[uid] = {"nome": nome, "nivel": nivel}
        salvar_usuarios(usuarios)
    return uid, aceitas, rejeitadas


def carregar_referencias(usuarios=None):
    """Retorna {id_usuario: [vetor_LBP, ...]} a partir das imagens de referência em disco."""
    usuarios = usuarios if usuarios is not None else carregar_usuarios()
    refs = {}
    for uid in usuarios:
        pasta = cfg.DIR_REFERENCIA / uid
        if not pasta.is_dir():
            continue
        vetores = []
        for img in sorted(pasta.iterdir()):
            if img.suffix.lower() in cfg.EXTENSOES:
                try:
                    vetores.append(pl.processar_imagem(img).vetor)
                except pl.ErroPipeline:
                    pass
        if vetores:
            refs[uid] = vetores
    return refs


# ---------- Dados ambientais fictícios ----------
def carregar_dados_ambientais():
    if not cfg.ARQ_AMBIENTAL.exists():
        cfg.BASE.mkdir(parents=True, exist_ok=True)
        cfg.ARQ_AMBIENTAL.write_text(json.dumps(DADOS_AMBIENTAIS_PADRAO, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    return json.loads(cfg.ARQ_AMBIENTAL.read_text(encoding="utf-8"))


def informacoes_liberadas(nivel):
    """Controle hierárquico: nível N acessa os conteúdos dos níveis 1..N."""
    dados = carregar_dados_ambientais()
    return [dados[str(n)] for n in range(1, nivel + 1)]
