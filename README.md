# Resolvedor de PPL - Trabalho M210

App em Streamlit que resolve um Problema de Programação Linear (2 a 4 variáveis)
pelo método Simplex, usando `scipy.optimize.linprog`.

## O que o app mostra
- **Ponto ótimo de operação** (valor de cada variável e do Z ótimo)
- **Preço-sombra** de cada restrição
- Se as **variações desejadas (Δb)** são viáveis
- O **novo lucro ótimo** e o **limite de validade do preço-sombra**

## Como rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```
O app abre no navegador. Preencha a função objetivo, as restrições e
(opcionalmente) o Δb desejado em cada restrição, depois clique em **Resolver**.

## Exemplo para testar
Max  Z = 3x₁ + 5x₂
- x₁ ≤ 4
- 2x₂ ≤ 12
- 3x₁ + 2x₂ ≤ 18

Resultado esperado: x₁ = 2, x₂ = 6, Z = 36, preços-sombra = (0; 1,5; 1).
