# Modelo de Análise da Lei de Benford

Para extratos, balanços, balancetes, razão, NFs e folha de clientes. Versão em texto do `Modelo_Benford.xlsx`: mesma metodologia, fórmulas e interpretação.

> Desvio de Benford é **indício para auditar**, não prova de fraude.

---

## 1. A lei

Em conjuntos de valores que variam em ordem de grandeza, o dígito inicial **d** aparece com frequência:

```
P(d) = log10(1 + 1/d)          (1º dígito, d = 1..9)
P(dd) = log10(1 + 1/dd)        (2 primeiros dígitos, dd = 10..99)
```

| 1º dígito | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| Esperado | 30,1% | 17,6% | 12,5% | 9,7% | 7,9% | 6,7% | 5,8% | 5,1% | 4,6% |

---

## 2. Passo a passo

1. **Escolha um tipo de dado por análise** (ex.: só saídas do extrato, só saldos do balancete).
2. **Limpe a base**: remova totais, subtotais e linhas de cabeçalho; cole como valor. O sinal é ignorado (débito e crédito juntos).
3. **Defina o valor mínimo** (padrão R$ 1,00). Valores menores e zeros ficam de fora.
4. **Confira a amostra**: mínimo de **300** lançamentos para o 1º dígito e **1.000** para 2 dígitos.
5. **Calcule** observado × esperado, desvio, Z, χ² e MAD (seção 3).
6. **Interprete** pelo MAD (seção 4) e investigue os dígitos em alerta.
7. **Volte aos lançamentos** dos dígitos que mais desviam e confira os documentos.

---

## 3. Cálculos

Seja **n** = quantidade de lançamentos analisados.

| Indicador | Fórmula |
|---|---|
| 1º dígito do valor `v` | primeiro algarismo de `abs(v)` (Excel: `VALUE(LEFT(TEXT(ABS(v),"0.0000000E+00"),1))`) |
| 2 primeiros dígitos | 1º + 3º caractere do mesmo texto científico |
| % observado `o_d` | contagem do dígito ÷ n |
| % esperado `e_d` | `LOG10(1+1/d)` |
| Quantidade esperada | `e_d × n` |
| Desvio | `o_d − e_d` |
| **Z** por dígito | `(abs(o_d − e_d) − 1/(2n)) / sqrt(e_d·(1−e_d)/n)` |
| Alerta | Z > 1,96 (95% de confiança) |
| χ² | `Σ (obs − esp)² / esp`, com gl = 8 (1 dígito) ou 89 (2 dígitos) |
| p-valor | `CHIDIST(χ², gl)`; p < 0,05 rejeita Benford |
| **MAD** | média de `abs(o_d − e_d)` sobre todos os dígitos |

---

## 4. Interpretação do MAD (Nigrini)

| Conformidade | 1º dígito | 2 dígitos |
|---|---|---|
| Estreita | ≤ 0,006 | ≤ 0,0012 |
| Aceitável | ≤ 0,012 | ≤ 0,0018 |
| Marginal | ≤ 0,015 | ≤ 0,0022 |
| **Não conformidade** | > 0,015 | > 0,0022 |

Priorize o **MAD**. O χ² fica hipersensível quando n é grande.

---

## 5. O que o desvio costuma indicar

| Padrão | Possível causa |
|---|---|
| Excesso de 5 e 6 no 1º dígito | Valores arredondados ou estimados |
| Excesso de 9 / 49 / 99 | Preços psicológicos ou valores abaixo de limite de aprovação |
| Pico em um dígito específico | Valor repetido (mensalidade, tarifa, parcelas) |
| Falta de dígitos 1 e 2 | Faixa limitada, teto ou piso |
| Excesso de 10, 20, 50 (2 dígitos) | Arredondamento / lançamentos "redondos" |
| Dados 100% conformes e "perfeitos" | Também merecem atenção (possível fabricação) |

---

## 6. Cautelas

- Não segue Benford: valores fixos, numeração (NF, CPF), faixas limitadas, tetos e pisos, bases com poucos lançamentos.
- Misturar tipos de dado (receita + tarifa + folha) distorce o teste.
- Use como evidência para **direcionar a revisão**, não como conclusão de laudo.

---

## 7. Leitura sugerida

- Mark J. Nigrini — *Benford's Law: Applications for Forensic Accounting, Auditing, and Fraud Detection* (Wiley, 2012).
- Nigrini — *Forensic Analytics* (Wiley).

---

## 8. Modelo de relatório por cliente

```
Cliente:            ____________________
Período:            ____________________
Base analisada:     ( ) extrato  ( ) balancete  ( ) razão  ( ) NFs
Valor mínimo:       R$ ______      n = ______
MAD 1º dígito:      ______  → ____________________
MAD 2 dígitos:      ______  → ____________________
χ² / p-valor:       ______ / ______
Dígitos em alerta:  ____________________
Lançamentos a conferir: ____________________
Conclusão / próximos passos: ____________________
```
