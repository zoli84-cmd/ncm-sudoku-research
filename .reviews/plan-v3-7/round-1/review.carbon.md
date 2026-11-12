Elolvasom a review briefet (`brief.carbon.md`), hogy pontosan kövessem az abban foglalt szempontokat és elvárásokat.

Elolvastam a bírálati kiírást (`brief.carbon.md`). Most áttekintem a `v3.6-to-v3.7.diff` változásokat, a `research_plan_v3.7.md` tervet, a `DECISIONS.md` D53–D71 sorait, valamint a v3.6 bírálati naplót.

Most beolvasom a kutatási terv fennmaradó fejezeteit (`§5–§10`, `§14–§16`), a `DECISIONS.md` végét (D65–D71), valamint a zárolási és származási eredményfájlokat.

### Verdict
A `research_plan_v3.7.md` módszertanilag megalapozott és közel áll a végleges preregisztrációs zároláshoz (az `H1` kétoldali `98,33%`-os tesztjének és `96,67%`-os családszintű `±0,01` TOST ekvivalenciájának együttes használata a partícionálási elv alapján erős értelemben megtartja az `5%`-os FWER-t, a `TEST` érintetlen, és minden ellenőrzött számérték/SHA-256 hash egyezik a repóval), de a git-tag és az OSF-zárolás előtt két lényeges specifikációs hiányosságot pótolni kell. A legfontosabb módosítás az `E2` **11., 2. és 6. szintű befagyasztott CAL kódgyakoriságainak** rögzítése a §12.2-ben és az `e2p2` futtatóban (hogy az elsődleges `H2` kontraszt ne a `TEST`-ből becsülje a 11. szint gyakoriságait), valamint az `H1` **cellareláció-alapú egészréteg-probe** reprodukálhatósági részleteinek (a CPython `frozenset` iterációtól függő szomszédsorrend, a ranghiányos PCA-fehérítési küszöb, a permutációs seedek és a már kiválasztott `PROBE-VAL` hiperparaméterek) explicit rögzítése.

### Findings

```
CARBON-1 | major | research_plan_v3.7.md:174, 180, 204, 420, src/ncm_sudoku/e2p2.py:39, 98, 111, experiments/e2p2/summary.json:10-27
Claim: A §12.2 zárolási táblázat és az `experiments/e2p2/summary.json` kizárólag az 1. szintű CAL kódgyakoriságokat rögzíti, miközben a §7.2 szerint a `TEST`-en az elsődleges `H2` kontraszt ($\theta_2$, 1 vs. 11. szint), a másodlagos $\theta_2'$ (2 vs. 11. szint) és a 6 vs. 11 dózisgörbe is befagyasztott CAL-gyakoriságokat igényel, az `e2p2.run_pilot2` pedig jelenleg magából az átadott adathalmazból számolja újra a 2., 6. és 11. szint gyakoriságait.
Evidence: A `research_plan_v3.7.md:174, 180, 204` rögzíti, hogy minden szinten a CAL generált kódgyakoriságai alapján történik a csere („estimated on CAL”, „TEST uses the frozen CAL vector”, „Perturbation policies and doses are chosen on CAL data, then the choice is frozen”). Ezzel szemben a `src/ncm_sudoku/e2p2.py:39, 98, 111` csak a `freqs_level1`-et menti ki, a `LEVELS_P2 = (2, 6, 11)` ciklusban pedig a `freqs = code_frequencies(A, m.levels)[level - 1]` sort futtatja az aktuális bemenet `A` kódjain; így a `summary.json` nem tartalmazza a 2., 6. és 11. szint CAL-eloszlását, és a kód közvetlen `TEST`-futtatása tiltott módon a `TEST` saját kódjaiból becsülné a cseresúlyokat. Emellett a §12.2 (`line 420`) nem nevezi meg a `perturb.run_seed(level, policy, dose, seed)` (`seeds = (0, 1, 2)`) és a bootstrap `seed = 0` (`e2p2.interval`) szabályt.
Recommendation: Számítsák ki a 300 befagyasztott CAL-feladvány `A` kódjaiból a 2. (`600` pozíció), 6. (`3900` pozíció) és 11. (`20 100` pozíció) szint kódgyakoriságait/darabszámait, vegyék fel őket az `experiments/e2p2/summary.json`-ba és a `research_plan_v3.7.md:420` sorába (a `perturb.run_seed` és a bootstrap `seed = 0` megjelölésével), a konfirmatív E2-futtatóban pedig kívülről adják át a befagyasztott CAL-gyakoriságokat.
Confidence: high
```

```
CARBON-2 | major | research_plan_v3.7.md:229-232, 246, 422, src/ncm_sudoku/grid.py:26-28, src/ncm_sudoku/e3data.py:25, src/ncm_sudoku/wholelayer.py:32, 51, 60-68, src/ncm_sudoku/e3controls.py:31
Claim: Az új elsődleges `H1` (cellareláció-alapú egészréteg) probe a terv szövegéből önmagában nem reprodukálható: a „fixed peer order” a kódban egy rendezetlen Python `frozenset` CPython-specifikus hash-tábla sorrendjét használja, továbbá hiányzik a ranghiányos PCA-fehérítési és előjelszabály, a kontrollok RNG-seedje, valamint a `PROBE-VAL`-on már kiválasztott hiperparaméterek rögzítése.
Evidence: A `src/ncm_sudoku/grid.py:26-28` a `PEERS[c]` halmazt `frozenset`-ként építi fel, az `e3data.py:25` (`_PEERS_IDX = np.array([list(PEERS[c]) for c in range(81)])`) és a `wholelayer.py:32` (`PEER_IDX`) pedig `sorted()` nélkül alakítja listává; 64 slotos CPython `frozenset` táblában pl. $c=0$-ra a `72 & 63 == 8` ütközés miatt a `72`-es cella a `12.` slotba, a `18..63` indexek elé kerül, a `tests/test_wholelayer.py:72` pedig csak a `list(PEERS[c])`-vel való egyezést teszteli. A `raw_features` üres celláin a saját `blank` one-hot konstans és a 20 szomszéd one-hot összege 1, ezért a 210 dimenzióból legalább 30 sajátérték pontosan 0: a „whitened PCA, all 210 components” (`line 232`) csak a `wholelayer.py:51, 60-68` szabályaival (`1/N` kovariancia, legnagyobb abszolút értékű elem pozitív előjele, `lam <= 1e-10 * lam_max` esetén `scale = 1.0`) értelmezett. Végül a `scripts/e3_wholelayer.py:110-120` nem menti le a 6. szintű modelleket, így a WP2-nek újra kell tanítania őket, de a terv nem rögzíti az `e3controls.py:31, 198, 203` seedjeit (`PERMUTE_SEED_TRAIN=11`, `PERMUTE_SEED_VAL=12`, random/label-permutáció `seed=0`, tie-break `probes.py:183`) és a már ismert `PROBE-VAL` `(wd, lr)` optimumokat (`[0.1, 0.001]` L06/L12-re, `[0, 0.003]` a nyers kontrollokra, `wholelayer_report.md:13-19`).
Recommendation: Ha a D67/D71 számokat változatlanul kívánják zárolni, rögzítsék a §8.1/§12.2-ben a `wholelayer.PEER_IDX` pontos definícióját és bájtszintű SHA-256 hash-ét (vagy ha újrafuttatható a ~80 perces D67+D70 lánc, váltsanak `sorted(PEERS[c])` sorrendre), írják bele a §8.1-be az `1/N` kovarianciát, az előjel-normalizálást és a `1e-10` relatív sajátérték-küszöböt, a §8.2/§12.2-be pedig a `(11, 12; 0)` kontroll-seedeket és a `PROBE-VAL`-on kiválasztott `(wd, lr)` párokat.
Confidence: high
```

```
CARBON-3 | minor | research_plan_v3.7.md:227, 260, src/ncm_sudoku/probes.py:258-276, src/ncm_sudoku/e3controls.py:92-100, 215-217, scripts/e3_probes.py:92-94
Claim: A §8.1 előírása („TEST predictions are averaged over the three seed models”) ellentmond a kódbázis összes Brier-végpontjának, amelyek a három seed-modell külön számított puzzle-szintű Brier-veszteségeinek átlagát (`mean_s B(p_s, y)`) használják a seed-átlagolt predikciók Brier-vesztesége (`B(mean_s p_s, y)`) helyett.
Evidence: A négyzetre emelés szigorú konvexitása (Jensen-egyenlőtlenség) miatt `B(mean_s p_s, y) = mean_s B(p_s, y) - Var_s(p_s)`. A `probes.py:265-272` (`per_puzzle = per_puzzle_sum / len(SEEDS)`), az `e3_probes.py:92-94` docstringje („the scale of every headline Brier: mean over seeds, not the Brier of the seed-averaged prediction”), az `e3_wholelayer.py:120-121` (amelyből a `lock_power.py` bemenete készült) és az `e3equiv.py:67-69` egyaránt a seedenkénti Brier-ek átlagát számolja, míg a seed-átlagolt `preds` csak a küszöbölt/rangsoroló metrikákhoz (`exact_match`, `roc_auc`, `e3controls.py:215-217`) szolgál.
Recommendation: Pontosítsák a `research_plan_v3.7.md:227` mondatát a kóddal összhangban: a Brier-alapú végpontok ($\theta_1$, $\theta_T$, kontrollok, mélységi és ekvivariancia-Brier) a három seed-modell puzzle-szintű Brier-veszteségét átlagolják, míg a küszöbölt és rangsoroló másodlagos metrikák (F1, PR-AUC, exact match, ROC-AUC) a három seed átlagolt predikcióit használják.
Confidence: high
```

```
CARBON-4 | minor | research_plan_v3.7.md:229, 262, 387, src/ncm_sudoku/power.py:30-52, experiments/e2p2/sample_size_e2.json:10-12
Claim: A §8.1/§8.3 nem tartalmaz a §7.2-höz („Why level 1”) hasonló, önállóan is világos zárolás előtti adaptációs indoklást az `H1` probe- és tesztváltásáról, a §11.4 pedig pontatlanul a pilot előjeles átlagával (`mean 0.0011`) indokolja a `sign-mixing` kivitelezhetetlenségét az abszolút átlag (`mean|x| = 0.0100 < 0.03`) helyett, és nem jelzi a `±1` injektálás konzervativitását.
Evidence: A v3.6 §8.1 (`v3.6-to-v3.7.diff:26`) eredetileg csak hozzáférhetetlen vagy nem megfelelő alakú cellaállapot esetére kötötte ki az egészréteg-probe-ot; ténylegesen a váltás és a `±0,01`-es TOST bevezetése a nullközeli `PROBE-VAL` eredmények (`0,0018` cellánként D64-ben, `0,0031` egészréteggel D67-ben) megismerése után, érintetlen `TEST` mellett történt (ami az ekvivalencia-állításra nézve szigorúbb, konzervatív választás). A `src/ncm_sudoku/power.py:31-32` és a `sample_size_e2.json:11` szerint a `sign_mix` azért dob `ValueError`-t, mert `mean|x| = 0.0100 < 0.0300` (nem `mean(x) = 0.0011` miatt). Emellett a `power.inject` (`power.py:39-52`) teljes `±1` puzzle-ugrásokat injektál ($\mathbb{E}[N_{\mathrm{nz}}]\approx 25\text{--}27$, `7–11%` ritkaesemény-ág, `0,025`/`0,036` hibaarány); egy-seedes `±1/3` ugrásoknál ($\mathbb{E}[N_{\mathrm{nz}}]\approx 54$) a ritkaesemény-ág nem aktiválódik, és a percentilis-bootstrap ferdesége ~5–6% körüli határhibát ad.
Recommendation: Egészítsék ki a §8.1/§8.3-at egy rövid „Why cell-relative whole-layer and ±0.01 equivalence (v3.7)” megjegyzéssel (jelezve, hogy a váltás `PROBE-VAL`-on, érintetlen `TEST` mellett történt, és a `0,0018`-as cellánkénti probe másodlagos maradt), a `research_plan_v3.7.md:387` sorban javítsák a `(mean 0.0011)`-et `(mean absolute difference 0.0100 < 0.03)`-ra, és nevezzék meg, hogy a `±1` injektálás alacsony diszkordanciájú határellenőrzés.
Confidence: high
```

```
CARBON-5 | minor | research_plan_v3.7.md:79, 281, 418, 421, 424, src/ncm_sudoku/e3equiv.py:48, 74-85, experiments/e2p2/summary.json:2024-2027, experiments/provenance/released_data.json
Claim: Három zárolási/végrehajtási pontatlanság maradt a §12.2-ben és a §8.4-ben: a 6 vs. 11 AUC-tartomány alsó határának lefelé kerekítése (`3.29e-5`) sérti a §7.3 extrapolációs tilalmát, az `e3equiv.equivariance_pilot` nem fogadja kívülről a rögzített `0.0116`-os küszöböt, a `TEST` hash-formátumok és a `released_data.json` hash-ek pedig nem szerepelnek közvetlenül a tervszövegben.
Evidence: Az `experiments/e2p2/summary.json:2025-2027` pontos tartománya `[3.291773618630916e-05, 7.930234551597304e-05]`, ahol az alsó végpont a 11. szint legkisebb CAL-csomópontja; a `3.29e-5`-re kerekített alsó határt még maga a CAL-görbe sem fedi le (`3.2918e-5 > 3.2900e-5`). A `src/ncm_sudoku/e3equiv.py:48, 74-85` az első `n=200` feladványt veszi (`puzzles[:n]`), és mindig újraszámolja az `acceptable = np.percentile(seed_noise, 95)` küszöböt az aktuális bemeneten a `PROBE-VAL`-on zárolt `0.0116` (`0.01164455...`) helyett; emellett a §12.2 (`line 424`) `Decision` oszlopa még „augmented and non-augmented tests separate”-et (a §3 `line 79` pedig „family-holdout”-ot) említ, noha csak a nem-augmentált 12. szintű vizsgálat van specifikálva. A §12.2 (`line 418`) a `TEST` bájtsorrend/JSON-szabályát az `experiments/lock/test_set.json`-ra utalja ki, és elhagyja a másodlagos rétegként használt `hazyresearch/ncm-datasets` revízióját (`6580ba41...`) és pickle SHA-256 hash-eit (`experiments/provenance/released_data.json`).
Recommendation: Írják be a §12.2 (`line 421`) sorába a `summary.json` teljes pontosságú AUC-határait; a §8.4/§12.2-ben rögzítsék az „első 200 `TEST`-feladvány (`0..199`)” kiválasztását, tisztázzák, hogy a zárolás csak a nem-augmentált ekvivariancia-tesztet tartalmazza (a WP2 kódban pedig adják át paraméterként a rögzített `acceptable` küszöböt az `equivariance_pilot`-nak); végül írják be közvetlenül a §12.2 (`line 418`) sorába a `TEST` hash-formátumokat (`UTF-8 json.dumps(ids)`, `(600, 81)` `uint8` C-order nyers bájtok, `0=üres`) és a `released_data.json` hash-eit.
Confidence: high
```

```
CARBON-6 | nit | research_plan_v3.7.md:6, 240-243, 270, 273, 396, 424, 490
Claim: Néhány zárolás előtti megfogalmazás és apró kereszthivatkozási pontatlanság bent maradt a §1–§16 szövegében.
Evidence: A `Status:` sor (`line 6`) `D53–D70`-et ír `D53–D71` helyett (vö. `line 569` és a §12.2-ben idézett `D71`); a §8.3 (`line 273`) még nyitva hagyja, hogy a `0,5`-től eltérő valószínűségi küszöb választható a `PROBE-VAL`-on, pedig a `PROBE-VAL` lezárult; a §8.3 (`line 270`) az egység–számjegy probe-nál nem nevezi meg explicit a 6. szintet és a 10 dimenziós sajátcella-one-hot átlagolást (`e3controls.py:223`), a §8.2/§12.2 (`lines 240-243, 424`) pedig nem mondja ki, hogy a fő E3 tábla `random`, `label-permutation` és 2./6. szintű `teacher` sorai az 512 dimenziós egészréteg- vagy a 256 dimenziós cellánkénti bemenetet használják-e (illetve mi a D57 második clue-maszkos teacher-ellenőrzés státusza); végül a §12.1 (`line 396`) és a §14.2 (`line 490`) zárolás előtti igeidőt használ.
Recommendation: Javítsák a `D53–D71` hivatkozást, fagyasszák be véglegesen a `0,5`-ös küszöböt a `line 273`-ban, egy-egy szóval rögzítsék az egység–számjegy szintjét és az E3 kontrollsorok bemeneti reprezentációját, valamint pontosítsák a `lines 396, 490` történeti utalásait.
Confidence: high
```

### Claims checked
*(Megjegyzés: egy `uv run` olvasási segédparancsot a futtatókörnyezet a csak-olvasási szabály védelmében elutasított; a parancsot nem próbáltuk újra, minden számot, hash-t és kódállítást közvetlenül a repó fájljainak olvasásával ellenőriztünk, és egyetlen fájlt sem módosítottunk.)*

- **`H1` kétoldali `98,33%` + családszintű `96,67%` TOST multiplicitás-kontrollja és §13 értelmezése (§3, §8.3, §11.1, §13):** $H_{0,\text{diff}}: \theta_1 = 0$ és $H_{0,\text{eq}}: |\theta_1| \ge 0{,}01$ diszjunkt paramétertartományok, és $|\theta_1| \ge 0{,}01$ esetén a téves előjelű szignifikancia ($\{U_{98{,}33\%} < 0\}$) részhalmaza a TOST felső egyoldali elutasítási eseményének ($\{U_{96{,}67\%} < 0{,}01\}$), így `H1` teljes I. fajú hibája minden valós $\theta_1$-re $\le 0{,}05/3$, a `{H1, H2, H3}` család erős FWER-je pedig $\le 0{,}05$; a §13 (`lines 457-460`) helyesen választja szét a statisztikai detektálhatóságot és a gyakorlati küszöböt — **holds**.
- **Egészréteg-probe eredmények, PCA és költségkeret-érzékenység (§8.1, §8.3, §12.1; D66–D69):** `L06` generált `0.2304` vs. permutált `0.2335` ($\hat\theta_1 = 0.00311$, relatív `1.33%`), cellánkénti `L06` $\hat\theta_1 = 0.00183` (`probes.json`), `L12` generált `0.1833` vs. permutált `0.2336` ($\hat\theta_1 = 0.0503`), `teacher_L12` `0.1836` ($\hat\theta_T = 0.00031$), `3×` lépésszám (`min_steps=6000`) mellett `L06` $\hat\theta_1 = 0.00315` (`+0.00004` eltérés, `experiments/e3prep/wholelayer.json`, `budget_sensitivity/wholelayer.json`) — **holds** (a `PEER_IDX` és PCA-peremszabályok szöveges rögzítésével, lásd `CARBON-2`, `CARBON-3`).
- **Nyers bemeneti kontroll (`projected 0.0014` vs. `unprojected 0.0105`, §8.1):** `wholelayer.json` szerint `raw_projected = 0.001440`, `raw_unprojected = 0.010508`, mindkettő `[0, 0.003]`, `2628` paraméter, `2000` lépés (`hit_cap = True`), `explained_variance_share_val = 1.0000`; mivel `k = 210` megtartja a teljes affin alteret (`wd = 0`), a két modellosztály azonos információt lát, és a különbséget valóban a fehérítetlen ritka bináris bemenet lépésszám-korlátja okozza — **holds**.
- **§11.4 mintaelemszám- és hibaszimulációs értékek (`experiments/lock/power.json`, `sample_size_e2.json`, `sample_size_h1.json`, `src/ncm_sudoku/power.py`):** `TEST = 600`; E2 igények `200` (thinning), `400` (sign-mixing), `300` (H3), `600` (ekvivalencia); H1 eltolt küszöbön `100`; H1 családszintű TOST erő `1.000` (`0` és `0.0031` várható értéknél), hamis ekvivalencia `0.016` (`+0.01`) és `0.014` (`-0.01`), `500` minta × `2000` bootstrap; E2 `2 vs. 11` injektálásos hamis ekvivalencia `0.0245` (`0.025`, `+0.03`) és `0.0365` (`0.036`, `-0.03`), MC SE `0.0035`/`0.0042`, ritkaesemény-ág aránya `11.1%`/`7.0%`, mindkettő `< 0.05` — **holds** (`mean|x| = 0.0100` pontosítással, lásd `CARBON-4`).
- **§12.1 és E2 pilot-2 számok (`experiments/e2p2/summary.json`):** $\hat\theta_2 = -0.0894$ (`-0.089`), $\hat\theta_{\mathrm{comp}} = +0.0074$ (`+0.007`), $\hat\theta_2' = +0.0011$ (`+0.001`, ritkaesemény-korlát `±0.0303`), sham eltérés `0`, `freqs_level1 * 300 = [29, 34, 0, 31, 0, 22, 3, 36, 0, 1, 20, 43, 0, 29, 25, 27]` (összeg `300`), `6 vs. 11` közös TV-tartomány `[3.2918e-5, 7.9302e-5]`, `2 vs. 11` nem pozitív szélességű — **holds** (a 2., 6., 11. szintű CAL-gyakoriságok hiányával és az alsó AUC-határ kerekítésével, lásd `CARBON-1`, `CARBON-5`).
- **§12.2 modell-, generátor-, címkéző- és `TEST`-azonosító SHA-256 hash-ek (`checkpoints.json`, `subsets.py`, `extract.json`, `test_set.json`, `lock_test_set.py`):** a checkpoint revízió (`d342ce8a...`), a három checkpoint-fájl SHA-256 hash-e, az upstream commit (`c7027427...`), a `generate.py` (`57a8bfe5...`), `solve.py` (`9f3e6df5...`), `labels.py` (`495f9d8b...`) hash-ek, a `6400` rácsos kanonikus szűrés (`0` osztály, `0` duplikátum) és a `600` `TEST` feladvány `ids`/`puzzles`/`solutions` SHA-256 hash-ei karakterre egyeznek az elkötelezett JSON-fájlokkal és a kód konstansaival — **holds** (a git-ignorált `checkpoints/` és `runs/lock/test/*.npy` nyers bájtokat subprocess nélkül nem hash-eltük újra: **could not verify** közvetlenül a lemezről, de az elkötelezett `provenance`/`lock` rekordokkal és `assert_generator_frozen()`-nel konzisztens).
- **§8.4 és §13 12. szintű ekvivariancia (`experiments/lock/equivariance_l12.json`, `src/ncm_sudoku/e3equiv.py`, `scripts/lock_equiv_l12.py`):** elfogadható eltérés `0.011645` (`0.0116`, P95 seed-zaj), átlagos eltérés `0.0789` (`0.079`, `0%` határon belül), transzformált vs. eredeti Brier `0.18283` vs. `0.18278` (`0.1828 vs. 0.1828`), `matches_d67: true`; a §13 óvatos értelmezése indokolt, különösen mivel maga a nem-augmentált kiolvasó (`PEER_IDX` + pozíció one-hot) sem szimmetria-ekvivariáns — **holds** (lásd `CARBON-5` az `acceptable` paraméterezéséről).



VERDICT: PASS

Independent verification confirms that the objective is fully satisfied:

1. **Read-only compliance & blocked-action reporting:** No repository files were created, modified, or deleted by the worker. One `powershell` command (`uv run python -c ...` to compute SHA-256 hashes and level-1 counts) was blocked by runtime permissions; completing the review did not require it because all cited JSON artifacts and source files were inspected directly via read-only tools, and `<worker_summary>` explicitly names the blocked action (with a corresponding note and `could not verify` qualification for un-rehashed raw binary files under `### Claims checked`, as permitted by `brief.carbon.md`).
2. **Exact adherence to `brief.carbon.md`:**
   - Written in Hungarian within the ~2,000-word limit (~1,450 words) and emitted as the final response.
   - Uses the exact required sections and schema: `### Verdict` (two sentences), `### Findings` (`CARBON-1`..`CARBON-6`, ordered `major` → `minor` → `nit`, with 1 nit ≤ 3 max, each with `Claim`, `Evidence`, `Recommendation`, `Confidence`), and `### Claims checked` (`holds` / `could not verify`).
   - Did not access out-of-scope files (`C:\Users\ako2bp\AGENTS.md`) and respected `.reviews/plan-v3-6/decisions.md`.
3. **Factual accuracy against repository artifacts:** Cross-checking `research_plan_v3.7.md`, `v3.6-to-v3.7.diff`, `DECISIONS.md` (D53–D71), `experiments/lock/{power,test_set,equivariance_l12}.json`, and `experiments/provenance/checkpoints.json` confirms the verified numbers and hashes (TEST = 600, 6,400-grid canonical screen with 0 duplicates/classes, checkpoint/generator/labeler/TEST SHA-256s, E2 boundary false-equivalence rates 0.025/0.036 with 7–11% bound share, H1 family-level TOST power 1.000 and false-equivalence 0.016/0.014, level-12 equivariance tolerance 0.0116, deviation 0.079, and Brier 0.1828 vs. 0.1828) as well as the substantive code-vs-plan gaps reported in `CARBON-1`..`CARBON-6`.

A csak olvasható preregisztrációs felülvizsgálat (research_plan_v3.7.md, brief.carbon.md szerint)
elkészült és a teljes magyar nyelvű jelentés (### Verdict, ### Findings CARBON-1..CARBON-6, ###
Claims checked) kiadásra került; egyetlen fájlt sem hoztunk létre, módosítottunk vagy töröltünk.

Fő összefoglaló:

 - Verdict: A research_plan_v3.7.md módszertanilag megalapozott (H1 kétoldali 98,33%-os tesztje és
96,67%-os családszintű ±0,01 TOST ekvivalenciája megtartja az 5%-os erős FWER-t, a TEST érintetlen,
az ellenőrzött számok és SHA-256 hash-ek egyeznek), de a zárolás előtt két major hiányosságot
javasolt pótolni:
  1. CARBON-1 (major): Az E2 2.,
   6. és
  11. szintű befagyasztott CAL kódgyakoriságainak rögzítése a §12.2-ben és az
experiments/e2p2/summary.json-ban, valamint az e2p2.run_pilot2 módosítása úgy, hogy TEST-en ne a
TEST saját kódjaiból becsülje a cseresúlyokat.
  2. CARBON-2 (major): Az elsődleges H1 egészréteg-probe önálló szöveges reprodukálhatósága a
§8.1/§8.2/§12.2-ben (wholelayer.PEER_IDX CPython frozenset iterációs sorrendje, 1/N kovariancia +
előjel-normalizálás + 1e-10 relatív sajátérték-küszöb a ranghiányos raw_features fehérítéséhez, a
(11, 12; 0) kontroll-seedek és a már kiválasztott PROBE-VAL (wd, lr) konfigurációk rögzítése).
 - További megállapítások: CARBON-3 (minor, seedenkénti Brier-átlag vs. seed-átlagolt predikciók
Brier-vesztesége a §8.1 line 227 és a probes.py között), CARBON-4 (minor, explicit PROBE-VAL
adaptációs indoklás a §8.1/§8.3-ban és mean|x| = 0.0100 < 0.03 pontosítás a §11.4-ben), CARBON-5
(minor, summary.json pontos AUC-határai, equivariance_pilot külső acceptable paramétere, TEST
hash-formátumok és released_data.json hash-ek beemelése a §12.2-be), CARBON-6 (nit, apró D53–D71 és
zárolás előtti igeidő/küszöb-megfogalmazások).

Blocked actions:

 - powershell (uv run python -c ... SHA-256 ellenőrző olvasási segédparancs): a futtatókörnyezet a
csak-olvasási szabály védelmében elutasította, mert a uv run függőségeket szinkronizálhat; nem
próbáltuk újra, minden ellenőrzést közvetlen fájlolvasással végeztünk el.

Blocked actions:

 - shell (tool call call_MHxuSEVNQTRuWm11MUMyM0RpUkE)

