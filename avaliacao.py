"""Avaliação de desempenho sobre base/teste/<id_usuario | desconhecido | invalido>/*.jpg"""
import csv

import config as cfg
import pipeline as pl
from reconhecimento import identificar

CENARIOS = {
    "cadastrado": "Usuário cadastrado (tentativa correta)",
    "desconhecido": "Pessoa não cadastrada (amostra não correspondente)",
    "invalido": "Entrada inválida (sem face detectável)",
}


def avaliar(referencias, limiar, salvar_csv=True):
    linhas = []
    if not cfg.DIR_TESTE.is_dir():
        print(f"Pasta de teste não encontrada: {cfg.DIR_TESTE}")
        return linhas
    for pasta in sorted(p for p in cfg.DIR_TESTE.iterdir() if p.is_dir()):
        esperado = pasta.name
        cenario = esperado if esperado in ("desconhecido", "invalido") else "cadastrado"
        for img in sorted(pasta.iterdir()):
            if img.suffix.lower() not in cfg.EXTENSOES:
                continue
            try:
                res = pl.processar_imagem(img)
                dec = identificar(res.vetor, referencias, limiar)
                obtido = dec.id_usuario if dec.reconhecido else "negado"
                if cenario == "cadastrado":
                    ok = dec.reconhecido and dec.id_usuario == esperado
                elif cenario == "desconhecido":
                    ok = not dec.reconhecido
                else:                                   # esperava-se erro de detecção
                    ok = False
                dist = dec.distancia
            except pl.ErroPipeline:
                obtido, dist = "entrada inválida", None
                ok = cenario == "invalido"
            linhas.append({"arquivo": f"{esperado}/{img.name}", "cenario": cenario, "esperado": esperado,
                           "obtido": obtido, "distancia": "" if dist is None else round(dist, 4),
                           "acerto": int(ok)})
    _imprimir_tabela(linhas)
    if salvar_csv and linhas:
        cfg.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
        with open(cfg.DIR_SAIDAS / "avaliacao.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0]))
            w.writeheader()
            w.writerows(linhas)
        print(f"\nDetalhes salvos em {cfg.DIR_SAIDAS / 'avaliacao.csv'}")
    return linhas


def _imprimir_tabela(linhas):
    if not linhas:
        print("Nenhuma imagem de teste encontrada.")
        return
    print(f"\n{'Cenário':<55}{'Testes':>7}{'Acertos':>9}{'Erros':>7}{'Acurácia':>10}")
    print("-" * 88)
    for chave, desc in CENARIOS.items():
        sub = [l for l in linhas if l["cenario"] == chave]
        if sub:
            a = sum(l["acerto"] for l in sub)
            print(f"{desc:<55}{len(sub):>7}{a:>9}{len(sub) - a:>7}{a / len(sub):>10.1%}")
    a = sum(l["acerto"] for l in linhas)
    print("-" * 88)
    print(f"{'GLOBAL':<55}{len(linhas):>7}{a:>9}{len(linhas) - a:>7}{a / len(linhas):>10.1%}")
    print("(FAR/FRR não calculados: o protocolo adotado é identificação 1:N.)")
