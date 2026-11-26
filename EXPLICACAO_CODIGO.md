# Guia Rápido para Apresentação — `trabalho_feliz.py`

Resumo direto de cada parte do código para apresentar ao professor.

---

## Visão Geral
- **Bibliotecas usadas:** apenas `numpy` (cálculos com matrizes) e `streamlit` (interface web). Nenhuma biblioteca de Programação Linear (como `scipy` ou `pulp`) é usada.
- **Modelo resolvido:** Maximizar $Z = c^T x$, sujeito a $Ax \le b$, $x \ge 0$ e $b \ge 0$, com 2, 3 ou 4 variáveis.

---

## 1. Tolerância Numérica (linhas 1–4)
- `EPS = 1e-9`: evita erros de ponto flutuante (ex.: `-1e-16` sendo tratado como negativo no critério de parada ou na viabilidade).

---

## 2. `resolver_simplex(c, A, b)` (linhas 7–64)

### a) Validação e Montagem do Quadro Inicial (linhas 8–20)
- Verifica se todos os valores do lado direito (`b`) são $\ge 0$.
- Cria a matriz `T` de tamanho `(m + 1) x (n + m + 1)`:
  - **Linha 0 (função objetivo):** `[-c1, ..., -cn, 0, ..., 0 | 0]`
  - **Linhas 1..m (restrições):** `[A | I | b]`, onde `I` é a identidade das variáveis de folga (`F1..Fm`).
- `base` guarda os índices das variáveis básicas atuais (começa com as folgas `F1..Fm`).

### b) Iterações do Simplex Tableau (linhas 22–38)
Repete até no máximo 200 iterações:
1. **Quem entra na base:** coluna `col` com o menor valor na linha `Z` (`argmin`). Se `T[0, col] >= 0`, chegou na solução ótima e sai do loop.
2. **Quem sai na base (teste da razão):** para cada linha com coeficiente positivo na coluna pivô (`T[i, col] > 0`), calcula `LD / T[i, col]` e escolhe a menor razão.
   - Se nenhum coeficiente for positivo, o problema é **ilimitado** (lança `ValueError`).
3. **Pivoteamento (Gauss-Jordan):**
   - Divide a linha pivô pelo elemento pivô (vira `1`).
   - Zera os demais elementos da coluna pivô nas outras linhas (inclusive na linha `Z`).
   - Atualiza `base[lin - 1] = col`.
4. Se passar de 200 iterações sem convergir, lança erro.

### c) Extração da Solução Ótima (linhas 40–45)
Do quadro final `T`, extrai direto:
- `ld = T[1:, -1]`: valores das variáveis na base ótima.
- `b_inv = T[1:, n : n + m]`: matriz inversa da base ótima ($B^{-1}$), que fica automaticamente nas colunas das folgas `F1..Fm`.
- `precos_sombra = T[0, n : n + m]`: preços-sombra ($y^T$), que ficam na linha `Z` sob as colunas das folgas.
- `lucro = T[0, -1]`: valor ótimo $Z^*$.
- `ponto`: monta o dicionário com `X1..Xn` e `F1..Fm` (quem está fora da base vale `0`).

### d) Faixas de Viabilidade do Preço-Sombra (linhas 47–57)
Para cada restrição $j$ (variando só $\Delta b_j$):
- A base ótima continua viável enquanto $LD_i + (B^{-1})_{i,j} \cdot \Delta b_j \ge 0$ para todo $i$.
- Se $(B^{-1})_{i,j} > 0$, gera um limite inferior para $\Delta b_j$ (`d_min = max(..., -ld[i] / a)`).
- Se $(B^{-1})_{i,j} < 0$, gera um limite superior para $\Delta b_j$ (`d_max = min(..., -ld[i] / a)`).
- Também calcula `LD Min = b[j] + d_min` e `LD Max = b[j] + d_max`.

---

## 3. `analisar_alteracoes(sol, deltas)` (linhas 67–76)
> **Requisito do enunciado (o professor 100% vai perguntar isso):**  
> *"Ao fornecer as novas condições [alterações no lado direito das restrições], a análise deve ser feita apenas com base no preço-sombra e nas faixas de viabilidade."*

O código **NÃO chama `resolver_simplex` novamente** ao analisar alterações no lado direito ($\Delta b$). Ele usa somente os resultados já salvos da solução ótima em `st.session_state["sol"]` (preços-sombra, $B^{-1}$ que define as faixas de viabilidade, `ld` e `lucro`):
1. **Teste de viabilidade (faixas de viabilidade):** `ld_novo = sol["ld"] + sol["b_inv"] @ deltas` e `viavel = all(ld_novo >= -EPS)`.
   - Para uma única restrição alterada ($\Delta b_j$), checar $LD + B^{-1}\Delta b \ge 0$ é **matematicamente idêntico** a verificar se $\Delta b_j$ está dentro da faixa $[\Delta\text{ Min}_j,\ \Delta\text{ Max}_j]$ (já que essas faixas foram calculadas justamente a partir de $LD_i + (B^{-1})_{i,j}\Delta b_j \ge 0$).
   - Para várias restrições alteradas ao mesmo tempo, essa mesma conta já faz o teste exato de viabilidade simultânea.
   - Se algum valor de `ld_novo` ficar negativo, a alteração saiu da faixa de viabilidade → a base ótima atual não vale mais (**INVIÁVEL**).
2. **Novo lucro (preço-sombra):** `novo_lucro = sol["lucro"] + sol["precos_sombra"] @ deltas` → $Z_{novo} = Z^* + \sum y_j \cdot \Delta b_j$, usando apenas o preço-sombra de cada restrição.
3. **Novo ponto ótimo:** atualiza `novo_ponto` com os valores de `ld_novo` nas variáveis da base ótima atual (sem refazer nenhum pivoteamento).

---

## 4. `fmt(v)` (linhas 79–84)
Função auxiliar de formatação: converte infinito em `+inf`/`-inf`, evita exibir `-0.00` e arredonda para 2 casas decimais.

---

## 5. Interface Streamlit (linhas 87–177)
- **Entradas (linhas 91–108):** seletor de variáveis (2, 3 ou 4), número de restrições (1 a 6), coeficientes da FO, coeficientes das restrições, LD e `Δb` inicial opcional.
- **Limpeza de estado (linhas 110–112):** se o usuário mudar o número de variáveis ou restrições, apaga a solução anterior do `st.session_state` para não misturar dimensões.
- **Botão "Resolver Simplex" (linhas 114–123):** chama `resolver_simplex`, salva em `st.session_state["sol"]` e, se algum `Δb` inicial foi preenchido, já roda `analisar_alteracoes`.
- **Exibição dos resultados (linhas 125–155):** mostra ponto ótimo, lucro ótimo, Quadro Simplex Ótimo e tabela com preços-sombra e faixas (`Δ Min`, `Δ Max`, `LD Min`, `LD Max`).
- **Alterações sucessivas (linhas 157–177):** campos para novos `Δb` e botão `"Analisar Alterações"`, que chama **apenas** `analisar_alteracoes` usando a solução salva em `st.session_state["sol"]`. Mostra os novos valores da base e se a alteração é **VIÁVEL** (com novo lucro e novo ponto) ou **INVIÁVEL** (quando alguma variável básica fica negativa).

---

## Possíveis Perguntas do Professor (cola rápida)

1. **Onde está o preço-sombra no quadro Simplex?**
   Na linha `Z` (linha 0) do quadro ótimo, nas colunas das variáveis de folga (`F1..Fm`).
2. **Onde está a matriz $B^{-1}$?**
   Nas linhas das restrições (linhas `1..m`) do quadro ótimo, também sob as colunas das variáveis de folga (`F1..Fm`), porque elas começaram como a matriz identidade $I$.
3. **Como o programa testa novas alterações sem recalcular o Simplex?**
   A solução ótima (`ld`, `b_inv`, `precos_sombra`, `lucro`) fica salva no `st.session_state`. Nas novas alterações, só fazemos $LD_{novo} = LD + B^{-1}\Delta b$ e $Z_{novo} = Z^* + y^T\Delta b$.
4. **Quando uma alteração é inviável?**
   Quando pelo menos um valor em $LD_{novo}$ fica menor que zero (uma variável básica ficaria negativa, significando que a base ótima atual não serve mais).
5. **E se eu alterar mais de uma restrição ao mesmo tempo?**
   A fórmula matricial $LD + B^{-1}\Delta b \ge 0$ já trata alterações simultâneas automaticamente (equivalente à regra dos 100%, só que exata).
