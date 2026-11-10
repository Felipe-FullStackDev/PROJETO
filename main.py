from pathlib import Path

import cv2

import avaliacao
import base_dados as bd
import config as cfg
import pipeline as pl
import reconhecimento as rc
import visualizacao as vz


class Estado:
    def __init__(self):
        self.recarregar()

    def recarregar(self):
        self.usuarios = bd.carregar_usuarios()
        self.referencias = bd.carregar_referencias(self.usuarios)
        self.limiar = rc.carregar_limiar()


def _caminho(texto):
    return Path(texto.strip().strip('"').strip("'"))


def _listar_imagens(entrada):
    p = _caminho(entrada)
    if p.is_dir():
        return sorted(f for f in p.iterdir() if f.suffix.lower() in cfg.EXTENSOES)
    return [p] if p.is_file() else []


# ---------- Ações ----------
def acao_cadastrar(st):
    nome = input("Nome (fictício) do usuário: ").strip()
    if not nome:
        return
    try:
        nivel = int(input("Nível de acesso (1, 2 ou 3): "))
        imgs = _listar_imagens(input("Pasta ou arquivo com imagens de referência: "))
        if not imgs:
            print("Nenhuma imagem encontrada.")
            return
        uid, ok, rej = bd.cadastrar_usuario(nome, nivel, imgs)
    except ValueError as e:
        print(f"Erro: {e}")
        return
    print(f"Usuário '{uid}': {ok} imagem(ns) cadastrada(s), {len(rej)} rejeitada(s).")
    for c, motivo in rej:
        print(f"  - {c}: {motivo}")
    if ok < 2:
        print("Aviso: recomenda-se >= 3 imagens de referência por usuário.")
    st.recarregar()


def acao_listar(st):
    if not st.usuarios:
        print("Nenhum usuário cadastrado.")
    for uid, u in st.usuarios.items():
        n = len(st.referencias.get(uid, []))
        print(f"  {uid:<20} {u['nome']:<25} {cfg.NIVEIS[u['nivel']]:<28} {n} ref.")
    print(f"Limiar de decisão atual: {st.limiar:.4f}")


def executar_identificacao(st, origem, salvar_nome="identificacao.png", mostrar=True):
    """Roda o pipeline completo para uma imagem (caminho ou array) e imprime o resultado."""
    try:
        res = pl.processar_imagem(origem)
    except pl.ErroPipeline as e:
        print(f"\n[ACESSO NEGADO] Entrada inválida: {e}")
        fig = vz.figura_pipeline(parcial=e.parcial, texto="ACESSO NEGADO\nEntrada inválida / sem face",
                                 cor="red")
        vz.exibir(fig, cfg.DIR_SAIDAS / salvar_nome, mostrar)
        return
    dec = rc.identificar(res.vetor, st.referencias, st.limiar)
    if dec.reconhecido:
        u = st.usuarios[dec.id_usuario]
        print(f"\n[ACESSO LIBERADO] {u['nome']} reconhecido(a) (distância {dec.distancia:.4f} <= "
              f"limiar {st.limiar:.4f}) - {cfg.NIVEIS[u['nivel']]}")
        for bloco in bd.informacoes_liberadas(u["nivel"]):
            print(f"\n  >> {bloco['titulo']}")
            for item in bloco["itens"]:
                print(f"     - {item}")
        texto = f"ACESSO LIBERADO\n{u['nome']}\n{cfg.NIVEIS[u['nivel']]}\ndist={dec.distancia:.3f}"
        cor = "green"
    else:
        d = "n/d" if dec.distancia is None else f"{dec.distancia:.4f}"
        print(f"\n[ACESSO NEGADO] Usuário não reconhecido (menor distância {d}, limiar {st.limiar:.4f}).")
        texto = f"ACESSO NEGADO\nnão reconhecido\ndist={d}"
        cor = "red"
    if dec.ranking:
        print("\n  Ranking:", ", ".join(f"{u} ({d:.3f})" for u, d in dec.ranking[:5]))
    vz.exibir(vz.figura_pipeline(res=res, texto=texto, cor=cor), cfg.DIR_SAIDAS / salvar_nome, mostrar)


def acao_identificar(st):
    if not st.referencias:
        print("Cadastre usuários antes de identificar.")
        return
    p = _caminho(input("Caminho da imagem de teste: "))
    executar_identificacao(st, p)


def acao_webcam(st):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Webcam indisponível.")
        return
    print("ESPAÇO = capturar | ESC = cancelar")
    quadro = None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        cv2.imshow("Captura (ESPACO/ESC)", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == 32:
            quadro = frame
            break
        if k == 27:
            break
    cap.release()
    cv2.destroyAllWindows()
    if quadro is not None:
        cfg.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
        pl.salvar_imagem(cfg.DIR_SAIDAS / "captura.jpg", quadro)
        executar_identificacao(st, quadro, "identificacao_webcam.png")


def acao_avaliar(st):
    avaliacao.avaliar(st.referencias, st.limiar)


def acao_calibrar(st):
    r = rc.calibrar_limiar(st.referencias)
    if r is None:
        print("Calibração requer >= 2 usuários e >= 2 imagens de referência por usuário.")
        return
    limiar, mg, mi = r
    rc.salvar_limiar(limiar)
    st.limiar = limiar
    print(f"Distância média genuínos: {mg:.4f} | impostores: {mi:.4f} | novo limiar: {limiar:.4f}")


def acao_painel(st):
    imgs = _listar_imagens(input("Pasta ou imagens de exemplo (mín. 4): "))[:6]
    resultados, titulos = [], []
    for i in imgs:
        try:
            resultados.append(pl.processar_imagem(i))
            titulos.append(i.name)
        except pl.ErroPipeline as e:
            print(f"  ignorada {i.name}: {e}")
    if len(resultados) < 4:
        print("São necessárias pelo menos 4 imagens válidas.")
        return
    vz.painel_exemplos(resultados, titulos, cfg.DIR_SAIDAS / "painel_exemplos.png", mostrar=True)
    print(f"Painel salvo em {cfg.DIR_SAIDAS / 'painel_exemplos.png'}")


MENU = [
    ("Cadastrar usuário fictício", acao_cadastrar),
    ("Listar usuários", acao_listar),
    ("Identificar usuário (imagem de teste)", acao_identificar),
    ("Identificar usuário (webcam)", acao_webcam),
    ("Avaliar desempenho (base/teste)", acao_avaliar),
    ("Calibrar limiar (com imagens de referência)", acao_calibrar),
    ("Gerar painel de exemplos para o relatório", acao_painel),
]


def main():
    bd.carregar_dados_ambientais()
    st = Estado()
    while True:
        print("\n=== APS - Identificação Biométrica Facial (1:N) ===")
        for i, (t, _) in enumerate(MENU, 1):
            print(f" {i}. {t}")
        print(" 0. Sair")
        op = input("> ").strip()
        if op == "0":
            break
        if op.isdigit() and 1 <= int(op) <= len(MENU):
            try:
                MENU[int(op) - 1][1](st)
            except Exception as e:  # tratamento de erro geral do protótipo
                print(f"Erro: {e}")
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()
