# Trabalho M210

| Nome                           | Matrícula | Curso |
|--------------------------------|-----------|-------|
| Marco Renzo Rodrigues Di Toro  | 150       | GES   |
| Kauã Victor Garcia Siécola     | 1887      | GEC   |
| Kawan Dos Reis Brito           | xxx       | xxx   |


## O que o app mostra
- **Ponto ótimo de operação** (valor de cada variável e do Z ótimo)
- **Preço-sombra** de cada restrição
- Se as **variações desejadas (Δb)** são viáveis
- O **novo lucro ótimo** e o **limite de validade do preço-sombra**

## Pra rodar essa budega
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Exemplo:
Máx Z = 3X + 5Y
- X ≤ 4
- 2Y ≤ 12
- 3X + 2Y ≤ 18

Resultado esperado: X=2, Y=6, Z=36, preços-sombra = (0; 1,5; 1).
