

Modelo: Max/Min `Z = c·x`, sujeito a `A·x <= b`, `x >= 0` (2 a 4 variáveis, até 6 restrições).

## Ideia geral em 3 passos
1. **Resolve** o PPL com `scipy.linprog` (HiGHS). Isso devolve `x`, folgas e duais.
2. **Reconstrói** a base ótima `B` e monta o Quadro Simplex Ótimo por álgebra matricial.
3. **Análise de Δb** usa só `B⁻¹`, `LD` e preços-sombra. Não chama o solver de novo.

## "Onde você calcula...?" (mapa de linhas)

| O quê | Linha | Como |
|---|---|---|
| Resolve o PPL | 35 | `linprog(..., method="highs")` |
| Z ótimo | 40 | `-res.fun` se maximizar, senão `res.fun` |
| Preço-sombra | 41-42 | duais do HiGHS, com sinal ajustado para Max/Min |
| Forma padrão `[A \| I]` (folgas) | 46 | `np.hstack([A, eye(m)])` |
| Base ótima (índices) | 16-26 e 52 | `_extrair_base` |
| `B⁻¹` | 53 | `np.linalg.inv(M[:, base])` |
| **LD ótimo** (`B⁻¹·b`) | 54 | `ld = b_inv @ b_arr` |
| Corpo do quadro (`B⁻¹·[A\|I]`) | 55 | `corpo = b_inv @ M` |
| Linha Z (`c_B·B⁻¹·M − c`) | 56 | `linha_z` |
| Montagem do quadro (Z embaixo) | 58-60 | `vstack` + `DataFrame` |
| Faixas de viabilidade (Δ Min / Δ Max) | 62-73 | usa as colunas de `B⁻¹` |
| **Recalcular o LD sem refazer tudo** | 86 | `ld_novo = ld + b_inv @ d` |
| Novo Z sem refazer | 88 | `z_novo = Z* + precos_sombra @ d` |
| Teste de viabilidade | 87 | `all(ld_novo >= -EPS)` |

## Perguntas prováveis

**Como recalcula o LD sem refazer o Simplex?** (linhas 83-96)
- Quando só `b` muda, a base `B` continua a mesma enquanto ela seguir viável.
- Então o novo valor das básicas é `LD_novo = LD + B⁻¹·Δb`.
- `B⁻¹` e `LD` já foram guardados em `st.session_state["sol"]` (linhas 78 e 164). Por isso `analisar_alteracoes` não chama o `linprog`.
- O novo Z é `Z* + yᵀ·Δb`, onde `y` são os preços-sombra.
- Se algum `LD_novo < 0`, a alteração é **inviável** para essa base. Seria preciso refazer o Simplex, e o app só avisa.
- Funciona também para vários Δb ao mesmo tempo. É um teste exato, melhor que a regra dos 100%, que é só condição suficiente.

**O que é `EPS = 1e-9` (linha 6)?**
- É uma tolerância numérica de ponto flutuante. Por exemplo, `0.1 + 0.2 - 0.3` dá `5e-17`, e não `0`.
- Evita dois problemas:
  - Tratar um zero numérico como negativo e marcar como inviável (`>= -EPS`, linhas 87 e 94).
  - Mostrar `-0.00` na tela (função `fmt`, linha 13).
- Também decide se um coeficiente de `B⁻¹` é positivo ou negativo nas faixas (linhas 66-67), e se uma variável está na base (linha 19).

**Como troca entre minimizar e maximizar?** (linhas 35, 40, 42)
- O `linprog` **só minimiza**.
- Max: resolve `min(−c·x)`, porque `max f = −min(−f)`.
- Depois desfaz o sinal:
  - `Z* = −res.fun` (linha 40).
  - `preço-sombra = −dual` (linha 42).
- Min: passa `c` direto, sem inverter nada.
- O restante (`B⁻¹`, `LD`, quadro) é igual nos dois casos, pois só depende de `A`, `b`, da base e de `c` original (`c_full`).
- No front, é só o `radio` da linha 137 (`maximizar = objetivo == "Maximizar"`).

**E restrições `>=`?**
- Multiplica por `-1` e usa `<=`. O campo `LD` aceita negativo.
- Exemplo: `2x1 + x2 >= 10` vira `-2x1 - x2 <= -10`.

**Por que existe `_extrair_base`?**
- O HiGHS dá `x`, folgas e duais, mas **não dá a lista de colunas da base**. Precisamos dela para calcular `B⁻¹`.
- A função ordena as colunas: primeiro as variáveis com valor > 0, que obrigatoriamente estão na base. Depois, em caso de degeneração, as de menor custo reduzido.
- Pega colunas que aumentam o posto da matriz (`matrix_rank`) até completar `m` colunas. Isso garante que `B` seja inversível.

**Onde está o preço-sombra no quadro?**
- Na linha `Z`, sob as colunas das folgas `S1..Sm` (`c_B·B⁻¹ = yᵀ`). Também aparece como `PS1..PSm` e na tabela de faixas.

**Onde está `B⁻¹` no quadro?**
- Nas linhas das restrições, sob as colunas das folgas. Elas começam como `I` e viram `B⁻¹·I` (linha 55).

**Como calcula a faixa de viabilidade do preço-sombra?** (linhas 62-73)
- Exige `LD_i + (B⁻¹)_{i,j}·Δb_j >= 0` para todo `i`.
- Coeficiente `a > 0` dá limite inferior: `Δb >= −LD_i/a`. Pega o `max`.
- Coeficiente `a < 0` dá limite superior: `Δb <= −LD_i/a`. Pega o `min`.
- Se não houver limite, fica `±inf`.
- `LD Min` e `LD Max` são `b_j + Δ`.

**Como trata problema inviável ou ilimitado?** (linhas 36-38)
- Pelo `res.status` do HiGHS: `2` é inviável e `3` é ilimitado. Aparece em `st.error`.

**Por que as colunas ficam fixas e o Z embaixo?**
- O quadro é calculado direto da base final, e não pivô a pivô. A ordem é sempre `VB | x | S | LD`, com a linha Z por último (linha 58).

## Pontos fracos (melhor saber antes de ele perguntar)
- Não implementa as iterações do Simplex (pivotamento). O ótimo vem do HiGHS e o quadro final é reconstruído por álgebra matricial.
- Só analisa mudança em `b`. Mudança em `c` ou em `A` não é tratada.
- Se Δb sai da faixa, o app só diz "inviável". Não troca de base nem resolve pelo Dual Simplex.
- Em soluções degeneradas, a base escolhida pode não ser a única possível. Os preços-sombra e as faixas podem diferir entre bases equivalentes.
