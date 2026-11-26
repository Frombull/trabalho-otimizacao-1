import numpy as np
import pandas as pd
from scipy.optimize import linprog
import streamlit as st

EPS = 1e-9


def fmt(v: float) -> str:
    """Formata números para exibição (trata infinito e -0.00)."""
    if np.isposinf(v):
        return "+inf"
    if np.isneginf(v):
        return "-inf"
    return f"{0.0 if abs(v) < EPS else v:.2f}"


def _extrair_base(M: np.ndarray, valores: np.ndarray, custos_red: np.ndarray) -> list[int]:
    """Escolhe m colunas linearmente independentes que formam a base ótima."""
    n_restr, n_total = M.shape
    candidatos = [j for j in range(n_total) if valores[j] > EPS]
    candidatos += [j for j in range(n_total) if j not in candidatos and abs(custos_red[j]) <= 1e-6]
    candidatos += [j for j in range(n_total) if j not in candidatos]

    base: list[int] = []
    for col in candidatos:
        if np.linalg.matrix_rank(M[:, base + [col]]) == len(base) + 1:
            base.append(col)
            if len(base) == n_restr:
                return base
    raise ValueError("Não foi possível montar uma base ótima inversível (verifique se há restrições redundantes).")


def resolver_ppl(c, A, b, maximizar: bool = True) -> dict:
    """Resolve Max/Min Z = c·x sujeito a A·x <= b, x >= 0 via SciPy,
    e reconstrói o Quadro Simplex Ótimo (com Z embaixo), B^-1, preços-sombra e faixas de viabilidade.
    """
    c_arr, A_arr, b_arr = np.array(c, float), np.array(A, float), np.array(b, float)
    n_vars, n_restr = len(c_arr), len(b_arr)

    # SciPy só minimiza: para maximizar usamos -c
    res = linprog(c=-c_arr if maximizar else c_arr, A_ub=A_arr, b_ub=b_arr, bounds=(0, None), method="highs")
    if res.status == 2:
        raise ValueError("Problema inviável (nenhum ponto satisfaz todas as restrições).")
    if res.status == 3:
        raise ValueError("Problema ilimitado (sem solução ótima finita).")
    if not res.success:
        raise ValueError(f"Erro ao resolver: {res.message}")

    z_otimo = float(-res.fun if maximizar else res.fun)
    duais = np.array(res.ineqlin.marginals, float)
    precos_sombra = -duais if maximizar else duais

    # Forma padrão [A | I] · [x, S] = b
    nomes = [f"x{j + 1}" for j in range(n_vars)] + [f"S{i + 1}" for i in range(n_restr)]
    M = np.hstack([A_arr, np.eye(n_restr)])
    c_full = np.concatenate([c_arr, np.zeros(n_restr)])
    valores = np.concatenate([res.x, res.slack])
    custos_red = np.concatenate([res.lower.marginals, -duais])

    # Base ótima, B^-1 e Quadro Simplex Ótimo (com linha Z sempre embaixo)
    base = _extrair_base(M, valores, custos_red)
    b_inv = np.linalg.inv(M[:, base])
    ld = b_inv @ b_arr
    corpo = b_inv @ M
    linha_z = c_full[base] @ corpo - c_full

    tabela = np.vstack([np.hstack([corpo, ld[:, None]]), np.append(linha_z, z_otimo)])
    quadro = pd.DataFrame(tabela, columns=nomes + ["LD"])
    quadro.insert(0, "VB", [nomes[idx] for idx in base] + ["Z"])
    for col in nomes + ["LD"]:
        quadro[col] = quadro[col].map(fmt)

    # Faixas de viabilidade do preço-sombra para cada restrição
    faixas = []
    for j in range(n_restr):
        d_min, d_max = -np.inf, np.inf
        for i in range(n_restr):
            a = b_inv[i, j]
            if a > EPS:
                d_min = max(d_min, -ld[i] / a)
            elif a < -EPS:
                d_max = min(d_max, -ld[i] / a)
        faixas.append({
            "Restrição": f"R{j + 1}",
            "LD Atual": fmt(b_arr[j]),
            "Preço-Sombra": fmt(precos_sombra[j]),
            "Δ Min": fmt(d_min),
            "Δ Max": fmt(d_max),
            "LD Min": fmt(b_arr[j] + d_min),
            "LD Max": fmt(b_arr[j] + d_max),
        })

    return {
        "maximizar": maximizar, "n_vars": n_vars, "n_restr": n_restr,
        "nomes": nomes, "base": base, "quadro": quadro, "ld": ld, "b_inv": b_inv,
        "precos_sombra": precos_sombra, "z_otimo": z_otimo,
        "ponto": {nome: float(val) for nome, val in zip(nomes, valores)},
        "faixas": pd.DataFrame(faixas),
    }


def analisar_alteracoes(sol: dict, deltas: list[float]):
    """Analisa alterações Δb usando APENAS B^-1, LD ótimo e preços-sombra (sem recalcular o PPL)."""
    d = np.array(deltas, float)
    ld_novo = sol["ld"] + sol["b_inv"] @ d
    viavel = bool(np.all(ld_novo >= -EPS))
    novo_z = sol["z_otimo"] + float(sol["precos_sombra"] @ d)

    novo_ponto = {nome: 0.0 for nome in sol["nomes"]}
    for i, idx in enumerate(sol["base"]):
        novo_ponto[sol["nomes"][idx]] = float(ld_novo[i])

    tabela_base = pd.DataFrame({
        "Variável Básica": [sol["nomes"][idx] for idx in sol["base"]],
        "Novo Valor": [fmt(v) for v in ld_novo],
        "Status": ["OK" if v >= -EPS else "Inviável (< 0)" for v in ld_novo],
    })
    return viavel, tabela_base, novo_z, novo_ponto


# --- Interface Streamlit ---
st.set_page_config(page_title="M210 - Simplex Tableau (v2)", layout="centered")
st.title("Simplex Tableau - M210")

c1, c2, c3 = st.columns(3)
n_vars = c1.selectbox("Número de variáveis", [2, 3, 4], index=0)
n_restr = int(c2.number_input("Número de restrições", min_value=1, max_value=6, value=3, step=1))
objetivo = c3.radio("Objetivo", ["Maximizar", "Minimizar"], horizontal=True)
maximizar = objetivo == "Maximizar"

st.subheader(f"Função Objetivo ({objetivo} Z)")
cols_z = st.columns(n_vars)
c = [cols_z[j].number_input(f"c{j + 1} (x{j + 1})", value=0.0, key=f"c_{j}") for j in range(n_vars)]

st.subheader("Restrições (<=) e Variações Iniciais (Δb)")
A, b, deltas_ini = [], [], []
for i in range(n_restr):
    cols = st.columns(n_vars + 2)
    linha = [cols[j].number_input(f"R{i + 1} x{j + 1}", value=0.0, key=f"a_{i}_{j}") for j in range(n_vars)]
    bi = cols[n_vars].number_input(f"LD {i + 1}", value=0.0, key=f"b_{i}")
    di = cols[n_vars + 1].number_input(f"Δb{i + 1}", value=0.0, key=f"di_{i}")
    A.append(linha); b.append(bi); deltas_ini.append(di)

if "sol" in st.session_state:
    s_ant = st.session_state["sol"]
    if s_ant["n_vars"] != n_vars or s_ant["n_restr"] != n_restr or s_ant["maximizar"] != maximizar:
        st.session_state.pop("sol", None)
        st.session_state.pop("analise", None)

if st.button("Resolver Simplex", type="primary", use_container_width=True):
    try:
        sol = resolver_ppl(c, A, b, maximizar=maximizar)
        st.session_state["sol"] = sol
        if any(abs(d) > EPS for d in deltas_ini):
            st.session_state["analise"] = (deltas_ini, *analisar_alteracoes(sol, deltas_ini))
        else:
            st.session_state.pop("analise", None)
    except ValueError as err:
        st.error(str(err))

if "sol" in st.session_state:
    sol = st.session_state["sol"]
    st.divider()
    st.subheader("Resultado Ótimo")

    cols_res = st.columns(sol["n_vars"] + 1)
    for j in range(sol["n_vars"]):
        cols_res[j].metric(f"x{j + 1}", fmt(sol["ponto"][f"x{j + 1}"]))
    cols_res[sol["n_vars"]].metric("Lucro ótimo (Z*)" if sol["maximizar"] else "Valor ótimo (Z*)", fmt(sol["z_otimo"]))

    st.write("**Quadro Simplex Ótimo**")
    st.dataframe(sol["quadro"], hide_index=True, use_container_width=True)

    st.write("**Preços-Sombra e Faixas de Viabilidade**")
    st.dataframe(sol["faixas"], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Novas Alterações no Lado Direito (Sem Recalcular Simplex)")
    cols_d = st.columns(sol["n_restr"])
    deltas = [cols_d[j].number_input(f"Novo Δb{j + 1}", value=0.0, key=f"d_{j}") for j in range(sol["n_restr"])]

    if st.button("Analisar Alterações"):
        st.session_state["analise"] = (deltas, *analisar_alteracoes(sol, deltas))

    if "analise" in st.session_state:
        deltas_usados, viavel, tabela_base, novo_z, novo_ponto = st.session_state["analise"]
        st.write(f"**Alterações analisadas:** {', '.join(f'Δb{j + 1} = {fmt(deltas_usados[j])}' for j in range(sol['n_restr']))}")
        st.write("**Novos valores das variáveis básicas (LD + B⁻¹·Δb):**")
        st.dataframe(tabela_base, hide_index=True, use_container_width=True)

        if viavel:
            ponto_str = ", ".join(f"x{j + 1} = {fmt(novo_ponto[f'x{j + 1}'])}" for j in range(sol["n_vars"]))
            rotulo = "Novo lucro ótimo" if sol["maximizar"] else "Novo valor ótimo (Z)"
            st.success(f"Alterações VIÁVEIS. {rotulo}: {fmt(novo_z)} | Novo ponto ótimo: {ponto_str}")
        else:
            st.error("Alterações INVIÁVEIS para a base ótima atual: pelo menos uma variável básica ficou negativa.")
