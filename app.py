from scipy.optimize import linprog
import streamlit as st
import numpy as np


# Funções de cálculo
def resolver_ppl(c, A, b, maximizar=True) -> tuple:
    """Resolve  max/min c·x  sujeito a  A·x <= b ,  x >= 0.

    O scipy só sabe MINIMIZAR, então para maximizar usamos -c. Retorna o
    resultado bruto do linprog e o valor da função objetivo com o sinal correto.
    """
    coef = [-ci for ci in c] if maximizar else list(c)
    res = linprog(c=coef, A_ub=A, b_ub=b, bounds=[(0, None)] * len(c), method="highs")

    if not res.success:
        return None, None

    valor = -res.fun if maximizar else res.fun
    return res, valor


def calcular_precos_sombra(res, maximizar) -> list:
    """Preço-sombra de cada restrição = valor dual (res.ineqlin.marginals).

    O scipy devolve o dual negativo para problemas de minimização; ajustamos o
    sinal para interpretar como "quanto Z melhora ao aumentar b em 1 unidade".
    """
    duais = res.ineqlin.marginals
    return [-d if maximizar else d for d in duais]



# Funções de exibição (cada uma desenha uma parte do resultado na tela)
def mostrar_ponto_otimo(res, valor, n_var) -> None:
    """Mostra o valor ótimo de cada variável e do Z."""
    st.subheader("Ponto ótimo de operação")
    colunas = st.columns(n_var + 1)
    for j in range(n_var):
        colunas[j].metric(f"x{j+1}", f"{res.x[j]:.2f}")
    colunas[n_var].metric("Z ótimo", f"{valor:.2f}")


def mostrar_precos_sombra(res, A, b, precos_sombra, n_rest) -> None:
    """Mostra o preço-sombra de cada restrição e se ela está ativa ou com folga."""
    st.subheader("Preço-sombra das restrições")
    for i in range(n_rest):
        folga = b[i] - A[i] @ res.x
        ativa = abs(folga) < 1e-6
        situacao = "ativa / recurso esgotado" if ativa else f"folga = {folga:.2f}"
        st.write(f"**Restrição {i+1}** -> preço-sombra = **{precos_sombra[i]:.2f}**  ({situacao})")


def analisar_variacoes(c, A, b, variacoes, precos_sombra, valor, maximizar, n_var, n_rest) -> None:
    """Aplica as variações Δb, verifica se são viáveis e checa o limite de validade.

    Compara o Z recalculado com a estimativa pelo preço-sombra: se forem iguais, a
    variação está dentro do limite de validade; se divergirem, a base ótima mudou.
    """
    st.subheader("Análise das variações Δb")

    if not any(abs(v) > 1e-9 for v in variacoes):
        st.info("Nenhuma variação Δb. Preencha os campos 'Δb desejado' nas restrições.")
        return

    b_novo = b + np.array(variacoes, dtype=float)
    res2, valor2 = resolver_ppl(c, A, b_novo, maximizar)

    if res2 is None:
        st.error("As variações deixam o problema inviável.")
        return

    delta_estimado = sum(precos_sombra[i] * variacoes[i] for i in range(n_rest))
    st.success("Variações viáveis.")

    colunas = st.columns(2)
    colunas[0].metric("Novo Z ótimo (recalculado)", f"{valor2:.2f}", delta=f"{valor2 - valor:+.2f}")
    colunas[1].metric("ΔZ estimado pelo preço-sombra", f"{delta_estimado:+.2f}")

    st.caption("Se o 'novo Z recalculado' bate com a estimativa pelo preço-sombra, a variação está dentro do limite de validade do preço-sombra. Se divergir, a base ótima mudou e o preço-sombra deixou de valer.")

    with st.expander("Ver novo ponto ótimo"):
        for j in range(n_var):
            st.write(f"x{j+1} = {res2.x[j]:.2f}")



# Funções de entrada de dados (montam o formulário e devolvem os valores)
def ler_funcao_objetivo(n_var, maximizar) -> list:
    """Lê os coeficientes da função objetivo e devolve a lista c."""
    st.subheader("Função objetivo")
    st.write(f"{'Max' if maximizar else 'Min'}  Z = c1·x1 + c2·x2 + ...")
    colunas = st.columns(n_var)
    return [colunas[j].number_input(f"c{j+1} (x{j+1})", value=1.0, key=f"c{j}") for j in range(n_var)]


def ler_restricoes(n_var, n_rest) -> tuple:
    """Lê a matriz A, o vetor b e as variações Δb desejadas em cada restrição."""
    
    st.subheader("Restrições  (formato  <= )")
    
    A, b, variacoes = [], [], []
    for i in range(n_rest):
        st.markdown(f"**Restrição {i+1}**")
        colunas = st.columns(n_var + 2)
        linha = [colunas[j].number_input(f"a{i+1}{j+1}", value=1.0, key=f"a{i}{j}") for j in range(n_var)]
        bi = colunas[n_var].number_input(f"<=  b{i+1}", value=10.0, key=f"b{i}")
        dv = colunas[n_var + 1].number_input(f"Δb{i+1} desejado", value=0.0, key=f"d{i}")
        A.append(linha)
        b.append(bi)
        variacoes.append(dv)
    
    return A, b, variacoes


# Main feliz
st.set_page_config(page_title="Resolvedor de PPL - M210")
st.title("Resolvedor Feliz")

col1, col2 = st.columns(2)
n_var = col1.selectbox("Número de variáveis", [2, 3, 4], index=0)
n_rest = int(col2.number_input("Número de restrições", min_value=1, max_value=6, value=2))

objetivo = st.radio("Objetivo", ["Maximizar", "Minimizar"], horizontal=True)
maximizar = objetivo == "Maximizar"

st.divider()

c = ler_funcao_objetivo(n_var, maximizar)

st.divider()

A, b, variacoes = ler_restricoes(n_var, n_rest)

st.divider()

if st.button("Resolver", type="primary", use_container_width=True):
    A_np = np.array(A, dtype=float)
    b_np = np.array(b, dtype=float)

    res, valor = resolver_ppl(c, A_np, b_np, maximizar)

    if res is None:
        st.error("O problema não tem solução viável (ou é ilimitado).")
        st.stop()

    precos_sombra = calcular_precos_sombra(res, maximizar)

    mostrar_ponto_otimo(res, valor, n_var)
    mostrar_precos_sombra(res, A_np, b_np, precos_sombra, n_rest)
    analisar_variacoes(c, A_np, b_np, variacoes, precos_sombra, valor, maximizar, n_var, n_rest)
