# Trabalho M210

| Nome                           | Matrícula | Curso |
|--------------------------------|-----------|-------|
| Marco Renzo Rodrigues Di Toro  | 150       | GES   |
| Kawan Dos Reis Brito           | 162       | GES   |
| Kauã Victor Garcia Siécola     | 1887      | GEC   |

--- 

- **Ponto ótimo de operação** (valor de cada variável e do Z ótimo)
- **Preço-sombra** de cada restrição
- Se as **variações desejadas (Δb)** são viáveis
- O **novo lucro ótimo** e o **limite de validade do preço-sombra**

## Rodando essa budega
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Exemplo:
Máx Z = 3X + 5Y
- X ≤ 4
- 2Y ≤ 12
- 3X + 2Y ≤ 18

Resultado esperado: X=2, Y=6, Z=36, preços-sombra = (0, 1.5, 1)

---

### Fluxograma com mermaid:


```mermaid
flowchart TD
    A["<b>Entrada</b><br/>c, matriz A, vetor b, Δb"]
    A -->|Resolver| B["Monta A e b (NumPy)"]

    B --> C["<b>resolver_ppl()</b><br/>linprog / Simplex"]

    C --> D{"Viável?"}
    D -->|Não| E["Erro: inviável"]

    D -->|Sim| F["<b>preço-sombra</b><br/>valores duais"]

    F --> G["Ponto ótimo (x, Z)"]
    F --> H["Preço-sombra"]

    G --> I["<b>Análise Δb</b><br/>recalcula Z"]
    H --> I

    I --> J{"Δb viável?"}
    J -->|Não| K["Erro: inviável"]
    J -->|Sim| L{"Z bate com<br/>a estimativa?"}

    L -->|Sim| M["Dentro do limite"]
    L -->|Não| N["Base mudou"]

    classDef codigo fill:#dbeafe,stroke:#2563eb,color:#1e293b;
    classDef mat fill:#ffedd5,stroke:#ea580c,color:#1e293b;
    classDef erro fill:#fee2e2,stroke:#dc2626,color:#1e293b;

    class A,B,G,H,I codigo;
    class C,F,L,M,N mat;
    class E,K erro;
```

---

### Descrição do trabalho:
> Desenvolver um código em Python para resolver um PPL com 2,3 ou 4 variáveis, usando o método Simplex Tableau. Deverá possuir uma entrada de dados amigável assim como uma saída. É permitido o uso de bibliotecas específicas de programação linear. A entrada de dados é composta pelos coeficientes da função objetivo e das restrições. Além das variações desejadas em cada restrição. A saída de dados deve conter o ponto ótimo de operação, o preço-sombra de cada restrição e se as alterações desejadas são viáveis. Caso as alterações sejam viáveis, apresentar o novo lucro ótimo e o limite de validade do preço-sombra. Deve ser desenvolvida uma interface gráfica (frontend) utilizando bibliotecas para este fim. Exemplo: streamlit, panel, gradio, etc.
