# BioAcesso — Identificação Biométrica Facial (1:N)

Protótipo acadêmico local para demonstrar um fluxo de identificação facial 1:N. A interface foi construída com Streamlit e os módulos originais de processamento foram mantidos.

## Executar

```bash
pip install -r requirements.txt
python preparar_demo.py  # opcional: prepara uma base demonstrativa
streamlit run app.py
```

O navegador abrirá a interface do BioAcesso. Para iniciar, cadastre perfis fictícios com imagens de referência autorizadas. Recomenda-se utilizar pelo menos 3 imagens por perfil.

## Recursos da interface

- Visão geral com indicadores da base local.
- Identificação por imagem enviada ou câmera.
- Cadastro de perfis e imagens de referência.
- Consulta e busca de pessoas cadastradas.
- Avaliação e calibração do limiar.

## Pipeline técnico

1. Aquisição, redimensionamento e conversão para escala de cinza.
2. Pré-processamento com filtro Gaussiano e CLAHE.
3. Detecção facial com Haar Cascade.
4. Extração de características LBP uniforme em grade 8×8.
5. Comparação por distância qui-quadrado e decisão pelo limiar configurado.

## Observação importante

Este projeto é exclusivamente demonstrativo e acadêmico. Os dados ambientais e os perfis são fictícios. O reconhecimento facial pode falhar e não deve ser utilizado para autenticação, vigilância, concessão de acesso ou qualquer decisão real sobre pessoas.
