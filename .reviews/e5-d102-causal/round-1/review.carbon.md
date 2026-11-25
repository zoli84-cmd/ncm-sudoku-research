Reading the review brief at `.reviews\e5-d102-causal\round-1\brief.carbon.md` to understand the scope, targets, and required review format.

Elolvastam a review briefet; következő lépésként átvizsgálom a D102 tervezetet, a kapcsolódó D101 specifikációt, a pilot eredményfájlokat és a hivatkozott forráskódokat.

Verdict

A D102 tervezet jelenlegi formájában nem kész a végrehajtásra (blocker), mert (1) az elsődleges
viselkedési végpont (code-change) és a decoded-grid change a közös megoldású párokon irányítatlan
perturbációs/károsodási mutatók az oksági donor-követés helyett, (2) az izotróp véletlen $512 \times
9$-es altér-kontroll 28-szor kisebb négyzetes normájú lépést injektál az erősen anizotróp $(x_d -
x_r)$ különbségeken, és (3) a hivatkozott „fagyasztott pilot P2/P4/P8 fej” súlyai nincsenek lemezre
mentve, ráadásul 3 független mag szigmoid-átlagolt együttesét alkotják egyetlen 9 soros lineáris fej
helyett. A legfontosabb módosítás az irányítatlan kódváltozás lecserélése rögzített $Z_{\le 6}$
melletti, irányított donor-/full-swap logit- és kód-illeszkedési végpontra (intervene.level_logits
és continue_generation(..., n_given_levels=6)), norma- és aktív-altér-illesztett ortogonális
kontrollal.

Findings

CARBON-1 | blocker | docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md:25-27
Claim: Az elsődleges viselkedési végpontként kijelölt code-change indikátor (eltér-e bármely 7–12.
szintű kód a tiszta recipienstől) és a decoded-grid change (cellaszintű Hamming-távolság a tiszta
futástól) irányítatlan perturbációs mutatók, amelyek a közös megoldású párokon az off-target
roncsolást pozitív oksági hatásként értékelik. Az 51 egyoldalúan megoldott páron mért rescue
($n=51$, legrosszabb esetbeli SE $\approx 7.0$ százalékpont, $\pm 14$ százalékpontos
CI-félszélesség) túl kicsi ahhoz, hogy döntési súlyt viseljen.
Evidence: A src/ncm_sudoku/e5pairs.py:52-60 szerint a pár két tagja ugyanazon egyértelmű 81 cellás
megoldáson osztozik, és a runs/e5/acts/probe_val/{a,b}/solved.npy alapján a PROBE-VAL párok
77.6%-ában (194/250 pár, 388/500 futás) mindkét tag tiszta futása megoldott, vagyis a tiszta
dekódolt rácsuk azonos: ezeken bármely nemnulla decoded-grid change tisztán roncsolás (hibás cella,
clue-sértés vagy validate.py:35-54 szerinti -1 formátumhiba, amelynek kezelése sincs rögzítve).
Ugyanakkor a runs/e5/acts/probe_val/{a,b}/codes.npy közvetlen ellenőrzése mutatja, hogy a tiszta a
és b 7–12. szintű kódjai 249/250 párban eltérnek (átlagosan 31.83 kódban a 287-ből; az azonos 1–6.
szintű kóddal rendelkező 88 pár közül 87-ben átlagosan 14.41 kódban; a 194 mindkettőben megoldott
párban átlagosan 18.49 kódban), tehát kód- és logit-szinten létezik valódi, irányított
donor-célpont, amelyet a src/ncm_sudoku/intervene.py:135-169 (level_logits) kaszkádmentesen ki tud
olvasni (vö. research_plan_v3.7.md:315-321).
Recommendation: Cseréljék le az irányítatlan code-change elsődleges végpontot irányított
donor-/full-swap illeszkedésre: (1) rögzített recipiens állapot mellett (6. passz / 7. szint
level_logits tiszta $Z_{\le 6}^{(r)}$-rel, valamint 0. passz / 1. szint) mérjék a 16-kódos eloszlás
$P_Q$ közeledését a réteg-2-beli both_empty full-swap $P_{\text{full}}$ eloszláshoz, pl.
$\operatorname{TV}(P_{\text{clean}}, P_{\text{full}}) - \operatorname{TV}(P_Q, P_{\text{full}})$
(vagy KL-csökkenés) formájában, külön diagnosztikaként közölve az irányítatlan
$\operatorname{TV}(P_Q, P_{\text{clean}})$ perturbációt; (2) teljes generálásnál bontsák szét a
c_patched != c_clean eseményeket donor-követő váltásokra (c_patched == c_full != c_clean) és
harmadik, off-target kódra ugrásokra (c_patched not in {c_clean, c_full}); (3) a dekódolt rácson a
megoldási arány változását, clue-megőrzést és formátumhibát mind az 500 futáson károsodási
diagnosztikaként közöljék, az $n=51$ rescue elemzést pedig sorolják kifejezetten feltáró/leíró
szerepbe.
Confidence: high

CARBON-2 | blocker | docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md:19-20,26
Claim: Az azonos rangú ($512 \times 9$), izotróp véletlen ortonormált altér nem érvényes kontroll a
próba-altérhez, mert a 2. rétegbeli $(x_d - x_r)$ különbségvektorok erősen kisdimenziós alterekbe
koncentrálódnak, így a próba-altér nagyságrenddel nagyobb $\ell_2$-normájú perturbációt injektál,
mint egy véletlen 9 dimenziós altér. Emiatt a probe − random kontraszt pusztán a beavatkozás normája
és az aktív enkóder-altérrel való egybeesés miatt is pozitív lesz.
Evidence: A runs/e5/acts/probe_val/{a,b}/prefix_cells.npy 2. rétegén (8103 both_empty cellapár) az
$(x_b - x_a) \in \mathbb{R}^{512}$ különbségmátrix SVD-spektruma alapján az első 9 szinguláris irány
a teljes $\sum |x_b - x_a|2^2$ variancia 49.51%-át hordozza (top-20: 68.64%, top-50: 88.38%), míg
egy Haar-véletlen $512 \times 9$-es ortonormált bázis várhatóan csak $9/512 = \mathbf{1.76%}$-ot fog
be (28.2-szer kisebb energia, ~5.3-szor kisebb $\ell_2$-lépés; az üres cellás koordináták
szórásaránya is 6.07×). A projekt saját E4 tervében (research_plan_v3.7.md:303-309,319-321,
DECISIONS.md:41,51 D23/D28) már rögzítették, hogy próba-irányú beavatkozáshoz normaillesztett
véletlen irány és a patchelési távolság naplózása kötelező.
Recommendation: Naplózzák minden futásra és feltételre a tényleges $|Q Q^\top (x_d - x_r)|2$ normát,
és vezessenek be norma- és kovariancia-illesztett kontrollt: (1) in-manifold nulltér-kontrollt
($Q\perp \in \mathbb{R}^{512 \times 9}$ ortonormált bázis a $\ker(\bar{W}{\text{state}})$ altérben,
a PROBE-TRAIN both_empty $(I - Q_{\text{probe}} Q_{\text{probe}}^\top)(x_d - x_r)$ különbségeinek
vezető főkomponenseiből vagy top-$m$ altéréből sorsolva, amely a megmaradó >50% valós
enkóder-varianciából merít összemérhető normával, miközben a P2 lineáris jelölt-logitokat pontosan
0-val változtatja), és/vagy (2) cellánként (vagy feladványonként) $\ell_2$-normára skálázott
véletlen ortonormált altereket az izotróp kontroll mellé.
Confidence: high

CARBON-3 | blocker | docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md:19,24
Claim: A tervezet „a fagyasztott pilot P2 shared head kilenc számjegy-sorából” építi fel $Q$-t, és a
4., 8. réteget is a „fagyasztott pilot shared fejekkel” olvassa ki, ám a pilot egyetlen
próbamodell-súlyt sem mentett lemezre, ráadásul az elsődleges shared kiolvasás 3 tanítási mag
szigmoid utáni valószínűség-átlaga (27 állapotsor), nem pedig egyetlen 9 × 512-es lineáris fej.
Evidence: A src/ncm_sudoku/e5pilot.py:97-115,137-142 a summarize_fit(fit) hívással
(src/ncm_sudoku/e3controls.py:126-134) eldobja a fit["state_dicts"] súlyokat, így az
experiments/e5/pilot/*.json és a runs/e5/pilot/*.npy kizárólag összefoglalókat és validációs
predikciókat tartalmaz. A src/ncm_sudoku/probes.py:53,56-70,85-87,268-289 szerint a fit_selected
három külön nn.Sequential(nn.Linear(593, 9), nn.Sigmoid()) modellt tanít (SEEDS = (0, 1, 2)), és a
szigmoid valószínűségeket átlagolja (preds_sum / len(SEEDS)). (Maga a pozíció-one-hot elhagyása
egyetlen fej esetén matematikailag egzakt, mert azonos $c$ cellán $W_{\text{pos}} e_c + b$ kiesik
$z(x_d, c) - z(x_r, c)$-ből, és $W_{\text{state}} Q Q^\top = W_{\text{state}}$ pontosan átírja a 9
logitot; az L-BFGS referencia e5pilot.py:151-184 egyetlen modellt tanít, de std-vel standardizált
koordinátákon – így nyers térben a sorok $W_{:512}^\top / \text{std}$ –, és P4-re nem is futott.)
Recommendation: Rögzítsék expliciten: (1) a P2, P4 és P8 shared próbák determinisztikus
újraillesztését és súlyainak (state_dicts) elmentését PROBE-TRAIN-en (bitre/lebegőpontosan
ellenőrizve az egyezést a runs/e5/pilot/P{2,4,8}__shared__none.npy predikciókkal), valamint (2) az
egyértelmű leképezést a 3 mag (3, 9, 512) súlyaiból egyetlen $512 \times 9$-es ortonormált $Q$
bázisra (pl. a 3 mag átlagolt $\bar{W}{\text{state}} = \frac{1}{3}\sum{s=0}^2 W_s[:, :512]$
mátrixának float64 QR/SVD-bázisa $\sigma_9 > 0$ rangellenőrzéssel, vagy az 1. mag súlymátrixa).
Confidence: high

CARBON-4 | major | docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md:24,34
Claim: A valószínűségi térben definiált, küszöb nélküli előjel-alapú donor-follow rate hibásan
működik telítődés és tiszta tévesztések mellett: float32-ben az $y_r = 1$ telített biteken több
logitegységnyi donor irányú elmozdulást is 0-nak mér, a nem telített biteken viszont a numerikus
zajt is teljes sikernek tekinti, P8-on pedig a tiszta próba tévesztései miatt még a tökéletes
donor-csere sem adhat 1.0-t.
Evidence: A src/ncm_sudoku/probes.py:87,274 float32-ben számolja a torch.nn.Sigmoid()-ot, amely $\ge
16.64$ logit felett pontosan 1.0f-re kerekít, míg negatív irányban $-88$-ig megőrzi a felbontást. A
runs/e5/pilot/P{2,4,8}__shared__none.npy diszkordáns bitjein (25 418 bit $\times 2$ irány $= 50,836$
eset): P4-en az $y_r = 1$ bitek 8.22%-án (2090 bit/irány) p_clean == 1.0 (p > 0.9999: 62.50%), míg
$y_r = 0$-nál 0.00%-án p_clean == 0.0 (p < 1e-4: 44.67%), így pl. egy $+22 \to +17$ logiteli tolódás
1.0 == 1.0 miatt elveszik, miközben $-22.000 \to -21.999$ teljes +1-et kap. Emellett P8-on a tiszta
recipiens predikciók 13.44%-a már a 0.5 donor-oldalán van, és a diszkordáns bitek $1 - \text{W-AUC}
= 4.25%$-án p_clean(d) kevésbé igazodik $y_d$-hez, mint p_clean(r), vagyis még az egzakt $x_r
\leftarrow x_d$ csere is az ellenkező irányba mozdítja $p$-t.
Recommendation: Értékeljék ki a P4 és P8 próbákat float64 logit-térben (Sigmoid előtt, pl. a
mag-átlagolt $\bar{z}(x, c)$ logittal), és a puszta előjelarány helyett két mutatót számoljanak: (1)
döntési átbillenési arányt (a diszkordáns bitek hányadán egyezik meg
$\mathbb{I}[\bar{z}{\text{patched}} \ge 0]$ a donor $y_d$ címkéjével, összevetve a tiszta
recipienssel és a full-swappel), valamint (2) folytonos logit-eltolódást – az előjeles $(2y_d -
1)(\bar{z}{\text{patched}} - \bar{z}{\text{clean}, r})$ különbséget és a helyesen rendezett tiszta
biteken a $(\bar{z}{\text{patched}} - \bar{z}{\text{clean}, r}) / (\bar{z}{\text{clean}, d} -
\bar{z}_{\text{clean}, r})$ arányt.
Confidence: high

CARBON-5 | major | docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md:18,25,32
Claim: Az összes (12) passz patchelése mellett kizárólag a 7–12. szintű kódváltozások értékelése
összemossa az 1–6. szintű kódokon ($Z_{\le 6}$-on) keresztüli közvetett kaszkádot a 6. szint utáni
közvetlen prefix-kiolvasással, így nem dönti el az E5 alapvető kérdését.
Evidence: A third_party/ncm/models/next_concept.py:585-690 és a src/ncm_sudoku/intervene.py:72-129
alapján az 1..6. szinteken megváltozó kódok megváltoztatják z_hat-ot ($Z_{\le 6}$), az E2 pedig
igazolta (DECISIONS.md:79,91 D42/D53, paper/sections/e2.tex:78), hogy az 1. szint az egyetlen erősen
érzékeny szint, ahol egyetlen kódcsere átlagosan tucatnyi későbbi szintű kódot ír át; így a 7–12.
szintű kódváltozás akkor is fellép, ha a 6–11. passzok egyáltalán nem olvassák a jelölt-alteret.
Másfelől a continue_generation(..., n_given_levels=6) már bitre pontosan validált
(tests/test_intervene.py:39-42), és feleannyi idő (0.69 s/feladvány, DECISIONS.md:46 D31) alatt fut.
Recommendation: Futtassák külön a két oksági útvonalat: (1) 6. szint utáni patchelés (passes 6..11,
tiszta $Z_{\le 6}^{(r)}$ rögzítve continue_generation(..., n_given_levels=6)-tal + 6. passzos
level_logits) a $Z_{\le 6}$-ot megkerülő közvetlen prefix-olvasás tesztelésére (< 1 óra CPU); (2)
teljes 12 passzos patchelés (passes 0..11 + 0. passzos level_logits), külön jelentve az 1–6. szintű
kódváltozásokat (és a keletkező $Z_{\le 6}$ elmozdulást) a 7–12. szintűektől, hogy a korai durva
tervezésben (1. szint) történő jelöltmaszk-használat se maradjon rejtve.
Confidence: high

CARBON-6 | major | docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md:21-23,26,36
Claim: A both_empty cellákra korlátozott csere a 3–8. rétegekben logikai ellentmondásba kerül a
recipiens érintetlen clue-tokenjeivel, a „full swap” nem matematikai felső korlát, az in-place x_r -
x_r sham pedig nem ellenőrzi a donor-aktivációk pontosságát és indexelését (amely a tárolt fp16
fájlok vagy eltérő batch-méretek használatakor sérülne).
Evidence: (1) Az experiments/e5/pairs.json:1322-1334 szerint átlagosan 32.4 both_empty cella mellett
a recipiensnek ~18.6 nem közös clue-ja van; a blocks[2..7] (next_concept.py:508,516) önfigyelése
ezeket újraolvassa, ami felülírhatja a 2. rétegbeli patchet vagy OOD hibrid állapotot kelthet (a
csak egyik tagban üres cellák kihagyása ettől függetlenül helyes, mert a probes.py:62 csak üres
cellákon tanult, így donor clue-pozíciók bevetítése clue-token-injekcióval keverné a jelöltmaszkot;
a RoPE forgatás common.py:86-90-ben pozícióazonos cserénél nem sérül). Nemlineáris blokkok és argmax
mellett egy 9D altér-vetítés több kódot változtathat meg, mint az x_r <- x_d, így a 26. sor „bounds
what any prefix-cell intervention at layer 2 can change” állítása hamis. (2) A
src/ncm_sudoku/e5extract.py:66 a prefix_cells.npy-t fp16-ban (0.0312 max kerekítési hiba,
experiments/e5/cost.json:80) és csak a 6. passzból mentette, miközben a prefix aktivációk
passzonként 7.6e-6 (2. réteg) – 1.2e-4 (8. réteg) eltérést mutatnak (cost.json:69-78,
DECISIONS.md:129 D91), a tiszta codes.npy pedig batch=50 mellett készült (scripts/e5_extract.py:63,
DECISIONS.md:38 D20).
Recommendation: (1) A donor $x_d$ aktivációkat pár-batchenként (pl. 25 pár = 50 feladvány, ~100 MB
RAM) online, float32-ben és minden célzott passzra külön nyerjék ki, azonos batch-alakkal a tiszta
és patchelt futások között (D20), klónozott kimeneten az additív x_r + ((x_d - x_r) @ Q) @ Q.T
képlettel (a (I - QQ^T)x_r + QQ^T x_d forma ~1 ULP hibát visz be $x_d = x_r$ esetén). (2) Egészítsék
ki az identitásteszteket valódi self-donor ellenőrzéssel ($d := r$ a teljes donor-kinyerési és
indexelési útvonalon átvezetve a both_empty és mind a 91 prefix-pozíción $\Rightarrow$ bitre egyező
kódok és logitok a hook nélküli tiszta futással) és query-izolációs ellenőrzéssel (blocks[1]
kimenetén out[:, P:] bitre azonos a tiszta futással). (3) A „ceiling / bounds” megfogalmazást
cseréljék „both_empty full-swap referenciára”, és rögzített $Z_{\le 6}^{(r)}$ mellett számolják ki a
teljes tiszta donor-prefix (level_logits(m, prefix_d, codes_r, 7)) referenciát is.
Confidence: high

CARBON-7 | minor | docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md:18,24,28
Claim: A 0-alapú blokkindexelés (blocks[1] vs. k* = 2), a P4/P8 reprezentációs kiolvasás
passz-indexe, valamint a próba-újraillesztés és donor-kinyerés időigénye nincs rögzítve a leírásban.
Evidence: A src/ncm_sudoku/e5extract.py:25-49 és az experiments/e5/cost.json:55 konvenciója szerint
a 0. réteg a blocks[0] bemenete, a k. réteg pedig a blocks[k - 1] kimenete (k* = 2 $\to$ blocks[1],
4. réteg $\to$ blocks[3], 8. réteg $\to$ blocks[7] a ln_f előtt); egy blocks[2]-re tett hook
csendben a szintén 1.0 W-AUC-jú P3-at patchelné. A 28. sor 1.9 h költsége (8 × 500 × 1.705 s = 1.89
h, cost.json:64) nem tartalmazza az fp32 donor-kinyerő passzt (~7–14 perc) és a P2/P4/P8 próbák
mentését (runs/e5/pilot_main.log:9,13: teljes rács ~30 perc, a már kiválasztott (0, 0.003)
konfiguráción < 1 perc).
Recommendation: Írják bele expliciten, hogy a patch a net.transformer.blocks[1] forward hookján, a
reprezentációs kiolvasás pedig a blocks[3] és blocks[7] kimenetén a LEVEL7_PASS = 6 passzban
történik, és tüntessék fel a próba-mentés + donor-passz kiegészítő idejét a költségtervben.
Confidence: high

CARBON-8 | minor | docs/superpowers/specs/2026-11-25-e5-d102-causal-design.md:20,26
Claim: Öt globálisan rögzített véletlen altér mellett a párszintű bootstrap nem méri a véletlen
bázisok sorsolási varianciáját, ritka diszkrét változások (< 20 nemnulla pár) esetén pedig a
percentilis bootstrap a későbbi protokollban nulla szélességűre fajulhat.
Evidence: A docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md:55 (Observation 3)
megmutatta, hogy kis számú globálisan rögzített véletlen irány minden párt azonos irányba tolhat el
szűk párszintű SE mellett; a DECISIONS.md:85,139 (D49, D101(3,5)) pedig < 20 nemnulla eltérésű
egységnél Clopper–Pearson korlátot és a 0 diszkordáns bitű párok kizárását írja elő (PROBE-VAL-on
minden párban $\ge 70$ diszkordáns bit van az experiments/e5/pairs.json:1332 szerint, így az $n=250$
pár / 500 futás a folytonos és párszintű pilot kontrasztokhoz elegendő).
Recommendation: Rögzítsék a véletlen ortonormált bázisok pontos sorsolását (pl. float64 QR pozitív
R-diagonállal i.i.d. $\mathcal{N}(0,1)$ mátrixokból), jelentik külön a véletlen magok közötti
szórást és min–max terjedelmet (egy-passzos logit-kiértékelésnél érdemes 10–20 véletlen magot
futtatni), és emeljék át a protokolltervbe a D49/D101(3,5) ritka-esemény és 0-diszkordáns-bit
szabályait.
Confidence: high

Claims checked

 - Pilot prefix W-AUC 1.0 a 2–3. rétegen, 0.958 a 8. rétegen, online MDL kompresszió 195.6 P2-n
(experiments/e5/pilot/P2__shared__none.json, P3__shared__none.json, P8__shared__none.json: 0.9575,
P2__shared__mdl.json: 195.58): holds
 - Generált Z<=6 W-AUC 0.504 (AdamW és L-BFGS), MDL kompresszió 1.029 a P0 1.049 alatt
(z6__shared__none.json: párszintű átlag 0.5036, bit-pooled 0.5035; z6__shared__lbfgs.json: 0.5036;
z6__shared__mdl.json: 1.0287; P0__shared__mdl.json: 1.0493): holds
 - Generálás 12 passzban, 91 tokenes feladvány-prefixszel (PREFIX_CELLS = 1 + CELL_TOKEN_INDICES) és
szintenkénti query pozíciókkal, KV-cache nélkül (checkpoints/sudoku/hard/config.yaml:22,26,
third_party/ncm/models/next_concept.py:521-697, src/ncm_sudoku/e5extract.py:20,
experiments/e5/cost.json:50-61): holds
 - A prefix pozíciók csak a prefixre figyelnek (gen_mask[:, :, :P, P:] = -inf és m0[:, :, :P, P:] =
-inf), a query pozíciók a prefixre és egymásra figyelnek, így egy prefix-patch kizárólag a későbbi
blokkok figyelmén keresztül hat a querykre, a RoPE pozíciókódolást nem sérti
(third_party/ncm/models/next_concept.py:507-508,592-593,
third_party/ncm/models/common.py:86-90,129,167): holds
 - A dekódolás mohó (greedy) és determinisztikus (src/ncm_sudoku/runner.py:21 és e5extract.py:42
temperature=0.0-val hívja a next_concept.py:488 argmax ágát; a next_concept.py:521 alapértelmezése
temperature=1.0, a bitre pontos determinizmus pedig a DECISIONS.md:38 D20 szerint azonos
batch-alakhoz kötött): holds
 - PROBE-VAL-on 250 párból 88 párnak azonosak az 1–6. szintű kódjai, 77.6%-ban (194/250) mindkét tag
megoldott, és 51 párban (26 + 25) pontosan az egyik tag megoldott
(runs/e5/acts/probe_val/{a,b}/{codes,solved}.npy, experiments/e5/extract.json:43-70): holds
 - Létezik lemezre mentett, fagyasztott pilot P2/P4/P8 shared fej egyetlen 9 soros súlymátrixszal
(src/ncm_sudoku/e5pilot.py:97-115,137-142 eldobja a state_dicts-et, a probes.py:53,268-289 pedig 3
tanítási mag szigmoid-átlagát használja): does not hold
 - A both_empty full-vector swap felső korlátot ad arra, amit bármely 2. rétegbeli prefix-cella
beavatkozás megváltoztathat (2026-11-25-e5-d102-causal-design.md:21,26 – csak ~32.4 cellát cserél a
81-ből, és nemlineáris transzformátor + argmax mellett a részaltér-vetítés nem monoton): does not
hold
 - Költségbecslés: 1.7 s/feladvány CPU-n, 8 feltétel × 500 futás $\approx 1.9\text{ h}$
(experiments/e5/cost.json:64: 1.7052 s, $4000 \times 1.705\text{ s} = 1.89\text{ h}$, a
donor-kinyerés és próba-újraillesztés idejét nem számolva): holds

