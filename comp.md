# Ciclo Dos Modelos - PNLD




## Visao Geral Do Fluxo


`Entrada .dzn -> preprocessamento -> paletizacao -> producao -> objetivo


Em todos os metodos, a ideia central e a mesma:
- decidir como agrupar encomendas em paletes;
- decidir quando cada palete e produzido;
- minimizar um objetivo com prioridade.
---
- `q` = produtor
- `i` = item (tipo de livro/material)
- `c` = centralizadora
- `t` = periodo de producao


---


## Modelo Principal - MiniZinc


Arquivo: `MODELAGEM_ENIAC.mzn`


### Ciclo
1. Le dados da instancia (`.dzn`).
2. Preprocessa:
   - encomenda -> item
   - encomenda -> centralizadora
   - encomenda -> produtor
3. Paletizacao com restricoes (`bin_packing`).
4. Producao com capacidade por periodo (`cumulative`).
5. Calcula objetivo com prioridade:
   - minimizar `ultimo_periodo`;
   - depois `TotalCentExtrasUsadas`;
   - depois `TotalPaletesUsados`.


### Papel desse modelo
- é a referencia matematica do artigo do Guilherme;
---


## Guloso/Mochila


Arquivo: `Guloso_ENIAC.py`


### Ciclo
1. Le `.dzn`.
2. Faz `parse_dzn` e `normalize_inputs`.
3. Agrupa encomendas por `(q,i,c)`.
4. Enche paletes com:
   - `FFD` (first fit decreasing) ou `Mochila` (knapsack).
5. Define periodos de producao durante a construcao.
6. Recalcula metricas no mesmo formato do MiniZinc.
7. Calcula `_objective`.




- pega um produtor `q`;
- escolhe um item `i` com demanda;
- no periodo `t`, respeita limite `qtd[q,i]`;
- vai abrindo paletes ate gastar a capacidade do periodo;
- quando nao cabe mais, avanca para `t+1`.
- ele construi uma agenda factivel em tempo real, sem busca global.


Depois de montar paletes e periodos, ele reconstrui os mesmos vetores do modelo base:
- `PaleteIndividualUsado`
- `inicio_producao`
- `distancia_paletes_prod_peri`
- `distancia_paletes`
- `TotalPaletesUsados`, `TotalTUsados`, `TotalCentExtrasUsadas`
- `_objective`


### Melhoria
- muito rapido (bom para solucao inicial e upper bound).


### Limite
- pode ficar preso em decisoes locais (sem garantia de otimo).


---


## CP Direto


Arquivo: `CP_ENIAC_Direto.py`


### O que e "CP Direto"?
E uma modelagem CP-SAT escrita explicitamente em Python com variaveis binarias/inteiras.
Em vez de usar as globais do MiniZinc diretamente, ele "abre" a formulacao.


### Variaveis principais
- `x[e,p]`: encomenda `e` vai para palete `p`.
- `y[p,g]`: palete `p` escolhe um grupo `g=(q,i,c)`.
- `z_qi`: ajuda a enxergar se o palete esta em um par `(q,i)`.
- `z_qc`: ajuda a enxergar se o palete atende par `(q,c)`.
- `start[p,t]`: palete `p` inicia no periodo `t`.


### Ciclo
1. Le `.dzn` e preprocessa.
2. Monta grupos viaveis `(q,i,c)`.
3. Cria variaveis `x,y,z,start`.
4. Adiciona restricoes (capacidade, homogeneidade, producao, item unico por periodo)
5. Resolve CP-SAT.
6. Extrai metricas e objetivo.


### Diferenca conceitual para o base MiniZinc
- Base: mais declarativo (foco na regra).
- CP Direto: mais construtivo/explicito (foco na estrutura interna do solver)


### Melhoria vs base
- maior controle para depurar, comparar e instrumentar benchmark.


### Limite
- numero de variaveis/restricoes pode crescer bastante.


---


## CP-SAT Completo


Arquivo: `eniac_cp_sat.py`


### Ciclo
1. Le `.dzn`.
2. Monta formulacao CP mais completa (fiel ao modelo).
3. Aplica aceleradores.
4. Resolve CP-SAT.
5. Reconstrui saida estilo MiniZinc.
6. Valida consistencia da solucao.


### Conceitos importantes


#### Upper bound do guloso
Ideia:
- roda guloso antes;
- pega objetivo guloso `obj_g`;
- adiciona restricao `objective <= obj_g`.


Efeito:
- CP nao perde tempo em solucoes piores que algo ja conhecido.
- busca fica mais focada.


#### Tightening
Ideia:
- adicionar limites seguros que reduzem espaco de busca sem remover otimo.
Exemplos:
- limite inferior de paletes por peso total/capacidade;
- limite superior em `ultimo_periodo` vindo de solucao conhecida.


Efeito:
- menos combinacoes para explorar.


#### Fixacoes parciais (para LNS)
Ideia:
- fixar parte das decisoes (ex.: palete/item/produtor de certas encomendas);
- deixar o restante livre para reotimizar.


Efeito:
- transforma "resolver tudo" em "resolver subproblema".


### Como funciona a validacao (`is_valid` e `validation_errors`)
Depois de resolver, o codigo reavalia a solucao fora do solver:
- checa dominio e consistencia;
- checa capacidade de palete;
- checa homogeneidade;
- checa capacidade de producao por periodo;
- checa item unico por produtor/periodo;
- recalcula metricas e `_objective`.


Se tudo bate:
- `is_valid = True`.


Se algo divergir:
- `is_valid = False`;
- detalhes ficam em `validation_errors`.


Isso aumenta confianca no resultado reportado.


---


## Local Search (refino em cima do guloso)


Arquivo: `eniac_local_search.py`


### Ciclo
1. Parte da solucao gulosa.
2. Escolhe paletes candidatos (com foco em reduzir periodo final).
3. Tenta mover palete para periodo mais cedo.
4. So aceita movimento se objetivo melhora.
5. Repete ate limite de tempo/iteracoes.


### Conceito do movimento
Mover um palete de `t_old` para `t_new < t_old` so se:
- nao viola capacidade `qtd[q,i]` no periodo novo;
- nao mistura item diferente no mesmo produtor/periodo.


### Regra de aceitacao
- calcula novo `_objective`;
- se melhorou: mantem;
- se piorou/empatou: desfaz.


Isso e uma busca local de melhoria estrita.


---


## Two-Phase (decomposicao)


Arquivo: `eniac_two_phase.py`


### Ciclo
1. Fase 1: paletiza com heuristica (`FFD` ou `Mochila`).
2. Fase 2: com paletes fixos, otimiza agendamento com CP-SAT.
3. Reconstroi metricas finais.


### Conceito
Decompor o problema em duas partes menores:
- parte combinatoria de empacotar;
- parte temporal de agendar.


### Vantagem
- menos pesado que CP completo;
- normalmente melhora o "quando produzir" mesmo com paletizacao fixa.


---


## LNS (Large Neighborhood Search)


Arquivo: `eniac_cp_sat_lns.py`


### Ciclo
1. Cria solucao inicial:
   - **CP curto**: roda CP com pouco tempo para tentar um bom ponto inicial;
   - se nao tiver solucao, usa guloso.
2. Em cada iteracao:
   - escolhe subconjunto para relaxar (`relax_set`);
   - fixa o restante (`fixed_orders`);
   - resolve CP do subproblema.
3. Atualiza melhor solucao se houver melhora.


### Diferenca para Two-Phase
- Two-Phase: separa por tipo de decisao (paletizar depois agendar).
- LNS: mantem modelo CP, mas reotimiza so "partes" por iteracao.


### "CP curto ou guloso" (conceito)
- CP curto = tentativa rapida de conseguir incumbente com qualidade.
- guloso = fallback garantido, muito rapido.


---


## Hybrid (orquestrador)


Arquivo: `eniac_hybrid.py`


### Ciclo
1. Define budget total (ex.: 30s).
2. Executa pipeline em sequencia:
   - guloso
   - local search
   - two-phase
   - CP (tight)
   - LNS no tempo restante
3. A cada etapa compara score e guarda melhor.
4. Retorna:
   - melhor solucao final;
   - de onde veio (`hybrid_best_from`);
   - trilha de tentativas (`hybrid_trials`).


### Conceito
Nao aposta em um unico metodo.
Combina:
- velocidade (guloso/LS),
- estrutura (two-phase),
- qualidade (CP/LNS).




---


## Resumo Rapido Para Fala


- MiniZinc define a regra matematica.
- Guloso gera resposta imediata.
- CP Direto/CP Completo trazem busca mais forte.
- LS melhora localmente.
- Two-Phase decompoe empacotamento vs agendamento.
- LNS reotimiza partes por iteracao.
- Hybrid junta tudo e escolhe o melhor no tempo disponivel.


---


## Comparacoes Entre Modelos (Nova Secao)


Esta secao complementa o documento com comparacoes diretas entre os metodos.


### 1) Comparacao conceitual (lado a lado)


| Metodo | Como paletiza | Como agenda producao | Tipo de busca | Vantagem principal | Limite principal |
|---|---|---|---|---|---|
| MiniZinc base | via restricoes globais | via `cumulative` | exata (solver) | referencia matematica | custo cresce com a instancia |
| Guloso | construtivo (`FFD`/`Mochila`) | durante a construcao | heuristica local | muito rapido | sem garantia de otimo |
| CP Direto | variaveis explicitas `x,y,z` | `start[p,t]` + restricoes | CP-SAT completo | controle fino do modelo | modelo grande |
| CP-SAT completo | equivalente ao base com reforcos | equivalente ao base | CP-SAT com aceleradores | melhor qualidade media | tempo maior que heuristicas |
| Local Search | herda do guloso | move periodos localmente | busca local | melhora barata do guloso | pode parar em otimo local |
| Two-Phase | heuristica fixa paletes | CP-SAT so no scheduling | decomposicao em 2 fases | bom equilibrio tempo/qualidade | paletizacao fica congelada |
| LNS | relaxa parte da solucao | CP em subproblemas | vizinhancas grandes iterativas | melhora incumbente com custo controlado | depende da qualidade inicial |
| Hybrid | combina varios metodos | combina varios metodos | portfolio com budget | maior robustez pratica | pipeline mais complexo |


### 2) Comparacao de estrategia (Two-Phase vs LNS)


- `Two-Phase`:
  - corta o problema por tipo de decisao.
  - primeiro decide paletes, depois otimiza so o tempo/producao.
  - bom quando voce quer um CP menor e previsivel.
- `LNS`:
  - mantem o modelo CP, mas reotimiza apenas parte da solucao a cada iteracao.
  - fixa a maior parte e relaxa um subconjunto (`relax_set`).
  - bom para refinar incumbente sem reabrir tudo.


### 3) Comparacao quantitativa (arquivos do projeto)


Fontes:
- `comparacao_ffd_mochila_eniac.csv`
- `comparacao_cp_direto_eniac.csv`
- `comparacao_cp_vs_guloso_vs_saida.csv`
- `resultados/multiseed_10x30/summary_by_method.csv`


#### 3.1 FFD vs Mochila (no Guloso)
- Total: 17 instancias
- Mochila melhor: 0
- FFD melhor: 0
- Empate: 17


Leitura:
- neste conjunto de testes, trocar `FFD` por `Mochila` nao mudou o objetivo final.


#### 3.2 CP Direto vs FFD
- Total: 17 instancias
- CP melhor: 8
- FFD melhor: 2
- Empate: 7
- Status CP Direto: 11 `OPTIMAL`, 6 `FEASIBLE`


Leitura:
- CP Direto tende a melhorar qualidade em parte relevante das instancias.


#### 3.3 CP-SAT vs Guloso
- Comparando onde ambos possuem objetivo:
  - CP melhor: 9
  - Guloso melhor: 0
  - Empate: 7


Leitura:
- CP e dominante sobre o guloso nesse recorte, com varios empates em casos mais simples.


#### 3.4 Multi-seed 10x30 (170 execucoes por metodo)


| Metodo | BKS hit rate | Gap medio (%) | Tempo medio (ms) |
|---|---:|---:|---:|
| hybrid | 92.94 | 0.0012 | 9632.6 |
| cp_tight | 90.00 | 0.0027 | 11008.1 |
| cp | 88.24 | 0.0106 | 11288.4 |
| two_phase | 82.35 | 2.3679 | 109.8 |
| lns | 75.88 | 0.0069 | 8264.6 |
| guloso | 41.18 | 2.5641 | 0.32 |
| ls | 41.18 | 2.5641 | 7.04 |


Como ler essa tabela:
- `BKS hit rate`: porcentagem de execucoes em que o metodo atingiu o melhor valor conhecido (BKS).
- `Gap medio (%)`: distancia percentual media para o BKS.
  - formula: `100 * (obj_metodo - BKS) / BKS`
  - quanto menor, melhor.


Exemplo com os valores perguntados:
- `92.94` em `BKS hit rate` significa que o metodo acertou o BKS em ~93 de cada 100 execucoes.
  - neste experimento (170 execucoes): `158/170`.
- `41.18` em `BKS hit rate` significa que o metodo acertou o BKS em ~41 de cada 100 execucoes.
  - neste experimento (170 execucoes): `70/170`.


Leitura:
- `hybrid` e `cp_tight` lideram qualidade.
- `two_phase` entrega bom custo-beneficio de tempo.
- `guloso` e `ls` sao extremamente rapidos, mas com gap medio maior.


### 4) Quando usar cada metodo (regra pratica)


- Se prioridade e velocidade imediata: `Guloso`.
- Se prioridade e qualidade maxima com validacao forte: `CP-SAT completo` / `CP-tight`.
- Se quer equilibrio tempo vs qualidade: `Two-Phase`.
- Se ja tem uma boa solucao e quer melhorar incrementalmente: `LNS`.
- Se quer robustez automatica em budget fixo: `Hybrid`.


---


## Comparacao Direta Com MiniZinc


### 1) Como interpretar a comparacao


- `gap_metodo_vs_saida = obj_metodo - saida_best_obj`
- Se gap < 0: metodo encontrou objetivo melhor que o melhor registrado no `minizinc`.
- Se gap = 0: empate com `minizinc`.
- Se gap > 0: metodo ficou pior que `minizinc`.


Importante:
- status encontrados no conjunto `benchmark_todos.csv`:
  - `COMPLETE`: 5 instancias
  - `PARTIAL`: 5 instancias
  - `EMPTY`: 4 instancias
  - `UNKNOWN`: 3 instancias
- por isso mostramos dois recortes:
  - apenas `COMPLETE` (mais conservador);
  - todas com referencia numerica (`saida_best_obj` disponivel), inclusive `PARTIAL`.


### 2) Recorte conservador: apenas `SAIDA = COMPLETE` (n=5)


| Metodo | Melhor que MiniZinc | Pior que MiniZinc | Empate |
|---|---:|---:|---:|
| guloso | 0 | 4 | 1 |
| cp | 1 | 2 | 2 |
| cp_tight | 1 | 2 | 2 |
| ls | 0 | 4 | 1 |
| lns | 1 | 2 | 2 |
| two_phase | 1 | 2 | 2 |
| hybrid | 1 | 2 | 2 |
| cp_direto | 1 | 2 | 2 |


Leitura:
- nos casos `COMPLETE`, os metodos CP (cp/cp_tight/cp_direto) e os refinamentos (lns/two_phase/hybrid) tiveram comportamento parecido.
- guloso e ls perderam mais vezes nesse recorte.


### 3) Recorte ampliado: com referencia numerica (`saida_best_obj`) (n=10)


| Metodo | Melhor que MiniZinc | Pior que MiniZinc | Empate | Gap medio |
|---|---:|---:|---:|---:|
| guloso | 1 | 8 | 1 | 158.2 |
| cp | 4 | 3 | 3 | -10.3 |
| cp_tight | 4 | 2 | 4 | -10.7 |
| ls | 1 | 8 | 1 | 158.2 |
| lns | 3 | 5 | 2 | 109.1 |
| two_phase | 3 | 4 | 3 | 214.5 |
| hybrid | 4 | 3 | 3 | -10.5 |
| cp_direto | 4 | 3 | 3 | -9.9 |


Leitura:
- `cp`, `cp_tight`, `hybrid` e `cp_direto` tiveram gap medio negativo (em media, melhores que o valor de referencia do `.SAIDA` nesse recorte).
- `guloso` e `ls` ficaram mais distantes da referencia.
- `lns` e `two_phase` melhoram em alguns casos, mas ainda com gap medio positivo no conjunto.


### 4) Comparacao conceitual: o que muda em relacao ao MiniZinc


- MiniZinc:
  - modelagem declarativa de alto nivel (global constraints).
  - excelente referencia para validar regra de negocio e objetivo.
- CP Python (`cp`, `cp_tight`, `cp_direto`):
  - mesma logica central, com controle fino de variaveis, cortes e estrategias.
  - mais flexivel para engenharia de desempenho (UB, tightening, fixacoes).
- Heuristicas (`guloso`, `ls`):
  - muito mais rapidas;
  - qualidade depende mais da instancia.
- Metodos compostos (`lns`, `two_phase`, `hybrid`):
  - tentam aproximar qualidade CP com custo controlado.
  - `hybrid` tende a ser mais robusto no agregado.




| Instancia | Guloso (ms) | LS (ms) | TwoPhase (ms) | CP (ms) | CP_Tight (ms) | LNS (ms) | Hybrid (ms) | CP_Direto (ms) | MiniZinc melhor sol. (ms) | MiniZinc final (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| i1031022.dzn | 0 | 8 | 41 | 1328 | 639 | 2144 | 3198 | 2977 | 4170 | 4170 |
| i1031033.dzn | 1 | 6 | 50 | 913 | 874 | 3549 | 3629 | 2285 | - | - |
| i103322.dzn | 1 | 9 | 50 | 1045 | 731 | 1587 | 1423 | 1705 | 1950 | 240590 |
| i103522.dzn | 0 | 6 | 59 | 582 | 434 | 1670 | 1679 | 2696 | 5700 | 5700 |
| i2031022.dzn | 1 | 9 | 137 | 12708 | 12828 | 10774 | 17673 | 20496 | 39750 | 39750 |
| i2031033.dzn | 1 | 12 | 130 | 12844 | 13080 | 11836 | 17531 | 20178 | 151520 | 151520 |
| i22222.dzn | 0 | 1 | 18 | 18 | 23 | 92 | 378 | 22 | - | - |
| i223722.dzn | 2 | 13 | 178 | 12983 | 12543 | 14553 | 20614 | 20206 | 56570 | 56570 |
| i223733.dzn | 2 | 15 | 149 | 12739 | 12707 | 10266 | 17883 | 20196 | - | 1000360 |
| i3031022.dzn | 1 | 19 | 357 | 13026 | 11524 | 14268 | 21802 | 21067 | - | 1000540 |
| i3031033.dzn | 1 | 11 | 490 | 12493 | 13636 | 13175 | 19270 | 21598 | - | 1000590 |
| i33322.dzn | 0 | 1 | 50 | 48 | 31 | 523 | 269 | 34 | - | - |
| i42222.dzn | 0 | 1 | 21 | 50 | 43 | 170 | 312 | 49 | 540 | 560 |
| i53522.dzn | 0 | 6 | 26 | 218 | 208 | 600 | 691 | 158 | 950 | 1020 |
| i63322.dzn | 0 | 1 | 32 | 109 | 105 | 323 | 478 | 91 | 1230 | 1230 |
| i73722.dzn | 0 | 5 | 42 | 624 | 414 | 1214 | 1446 | 1246 | 1950 | 409110 |
| i73733.dzn | 0 | 5 | 31 | 288 | 262 | 817 | 1086 | 689 | - | - |


Legenda MiniZinc:
- `----------`: encontrou uma solucao e continua buscando melhoria.
- `==========`: terminou a busca (prova de otimalidade/encerramento completo).
- `MiniZinc melhor sol. (ms)`: tempo ate encontrar o melhor `_objective`
- `MiniZinc final (ms)`: ultimo `% time elapsed`



