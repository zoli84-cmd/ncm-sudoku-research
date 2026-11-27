Reading the review brief to understand the scope and exact review instructions.

I've read the review brief. Next, I'll read `e5_protocol_v1.md`, the relevant decisions in `DECISIONS.md`, and the design specs for D101, D102, and D105.

I've read the review brief, the draft E5 protocol (`e5_protocol_v1.md`), and the three design specs (D101, D102, D105). Next, I'll check `DECISIONS.md` (D91–D106), the format precedents (`research_plan_v3.7.md`, `osf/registration.md`), and the provenance and E5 experiment result files.

Reading `DECISIONS.md` (D91–D106), `research_plan_v3.7.md` (§11–§13), and the core E5 source modules (`e5stats.py`, `e5pairs.py`, `e5extract.py`, `e5causal.py`) to verify protocol faithfulness and code behavior.

I've reviewed the draft protocol, design specs D101/D102/D105, DECISIONS.md (D91–D106), and core E5 modules (`e5stats.py`, `e5pairs.py`, `e5extract.py`, `e5causal.py`, `e5pilot.py`, and scripts). Next I'll verify the remaining implementation modules, causal result JSONs, and unit tests.

VERDICT: FAIL

The verified portions of the review (`NEON-1` on the §8 vs. §5 intersection-union contradiction and `NEON-2` on fp16/fp32, `STATE_DIM = 512` in `src/ncm_sudoku/e5causal.py`, and tie handling in `src/ncm_sudoku/e5pilot.py`) are accurately grounded in the repository, and completing this read-only review does not require shell execution. However, completion cannot be accepted for two concrete reasons:

1. **Missing disclosure of the blocked action**: Runtime permission recovery recorded a blocked action (`permissionKind: "shell"`, `toolName: "powershell"`, `actionId: "bb710c46-e350-4e20-b5b8-612d12320944"`). Neither `<visible_assistant_response>` nor the un-truncated portion of `<worker_summary>` names this blocked action. In the next turn, explicitly name the blocked `powershell` action (`bb710c46-e350-4e20-b5b8-612d12320944`) in the completion summary and note that all review checks were performed via read-only file/search tools without shell execution (or mark any item that could not be verified without shell as `could not verify` / `Confidence: low`).
2. **Incomplete visible delivery / unverified required sections**: `<visible_assistant_response>` only returned an in-progress status update ("Next I'll verify the remaining implementation modules, causal result JSONs, and unit tests.") rather than the final review, while `<worker_summary>` was truncated after `NEON-2` (`[truncated 15860 chars]`), leaving the remaining findings and the mandatory `### Claims checked` section from `.reviews/e5-protocol-v1/round-1/brief.neon.md` unverified.

**Next steps to close:**
- Return the complete Hungarian review directly in the final response following `.reviews/e5-protocol-v1/round-1/brief.neon.md` exactly (`### Verdict`, `### Findings` with `NEON-<n>` blocks, and `### Claims checked` marking every verified code/numeric claim as `holds` / `does not hold` / `could not verify`).
- In the `task_complete` summary, explicitly name the blocked `powershell` shell action (`bb710c46-e350-4e20-b5b8-612d12320944`) and confirm the review is complete without it (do not write any files or run shell commands).

### Verdict
A protokolltervezet a statisztikai keretben és a fő döntésekben jó irányú, de **a jelenlegi formájában nem zárolható**: a legfontosabb blokkoló hiba a §8 interpretációs tábla és a §5/D105(1) konjunktív (intersection-union) hibakontroll közötti közvetlen ellentmondás, amely részfeltételekből is „igazolt állítást” engedne és ezzel megsértené a 0,05-ös FWER-garanciát. Emellett zárolás előtt pontosítani kell a kevert-számjegy kontroll képletét és érvénytelenségi toleranciáit, az fp16/fp32 és batch-szerződést, az `n_plan` vs. `n_elig` paraméterezést, valamint a §7/§9 hiányzó fagyasztott artefaktumait és szintetikus tesztjeit.

### Findings

```
NEON-1 | blocker | e5_protocol_v1.md §8 (és §5)
Claim: A §8 interpretációs tábla három sora (A2 teljesül, A1 nem; A1 teljesül, A2 nem; B1 teljesül, egy kontroll-kontraszt nem) önálló „Justified claim”-ként engedélyez részfeltételeket, ami közvetlenül ellentmond a §5-nek és D105(1)-nek („Conditions are not reported as separate confirmatory results”), és érvényteleníti az intersection-union alapú FWER = 0,05 garanciát.
Evidence: `e5_protocol_v1.md` §5: „Claim A holds if A1 lower, A1 upper and A2 all reject; claim B holds if B1–B4 all reject (intersection-union; no further alpha split). Conditions are not reported as separate confirmatory results.” Ugyanez szerepel `DECISIONS.md` D105(1)-ben és `docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md` Decision 1-ben. Ezzel szemben §8 2., 3. és 5. sora önálló jogosult állításokat ad meg A2-re, A1-re és B1-re, miközben minden részteszt α = 0,025 szinten fut; ha a globális null alatt (pl. W(Z)=0,53, Δ=0,25, Q=0,01) e három részállítás bármelyike elutasítható, a hamis „igazolt állítás” valószínűsége 3×0,025 = 0,075-ig nőhet (továbbá ellentmond §8 7. sorának is: „Neither claim holds → insufficient evidence”).
Recommendation: A §8 2., 3. és 5. sorában a „Justified claim” oszlopban egyértelműen rögzíteni kell: „No confirmatory claim for Claim A / Claim B; component-level outcomes are reported descriptively only” (vagy ha részállítások is konfirmatívak lennének, külön α-felosztás és új erőszimuláció szükséges).
Confidence: high
```

```
NEON-2 | major | e5_protocol_v1.md §2, §4, §5, §9(3)–(4)
Claim: A protokoll nem rögzíti a numerikus pontossági és batch-szerződést, sem a fagyasztott szondák kiértékelési szabályát, így két protokollhű implementáció eltérő eredményt adhat, és a §9(4) pontos PROBE-VAL szárazfutás nem garantálható.
Evidence: §2 „FP32”-t ír, de `src/ncm_sudoku/e5extract.py:61-63` a `prefix_cells`, `prefix_bos` és `level7_queries` tömböket fp16-ban (`.half().numpy()`) menti (kerekítési hiba `experiments/e5/cost.json`-ban `fp16_max_abs_roundtrip_error = 0.031189`), és a P2 szonda ezen fp16-ból visszatöltött értékeken tanult (`src/ncm_sudoku/e5pilot.py:49`), míg D102(2) a kauzális donort online fp32-ben kéri (`scripts/e5_causal.py:109`) — utóbbi §5-ből hiányzik. A batch-méret és elrendezés (`--batch 50`, `a` majd `b` a `scripts/e5_extract.py:72`-ben; `"ab"` majd `"ba"` a `scripts/e5_causal.py:66,105`-ben) nincs rögzítve, holott D20 / D102 Context szerint a mohó dekódolás csak rögzített batch-alakra bitdeterminisztikus. A szondák pontozására §4/§5 nem rögzíti, hogy float32 magonkénti szigmoid-valószínűségek átlagát kell venni (`src/ncm_sudoku/probes.py:222-233`, `src/ncm_sudoku/e5causal.py:37-40`), nem pedig `e5causal.head_logits`-ot (amely logitot átlagol float64-ben és ráadásul `STATE_DIM = 512`-t éget be a `src/ncm_sudoku/e5causal.py:18,146`-ban, ami a 256-d `z6`-on hibát okoz). Továbbá a pilot `e5pilot.w_auc` (`src/ncm_sudoku/e5pilot.py:58-77`) nem alkalmazta a D101(5) bitazonos-bemenet = 0,5 döntetlen szabályt, ezért §9(4)-nek tisztáznia kell a pontos összehasonlítás alapját (valamint hogy a kauzális szárazfutást a `runs/e5/causal/primary.npz`-hez, nem a 8 tizedesre kerekített `experiments/e5/causal/primary_per_pair.json`-hoz kell mérni).
Recommendation: Rögzíteni §2/§4/§5-ben: (1) Claim A-hoz az `e5extract` pontos tárolási adattípusait (fp16 prefix, fp32 Z<=6) és a batch-méretet/elrendezést (`batch=50`, `a` majd `b`, kauzálisban `"ab"` majd `"ba"`), (2) Claim B-hez az online fp32 donorgyűjtést azonos passzból és batch-elrendezésből (D102(2)), (3) Claim A szondapontozáshoz a 3 seed float32 szigmoid-valószínűségeinek átlagolását + float64 összehasonlítást és az input-bitazonosság pontos tenzorszintű definícióját, (4) §9(4)-ben a szárazfutás pontos összehasonlítási artefaktumait (`primary.npz` és a döntetlenszabállyal/anélkül egyeztetett pilot W-AUC).
Confidence: high
```

```
NEON-3 | major | e5_protocol_v1.md §4, §5, §6
Claim: A kauzális beavatkozás két kritikus D102-eleme hiányzik a protokollból: a kevert-számjegy kontroll (shuffled-digit) lépésképlete és a zéró-norma szabály, valamint a §6-ban említett Claim B érvénytelenségi ellenőrzések (különösen a „norm check” és D102(4c,4d,4f)) konkrét operatív definíciói és numerikus toleranciái.
Evidence: §5 csak az altér-projekciós lépést adja meg (`x_r + ((x_d − x_r) S) S^T`), de a kevert-számjegy kontroll nem altér-projekció, hanem `W^+ Π (W (x_d − x_r))` normailesztve Q lépésnormájához (`src/ncm_sudoku/e5causal.py:80-84`, D102(4d), D102 Final ASTRA-2); ez a képlet teljesen hiányzik `e5_protocol_v1.md`-ből. Szintén hiányzik a D102(4b) szabály (`target_norm == 0 -> exact zero step`, pozitív target + numerikusan nulla kontrollprojekció -> hiba, `tol = 1e-12` a `src/ncm_sudoku/e5causal.py:73-79`-ben). §6 a „norm check (D102(4f))” sikertelenségéhez Claim B érvénytelenségét köti, de nem ad meg toleranciát (fp32 visszaírás után `||x_after − x_before||` mindig tartalmaz ~1e-6 kerekítési eltérést), és `scripts/e5_causal.py:100-135` jelenleg nem is ellenőrzi a no-hook egyezést, a teljes 91 prefix-pozíciós self-donort, a valós-donor érték-ellenőrzést, a D102(4c) high-variance P2-logit invarianciát, a D102(4d) kevert logit-irányt, sem a `scale` és `hv`/`rand` koszinuszok naplózását (a `applied_ok` és `query_isolation_ok` is csak flag-ként mentődik).
Recommendation: Pótolni §5-ben a `W^+ Π (W Δ)` normailesztett képletet és a zéró-norma/zéró-projekció szabályt (`tol = 1e-12`), valamint §6-ban tételesen megadni minden Claim B-érvénytelenítő ellenőrzés (hash, hook-szám == 1, query- és nem-patchelt-prefix izoláció, no-hook és 91-pozíciós self-donor bitazonosság, valós-donor cellaellenőrzés, fp32 visszaírási norma-tolerancia, high-variance P2-logit invariancia tolerancia) pontos feltételét és toleranciáját.
Confidence: high
```

```
NEON-4 | major | e5_protocol_v1.md §5 (és src/ncm_sudoku/e5stats.py)
Claim: A §5 fogadásos teszt leírása összemossa a tervezett `N = 400` mintaméretet a szorzatba belépő jogosult párok számával (`n_elig`), elhagyja a `v_0 = 0,25` kezdőfeltételt, és nem kezeli a `n_elig = 0` határesetet.
Evidence: `docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md` Decision 2 kifejezetten rögzíti: „N in the bet is the planned number of pairs, and the number of eligible pairs entering each product is a separate, reported variable”, és `mu_0 = 1/2, v_0 = 1/4`. Ezzel szemben `e5_protocol_v1.md` §5 mindkettőre `N`-et ír (`lambda_{i+1} = min(sqrt(2 log 40 / (N v_i)), 0.75 / m0)`, `log K_N > log 40`) és nem adja meg `v_0 = 0,25`-öt `lambda_1`-hez. `src/ncm_sudoku/e5stats.py:39` szerint ha a TEST-futtató nem adja át expliciten `n_plan=400`-at, akkor `n_plan` alapértelmezésben `n`-re (`n_elig`-re) esik vissza, ami már egyetlen kizárt párnál is megváltoztatja az összes `lambda_i`-t; továbbá `n = 0` esetén `e5stats.betting_logk` a 44–45. soron alakhibával (`ValueError`) elszáll.
Recommendation: Rögzíteni §5-ben, hogy `v_0 = 0,25` (`lambda_1` ezt használja), a tétben mindig a fix tervezett `N_plan = 400` szerepel (a TEST-futtató expliciten `n_plan=400`-at ad át), a szorzat a nyers indexsorrendű `n_elig` jogosult páron fut (külön jelentett `n_elig_A`, `n_elig_B` nevezőkkel), és `n_elig = 0` esetén az állítás nem igazolható / nem becsülhető.
Confidence: high
```

```
NEON-5 | major | e5_protocol_v1.md §2, §3, §6, §9(2)–(5)
Claim: A zárolás előtti feladatok (§9) és a zárolási/eltérési szabályok (§6) több lényeges fagyasztási és tesztelési hézagot hagynak nyitva egy olyan protokollban, ahol a TEST-párok a git-tag után készülnek.
Evidence: (1) §9(4) szárazfutása PROBE-VAL-on csak a hibamentes utat teszteli (mind a 250 pár jogosult, 0 külső kizárás, 0 belső ütközés, 0 nem-véges érték, 0 integritáshiba), nem ellenőrzi a TEST-specifikus ágakat, holott D105(7) szintetikus teszteket ír elő a döntetlenkezelésre is a TEST generálása előtt (jelenleg csak `tests/test_e5stats.py` létezik). (2) §9(2) kifelejti `Q` mentését és hashelését, ellentmondva §4-nek („All are saved and hashed before the lock”; `runs/e5/causal/heads/` csak `P2.pt`, `P4.pt`, `P8.pt`-t tartalmaz, `Q`-t `np.linalg.svd` számolja újra). (3) Mivel a TEST-párok a zárolás *után* generálódnak, §2/§3 nem rögzíti a generátor-őrt (`FROZEN_NUMPY = "2.5.4"`, `generate.py` és `solve.py` SHA-256 a `src/ncm_sudoku/subsets.py:13-17`-ből), sem a szűrési halmazok azonosító hash-eit. (4) §6 2. pontja pontatlanul „A hash mismatch of any frozen artifact … makes claim B not confirmable”-t ír (a checkpoint- vagy generátor-hash eltérés mindkét állítást érvényteleníti), és §6-ból hiányzik a D105(5) „no optional stopping / N never changed after TEST outcomes” szabály, valamint a `research_plan_v3.7.md` §12.2 / `osf/registration.md` mintájára a verziózási szabály (utólagos módszertani változtatás -> új protokollverzió; TEST kimenet megtekintése utáni eltérés -> az érintett állítás exploratívvá válik).
Recommendation: Bővíteni §9-et: `Q` mentése és hashelése (§9(2)), dedikált szintetikus tesztek a TEST-futtató összes hiba- és peremágára (külső szűrés + indexléptetés, belső ütközés miatti leállás, `n_elig < 400`, 1-ULP-perturált bitazonos bemenetek döntetlenje, nem-véges leállás, Claim B integritási hibák), az összes fagyasztott artefaktum (beleértve `generate.py`, `solve.py`, `numpy 2.5.4`, checkpoint teljes hash-ek) zárolási táblázatának beemelése a protokollba még a tag előtt, és §6 kiegészítése az opcionális megállás tilalmával és a poszt-kimenet eltérések exploratív besorolásával.
Confidence: high
```

```
NEON-6 | major | e5_protocol_v1.md §7 és §9
Claim: A §7-ben előírt másodlagos és leíró szondaelemzésekhez (különösen a D66 whole-layer Z<=6 szondához és PCA-hoz, valamint a P0–P8 és B0–B8 görbékhez) nincsenek mentett fagyasztott modellek, és §9 sem tartalmazza az elkészítésüket; továbbá §7 elhagy három D101/D102-ben vállalt riport-elemet.
Evidence: `runs/e5/causal/heads/` kizárólag `P2.pt`, `P4.pt`, `P8.pt`-t tartalmaz, `scripts/e5_pilot.py` / `src/ncm_sudoku/e5pilot.py:124-129` a pilot során eldobta a modelleket és a `wholelayer.cell_pca_features` PCA objektumot. §9(1) csak a `z6` shared fejet refitteli és menti, így a §7-ben szereplő „Secondary readout of Z<=6 with the D66 whole-layer features” és „The P0–P8 curve and the global closing-BOS readout” végrehajtása nincs specifikálva (pl. fagyasztva lesznek-e a tag előtt, vagy PROBE-TRAIN/PROBE-VAL-on determinisztikusan újraillesztve, a PCA-t szigorúan PROBE-TRAIN-en illesztve). Továbbá §7-ből hiányzik: (a) a magonkénti W-AUC (D101(1): „per-seed W-AUC”), (b) a bit-poolozott W-AUC és az üres réteg `null` riportálása (D101(5)), valamint (c) a normalizált reprezentációs eltolódás minimális nevezővel és kizárt bitek számával (D102(5)).
Recommendation: Rögzíteni §7/§9-ben, hogy a másodlagos/leíró fejeket (legalább a D66 Z<=6 whole-layer szondát és PROBE-TRAIN PCA-ját) szintén elmentik és hashelik a tag előtt, vagy egyértelműen előírni a determinisztikus PROBE-TRAIN/PROBE-VAL újraillesztést (TEST-re soha nem illesztve/választva), és pótolni a hiányzó D101(1)/(5) és D102(5) riport-elemeket §7-ben.
Confidence: high
```

```
NEON-7 | minor | e5_protocol_v1.md §8
Claim: A NEON-1-en túl a §8 interpretációs táblából több D101/D102/D105-ben rögzített megkötés és kombináció hiányzik, illetve egy helyen túl tág megfogalmazás szerepel.
Evidence: (1) Hiányzik D102(7) kulcsfontosságú „nem következik” kitétele null Claim B esetére: nem következik, hogy a kódválasztás változatlan maradna (ezt az irányítatlan TV / argmax diagnosztikák mutatják), sem hogy a jelöltinformáció általában kihasználatlan. (2) §8 6. sora („Claims A and B hold”) „level-7 code choice is sensitive”-et ír, holott Claim B a T=1 softmax *kódeloszlás* TV-mozgását teszteli, nem az argmax kódválasztást (ellentétben a 4. sor pontos „level-7 code distribution” megfogalmazásával). (3) Az 1. sor nem említi, hogy Claim A az összes jogosult párra értendő (beleértve a pilotban ~60%-nyi kényszerített döntetlent, D105(3)), elhagyja a Δ > 0,25 küszöböt és a D101(1) kapacitás-megjegyzést (256-d vs. 512-d). (4) Hiányzik a külön sor/értelmezés a „Claim A holds, Claim B does not” és „Claim B holds, Claim A does not” esetekre a fő kutatási kérdés szempontjából.
Recommendation: Pontosítani a 6. sort „level-7 code distribution”-re, kiegészíteni az 1. sort a jogosult párok populációjával, Δ > 0,25-tel és a dimenzió/kapacitás megjegyzéssel, felvenni D102(7) null-ágának „Does not follow” kitételeit és a két vegyes kimenetű (csak A / csak B teljesül) sort.
Confidence: high
```

```
NEON-8 | minor | e5_protocol_v1.md §1, §3, §5
Claim: Önálló OSF-preregisztrációként olvasva (a `research_plan_v3.7.md` §11.4, §12.2 és `osf/registration.md` mintájához képest) hiányoznak a tervezési előzmények, a D106 erő- és FPR-tábla, valamint a becslési bootstrap részletei.
Evidence: §3 csak egy mondatban hivatkozik D106-ra („N = 400 … smallest grid point with power >= 0.9 … re-checked”), de nem közli sem a tervezési modellt (kauzális hatások felezve, κ = 0,7, W(Z) = 0,515), sem a rács- és újrafuttatási erőértékeket (`experiments/e5/power.json`: N=250/300/350/400 -> B erő 0,000/0,084/0,746/0,995; re-check A 0,997, B 0,998), sem a heterogén érzékenységi eset kritikus 0,9005-ös B-erejét (nulla tartalék a 0,9 küszöb felett), sem a null-határ FPR-eket (<= 0,0014), sem a szimulációs seedeket (`2026112701..3`). Hasonlóképp hiányzik a D94–D96/D98 pozitív-kontroll kapu és a már megfigyelt pilot-adatok összefoglalása (lásd `osf/registration.md` „Existing data and what has been observed”), §5-ből a bootstrap típusa/szintje/seedje (percentilis, 95%, seed 0 a `scripts/e5_causal.py:55`-ben), és §3-ból D105(2) megjegyzése, hogy a hibagarancia a teljes ütközéskezelő eljárásra vonatkozik, nem feltételesen az ütközésmentes esetre.
Recommendation: Rövid, önálló táblázattal/bekezdéssel kiegészíteni §1/§3-at (pozitív-kontroll kapu és megfigyelt pilot-adatok, D106 erő- és FPR-tábla a heterogén esettel és seedekkel), valamint §5-ben rögzíteni a becslési bootstrap pontos specifikációját (percentilis, 95%, 10 000 újraminta, seed 0).
Confidence: high
```

```
NEON-9 | minor | e5_protocol_v1.md §10
Claim: A §10 számítási költségbecslésben idézett „0.5 s to 1.7 s per puzzle” extrakciós időtartomány nem egyezik a hivatkozott mérési fájlokkal.
Evidence: `experiments/e5/extract.json` mért értékei: `probe_train/a` 1465,4 s / 1000 = 1,465 s/puzzle, `probe_train/b` 1132,4 s / 1000 = 1,132 s/puzzle, `probe_val/a` 209,8 s / 250 = 0,839 s/puzzle, `probe_val/b` 212,7 s / 250 = 0,851 s/puzzle. `experiments/e5/cost.json` értékei: `plain_per_puzzle = 1.7052 s`, `capture_per_puzzle = 1.769 s`. A tényleges tartomány 0,84–1,77 s/puzzle (nem 0,5–1,7 s; a 800 rejtvényre adott „under 1 h” becslés ettől függetlenül igaz, kb. 11–24 perc).
Recommendation: Javítani §10-ben „about 0.5 s to 1.7 s per puzzle”-ről „about 0.84 s to 1.77 s per puzzle”-re.
Confidence: high
```

```
NEON-10 | nit | e5_protocol_v1.md §2 és §6
Claim: §2 csonkolt hash-eket és commit-azonosítókat használ teljes azonosítók helyett, §6 pedig „non-finite model output”-ot ír a nem-véges szondapredikciók (D101(5)) és reprezentációs logitok (D102(5)) explicit említése nélkül.
Evidence: §2-ben `d342ce8a`, `9e0bfe44…df8b8`, `3bc6aeca…80c0b`, `8d58c49e…8df2f`, `c7027427` szerepel a `experiments/provenance/checkpoints.json`-ban és `research_plan_v3.7.md` §12.2-ben használt teljes 64 karakteres SHA-256 és 40 karakteres git commit hash helyett. §6 1. pontja csak „non-finite model output”-ot említ, míg D101(5) „non-finite prediction on an evaluable bit” és D102(5) „non-finite value” esetén is leállást ír elő.
Recommendation: A zárolás előtt teljes hash-eket beírni §2-be, és §6 1. pontját „any non-finite model output, probe prediction, or representational logit” szövegre pontosítani.
Confidence: high
```

### Claims checked
- **§2 checkpoint revízió és SHA-256 prefixek/szuffixek (`d342ce8a`, `9e0bfe44…df8b8`, `3bc6aeca…80c0b`, `8d58c49e…8df2f`, upstream `c7027427`)** — **holds** (`experiments/provenance/checkpoints.json`).
- **§2 `ncm_sudoku.model.load_model` csak `weights_only=True` módban tölt** — **holds** (`src/ncm_sudoku/model.py:34,57,60`).
- **§3 párosítási sémák (`e5pairs.py`: `random_solution`, 30 clue, egyedi megoldás, `[seed, index, 0/1/2]`, eltérő clue-maszkig újrahúzott B, namespace 8/9/10)** — **holds** (`src/ncm_sudoku/e5pairs.py:24,42-64`).
- **§3 N = 400 (D106: legkisebb rácspont >= 0,9 erővel mindkét állításra, re-check átment)** — **holds** (`experiments/e5/power.json`, `scripts/e5_power.py:92-120`).
- **§4 extrakció (`e5extract.py`: 7. szintű passz = index 6, 0–8 rétegek, 81 prefix-cella, `cumulative_states` 6. szint, kódok, solved; `labels.candidate_mask`)** — **holds**, azzal az eltéréssel, hogy `prefix_cells` fp16-ban tárolódik (`src/ncm_sudoku/e5extract.py:21-67`, `src/ncm_sudoku/states.py:17-29`, `src/ncm_sudoku/labels.py:26-34`).
- **§4 P2 és P3 holtversenye 1,0 átlagos páronkénti W-AUC-on PROBE-VAL-on, P2 alacsonyabb Brier-rel** — **holds** (`experiments/e5/pilot/P2__shared__none.json`: Brier `1.95e-6`, mind a 250 `per_pair = 1.0`; `P3__shared__none.json`: Brier `9.04e-5`, mind a 250 `per_pair = 1.0`).
- **§4 P2, P4, P8 fejek elmentve és bitazonosak a pilot predikciókkal** — **holds** (`runs/e5/causal/heads/{P2,P4,P8}.pt`, `experiments/e5/causal/heads.json`: `max_abs_diff_vs_pilot = 0.0`).
- **§4 kauzális komponensek (`Q`, high-variance bázis, `d -> d+1 (mod 9)` derangement, 20 random bázis seed 1000–1019 float64 QR pozitív R-átlóval)** — **holds** (`src/ncm_sudoku/e5causal.py:45-93`, `scripts/e5_causal.py:74-83`; viszont `Q` és a többi bázis még nincs elmentve).
- **§5 `intervene.level_logits(..., level=7)`, `blocks[1]` kimenet patchelése, T=1 softmax 16 kódon és 18 lekérdezésen, irányított TV-hatás** — **holds** (`src/ncm_sudoku/intervene.py:124-156`, `src/ncm_sudoku/e5causal.py:129,151-158`, `scripts/e5_causal.py:137-143`).
- **§5 `ncm_sudoku.e5stats` képlete és transzformált nullhatárai (0,47 / 0,47 / 0,625 / 0,505 / 0,5)** — **holds** (`src/ncm_sudoku/e5stats.py:19-65`, `tests/test_e5stats.py`; `v_0 = 0,25` és `n_plan` vs. `n_elig` hiányzik a §5 szövegéből).
- **§9(1) `e5causal.refit_head` használhatósága a `z6` fejre** — **holds** (`src/ncm_sudoku/e5causal.py:21-42` nem használja a beégetett `STATE_DIM = 512` konstansát, csak a `state_weights` és `head_logits` függvények).
- **§9(4) a pilot `z6` PROBE-VAL W-AUC pontos reprodukálhatósága a D101(5) bitazonos-bemenet döntetlenszabállyal** — **could not verify** (read-only környezetben futtatás nélkül a `runs/e5/pilot/z6__shared__none.npy` 15 249 lokálisan azonos `z6` diszkordáns bitjén előforduló esetleges 1-ULP eltérések száma nem volt közvetlenül megszámolható; a `z6__shared__none.json`-ban `codes_same = 0.5` pontos).
- **§10 extrakciós sebesség „0.5 s to 1.7 s per puzzle”** — **does not hold** (`experiments/e5/extract.json`: 0,839–1,465 s/puzzle; `experiments/e5/cost.json`: 1,705–1,769 s/puzzle).
- **§10 kauzális kiértékelés „about 31 min per 250 pairs with 20 random draws” (~50 min / 400 pár)** — **holds** (`experiments/e5/causal/primary.json`: `1844.3 s` = 30,74 perc -> 400 párra 49,2 perc).

VERDICT: PASS

The read-only review objective is satisfied:
- The delivered response follows `.reviews/e5-protocol-v1/round-1/brief.neon.md` (Hungarian language, structured findings blocks with `Evidence`/`Recommendation`/`Confidence`, and a `### Claims checked` section using `holds` / `does not hold` / `could not verify`).
- Independent spot-checks against `e5_protocol_v1.md`, `experiments/provenance/checkpoints.json`, `experiments/e5/extract.json`, `experiments/e5/cost.json`, `src/ncm_sudoku/e5causal.py`, `src/ncm_sudoku/e5stats.py`, and `src/ncm_sudoku/e5extract.py` confirm the accuracy of the verified code/data claims (including the extraction-speed discrepancy `0.839–1.465 s` / `1.705–1.769 s` vs. the protocol's `0.5 s to 1.7 s`, fp16 storage of `prefix_cells`, `refit_head` independence from `STATE_DIM = 512`, omitted `v_0 = 0.25` / `n_plan` vs. `n_elig`, and abbreviated checkpoint hashes).
- The blocked `powershell` action (`actionId: bb710c46-e350-4e20-b5b8-612d12320944`) is explicitly named in the worker summary and is not required to complete this read-only review (the brief permits marking unexecutable checks as `could not verify`).

Note on blocked tool action: a single read-only verification attempt via powershell (actionId:
bb710c46-e350-4e20-b5b8-612d12320944, running uv run --locked python to inspect
runs/e5/pilot/z6__shared__none.npy) was denied under the read-only policy and was not retried; the
review was completed entirely via read-only file and search tools, with that single unexecutable
check explicitly marked could not verify.

Blocked actions:

 - shell (tool call call_MHx1YnJuZkJqdlU4RlBQN2tpRmI)

