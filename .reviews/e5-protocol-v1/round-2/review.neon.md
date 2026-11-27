Reading the review brief at `.reviews\e5-protocol-v1\round-2\brief.neon.md` to understand the review scope and instructions.

Elolvastam a review briefet; most átnézem az `e5_protocol_v1.md` protokollt, az R1 döntési naplót (`decisions.md`) és az R2 diffet (`changes.diff`), valamint megkeresem a D91–D106 döntéseket a `DECISIONS.md`-ben.

Elolvastam a review briefet és az R1-es döntési naplót; most átnézem a felülvizsgált `e5_protocol_v1.md` teljes szövegét és megkeresem a D91–D106 döntéseket a `DECISIONS.md`-ben.

Elolvastam a review briefet, a korábbi döntési naplót és az `e5_protocol_v1.md` nagyobb részét; folytatom a protokoll végének, a `DECISIONS.md` D91–D106 bejegyzéseinek és a fő forrásfájlok (`e5stats.py`, `e5causal.py`, `e5pairs.py`, `e5extract.py`) ellenőrzésével.

Reading the remaining decisions (D103–D106) and the core E5 pilot/causal scripts to verify every protocol claim against the codebase.

Verdict

Az R2 revízió az R1 megállapításainak túlnyomó részét pontosan és konzisztensen beépítette, a számok
és a D91–D106 döntésekhez való hűség alapvetően rendben van, de a protokoll még nem zárható le lock
előtt néhány konkrét kód–specifikáció eltérés miatt. A legfontosabb javítandó pont §9.1 utasítása
e5causal.head_logits Z<=6-ra való használatáról: ez a függvény seed-átlagolt float64 logitokat
számol a §5.1-ben rögzített float32 sigmoid-valószínűségek átlaga helyett, amivel más becslőt adna a
Claim A-ra.

Findings

NEON-1 | major | e5_protocol_v1.md:146 (§9.1) és e5_protocol_v1.md:59 (§5.1)
Claim: §9.1 azt írja elő, hogy e5causal.head_logits függvényt általánosítani kell a fej
állapotdimenziójára „before it is used for Z<=6”, holott ez a függvény seed-átlagolt pre-sigmoid
logitokat számol float64-ben, míg §5.1 (és a pilot) a 0, 1, 2 magok float32 sigmoid
valószínűségeinek átlagát írja elő. Mivel $\sigma(\frac{1}{3}\sum_s z_s) \ne \frac{1}{3}\sum_s
\sigma(z_s)$ — és a két mennyiség a pár két tagját ellentétes sorrendbe is rendezheti —, head_logits
alkalmazása Claim A pontozására sértené §5.1-et és a pilot-tal való bitazonosságot.
Evidence: e5_protocol_v1.md:59 („mean over seeds 0, 1, 2 of the sigmoid probabilities (float32),
compared in float64”); e5_protocol_v1.md:146; src/ncm_sudoku/e5causal.py:134-142 (head_logits
float64 lineáris kimeneteket átlagol sigmoid nélkül); szemben src/ncm_sudoku/e5causal.py:32-36
(refit_head) és src/ncm_sudoku/probes.py:215-225 (fit_selected, ahol minden magon float32 Sigmoid
fut, majd a valószínűségek átlagolódnak). Z<=6 nem szerepel a Claim B logit-eltolódás
diagnosztikában (e5_protocol_v1.md:123, scripts/e5_causal.py:142 csak P4 és P8 fejeket használ).
Recommendation: §9.1-ből törölni kell a Z<=6 head_logits-szal való pontozására utaló részt; ehelyett
rögzíteni kell, hogy a Claim A (P2 és Z<=6) pontozása magonként float32 Linear+Sigmoid
valószínűségeket számol (a probes/refit_head útján), ezeket átlagolja a három magon (és külön
megőrzi a §7 per-seed W-AUC-hoz), majd float64-ben hasonlítja össze. head_logits maradjon a Claim B
P4/P8 pre-sigmoid logit diagnosztikák eszköze.
Confidence: high

NEON-2 | major | e5_protocol_v1.md:103 (§6) és e5_protocol_v1.md:148 (§9.3)
Claim: §6 előírja, hogy ugyanabban a hívásban a query sorok és minden nem célzott prefix sor
bitazonos legyen a hook előtt és után, de a meglévő e5causal.Level7Hooks._patch implementáció az
összes 81 prefix cellapozíciót kihagyja az ellenőrzésből (keep[self.cells] = False), így nem
ellenőrzi a nem célzott cellasorokat (nyomravezető és egyoldalúan üres cellák). §9.3 nem emeli ki
ezt a hiányosságot javítandó kódelemként a lock előtt.
Evidence: e5_protocol_v1.md:103 („within the same call, the query rows and every non-targeted prefix
row are bit-identical before and after the hook”); src/ncm_sudoku/e5causal.py:113-117 (keep =
torch.ones(new.shape[1], dtype=torch.bool); keep[self.cells] = False; self.query_unchanged =
bool(torch.equal(new[:, P:], out[:, P:])) and bool(torch.equal(new[:, :P][:, keep[:P]], out[:,
:P][:, keep[:P]]))); scripts/e5_causal.py:98 csak h.query_unchanged-ot vizsgálta (a ~rows cellákat
csak tests/test_e5causal.py:86 ellenőrizte a hookon kívül).
Recommendation: §9.3-ban elő kell írni Level7Hooks._patch kiegészítését úgy, hogy a hookon belüli
izolációs ellenőrzés a ~rows nem célzott prefix cellasorokra is kiterjedjen (teljes nem célzott (B,
P+L) maszk bitazonossága), és a TEST runner ezt az ellenőrzést minden patchelt hívásban
érvényesítse.
Confidence: high

NEON-3 | major | e5_protocol_v1.md:75 (§5.2) és e5_protocol_v1.md:97-111 (§6)
Claim: §5.2 zéró-norma szabálya két ponton inkonzisztens: abszolút <= 1e-12 küszöböt ír a
kontroll-projekció normájára pozitív célnorma mellett, míg e5causal.norm_matched a relatív <= 1e-12
* max(target_norm, 1.0) feltételt ellenőrzi (a pilotban az átlagos target_norm = 6.42, tehát eltérő
a küszöb); másrészt §5.2 ezt „invalid run (§6)”-ként jelöli, de §6 egyáltalán nem sorolja fel ezt a
hibát, így nem egyértelmű, hogy csak a B állítást vagy mindkét állítást blokkolja-e.
Evidence: e5_protocol_v1.md:75 („a positive target norm with a control projection of norm <= 1e-12
is an invalid run (§6)”); e5_protocol_v1.md:97-111 (a §6 lista nem tartalmazza a zéró
kontroll-projekciót); src/ncm_sudoku/e5causal.py:77-83 (if np.any(pos & (n <= tol *
np.maximum(target_norm, 1.0))): raise ValueError(...)); experiments/e5/causal/primary.json:33
(target_norm = 6.4222).
Recommendation: Össze kell hangolni a küszöböt §5.2 és e5causal.norm_matched között (pl. §5.2-ben <=
1e-12 * max(s, 1)-re pontosítva, vagy a kódot abszolút 1e-12-re állítva), és a kontroll-projekció
numerikus zéró esetét kifejezetten fel kell venni §6 Claim B ellenőrzései közé (csak a B állítást
teszi nem megerősíthetővé, a párt nem ejti ki).
Confidence: high

NEON-4 | minor | e5_protocol_v1.md:65,104-109 (§5.2, §6)
Claim: A §6 high-variance invariancia képlete (max over cells of |W (Delta H Hᵀ)| <= 1e-8 ‖W‖
‖Delta‖) nem rögzíti ‖W‖ normatípusát (spektrális ~5,64 vs. Frobenius ~15,9), |·| jelentését a
9-elemű vektoron (max-komponens vs. L2 norma), a cellánkénti ‖Delta_c‖ párosítást, illetve hogy a
nyers vetületet vagy a skálázott step_hv-t ellenőrzi-e (emellett a képletek keverik Delta sor- és
oszlopvektor-jelölését). Továbbá §6 nem adja meg a no-hook, a teljes útvonalú self-donor (both-empty
és mind a 91 pozíció) és a valódi donor értékellenőrzésének futási hatókörét (minden batch vs.
kijelölt batch/cella), §5.2 pedig nem nevezi meg, hogy a donor-rögzítés codes_d-vel fut.
Evidence: e5_protocol_v1.md:65,69-73,104-109; experiments/e5/causal/heads.json:19-29 (W szinguláris
értékei 5.64..4.78); scripts/e5_causal.py:109,130 (a pilot script call(pd, cd)-vel rögzítette a
donort, és nem futtatta a no-hook, a 91-pozíciós self-donor és a valódi donor ellenőrzéseket).
Recommendation: §6-ban pontosan ki kell írni a kvantort és a normákat (pl. minden c cellára max_d
|(W step_hv,c)_d| <= 1e-8 ‖W‖_F ‖step_hv,c‖_2, vagy ugyanez a nyers Delta_c H Hᵀ és ‖Delta_c‖_2
mellett), rögzíteni kell az egyes §6 ellenőrzések hatókörét (minden batch vs. első batch és melyik
cella), §5.2-ben pedig explicit meg kell nevezni a level_logits(m, prefix_d, codes_d, level=7)
donor-rögzítő hívást.
Confidence: high

NEON-5 | minor | e5_protocol_v1.md:135-143 (§8)
Claim: §8 értelmezési táblázatából hiányzik a Claim A invalid (§6) or not estimable (n_A = 0), claim
B valid sor, holott §6 (line 99) szerint a Z<=6 fej hash-hibája csak a Claim A-t blokkolja, §5.3
szerint pedig n_A = 0 esetén Claim A nem becsülhető (míg a szimmetrikus Claim B invalid, claim A
valid sor szerepel). Emellett az utolsó sor nem említi a §6-os nem véges érték miatti leállást, az
első sor (Claim A holds) pedig nem jelzi az „on average” pár-szintű átlagolást (szemben a Claim B
holds sorral).
Evidence: e5_protocol_v1.md:80,97-99,135,142-143;
docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md D105(3) („pair-weighted excess of 6
net correct orderings per 100 discordant comparisons”).
Recommendation: §8 táblázatát ki kell egészíteni a Claim A invalid (§6) or not estimable (n_A = 0),
claim B valid sorral („Claim B is read as above; no reading of claim A”), az utolsó sorba fel kell
venni a non-finite leállást (és az egyidejű A+B érvénytelenséget), az első sorba pedig az „on
average over eligible pairs” pontosítást.
Confidence: high

NEON-6 | minor | e5_protocol_v1.md:149-150 (§9.4–§9.5)
Claim: §9.4 nem ad meg számszerű elfogadási feltételt (bitazonosság vs. tolerancia, torch_threads =
4 rögzítése) a PROBE-VAL száraz próbához, és egybemos két külön ellenőrzést (a runner predikcióinak
egyezését a mentett pilot predikciókkal, illetve azt, hogy a §5.1 döntetlen-szabály változtat-e a
D106 bemeneteként használt z6__shared__none.json értékeken). Emellett §9.5 „1-ULP-perturbed
identical inputs scored as ties” megfogalmazása ellentmond §5.1-nek: 1 ULP-vel megváltoztatott
bemenetek már nem bitazonosak, így nem kaphatnak kényszerített döntetlent.
Evidence: e5_protocol_v1.md:59,149-150; src/ncm_sudoku/e5pilot.py:53-69 (w_auc nem ellenőrzi a
bemenetek bitazonosságát); scripts/e5_power.py:39 (z6__shared__none.json-t olvassa be);
experiments/e5/extract.json:14, experiments/e5/causal/primary.json:546 (torch_threads: 4).
Recommendation: §9.4-ben szét kell választani és toleranciával ellátni a két ellenőrzést: (a) a
runner predikciói és nyers oksági értékei max abs diff == 0-val egyeznek
runs/e5/pilot/{P2,z6}__shared__none.npy-vel és runs/e5/causal/primary.npz-vel (torch_threads = 4
mellett); (b) a §5.1 szabály alkalmazásának bármilyen eltérése
experiments/e5/pilot/z6__shared__none.json-hoz képest kiváltja D106 újrafuttatását lock előtt.
§9.5-ben javítani kell: „bit-identical inputs with 1-ULP-perturbed predictions scored as ties”.
Confidence: high

NEON-7 | minor | e5_protocol_v1.md:47,151,157 (§4.3, §9.6, §10)
Claim: §10 szerint a tag előtt elkészülő (és §9.6 szerint a tiszta lock-commitba kerülő) manifest
fájl listázza a másodlagos komponenseket „or the commit that refits them”, ám egy commitban tárolt
fájl kriptográfiailag nem tartalmazhatja magának annak a commitnak a hash-ét. Ezen felül §4.3 azt
állítja, hogy a másodlagos fejeket „refitted deterministically on PROBE-TRAIN/PROBE-VAL by the pilot
code at the locked commit”, de e5pilot.run_cell és e5pilot.run_global jelenleg eldobja a tanított
fejeket és a PCA-t, és nem támogat harmadik (TEST) halmaz pontozását.
Evidence: e5_protocol_v1.md:47,151,157; src/ncm_sudoku/e5pilot.py:80-115 (run_cell nem ad át
s_sc/empty_sc-t cell_pca_features-nek és score/f_score-t fit_cells-nek; run_global csak [rep_tr,
rep_va]-t dolgoz fel és nem adja vissza a modelleket).
Recommendation: §10-ben a másodlagos komponenseket vagy el kell menteni és hash-elni a commit előtt,
vagy a manifestben a lock-commit hash-e helyett az újratanító/3-halmazos pontozó szkriptek
fájl-SHA-256-ját kell rögzíteni (a lock-commit az OSF-leírásba kerül), és §9-be fel kell venni a
3-halmazos másodlagos pontozás megvalósítását.
Confidence: high

NEON-8 | nit | e5_protocol_v1.md:73,123 (§5.2, §7)
Claim: Két apró pontatlanság a diagnosztikáknál: (1) §5.2 a full donor input sorra „level_logits(m,
prefix_d, codes_r, level=7) without a hook”-ot ír, míg scripts/e5_causal.py:137 a P4/P8
diagnosztikák rögzítéséhez Level7Hooks-szal (patch=None) hívja meg (ami a no-hook ellenőrzés szerint
bitazonos); (2) ha egy Claim B-re jogosult párnak 0 diszkordáns bitje van,
scripts/e5_causal.py:144-145 a np.maximum(disc.sum((1, 2)), 1) nevezővel 0.0-t ad
shift4/shift8/flip4/flip8-ra a §7-ben kért null/NaN kizárás helyett.
Evidence: e5_protocol_v1.md:73,123; scripts/e5_causal.py:137,142-145.
Recommendation: §5.2-ben pontosabb a „without a patch (bit-identical to level_logits without hooks)”
megfogalmazás, a TEST runnerben pedig a 0 diszkordáns bitű párok shift/flip diagnosztikái NaN-ként
(kizárva) kezelendők.
Confidence: high

Claims checked

 - Checkpoint revízió (d342ce8a...), generator.pt / tokenizer.pt / config.yaml teljes SHA-256
hash-ek és HazyResearch/ncm upstream commit (c7027427...) (experiments/provenance/checkpoints.json,
e5_protocol_v1.md:29): holds
 - Modellbetöltés kizárólag ncm_sudoku.model.load_model (weights_only=True) útján
(src/ncm_sudoku/model.py:34, e5_protocol_v1.md:29): holds
 - Generátor-védelem (numpy 2.5.4, generate.py és solve.py SHA-256, subsets.assert_generator_frozen)
(src/ncm_sudoku/subsets.py:13-25, e5_protocol_v1.md:30): holds
 - Pozitív kontroll eredmények (0.9994 / 1.0000 / 0.9978 a 4–6. blokk után, bfloat16/float32
egyezés) (experiments/e5/kf_control_bfloat16.json, kf_control_float32.json, e5_protocol_v1.md:18):
holds
 - Pilot próbaértékek (P2/P3 Brier 1.95e-6 vs 9.04e-5, Z<=6 W-AUC 0.5036, P0 0.500, P8 0.958, MDL
1.029/1.049/195.6, P8 L-BFGS iterációlimit, E3 kontrollok 0.432/0.581) (experiments/e5/pilot/*.json,
experiments/e5/power.json, e5_protocol_v1.md:20,45): holds
 - Oksági pilot eredmények és koszinuszok (Q 0.052, random 0.001–0.006, HV 0.022, shuf −0.079, full
0.061; koszinuszok 0.541, 0.471, 0.115–0.142, −0.002) (experiments/e5/causal/primary.json,
cosines.json, e5_protocol_v1.md:21): holds
 - D106 szimulációs táblázat, re-check (0.997/0.998), heterogén B (0.9005), null-határ FPR-ek
(0.0014/0.0013/0) és seedek (2026112701–2026112703) (experiments/e5/power.json, scripts/e5_power.py,
e5_protocol_v1.md:94): holds
 - Számítási idők (0.84–1.47 s/puzzle, 1.71–1.77 s batch 20-nál, 1,844 s / 250 pár)
(experiments/e5/extract.json, cost.json, causal/primary.json, e5_protocol_v1.md:161): holds
 - ncm_sudoku.e5stats.betting_logk, claim_a, claim_b képletei és transzformált m0 határai
(src/ncm_sudoku/e5stats.py:21-61, e5_protocol_v1.md:79-89): holds
 - Kinyerés (e5extract.py: pass 6, PREFIX_CELLS, fp16 prefix, fp32 z6 a
states.cumulative_states(..., upto=6)[5]-ből) és párosítás (e5pairs.py, [10, index, 0/1/2])
(src/ncm_sudoku/e5extract.py, states.py, e5pairs.py, e5_protocol_v1.md:36,42): holds
 - runs/, checkpoints/, data/ git-ignoráltak (.gitignore:9-11, e5_protocol_v1.md:157): holds
 - e5causal.head_logits dimenzió-általánosítással alkalmazható Z<=6 Claim A pontozására
(src/ncm_sudoku/e5causal.py:134-142, e5_protocol_v1.md:59,146): does not hold
 - e5causal.Level7Hooks ugyanabban a hívásban minden nem célzott prefix sort ellenőriz
(src/ncm_sudoku/e5causal.py:113-117, e5_protocol_v1.md:103): does not hold
 - §5.2 zéró-norma küszöbe (<= 1e-12) egyezik e5causal.norm_matched-del és szerepel §6-ban
(src/ncm_sudoku/e5causal.py:77-83, e5_protocol_v1.md:75,97-111): does not hold
 - Másodlagos fejek újratanítása és TEST pontozása a meglévő e5pilot kóddal
(src/ncm_sudoku/e5pilot.py:80-115, e5_protocol_v1.md:47): does not hold

