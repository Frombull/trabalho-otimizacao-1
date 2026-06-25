# Roteiro de Apresentação

## 1. Visão geral

"É um resolvedor de **Programação Linear** feito em **Python**, com interface web em
**Streamlit**. O usuário monta o problema na tela - função objetivo, restrições e as
variações desejadas - e o programa devolve o **ponto ótimo**, o **preço-sombra** de cada
restrição e a **análise das variações**. O cálculo em si usa a biblioteca **SciPy**
(função `linprog`)."

---

## 2. As 3 partes do código

O código é dividido em **três blocos - calcular, exibir e ler dados** - pra ficar fácil de
entender: cada função faz uma coisa só.

### Bloco 1 - Cálculo (onde o problema é resolvido)
- **`resolver_ppl`**: manda o problema pro SciPy.
  - Detalhe: o SciPy só sabe *minimizar*, então pra *maximizar* a gente troca o sinal dos
    coeficientes (`-c`) e depois corrige o sinal do resultado.
- **`calcular_precos_sombra`**: pega os valores duais que o SciPy devolve (`marginals`) -
  é o preço-sombra de cada restrição.

### Bloco 2 - Exibição (onde o resultado vira tela)
- **`mostrar_ponto_otimo`**: mostra o valor de cada variável (x1, x2, ...) e o Z ótimo.
- **`mostrar_precos_sombra`**: lista o preço-sombra de cada restrição.
- **`analisar_variacoes`**: aplica as variações Δb, resolve de novo e diz se ficou viável
  e qual o novo Z.

### Bloco 3 - Entrada de dados (onde o usuário digita)
- **`ler_funcao_objetivo`** e **`ler_restricoes`**: montam os campos de digitação
  (coeficientes, lados direitos `b` e as variações Δb).

---

## 3. O fluxo

"No fim, o programa monta a tela: escolhe quantas variáveis e restrições, lê os dados, e
quando o usuário clica em **Resolver**, ele chama o solver e exibe os três blocos de
resultado na sequência."
