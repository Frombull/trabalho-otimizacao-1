## Visão Geral
- **Bibliotecas usadas:**
  - `scipy.optimize.linprog` (solver `highs`): resolve o PPL de forma numérica robusta (o enunciado permite bibliotecas de PL).
  - `numpy`: operações matriciais ($B^{-1}$, multiplicação de matrizes, posto da matriz, faixas de viabilidade).
  - `pandas`: formatação das tabelas (Quadro Simplex Ótimo, faixas e análise de alterações).
  - `streamlit`: interface web interativa.
- **Modelo resolvido:** **Maximizar** ou **Minimizar** $Z = c^T x$, sujeito a $Ax \le b$ e $x \ge 0$, com 2, 3 ou 4 variáveis.
  - **Restrições $\ge$:** o campo `LD` aceita números negativos, então qualquer restrição $a^T x \ge b$ pode ser inserida multiplicada por $-1$ ($-a^T x \le -b$), sem precisar complicar o código com múltiplos sinais.
- **Convenções do Quadro Simplex Ótimo:**
  - Variáveis de decisão: `x1, x2, ...` e variáveis de folga: `S1, S2, ...`.
  - **Colunas fixas** na ordem original (`VB | x1 ... xn | S1 ... Sm | LD`), sem trocar nomes de colunas na pivotação.
  - **Linha `Z` sempre na parte inferior** do quadro.

---

## 1. Tolerância Numérica e Formatação (linhas 6–13)
- `EPS = 1e-9` (linha 6): tolerância para erros de ponto flutuante (ex.: `-1e-16` sendo tratado como negativo ao testar viabilidade `>= -EPS`, ou um pivô quase zero causando divisão por zero).
- `fmt(v)` (linhas 9–13): formata números com 2 casas decimais, converte infinito em `+inf`/`-inf` e evita exibir `-0.00`.

---

## 2. `_extrair_base(M, valores, custos_red)` (linhas 16–26)
O `linprog` do SciPy entrega a solução ótima (`res.x`, `res.slack`, duais), mas não devolve diretamente a lista de índices das $m$ colunas da base ótima $B$. Essa função reconstrói a base ótima a partir da forma padrão $M = [A \mid I]$:
1. **Ordenação de prioridade (linha 19):** ordena todas as $n + m$ colunas priorizando:
   - Primeiro, variáveis com valor positivo na solução ótima (`valores[j] > EPS`), pois toda variável estritamente positiva obrigatoriamente está na base.
   - Depois (para casos **degenerados**, em que alguma variável básica vale `0`), as variáveis com menor custo reduzido em módulo (`abs(custos_red[j])`), que são as candidatas a completar a base com custo reduzido zero.
2. **Independência linear (linhas 20–25):** percorre as colunas nessa ordem e só adiciona uma coluna à `base` se o posto (`np.linalg.matrix_rank`) aumentar em 1. Ao completar $m$ colunas, temos uma submatriz $B = M_{:,\text{base}}$ garantidamente quadrada e inversível.
3. Se não for possível formar $m$ colunas linearmente independentes (ex.: restrições redundantes), lança `ValueError` (linha 26).

---

## 3. `resolver_ppl(c, A, b, maximizar=True)` (linhas 29–80)

### a) Resolução via SciPy (linhas 31–42)
- Converte `c`, `A`, `b` para arrays NumPy (`float`) e extrai `n` (variáveis) e `m` (restrições).
- **Truque Max/Min (linha 35):** o `linprog` sempre minimiza.
  - Se `maximizar=True`, passamos `-c_arr` (pois $\max c^T x = -\min(-c^T x)$).
  - Se `maximizar=False`, passamos `c_arr` diretamente.
- Se `res.success` for falso (linhas 36–38), traduz o código de erro do HiGHS: status `2` = **Problema inviável**, status `3` = **Problema ilimitado**.
- **Valor ótimo e preços-sombra (linhas 40–42):**
  - `z_otimo`: inverte o sinal de `res.fun` se for maximização (`-res.fun`).
  - `duais = res.ineqlin.marginals`: derivadas do objetivo *minimizado* em relação ao lado direito $b$.
  - `precos_sombra = -duais if maximizar else duais`: ajusta o sinal para que `precos_sombra[j]` seja sempre $\frac{\partial Z^*}{\partial b_j}$ (quanto $Z^*$ varia ao aumentar $b_j$ em $+1$ unidade), tanto em Max quanto em Min.

### b) Forma Padrão e Montagem do Quadro Simplex Ótimo (linhas 44–60)
Monta a forma padrão $[A \mid I]\begin{bmatrix}x \\ S\end{bmatrix} = b$:
- `nomes`: `["x1", ..., "xn", "S1", ..., "Sm"]`.
- `M = [A | I]`, `c_full = [c | 0]`, `valores = [res.x | res.slack]`.
- `custos_red = [res.lower.marginals, -duais]`: custos reduzidos das variáveis originais e das folgas.

Com a base ótima encontrada por `_extrair_base`, calcula o **Quadro Simplex Ótimo** diretamente pela álgebra matricial do Simplex (sem precisar armazenar todos os quadros intermediários):
- `b_inv = np.linalg.inv(M[:, base])` $\rightarrow B^{-1}$
- `ld = b_inv @ b_arr` $\rightarrow$ valores das variáveis básicas ($B^{-1}b$)
- `corpo = b_inv @ M` $\rightarrow$ coeficientes das restrições no quadro ótimo ($B^{-1}[A \mid I] = [B^{-1}A \mid B^{-1}]$)
- `linha_z = c_full[base] @ corpo - c_full` $\rightarrow$ coeficientes da linha $Z$ ($c_B^T B^{-1} M - c^T$). Sob as colunas das folgas `S1..Sm`, isso resulta exatamente em $c_B^T B^{-1} = y^T$ (os preços-sombra).
- Empilha o corpo acima da linha `Z` (`np.vstack`, linha 58) para manter **`Z` na última linha**, cria o `DataFrame` com as colunas fixas `VB | x1..xn | S1..Sm | LD` e aplica `fmt`.

### c) Faixas de Viabilidade do Preço-Sombra (linhas 62–73)
Para cada restrição $j$ (variando apenas $\Delta b_j$):
- A base ótima atual continua viável enquanto todas as variáveis básicas continuarem não negativas:
  $$LD_i + (B^{-1})_{i,j} \cdot \Delta b_j \ge 0 \quad \forall i$$
- Olhando a coluna $j$ de $B^{-1}$ (`col = b_inv[:, j]`):
  - Se $a = (B^{-1})_{i,j} > 0$, obtemos $\Delta b_j \ge -LD_i / a \implies$ limite inferior `d_min = max(...)` (ou `-inf` se nenhum $a > 0$).
  - Se $a = (B^{-1})_{i,j} < 0$, obtemos $\Delta b_j \le -LD_i / a \implies$ limite superior `d_max = min(...)` (ou `+inf` se nenhum $a < 0$).
- Também calcula os limites absolutos do lado direito: `LD Min = b[j] + d_min` e `LD Max = b[j] + d_max`.

---

## 4. `analisar_alteracoes(sol, deltas)` (linhas 83–96)
> **Requisito central do trabalho (o professor com certeza vai perguntar isso):**  
> *"Ao fornecer as novas condições [alterações no lado direito das restrições], a análise deve ser feita apenas com base no preço-sombra e nas faixas de viabilidade."*

O código **NÃO chama `resolver_ppl` nem `linprog` novamente** ao analisar alterações $\Delta b$. Ele usa exclusivamente os dados salvos da solução ótima em `st.session_state["sol"]` (`ld`, `b_inv`, `precos_sombra`, `z_otimo`):
1. **Teste de viabilidade (linhas 86–87):**
   - `ld_novo = sol["ld"] + sol["b_inv"] @ d`
   - `viavel = bool(np.all(ld_novo >= -EPS))`
   - Para uma única restrição alterada ($\Delta b_j$), checar $LD + B^{-1}\Delta b \ge 0$ é **matematicamente idêntico** a verificar se $\Delta b_j \in [\Delta\text{Min}_j,\ \Delta\text{Max}_j]$.
   - Para várias restrições alteradas ao mesmo tempo, essa mesma equação matricial faz o teste exato de viabilidade simultânea (melhor que a regra dos 100%, que é apenas condição suficiente).
   - Se algum elemento de `ld_novo` ficar negativo (`< -EPS`), a alteração saiu da região de viabilidade da base ótima atual (**INVIÁVEL**).
2. **Novo valor ótimo via preço-sombra (linha 88):**
   - `novo_z = sol["z_otimo"] + float(sol["precos_sombra"] @ d)` $\rightarrow Z_{\text{novo}} = Z^* + \sum y_j \cdot \Delta b_j$.
3. **Novo ponto ótimo (linha 89):** atualiza o valor de cada variável básica com `ld_novo` (quem está fora da base continua `0`).
4. **Tabela de saída (linhas 91–96):** monta o `DataFrame` com `Variável Básica`, `Novo Valor` e `Status` (`OK` ou `Inviável (< 0)`).

---

## 5. Interface Streamlit (linhas 99–174)
- **Configuração e entradas (linhas 100–119):**
  - Seletor de número de variáveis (`2`, `3` ou `4`), número de restrições (`1` a `6`) e objetivo (`Maximizar` / `Minimizar`).
  - Campos para coeficientes da função objetivo (`c1..cn`), coeficientes das restrições (`<=`), lados direitos (`LD`) e variações iniciais opcionais (`Δb`).
- **Limpeza automática de estado (linhas 121–123):** se o usuário alterar `n_vars`, `n_restr` ou `maximizar`, limpa `sol` e `analise` do `st.session_state` para não misturar resultados de modelos diferentes.
- **Botão `"Resolver Simplex"` (linhas 125–134):** chama `resolver_ppl`, salva o resultado em `st.session_state["sol"]` e, se houver algum `Δb` inicial diferente de zero, já executa `analisar_alteracoes`. Erros de modelo (inviável, ilimitado, base redundante) aparecem via `st.error`.
- **Exibição do Resultado Ótimo (linhas 136–155):**
  - Linha 1 de cartões (`st.metric`): `x1..xn` e `Lucro ótimo (Z*)` (ou `Valor ótimo (Z*)` em minimização).
  - Linha 2 de cartões (`st.metric`): preços-sombra explícitos `PS1..PSm`.
  - Tabela do **Quadro Simplex Ótimo** (colunas fixas, linha `Z` embaixo).
  - Tabela de **Preços-Sombra e Faixas de Viabilidade** (`LD Atual`, `Preço-Sombra`, `Δ Min`, `Δ Max`, `LD Min`, `LD Max`).
- **Novas alterações sucessivas (linhas 157–174):**
  - Campos para `Novo Δb1..Δbm` e botão `"Analisar Alterações"`, que chama **apenas** `analisar_alteracoes` usando a solução salva.
  - Mostra a tabela com os novos valores da base e informa se as alterações são **VIÁVEIS** (com novo `Z` e novo ponto `x1..xn`) ou **INVIÁVEIS**.

---

## Possíveis Perguntas do Professor (cola rápida)

1. **Onde está o preço-sombra no Quadro Simplex Ótimo?**
   Na última linha (`Z`), nas colunas das variáveis de folga (`S1..Sm`). Eles também aparecem destacados logo acima como `PS1..PSm` e na tabela de faixas.
2. **Onde está a matriz $B^{-1}$ no quadro?**
   Nas linhas das restrições (linhas `0..m-1`), sob as colunas das variáveis de folga (`S1..Sm`), porque no quadro inicial elas formavam a matriz identidade $I$ e foram multiplicadas por $B^{-1}$ (`corpo = b_inv @ M`).
3. **Por que vocês precisaram da função `_extrair_base` usando SciPy?**
   Porque o `scipy.optimize.linprog` (HiGHS) retorna o valor ótimo de `x`, as folgas e os duais, mas não retorna diretamente a lista de colunas da base ótima. Como precisamos de $B^{-1}$ para montar o Quadro Simplex Ótimo, as faixas de viabilidade e testar $\Delta b$ sem rodar o solver de novo, reconstruímos $B$ escolhendo $m$ colunas linearmente independentes (priorizando variáveis positivas e, em casos degenerados, menor custo reduzido).
4. **Como o programa lida com Minimização e com restrições $\ge$?**
   - **Minimização:** o SciPy minimiza nativamente; na maximização multiplicamos `c` por `-1` e invertemos o sinal de `Z*` e dos duais no final.
   - **Restrições $\ge$:** como o `LD` aceita valores negativos, basta multiplicar a restrição por `-1` (ex.: $2x_1 + x_2 \ge 10$ vira $-2x_1 - x_2 \le -10$) e o HiGHS resolve normalmente.
5. **Como o programa testa novas alterações $\Delta b$ sem recalcular o Simplex?**
   A solução ótima (`ld`, `b_inv`, `precos_sombra`, `z_otimo`) fica salva em `st.session_state["sol"]`. Nas alterações, `analisar_alteracoes` só calcula $LD_{\text{novo}} = LD + B^{-1}\Delta b$ e $Z_{\text{novo}} = Z^* + y^T \Delta b$, sem chamar `linprog`.
6. **Quando uma alteração é inviável?**
   Quando pelo menos um componente de $LD_{\text{novo}}$ fica negativo (`< -EPS`), indicando que alguma variável básica ficaria negativa e a base ótima atual deixa de ser viável.
7. **Por que existe a constante `EPS = 1e-9`?**
   Por causa da aritmética de ponto flutuante (IEEE 754): contas como `0.1 + 0.2 - 0.3` podem gerar `-1e-16` em vez de `0`. Sem `EPS`, um zero numérico poderia ser confundido com número negativo (marcando uma solução válida como inviável) ou gerar `-0.00` na tela e divisões instáveis no cálculo das faixas.
8. **E se o usuário alterar mais de uma restrição ao mesmo tempo?**
   A fórmula matricial $LD + B^{-1}\Delta b \ge 0$ já avalia alterações simultâneas de forma exata, e $Z^* + y^T\Delta b$ soma o impacto de cada preço-sombra.
