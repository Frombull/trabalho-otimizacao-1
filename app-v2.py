import numpy as np
import pandas as pd
from scipy.optimize import linprog
import streamlit as st

EPS = 1e-9


def fmt(v: float) -> str:
    """Formata número para exibição (trata infinito e evita -0.00)."""
    if np.isinf(v):
        return "+inf" if v > 0 else "-inf"
    return f"{0.0 if abs(v) < EPS else v:.2f}"


def _extrair_base(M: np.ndarray, valores: np.ndarray, custos_red: np.ndarray) -> list[int]:
    """Escolhe m colunas linearmente independentes que formam a base ótima."""
    # Prioriza variáveis positivas (> 0) e depois as de menor custo reduzido (caso degenerado)
    ordem = sorted(range(M.shape[1]), key=lambda j: (valores[j] <= EPS, abs(custos_red[j])))
    base: list[int] = []
    for col in ordem:
        if np.linalg.matrix_rank(M[:, base + [col]]) == len(base) + 1:
            base.append(col)
            if len(base) == M.shape[0]:
                return base
    raise ValueError("Não foi possível montar uma base ótima inversível (há restrições redundantes?).")


def resolver_ppl(c, A, b, maximizar: bool = True) -> dict:
    """Resolve Max/Min Z = c·x (A·x <= b, x >= 0) via SciPy e monta o Quadro Simplex Ótimo."""
    c_arr, A_arr, b_arr = np.array(c, float), np.array(A, float), np.array(b, float)
    n, m = len(c_arr), len(b_arr)

    # SciPy só minimiza: para maximizar usamos -c
    res = linprog(c=-c_arr if maximizar else c_arr, A_ub=A_arr, b_ub=b_arr, bounds=(0, None), method="highs")
    if not res.success:
        erros = {2: "Problema inviável (sem solução).", 3: "Problema ilimitado."}
        raise ValueError(erros.get(res.status, f"Erro ao resolver: {res.message}"))

    z_otimo = float(-res.fun if maximizar else res.fun)
    duais = np.array(res.ineqlin.marginals, float)
    precos_sombra = -duais if maximizar else duais

    # Forma padrão [A | I] · [x, S] = b
    nomes = [f"x{j + 1}" for j in range(n)] + [f"S{i + 1}" for i in range(m)]
    M = np.hstack([A_arr, np.eye(m)])
    c_full = np.concatenate([c_arr, np.zeros(m)])
    valores = np.concatenate([res.x, res.slack])
    custos_red = np.concatenate([res.lower.marginals, -duais])

    # Base ótima, B^-1 e Quadro Simplex Ótimo (linha Z embaixo)
    base = _extrair_base(M, valores, custos_red)
    b_inv = np.linalg.inv(M[:, base])
    ld = b_inv @ b_arr
    corpo = b_inv @ M
    linha_z = c_full[base] @ corpo - c_full

    tabela = np.vstack([np.hstack([corpo, ld[:, None]]), np.append(linha_z, z_otimo)])
    quadro = pd.DataFrame(tabela, columns=nomes + ["LD"]).map(fmt)
    quadro.insert(0, "VB", [nomes[i] for i in base] + ["Z"])

    # Faixas de viabilidade do preço-sombra (LD + B^-1·Δb >= 0)
    faixas = []
    for j in range(m):
        col = b_inv[:, j]
        d_min = max((-ld[i] / a for i, a in enumerate(col) if a > EPS), default=-np.inf)
        d_max = min((-ld[i] / a for i, a in enumerate(col) if a < -EPS), default=np.inf)
        faixas.append({
            "Restrição": f"R{j + 1}", "LD Atual": fmt(b_arr[j]),
            "Preço-Sombra": fmt(precos_sombra[j]),
            "Δ Min": fmt(d_min), "Δ Max": fmt(d_max),
            "LD Min": fmt(b_arr[j] + d_min), "LD Max": fmt(b_arr[j] + d_max),
        })

    return {
        "cfg": (n, m, maximizar), "nomes": nomes, "base": base,
        "quadro": quadro, "faixas": pd.DataFrame(faixas),
        "ld": ld, "b_inv": b_inv, "precos_sombra": precos_sombra,
        "z_otimo": z_otimo, "x": res.x,
    }


def analisar_alteracoes(sol: dict, deltas: list[float]):
    """Analisa Δb usando APENAS B^-1, LD ótimo e preços-sombra (sem recalcular o Simplex)."""
    d = np.array(deltas, float)
    ld_novo = sol["ld"] + sol["b_inv"] @ d
    viavel = bool(np.all(ld_novo >= -EPS))
    novo_z = sol["z_otimo"] + float(sol["precos_sombra"] @ d)
    novo_ponto = {sol["nomes"][idx]: float(val) for idx, val in zip(sol["base"], ld_novo)}

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
    A.append([cols[j].number_input(f"R{i + 1} x{j + 1}", value=0.0, key=f"a_{i}_{j}") for j in range(n_vars)])
    b.append(cols[n_vars].number_input(f"LD {i + 1}", value=0.0, key=f"b_{i}"))
    deltas_ini.append(cols[n_vars + 1].number_input(f"Δb{i + 1}", value=0.0, key=f"di_{i}"))

if "sol" in st.session_state and st.session_state["sol"]["cfg"] != (n_vars, n_restr, maximizar):
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
    n, m, is_max = sol["cfg"]

    st.divider()
    st.subheader("Resultado Ótimo")
    cols_res = st.columns(n + 1)
    for j in range(n):
        cols_res[j].metric(f"x{j + 1}", fmt(sol["x"][j]))
    cols_res[n].metric("Lucro ótimo (Z*)" if is_max else "Valor ótimo (Z*)", fmt(sol["z_otimo"]))

    st.write("**Quadro Simplex Ótimo**")
    st.dataframe(sol["quadro"], hide_index=True, use_container_width=True)

    st.write("**Preços-Sombra e Faixas de Viabilidade**")
    st.dataframe(sol["faixas"], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Novas Alterações no Lado Direito (Sem Recalcular Simplex)")
    cols_d = st.columns(m)
    deltas = [cols_d[j].number_input(f"Novo Δb{j + 1}", value=0.0, key=f"d_{j}") for j in range(m)]

    if st.button("Analisar Alterações"):
        st.session_state["analise"] = (deltas, *analisar_alteracoes(sol, deltas))

    if "analise" in st.session_state:
        deltas_usados, viavel, tabela_base, novo_z, novo_ponto = st.session_state["analise"]
        st.write(f"**Alterações:** {', '.join(f'Δb{j + 1} = {fmt(deltas_usados[j])}' for j in range(m))}")
        st.dataframe(tabela_base, hide_index=True, use_container_width=True)

        if viavel:
            ponto_str = ", ".join(f"x{j + 1} = {fmt(novo_ponto.get(f'x{j + 1}', 0.0))}" for j in range(n))
            st.success(f"Alterações VIÁVEIS. Novo {'lucro' if is_max else 'valor'} ótimo: {fmt(novo_z)} | Novo ponto: {ponto_str}")
        else:
            st.error("Alterações INVIÁVEIS para a base ótima atual: pelo menos uma variável básica ficou negativa.")
