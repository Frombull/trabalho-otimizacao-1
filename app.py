import numpy as np
import streamlit as st

EPS = 1e-9


def resolver_simplex(c, A, b):
    n, m = len(c), len(b)
    if any(bi < -EPS for bi in b):
        raise ValueError("Todos os valores do lado direito (LD) devem ser >= 0.")

    # Quadro inicial: linha 0 = Z, linhas 1..m = restrições, colunas = [X1..Xn, F1..Fm, LD]
    T = np.zeros((m + 1, n + m + 1), dtype=float)
    T[0, :n] = -np.array(c, dtype=float)
    T[1:, :n] = np.array(A, dtype=float)
    T[1:, n : n + m] = np.eye(m)
    T[1:, -1] = np.array(b, dtype=float)

    base = list(range(n, n + m))
    nomes = [f"X{i+1}" for i in range(n)] + [f"F{j+1}" for j in range(m)]

    for _ in range(200):
        col = int(np.argmin(T[0, :-1]))
        if T[0, col] >= -EPS:
            break

        ratios = [T[i, -1] / T[i, col] if T[i, col] > EPS else np.inf for i in range(1, m + 1)]
        lin = int(np.argmin(ratios)) + 1
        if np.isinf(ratios[lin - 1]):
            raise ValueError("Problema ilimitado (sem solução ótima finita).")

        T[lin] /= T[lin, col]
        for i in range(m + 1):
            if i != lin:
                T[i] -= T[i, col] * T[lin]
        base[lin - 1] = col
    else:
        raise ValueError("O Simplex não convergiu em 200 iterações.")

    ld = T[1:, -1]
    b_inv = T[1:, n : n + m]
    precos_sombra = T[0, n : n + m]
    ponto = {nome: 0.0 for nome in nomes}
    for i, idx in enumerate(base):
        ponto[nomes[idx]] = float(ld[i])

    # Faixas de viabilidade (limites de validade do preço-sombra) para cada restrição
    faixas = []
    for j in range(m):
        d_min, d_max = -np.inf, np.inf
        for i in range(m):
            a = b_inv[i, j]
            if a > EPS:
                d_min = max(d_min, -ld[i] / a)
            elif a < -EPS:
                d_max = min(d_max, -ld[i] / a)
        faixas.append((d_min, d_max, b[j] + d_min, b[j] + d_max))

    return {
        "n": n, "m": m, "nomes": nomes, "base": base, "T": T,
        "b": np.array(b, dtype=float), "ld": ld, "b_inv": b_inv,
        "precos_sombra": precos_sombra, "lucro": float(T[0, -1]),
        "ponto": ponto, "faixas": faixas,
    }


def analisar_alteracoes(sol, deltas):
    """Analisa alterações no LD usando APENAS B^-1, LD ótimo e preços-sombra (sem recalcular Simplex)."""
    deltas = np.array(deltas, dtype=float)
    ld_novo = sol["ld"] + sol["b_inv"] @ deltas
    viavel = bool(np.all(ld_novo >= -EPS))
    novo_lucro = sol["lucro"] + float(sol["precos_sombra"] @ deltas)
    novo_ponto = {nome: 0.0 for nome in sol["nomes"]}
    for i, idx in enumerate(sol["base"]):
        novo_ponto[sol["nomes"][idx]] = float(ld_novo[i])
    return viavel, ld_novo, novo_lucro, novo_ponto


def fmt(v):
    if np.isposinf(v):
        return "+inf"
    if np.isneginf(v):
        return "-inf"
    return f"{0.0 if abs(v) < EPS else v:.2f}"


# --- Interface Streamlit ---
st.set_page_config(page_title="M210 - Simplex Tableau", layout="centered")
st.title("Simplex Tableau - M210")

col1, col2 = st.columns(2)
n_vars = col1.selectbox("Número de variáveis", [2, 3, 4], index=0)
n_restr = col2.number_input("Número de restrições", min_value=1, max_value=6, value=3, step=1)

st.subheader("Função Objetivo (Maximizar Z)")
cols_z = st.columns(n_vars)
c = [cols_z[j].number_input(f"c{j+1} (X{j+1})", value=0.0, key=f"c_{j}") for j in range(n_vars)]

st.subheader("Restrições (<=) e Variações Iniciais (Δb)")
A, b, deltas_ini = [], [], []
for i in range(n_restr):
    cols = st.columns(n_vars + 2)
    linha = [cols[j].number_input(f"R{i+1} X{j+1}", value=0.0, key=f"a_{i}_{j}") for j in range(n_vars)]
    bi = cols[n_vars].number_input(f"LD {i+1}", value=0.0, min_value=0.0, key=f"b_{i}")
    di = cols[n_vars + 1].number_input(f"Δb{i+1}", value=0.0, key=f"di_{i}")
    A.append(linha)
    b.append(bi)
    deltas_ini.append(di)

if "sol" in st.session_state and (st.session_state["sol"]["n"] != n_vars or st.session_state["sol"]["m"] != n_restr):
    st.session_state.pop("sol", None)
    st.session_state.pop("analise", None)

if st.button("Resolver Simplex"):
    try:
        sol = resolver_simplex(c, A, b)
        st.session_state["sol"] = sol
        if any(abs(d) > EPS for d in deltas_ini):
            st.session_state["analise"] = (deltas_ini, *analisar_alteracoes(sol, deltas_ini))
        else:
            st.session_state.pop("analise", None)
    except ValueError as e:
        st.error(str(e))

if "sol" in st.session_state:
    sol = st.session_state["sol"]
    st.divider()
    st.subheader("Resultado Ótimo")

    ponto_str = ", ".join(f"X{j+1} = {fmt(sol['ponto'][f'X{j+1}'])}" for j in range(sol["n"]))
    st.write(f"**Ponto ótimo:** {ponto_str}")
    st.write(f"**Lucro ótimo (Z*):** {fmt(sol['lucro'])}")

    st.write("**Quadro Simplex Ótimo**")
    vbs = ["Z"] + [sol["nomes"][idx] for idx in sol["base"]]
    tabela_quadro = [
        {"VB": vbs[i], **{sol["nomes"][j]: fmt(sol["T"][i, j]) for j in range(len(sol["nomes"]))}, "LD": fmt(sol["T"][i, -1])}
        for i in range(sol["m"] + 1)
    ]
    st.table(tabela_quadro)

    st.write("**Preços-Sombra e Faixas de Viabilidade**")
    tabela_ps = [
        {
            "Restrição": f"R{j+1}",
            "LD Atual": fmt(sol["b"][j]),
            "Preço-Sombra": fmt(sol["precos_sombra"][j]),
            "Δ Min": fmt(sol["faixas"][j][0]),
            "Δ Max": fmt(sol["faixas"][j][1]),
            "LD Min": fmt(sol["faixas"][j][2]),
            "LD Max": fmt(sol["faixas"][j][3]),
        }
        for j in range(sol["m"])
    ]
    st.table(tabela_ps)

    st.divider()
    st.subheader("Novas Alterações no Lado Direito (Sem Recalcular Simplex)")
    cols_d = st.columns(sol["m"])
    deltas = [cols_d[j].number_input(f"Novo Δb{j+1}", value=0.0, key=f"d_{j}") for j in range(sol["m"])]

    if st.button("Analisar Alterações"):
        st.session_state["analise"] = (deltas, *analisar_alteracoes(sol, deltas))

    if "analise" in st.session_state:
        deltas_usados, viavel, ld_novo, novo_lucro, novo_ponto = st.session_state["analise"]
        st.write(f"**Alterações analisadas:** {', '.join(f'Δb{j+1} = {fmt(deltas_usados[j])}' for j in range(sol['m']))}")
        st.write("**Novos valores das variáveis básicas (LD + B⁻¹·Δb):**")
        st.table([
            {"Variável Básica": sol["nomes"][sol["base"][i]], "Novo Valor": fmt(ld_novo[i]), "Status": "OK" if ld_novo[i] >= -EPS else "Inviável (< 0)"}
            for i in range(sol["m"])
        ])
        if viavel:
            novo_p_str = ", ".join(f"X{j+1} = {fmt(novo_ponto[f'X{j+1}'])}" for j in range(sol["n"]))
            st.success(f"Alterações VIÁVEIS. Novo lucro ótimo: {fmt(novo_lucro)} | Novo ponto ótimo: {novo_p_str}")
        else:
            st.error("Alterações INVIÁVEIS para a base ótima atual: pelo menos uma variável básica ficou negativa.")
