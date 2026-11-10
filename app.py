from pathlib import Path
from tempfile import NamedTemporaryFile
import os

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

import avaliacao
import base_dados as bd
import config as cfg
import pipeline as pl
import reconhecimento as rc

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
ALLOWED = cfg.EXTENSOES

def carregar_estado():
    usuarios = bd.carregar_usuarios()
    referencias = bd.carregar_referencias(usuarios)
    return usuarios, referencias

def erro(mensagem, status=400):
    return jsonify({"ok": False, "error": mensagem}), status

@app.get("/")
def index():
    return send_from_directory(app.root_path, "index.html")

@app.get("/api/status")
def status():
    usuarios, refs = carregar_estado()
    return jsonify({
        "ok": True,
        "pessoas": len(usuarios),
        "referencias": sum(len(v) for v in refs.values()),
        "limiar": rc.carregar_limiar()
    })

@app.get("/api/people")
def listar_pessoas():
    usuarios, refs = carregar_estado()
    itens = []
    for uid, pessoa in usuarios.items():
        pasta = cfg.DIR_REFERENCIA / uid
        imagens = len([p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED]) if pasta.exists() else 0
        itens.append({
            "id": uid,
            "name": pessoa.get("nome", uid),
            "level": pessoa.get("nivel", 1),
            "images": imagens,
            "references": len(refs.get(uid, []))
        })
    return jsonify({"ok": True, "people": itens})

@app.post("/api/people")
def cadastrar_pessoa():
    nome = (request.form.get("name") or "").strip()
    try:
        nivel = int(request.form.get("level", "1"))
    except ValueError:
        return erro("Nível de acesso inválido.")
    arquivos = request.files.getlist("photos")
    if not nome:
        return erro("Informe o nome da pessoa.")
    if nivel not in cfg.NIVEIS:
        return erro("O nível deve ser 1, 2 ou 3.")
    if not arquivos or not any(f.filename for f in arquivos):
        return erro("Selecione pelo menos uma imagem de referência.")
    usuarios = bd.carregar_usuarios()
    if any(p.get("nome", "").casefold() == nome.casefold() for p in usuarios.values()):
        return erro("Já existe uma pessoa cadastrada com esse nome.")
    temporarios, validos = [], []
    try:
        for arquivo in arquivos:
            if not arquivo.filename:
                continue
            ext = Path(secure_filename(arquivo.filename)).suffix.lower()
            if ext not in ALLOWED:
                continue
            with NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                arquivo.save(tmp)
                temporarios.append(tmp.name)
                validos.append(Path(tmp.name))
        if not validos:
            return erro("Nenhuma imagem em formato aceito. Use JPG, PNG, BMP ou WEBP.")
        uid, aceitas, rejeitadas = bd.cadastrar_usuario(nome, nivel, validos)
        if aceitas == 0:
            return erro("Nenhuma imagem foi aceita. Verifique iluminação, enquadramento e se há um rosto visível.")
        return jsonify({
            "ok": True, "id": uid, "name": nome, "level": nivel,
            "accepted": aceitas, "rejected": len(rejeitadas),
            "message": f"Cadastro realizado: {aceitas} imagem(ns) processada(s)."
        })
    except Exception as exc:
        app.logger.exception("Falha no cadastro")
        return erro(f"Não foi possível cadastrar: {exc}", 500)
    finally:
        for item in temporarios:
            try: os.unlink(item)
            except OSError: pass

@app.delete("/api/people/<uid>")
def excluir_pessoa(uid):
    usuarios = bd.carregar_usuarios()
    if uid not in usuarios:
        return erro("Cadastro não encontrado.", 404)
    pasta = cfg.DIR_REFERENCIA / uid
    if pasta.exists():
        import shutil
        shutil.rmtree(pasta)
    usuarios.pop(uid, None)
    bd.salvar_usuarios(usuarios)
    return jsonify({"ok": True, "message": "Cadastro removido."})

@app.post("/api/identify")
def identificar_pessoa():
    arquivo = request.files.get("photo")
    if not arquivo or not arquivo.filename:
        return erro("Selecione ou capture uma imagem.")
    ext = Path(secure_filename(arquivo.filename)).suffix.lower() or ".jpg"
    if ext not in ALLOWED:
        return erro("Formato de imagem não aceito.")
    tmp_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            arquivo.save(tmp)
            tmp_path = tmp.name
        resultado = pl.processar_imagem(tmp_path)
        usuarios, referencias = carregar_estado()
        if not referencias:
            return erro("Ainda não existem imagens de referência cadastradas.", 409)
        decisao = rc.identificar(resultado.vetor, referencias, rc.carregar_limiar())
        resposta = {
            "ok": True, "recognized": decisao.reconhecido,
            "distance": decisao.distancia,
            "threshold": rc.carregar_limiar(),
            "ranking": [{"id": uid, "name": usuarios.get(uid, {}).get("nome", uid), "distance": dist}
                        for uid, dist in decisao.ranking[:5]]
        }
        if decisao.reconhecido:
            pessoa = usuarios[decisao.id_usuario]
            nivel = int(pessoa.get("nivel", 1))
            resposta.update({
                "name": pessoa.get("nome", decisao.id_usuario),
                "level": nivel,
                "level_name": cfg.NIVEIS[nivel],
                "information": bd.informacoes_liberadas(nivel)
            })
        return jsonify(resposta)
    except pl.ErroPipeline as exc:
        return jsonify({"ok": True, "recognized": False, "invalid": True, "message": str(exc)}), 200
    except Exception as exc:
        app.logger.exception("Falha na identificação")
        return erro(f"Falha ao processar a imagem: {exc}", 500)
    finally:
        if tmp_path:
            try: os.unlink(tmp_path)
            except OSError: pass

@app.post("/api/calibrate")
def calibrar():
    _, referencias = carregar_estado()
    resultado = rc.calibrar_limiar(referencias)
    if resultado is None:
        return erro("A calibração exige pelo menos duas pessoas cadastradas e duas imagens válidas por pessoa.")
    limiar, media_genuinos, media_impostores = resultado
    rc.salvar_limiar(limiar)
    return jsonify({"ok": True, "threshold": limiar, "genuine_mean": media_genuinos,
                    "impostor_mean": media_impostores})

@app.post("/api/evaluate")
def avaliar():
    _, referencias = carregar_estado()
    if not referencias:
        return erro("Cadastre pessoas e imagens de referência antes da avaliação.")
    linhas = avaliacao.avaliar(referencias, rc.carregar_limiar(), salvar_csv=True)
    if not linhas:
        return erro("Nenhuma imagem encontrada em base/teste/<pessoa|desconhecido|invalido>.")
    total = len(linhas)
    acertos = sum(int(x["acerto"]) for x in linhas)
    return jsonify({"ok": True, "total": total, "hits": acertos,
                    "accuracy": round(acertos / total * 100, 2),
                    "csv": "saidas/avaliacao.csv"})

if __name__ == "__main__":
    bd.carregar_dados_ambientais()
    print("\\nBioAcesso disponível em http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
