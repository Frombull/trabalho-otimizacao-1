from scipy.optimize import linprog
import streamlit as st
import numpy as np


# Resolve o PPL
def resolver_ppl(c, A, b, maximizar=True):
    """
    Resolve  max (ou min)  c·x
             sujeito a      A·x <= b ,  x >= 0

    O scipy só sabe MINIMIZAR, então para maximizar usamos -c.
    Retorna o resultado bruto do linprog e o valor da função objetivo
    já com o sinal correto.
    """
    coef = [-ci for ci in c] if maximizar else list(c)

    res = linprog(
        c=coef,
        A_ub=A,
        b_ub=b,
        bounds=[(0, None)] * len(c),   # todas as variáveis >= 0
        method="highs",                # método Simplex/PL do scipy
    )

    if not res.success:
        return None, None

    valor = -res.fun if maximizar else res.fun
    return res, valor


# Interface
st.set_page_config(page_title="Resolvedor de PPL - M210", page_icon="📈")

st.title("Resolvedor Feliz")

# --- Escolhas básicas ---
col1, col2 = st.columns(2)
with col1:
    n_var = st.selectbox("Número de variáveis", [2, 3, 4], index=0)
with col2:
    n_rest = st.number_input("Número de restrições", min_value=1, max_value=6, value=2)

objetivo = st.radio("Objetivo", ["Maximizar", "Minimizar"], horizontal=True)
maximizar = objetivo == "Maximizar"

st.divider()

# --- Função objetivo ---
st.subheader("Função objetivo")
st.write(f"{'Max' if maximizar else 'Min'}  Z = c₁·x₁ + c₂·x₂ + ...")
cols = st.columns(n_var)
c = []
for j in range(n_var):
    with cols[j]:
        c.append(st.number_input(f"c{j+1} (x{j+1})", value=1.0, key=f"c{j}"))

st.divider()

# --- Restrições ---
st.subheader("Restrições  (formato  ≤  )")

A = []
b = []
variacoes = []
for i in range(int(n_rest)):
    st.markdown(f"**Restrição {i+1}**")
    cols = st.columns(n_var + 2)
    linha = []
    for j in range(n_var):
        with cols[j]:
            linha.append(st.number_input(f"a{i+1}{j+1}", value=1.0, key=f"a{i}{j}"))
    with cols[n_var]:
        bi = st.number_input(f"≤  b{i+1}", value=10.0, key=f"b{i}")
    with cols[n_var + 1]:
        # variação desejada em b (Δb) para a análise de sensibilidade
        dv = st.number_input(f"Δb{i+1} desejado", value=0.0, key=f"d{i}")
    A.append(linha)
    b.append(bi)
    variacoes.append(dv)

st.divider()

# Botão resolver
if st.button("Resolver", type="primary", use_container_width=True):

    A_np = np.array(A, dtype=float)
    b_np = np.array(b, dtype=float)

    res, valor = resolver_ppl(c, A_np, b_np, maximizar)

    if res is None:
        st.error("O problema não tem solução viável (ou é ilimitado).")
        st.stop()

    # ---------- Ponto ótimo ----------
    st.subheader("✅ Ponto ótimo de operação")
    pcols = st.columns(n_var + 1)
    for j in range(n_var):
        pcols[j].metric(f"x{j+1}", f"{res.x[j]:.2f}")
    pcols[n_var].metric("Z ótimo", f"{valor:.2f}")

    # ---------- Preço-sombra ----------
    # O preço-sombra é o valor dual de cada restrição.
    # No scipy fica em res.ineqlin.marginals (vem negativo para problema de min;
    # ajustamos o sinal para interpretar como "quanto Z melhora por +1 em b").
    st.subheader("Preço-sombra das restrições")
    duais = res.ineqlin.marginals
    precos_sombra = [-d if maximizar else d for d in duais]

    for i in range(int(n_rest)):
        folga = b_np[i] - A_np[i] @ res.x
        ativa = abs(folga) < 1e-6
        st.write(
            f"**Restrição {i+1}** → preço-sombra = **{precos_sombra[i]:.2f}**  "
            f"({'ativa / recurso esgotado' if ativa else f'folga = {folga:.2f}'})"
        )

    # ---------- Análise das variações desejadas ----------
    st.subheader("Análise das variações Δb")

    tem_variacao = any(abs(v) > 1e-9 for v in variacoes)
    if not tem_variacao:
        st.info("Nenhuma variação Δb. Preencha os campos 'Δb desejado' "
                "nas restrições para ver a análise de sensibilidade.")
    else:
        # Aplica as variações e re-resolve para checar viabilidade
        b_novo = b_np + np.array(variacoes, dtype=float)
        res2, valor2 = resolver_ppl(c, A_np, b_novo, maximizar)

        if res2 is None:
            st.error("As variações desejadas tornam o problema inviável.")
        else:
            # Estimativa pelo preço-sombra: ΔZ ≈ Σ (preço-sombra · Δb)
            delta_estimado = sum(precos_sombra[i] * variacoes[i]
                                 for i in range(int(n_rest)))
            st.success("As variações desejadas são viáveis.")

            ccols = st.columns(2)
            ccols[0].metric("Novo Z ótimo (recalculado)", f"{valor2:.2f}",
                            delta=f"{valor2 - valor:+.2f}")
            ccols[1].metric("ΔZ estimado pelo preço-sombra", f"{delta_estimado:+.2f}")

            st.caption(
                "Se o 'novo Z recalculado' bate com a estimativa pelo preço-sombra, "
                "a variação está **dentro do limite de validade** do preço-sombra. "
                "Se divergir, a base ótima mudou e o preço-sombra deixou de valer."
            )

            # Mostra o novo ponto ótimo
            with st.expander("Ver novo ponto ótimo"):
                for j in range(n_var):
                    st.write(f"x{j+1} = {res2.x[j]:.2f}")
