I will read the review brief at `.reviews\e5-d101-readout\round-1\brief.carbon.md` and inspect the repository root to understand the scope and exact instructions for this read-only review.

Elolvastam a review briefet; most beolvasom a D101 tervezetet, a kapcsolódó E5 forráskódokat, a kísérleti JSON fájlokat és a DECISIONS.md releváns részét.

Verdict

A D101 tervezet jelenlegi formájában nem kész a rögzítésre (blocker), mert a 2. pontban javasolt
párszintű sign-flip teszt és az Observation 3 diagnózisa hibás: egy rögzített próbára kondicionálva
a kontrollok W-AUC-ja (0.4317 a P1/permuted, 0.5812 a P2/labels esetében) szisztematikusan eltér
0.5-től, így a javasolt elsődleges nullteszt magukon a negatív kontrollokon is $p < 10^{-30}$-nal
elutasítja a 0.5-öt. A legfontosabb módosítás a 0.5-ös pontnullra épülő sign-flip teszt (és a
validációs szivárgást tartalmazó labels kontroll) lecserélése közvetlen párosított Prefix − Z<=6
kontrasztra, a Z<=6-ra előírt praktikus ekvivalencia-határra (TOST), valamint próbaszintű
permutációs nullra.

Findings

CARBON-1 | blocker | docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md:45,53
Claim: Az Observation 3 tévesen a páron belüli bit-korrelációval magyarázza a kontrollok
0.43–0.58-as W-AUC-ját, ezért a D101(2) szerinti párszintű sign-flip teszt (mean(per_pair) vs. 0.5)
nem kontrollálja az I. fajú hibát rögzített próbára kondicionálva, a zárójeles állítás („swapping
the two members maps a pair's W-AUC w to 1 − w”) pedig matematikailag hamis. Egyetlen permutációs
maggal (PERMUTE_SEED_TRAIN=11) a másodlagos rep − permuted W-AUC különbség is ±7 százalékpontos
rögzített torzítást szenved, a labels kontroll pedig valódi validációs címkéket szivárogtat vissza.
Evidence: A src/ncm_sudoku/e5pilot.py:61-68-ban (a, b) felcserélése (pa, ya)-t és (pb, yb)-t együtt
cseréli, tehát w változatlan marad (w -> w); a w -> 1 − w transzformáció a predikciók címkékhez
képesti felcserélése, ami nem invariáns a null alatt, ha a reprezentáció függ a clue-maszktól. Az
azonos cellán a pozíció-one-hot és a bias (src/ncm_sudoku/probes.py:66-67) kiesik pa − pb-ből, a >
reláció pedig skálainvariáns, így a regularizációval zsugorított kontrollsúlyok (W) egyetlen
tanítási permutációból (src/ncm_sudoku/e3controls.py:32,175, seed=11) származó véletlen
iránykoszinusza minden párra azonos előjelű eltolást okoz: a
experiments/e5/pilot/P1__shared__permuted.json:541,545-629 párszintű értékei szinte mind 0.5 alatt
vannak (overall=0.4317, SE ≈ 0.003, vagyis ~20 SE-vel 0.5 alatt!), és a reziduális folyam miatt az
összes P1–P8 permuted kontroll < 0.5 (0.4317–0.4908). Eközben a control="labels" ág
(src/ncm_sudoku/e5pilot.py:100, src/ncm_sudoku/e3controls.py:160-161) csak a PROBE-TRAIN címkéket
permutálja, de a korai megállítást (80 epoch) és a (wd, lr) rácsot a valódi, nem permutált PROBE-VAL
címkéken választja ki (src/ncm_sudoku/probes.py:165,239), így valódi jelölt-irányokat válogat ki
(experiments/e5/pilot/P2__shared__labels.json:3-7,515-543: lr=0.003, best_epoch=66,61,9,
val_brier_mean=0.2305 < 0.2325, w_auc=0.5812, és minden P1–P8/labels > 0.5).
Recommendation: (1) A labels kontrollban a hangolási (PROBE-VAL) címkéket is függetlenül permutálják
(train_va), ahogy a permuted_control teszi. (2) Vessék el a 0.5 elleni párszintű sign-flip tesztet
olyan reprezentációkon, amelyek a clue-maszkkal változnak; helyette az állapot–modell összevetés
elsődleges próbastatisztikája a közvetlen párosított W-AUC(P_k*) − W-AUC(Z<=6) különbség legyen
párszintű bootstrap-intervallummal, a nullkontrollhoz pedig vagy kalibrált Brier-kontrasztot, vagy
sok ($M \ge 100$) független feladvány-permutációra illesztett kontrollpróba próbaszintű eloszlását
használják egyetlen seed=11 helyett. (3) Rögzítsék explicit szabályként a diszkordáns bit nélküli
(cnt == 0, NaN) párok eldobását és naplózását (src/ncm_sudoku/wp2eval.py:34-37 mintájára).
Confidence: high

CARBON-2 | major | docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md:7,52-57
Claim: A P2 / shared 1.0000-ás pilot eredménye önmagában triviálisan várható 1 lépéses szomszéd-clue
aggregációt mér (amely ráadásul nem is látja Z<=6-ot), miközben a D101 nem definiál sem közvetlen
Prefix − Z<=6 elsődleges kontrasztot, sem praktikus ekvivalencia-határt (TOST) Z<=6-ra. Emiatt
megfelelően nagy TEST elemszámnál a Z<=6 (0.5054 / 0.5081) és a P2 (1.0000) egyaránt szignifikánsan
meghaladhatja a 0.5-ös pontnullt, döntési szabály nélkül hagyva az E5 alapvető („állapot vagy
generátor”) kérdését, miközben a Z<=6-ot ténylegesen olvasó level7_queries reprezentáció kimarad.
Evidence: A candidate_mask (src/ncm_sudoku/labels.py:29-36) kizárólag azt ellenőrzi, szerepel-e a
számjegy a 20 közvetlen peer adott clue-jai között (nincs többlépéses következtetés), a
NextConceptTransformer._decode_level_logits (third_party/ncm/models/next_concept.py:506-507) maszkja
(gen_mask[:, :, :P, P:] = -inf) pedig tiltja, hogy a prefix pozíciók (P0–P8, B0–B8) a target
pozíciókra figyeljenek, így a prefix aktivációk függetlenek Z<=6-tól és minden generálási passzban
azonosak (DECISIONS.md:129, D91); mire a level7_queries a háló tetején kiolvassa a prefixet (P8), a
shared exact match 1.000-ról 0.469-re esik (experiments/e5/pilot/P8__shared__none.json:799). Eközben
a src/ncm_sudoku/e5extract.py:57 már kinyerte a Z<=6-ot és a prefixet ténylegesen kombináló
level7_queries (9 x 18 x 512) aktivációkat, de ezekre egyetlen próba sem futott, Z<=6-on pedig a
0.5054-es (z6__shared__none.json:543) érték pont úgy viselkedik, mint az E3 H1-ben a 0.0031-es
Brier-nyereség (DECISIONS.md:106, D68).
Recommendation: (1) Rögzítsenek közvetlen párosított elsődleges kontrasztot (W-AUC(P_k*) −
W-AUC(Z<=6)) ÉS előre megadott TOST ekvivalencia-/gyengeségi sávot a Z<=6 olvashatóságára (ahogy a
D68 tette a H1 ±0.01-es határával). (2) Egészítsék ki a protokollt a már kinyert level7_queries
(untied head) vizsgálatával és/vagy a labels.inference_waves (src/ncm_sudoku/labels.py:52-95) depth
>= 2 következtetési hullámainak bontásával, és kössék ki az interpretációs táblában, hogy a P2
lineáris olvashatósága csak azt bizonyítja, hogy az 1 lépéses jelöltmaszk jelen van a
puzzle-encoderben, de azt nem, hogy a generátor kauzálisan használja is azt (ehhez a D102 kauzális
aktivációcsere és véletlen-altér kontroll szükséges, vö. Rodrigues et al. 2026,
paper/sections/discussion.tex:21).
Confidence: high

CARBON-3 | major | docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md:54
Claim: A D101(3) rétegválasztási szabálya („the layer with the highest mean per-pair W-AUC on the
PROBE-VAL pairs (P2 in this pilot)”) nem egyértelmű már a pilot adatokon sem, mert a P2 és a P3
egyaránt pontosan 1.0000 párszintű W-AUC átlagot ér el, döntetlen-feloldó szabály pedig nincs
megadva. Emellett a 1.0 plafonértéken a projekt párszintű percentilis bootstrapje nulla szélességű
[1.0, 1.0] intervallummá fajul.
Evidence: Mind a experiments/e5/pilot/P2__shared__none.json:541-797, mind a
experiments/e5/pilot/P3__shared__none.json:541-797 fájlban az összes (250/250) per_pair elem
pontosan 1.0 (overall = 1.0), így mean(per_pair) mindkét rétegen pontosan 1.0 (P2 és P3 csak
val_brier_mean-ben tér el: 1.95e-6 vs. 9.04e-5, ill. exact_match-ben: 1.0 vs. 0.99953). Bár egy
PROBE-VAL-on egyértelműen kiválasztott, befagyasztott k* réteg egyszeri TEST kiértékelése nem okoz
szelekciós torzítást a TEST becslésben, ha a TEST-en is minden pár w_i = 1.0, akkor w_i − 0.5 = 0.5
miatt a src/ncm_sudoku/e2p2.py:517-524 nz = n >= 20 ágra fut (a ritka esemény korlát csak 0 körüli
különbségeket figyel), és nulla szélességű [1.0, 1.0] bootstrap CI-t ad.
Recommendation: Egészítsék ki a D101(3) szabályt determinisztikus tie-breakerrel: (1) legmagasabb
átlagos párszintű W-AUC PROBE-VAL-on, egyenlőség esetén (2) legalacsonyabb val_brier_mean
PROBE-VAL-on (ez egyértelműen P2-t választja: 1.95e-6 < 9.04e-5), további egyenlőség esetén (3)
legkisebb rétegindex. A D101(2) bootstrapjéhez pedig írjanak elő felső/alsó határeset-szabályt: ha
kevesebb mint 20 párnál teljesül w_i < 1 (vagy w_i != 0.5), alkalmazzanak Clopper–Pearson / Wilson
konzervatív korlátot a research_plan_v3.7.md:375 (§11.2) elvével összhangban.
Confidence: high

CARBON-4 | major | docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md:47,52,56
Claim: Az Observation 4 tévesen állítja, hogy néhány globális illesztés kivételével minden pilot
próba a (wd=0, lr=0.003) rácshatárt választotta; valójában az 53 illesztésből 32 – köztük minden
egyes Z<=6 illesztés – a túlsó (wd=0.1, lr=0.001) határt választotta korai megállással, így a
D101(5) szerinti 4x-budget újratanítás a kiválasztott Z<=6 konfiguráción hatástalan (no-op).
Emellett a shared kiolvasás skálázatlanul adja át a 256 dimenziós interpolált kódkönyvi összeget
(Z<=6, 3042 paraméter) és az 512 dimenziós reziduális folyamot (P_k, 5346 paraméter) az AdamW-nek,
noha a D68 már kimutatta, hogy a skálázatlan bemenet a 2000 lépéses korlát mellett a null felé
torzíthat.
Evidence: A experiments/e5/pilot/z6__shared__none.json:3-5,515-537 (config=[0.1, 0.001],
best_epoch=5,8,6 / 80, any_hit_cap=false) és a z6__whole__none.json:3-5,515-537 (config=[0.1,
0.001], best_epoch=2,2,2 / 80, any_hit_cap=false) egyaránt a korai epochokban állt meg, és az egész
10 pontos rácson egyetlen futás sem érte el a lépéskorlátot; csak a P1–P8/shared/none (8),
P0–P8/whole/none (9) és B1–B4/global/none (4) – összesen 21/53 futás – választotta a [0, 0.003]-at.
Mivel a src/ncm_sudoku/probes.py:150-165 determinisztikus minibatch-sorrendet használ epochonként, a
[0.1, 0.001] konfiguráció 320 epochig futtatása újra a 2–8. epochnál fog megállni. A Z<=6 saját
pozíciós kiolvasása (shared, n_params=3042) önmagában méltányos közös elsődleges kiolvasás akkor, ha
a másodlagos Z<=6 / whole (n_params=5346, pontosan megegyezik a P_k / shared méretével, és kezeli a
third_party/ncm/models/quant.py:404-411 1D interpolációját) és a konvergált L-BFGS referencia
mellette marad (míg a whole a P0-n – P0__whole__none.json:541, explained_variance_share=1.0 – és a
reziduális kapcsolatok miatt P1–P8-on valóban a nyers clue-bemenetet méri, Z<=6-on viszont nem, mert
Z<=6 csak a 35 diszkrét VQ-kódból épül fel: src/ncm_sudoku/states.py:16-28).
Recommendation: Javítsák az Observation 4-et a tényleges konfigurációkra; standardizálják a shared
bemeneti jellemzőket koordinátánként a PROBE-TRAIN üres celláin (a D68 elve szerint), vagy a
D101(5)-ben a konvergált, standardizált bemenetű, széles $C$-rácson hangolt teljes-batcshu L-BFGS L2
logisztikus próbát tegyék meg az optimalizációs/skálázási kontrollnak Z<=6 (shared és whole), P2 és
P8 esetén. Vágják le a felesleges 4x-AdamW újratanítást Z<=6-ról, valamint vegyék ki a D101(1)-ben
már tisztán leíróvá minősített, 373 977 paraméteres B3 globális fejet az online MDL és a 4x-budget
körből (ahol a kis korai MDL-blokkokon wd=0 mellett súlyos túlilleszkedés lépne fel).
Confidence: high

CARBON-5 | minor | src/ncm_sudoku/e5pilot.py:61-76
Claim: Az Observation 1 állításával szemben a Z<=6 teacher és a P0 / shared W-AUC-ja a kódban nem
garantáltan pontosan 0.5 (0.5000197 ill. 0.5000393 a pilotban), mert az egymás után fűzött [a; b]
batchen futtatott float32 mátrixszorzás 1 ULP-nyi eltérést okozhat azonos bemeneti vektorokon, amit
a p_cand == p_non egzakt egyenlőségvizsgálat féloldalas nyereségként (1.0 vagy 0.0) számol el.
Emellett a w_auc függvény skalárként jelenleg a bitekre súlyozott (pooled) arányt adja vissza, nem a
D101(2)-ben előírt párszintű átlagot.
Evidence: A experiments/e5/extract.json:77,92 szerint a probe_val/a/z6_teacher és
probe_val/b/z6_teacher fájlok SHA-256 hash-e bitre azonos (05a6637a...), mégis a
experiments/e5/pilot/z6_teacher__shared__none.json:541-543,670 és a
z6_teacher__whole__none.json:548-550 overall = 0.5000196710992211-et (per_pair[124] = 0.50455), a
P0__shared__permuted.json:541-543,670,795 pedig overall = 0.500039342198442-t ad. Ennek oka, hogy a
probes.build_inputs (src/ncm_sudoku/probes.py:62-67) az a és b üres celláit egyetlen (25500, F+81)
méretű float32 tenzorba fűzi (12750 sor tagonként, nem többszöröse a SIMD/MKL blokkméretnek), így a
model(features_va) (probes.py:249) 1 ULP eltérést adhat ugyanarra a bemenetre, ami a
src/ncm_sudoku/e2p2.py:517 1e-12-es küszöbénél nagyságrendekkel nagyobb (~0.0045) ál-eltérést kelt
egy párban. Továbbá a src/ncm_sudoku/e5pilot.py:72-76 overall/codes_same/codes_differ mezői
num[sel].sum() / cnt[sel].sum()-ot számolnak, és egy esetleges NaN predikciót a 67. sor 0.0-vá
alakít NaN helyett.
Recommendation: A kiértékelésnél számolják a lineáris próba predikcióit float64-ben (vagy értékeljék
ki a-t és b-t külön, azonos alakú batchekben), védjék a w_auc 67. sorát explicit isnan
ellenőrzéssel, és egészítsék ki a w_auc visszatérési szótárát a párszintű átlagokkal
(pair_mean_overall, pair_mean_codes_differ, pair_mean_codes_same).
Confidence: high

CARBON-6 | minor | docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md:55
Claim: A Z<=6 elsődleges becslésének szűkítése a különböző 1–6. szintű kódú párokra (codes_differ,
~65%), miközben a prefix az összes páron fut, egy modell utáni endogén eseményre kondicionál,
megakadályozza a tiszta párosított összehasonlítást az összes páron, és ~35%-kal csökkenti a Z<=6
effektív TEST elemszámát. Bár ez a szűkítés a Z<=6 0.5-től mért eltérését 1 / (1 − q) ≈
1.54-szeresére növeli (tehát a „Z<=6 gyenge” állításra nézve konzervatív), elfedi azt az alapvető
szerkezeti eredményt, hogy a párok egyharmadán a kvantálás információelméletileg kizárja a
jelöltmaszk-különbség megőrzését (0.825-ös elméleti W-AUC plafon).
Evidence: A PROBE-VAL halmazon a diszkordáns bitek 35.16%-a (8936 / 25418, 88 pár a 250-ből) esik a
codes_same rétegbe, és a nem telített prefix rétegeken a két réteg között kisebb nehézségi különbség
látszik (experiments/e5/pilot/P8__shared__none.json:542-543: codes_same = 0.9533 vs. codes_differ =
0.9598).
Recommendation: Az elsődleges párosított Prefix − Z<=6 kontrasztot számolják az összes TEST páron
(ahol a 35%-os kódazonosság maga is a kumulatív állapot korlátjának bizonyítéka), és emellett
szimmetrikusan – mind Z<=6-ra, mind P_k*-ra – közöljék a codes_differ réteget
társ-elsődleges/másodlagos feltételes elemzésként; a TEST elemszám-tervezésnél pedig 1 / 0.65-tel
skálázzák fel a párszámot, hogy a codes_differ réteg is elérje a célzott erőt.
Confidence: high

CARBON-7 | nit | docs/superpowers/specs/2026-11-25-e5-d101-readout-design.md:13,16
Claim: A Context szakasz két háttér-összefoglalója apró pontatlanságot tartalmaz: a D96-nál nem
minden illesztés futott a végső epochig (a 8. blokk nem), a 7. szintű passz leírása („it reads Z<=6,
prefix positions layers 0–8”) pedig félreérthetően sugallja, hogy a prefix pozíciók olvassák a
Z<=6-ot.
Evidence: A experiments/e5/kf_control_bfloat16.json:2200-2501 (és DECISIONS.md:134, D96) szerint
csak az 1–7. blokkok választották a (0, 0.003) rácshatárt hit_cap: true mellett, a 8. blokk mind a
30 futása hit_cap: false volt ([0.1, 0.001]; továbbá a kf_control_float32.json:635 6. blokkja négy
tizedesre 0.9979). A third_party/ncm/models/next_concept.py:506-507 alapján pedig a 6. passzban csak
a level7_queries pozíciók olvassák Z<=6-ot, a prefix pozíciók nem.
Recommendation: Pontosítsák a 13. sort „blocks 1–7”-re, a 16. sorban pedig tegyék egyértelművé, hogy
a 7. szintű passzban a query pozíciók olvassák a Z<=6-ot és a prefixet, míg maguk a prefix rétegek
csak a feladvány tokenjeire figyelnek.
Confidence: high

Claims checked

 - Kézirat állításai a 6. szintű kumulatív állapotról és a generátor aktivációinak nyitva hagyott
szerepéről (paper/sections/e3.tex:29-37, paper/sections/discussion.tex:31-32): holds
 - D94–D96, D98 pozitív kontroll exact match értékek 0.9994 / 1.0000 / 0.9978 a 4–6. blokk után
(experiments/e5/kf_control_bfloat16.json:9,322,635, kf_control_float32.json:9,322,635 – utóbbiban a
6. blokk 0.99787): holds
 - D96 összefoglalója, miszerint a pozitív kontrollban minden illesztés az utolsó epochig futott és
a rácshatárt választotta (kf_control_bfloat16.json:2200-2501, 8. blokk hit_cap: false, config=[0.1,
0.001]): does not hold
 - D95: a globális pozíció 729 kimenetű untied fejet használ (src/ncm_sudoku/e5probes.py:67-74),
mert az E3 megosztott fej (src/ncm_sudoku/probes.py:55-68) egyetlen globális vektorból csak
pozíciófüggő eltolást tudna képezni: holds
 - D97, D99: 1000 PROBE-TRAIN és 250 PROBE-VAL pár, azonos megoldás, két 30 clue-s egyértelmű maszk,
kanonikus átfedés nélkül, ~32 közös üres cella, ~31.6 eltérő maszkú cella, ~103 eltérő bit
(experiments/e5/pairs.json:1030-1055,1320-1360, src/ncm_sudoku/e5pairs.py:33-57): holds
 - Aktiváció-kinyerés (experiments/e5/extract.json, src/ncm_sudoku/e5extract.py:21,49-63): 7. szintű
passz, 86–88%-os megoldási arány (85.8%–88.0%), és az 1–6. szintű generált kódok a párok 32–35%-ában
azonosak (PROBE-VAL-on a bitek 35.16%-a, 88/250 = 35.2% pár): holds
 - Pilot táblázat 19 sorának kerekített számai (w_auc.overall, w_auc.codes_differ,
summary.val_brier_mean, metrics.exact_match) a experiments/e5/pilot/*.json fájlokhoz képest
(megjegyezve, hogy a táblázat W-AUC oszlopai a bitekre összegzett pooled értékek, nem párszintű
átlagok): holds
 - src/ncm_sudoku/e5pilot.py:61-76 (w_auc): bit-kiválasztás (mindkét tagban üres cella és pontosan
az egyikben jelölt számjegy) és 0.5-ös tie-kezelés egzakt egyenlőségre: holds
 - Observation 1: a P0 / shared és a Z<=6 teacher minden esetben azonos predikciót és pontosan 0.5
W-AUC-t ad a kódban (z6_teacher__shared__none.json:541 és z6_teacher__whole__none.json:548:
0.5000197; P0__shared__permuted.json:541: 0.5000393 az 1 ULP-s batch-eltérés miatt): does not hold
 - Observation 2: a whole_layer_features (src/ncm_sudoku/wholelayer.py:99-125,139-149) P0-n a 20
peer nyers clue-tokenjeit méri (P0__whole__none.json:541: explained_variance_share = 1.0),
amelyekből a candidate_mask (src/ncm_sudoku/labels.py:29-36) küszöbölt lineáris függvény: holds
 - Observation 3: a kontrollok 0.43–0.58-as W-AUC-ját a páron belüli bit-korreláció okozza
(P1__shared__permuted.json:541-629 és P2__shared__labels.json:541-629: párszinten is ~18–20 SE
eltérés 0.5-től próbaszintű iránytorzítás ill. validációs címkeszivárgás miatt): does not hold
 - Observation 4: néhány globális illesztés kivételével minden pilot illesztés a (wd=0, lr=0.003)
rácshatárt választotta (experiments/e5/pilot/*.json: 53-ból 32 illesztés, köztük az összes z6 és
z6_teacher próba [0.1, 0.001]-et vagy [0.1, 0.003]-at választott): does not hold
 - D101(2): a pár két tagjának felcserélése a pár w W-AUC-ját 1 − w-be viszi
(src/ncm_sudoku/e5pilot.py:61-68: a tagok cseréje w-t invariánsan hagyja): does not hold
 - D101(3): a legmagasabb átlagos párszintű W-AUC szabálya a pilotban egyértelműen P2-t választja
(P2__shared__none.json:541-797 és P3__shared__none.json:541-797 egyaránt pontosan 1.0000 minden
páron): does not hold

