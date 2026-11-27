Először az R2 szövegét vetem össze az elfogadott R1 megállapításokkal és a döntésekkel, majd a kódban és a mentett eredményekben ellenőrzöm a végrehajthatóságot.

A fogadási képlet és a két állítás döntési logikája egyezik a kóddal. Most azt ellenőrzöm, hogy a dry run, az érvényességi kapuk és a manifest ugyanezt az eljárást rögzítik-e.

### Verdict

A két confirmatory állítás, a fogadási teszt és a belső ütközés szabálya összhangban van D105-tel, de az R2 még nem zárolható. A legfontosabb javítás, hogy a TEST indításának feltétele legyen egy sikeres, hashhez kötött dry run, amely igazolja, hogy a B ág a ténylegesen beírt beavatkozásokat ellenőrzi, és hibánál nem hoz döntést.

### Findings

SOL-1 | blocker | e5_protocol_v1.md:105–115 (§6)  
Claim: A B kapuja nem igazolja, hogy a modell minden célcellába a megfelelő vektort kapta. Egy hibás irányú, de azonos normájú beírás a kijelölt ellenőrző cellán kívül átmehet: a normateszt a hosszúságot, a két irányteszt pedig a beírás előtti, nyers vektort vizsgálja.  
Evidence: A `src\ncm_sudoku\e5causal.py:119–132` izolációs ellenőrzése mind a 81 cellasort kihagyja, így a nem célzott cellasorokat sem ellenőrzi; a `scripts\e5_causal.py:102–111,147–151` csak jelzőként rögzíti az izolációt, a self-donor pedig közvetlenül a recipiens értékeit írja vissza. A §6 új szabályában a H ellenőrzése a normára skálázott lépés előtt történik; a skálázás az ortogonalitási hibát is felnagyíthatja. A „no-hook” összevetés két oldalát a szöveg nem különbözteti meg.  
Recommendation: Minden feltételnél és célcellánál hasonlítsátok össze a tényleges sort a függetlenül kiszámított, fp32-re kerekített várt sorral; minden más sort bitenként ellenőrizzetek. Az irány- és invarianciateszt nevezze meg a normára skálázott vektort, a normát és a toleranciát, valamint kezelje külön a nulla lépést. A no-hook kontroll legyen a csak rögzítő hook és a teljesen hook nélküli hívás összevetése; a self-donor járja be a teljes donorutat. A szintet és a hívásszámot is ellenőrizzétek, és egy modellpéldányon egyszerre csak egy hookos forward fusson.  
Confidence: high

SOL-2 | major | e5_protocol_v1.md §4.4, §5.2 és §6  
Claim: A leírt zérusszabály eltér a pilot kódjától, a donorút pedig nem rögzíti explicit módon a donor kódjait és az online aktivációforrást. Két jóhiszemű implementáció ezért eltérő patch-et vagy eltérő érvényességi döntést adhat.  
Evidence: A `src\ncm_sudoku\e5causal.py:75–85` küszöbe `1e-12 * max(s, 1)`, nem `1e-12`; például `s = 2` és `‖raw‖ = 1.5e-12` a kódban hiba, a szöveg szerint nem. A `scripts\e5_causal.py:115–123` a donor saját tiszta 1–6. szintű kódjaival, külön, azonos kiosztású 7. szintű hívásban gyűjti az online fp32 donoraktivációt; a recipiens kódjait donorpreffixel csak a külön `full_input` referencia használja (`:158–162`).  
Recommendation: Rögzítsetek egyetlen küszöböt a szövegben és a kódban, a pozitív célnormájú hibát kifejezetten B-érvénytelenként kezelve. Írjátok elő a donor saját tiszta kódjait, az online fp32 rögzítést és a mentett fp16 aktivációk kizárását a donorútból.  
Confidence: high

SOL-3 | major | e5_protocol_v1.md:102,151 (§6, §9.3)  
Claim: A pre-lock feladat csak az aggregálás előtti végességellenőrzést említi, de a §6 korábbi pontokon ír elő leállást. A pilot függvényeinek egyszerű újrafelhasználása ezt nem teljesíti.  
Evidence: A `src\ncm_sudoku\e5extract.py:42,57–70` az upstream generáláson belül már végrehajtott argmaxok után kap vissza eredményt (`third_party\ncm\models\next_concept.py:489`), majd `.half()`-ot hív. A `src\ncm_sudoku\e5pilot.py:63–79` egy `NaN` összehasonlítást veszteségként pontozhat; a `src\ncm_sudoku\e5causal.py:29–41` refit-ellenőrzése `nanmax`-ot használ, így a nulla maximális eltérés önmagában nem igazolja a predikciók azonosságát.  
Recommendation: Tegyétek a §9.3 elfogadási feltételévé az ellenőrzést a generálás minden greedy döntése előtt, az fp16 tárolás előtt és után, valamint a probe és a kauzális ág aggregálása előtt. A refitnél ellenőrizzétek külön az értékelhető elemek végességét, majd a predikciók azonosságát; szintetikus hibával igazoljátok, hogy egyik út sem tudja elnyelni a nem véges értéket.  
Confidence: high

SOL-4 | major | e5_protocol_v1.md:96–98,147–154 (§5.4, §9)  
Claim: A dry run összehasonlítás, de nincs átmenési szabálya, és a D106 újraértékelése után sincs kimondva D105 „nincs lock, nincs TEST” ága. A nyers kauzális fájl ráadásul pozíciókat tárol, nem párazonosítókat.  
Evidence: A `scripts\e5_causal.py:175–187` a `(pozíció, irány)` kulcsot menti. A nyers `primary.npz` és az exportált `primary_per_pair.json` Q-értékei között legfeljebb `4.97e-9` eltérést találtam; a mentett P2 és Z≤6 predikciók újrapontozásakor a kényszerdöntetlen-szabály egyetlen pilot-párértéket sem módosított. A `scripts\e5_power.py:38–45,116–145` a JSON-os sorokat pozíció alapján párosítja, és külön kezeli a sikertelen rácskeresést, illetve újraellenőrzést.  
Recommendation: Kössétek a nyers referenciafájlokat a hash-elt, rendezett PROBE-VAL ID-listához, és előre írjátok le, hol kell bitazonosság, illetve hol megengedett számszerű tolerancia. Csak az összes érvényességi kapun átment dry run engedje a zárolást. Az eltérést a végleges pontozással és azonosítóhoz kötött sorokkal értékeljétek újra; ha a rács vagy a független re-check nem éri el a 0,9-et mindkét állításra, ne legyen tag, OSF-lock vagy TEST.  
Confidence: high

SOL-5 | major | e5_protocol_v1.md §3, §4.4, §5.1 és §5.3  
Claim: Az extrakció és a kauzális futás kötegelése rögzített, a probe inferenciájáé és a szálbeállítás viszont nincs. A címkealapú kizárás így megváltoztathatja a pontozási batch-et, holott a fogadási teszt garanciája az alkalmas párok feltételes átlagára vonatkozik.  
Evidence: A `src\ncm_sudoku\probes.py:56–69` az üres cellákat lapítja, az `e5causal.py:25–39` a teljes validációs mátrixot egyszerre értékeli ki. D20 (`DECISIONS.md:38`) csak azonos alak és kiosztás mellett vállal ismételhetőséget; a D101-terv 47. sora tényleges 1 ULP-os eltérést dokumentál. Az extrakció és a kauzális pilot 4 szálat rögzít (`experiments\e5\extract.json:12`, `experiments\e5\causal\primary.json:546`), amit a `src\ncm_sudoku\g0.py:35–45` csak leolvas.  
Recommendation: A lock előtt rögzítsétek a szálbeállítást és a probe sorainak sorrendjét, batch-méretét, valamint a maradék batch kezelését. A jogosultsági maszk ne csoportosítsa át a pontozási bemeneteket; csak a statisztikába kerülő sorokat válassza ki. PROBE-VAL-on ellenőrizzétek a pontszámok függetlenségét a batch szomszédaitól és a pozíciótól; ha ez nem tartható, válasszatok páronként rögzített kiértékelést, mielőtt a nominális garanciára hivatkoztok.  
Confidence: medium

SOL-6 | major | e5_protocol_v1.md:118–119,147–158 (§6, §9–10)  
Claim: A manifest azonosítja, de nem teszi visszaállíthatóvá a lokális, git által figyelmen kívül hagyott fájlokat. A megszakítás utáni folytatás sincs megkülönböztetve egy már érvénytelen vagy befejezett TEST megismétlésétől.  
Evidence: A `.gitignore:7–13` kizárja a súlyokat, adatokat és nyers futásokat; a `scripts\e5_causal_heads.py:34–45` a `.pt` fájlokat a `runs` alatt menti. A `scripts\e5_extract.py:84–96` meglévő `done.json` esetén nem ellenőrzi újra a kész kimenetfájlokat. A projekt precedense (`src\ncm_sudoku\wp2.py:237–278,336–371`) a dry jóváhagyást és a folytatást az ellenőrzött futásállapothoz köti.  
Recommendation: Adjátok meg a fájlok tartós, jogszerű beszerzési helyét vagy rekonstruálási receptjét, és igazoljátok tiszta környezetből a visszaállítást. Rögzítsétek a hash-formátumot is: a pilot a tömb tartalmát hasheli, nem az `.npy` fájlt (`src\ncm_sudoku\subsets.py:34–40`). A runner kizárólag ugyanazt a megszakadt futást folytathassa ellenőrzött bemenetekből és kimenetekből; lezárt vagy érvénytelen futásra ne legyen újrapróbálkozás. Lock utáni módszerváltáshoz eredménybetekintéstől függetlenül új verzió kell.  
Confidence: high

SOL-7 | major | e5_protocol_v1.md:102–106,131–145 (§6, §8)  
Claim: Az értelmezési tábla helyesen nem emeli külön confirmatory eredménnyé az A1/A2 vagy B1–B4 komponenseket, de az A sor páronkénti állításként is olvasható, a „100 összehasonlítás” pedig összepoolozott bites nevezőt sugall. A P2-hash közös hiba, és az A-érvénytelen/B-érvényes esetet a tábla nem mondja ki.  
Evidence: A `src\ncm_sudoku\e5stats.py:54–68` páronkénti bemenetek átlagfeltételeit és együttes kapukat használ; a `src\ncm_sudoku\e5pilot.py:72–82` megkülönbözteti a bitpoolozást a páronkénti értékektől. A P2 mindkét kapuban szerepel (§6, 104. és 106. sor), míg például a Z≤6 fej hash-hibája csak A-t érinti.  
Recommendation: Az A sort írjátok az alkalmas párok populációjának **egyenlő pársúlyú átlagára**, a hat nettó helyes sorrendezést is így értelmezve. Áganként különítsétek el az igazolt, nem igazolt, nem becsülhető és érvénytelen kimenetet; a P2-hibát soroljátok a közös hibákhoz, és mondjátok ki, hogy A-specifikus hiba mellett az érvényes B önállóan értelmezhető.  
Confidence: high

SOL-8 | minor | e5_protocol_v1.md §4.1, §5.4 és §9.3  
Claim: A külső és belső szűrés elkülönítése helyes, de a D105(7) által kért szűrési napló nincs előírva, és a generálási hiba kezelése sincs rögzítve. Csak az elfogadott ID-kból nem ellenőrizhető, hogy egy kihagyott index valódi külső találat volt-e.  
Evidence: A `src\ncm_sudoku\e5pairs.py:41–65` `GenerationError`-ral megállhat; a `src\ncm_sudoku\symmetry.py:120–135` visszaadja az ütköző ID-ket. A `scripts\e5_pairs.py:43–66` PROBE-ra való: a belső ütközéseket is lecseréli, amit TEST-en tilos átvenni.  
Recommendation: Mentsétek a nyers indexet, a párazonosítót, az elutasítás okát és a külső találat ID-ját; belső ütközésnél az érintett párokat és a végleges vétót. Generálási hiba ne válhasson hallgatólagosan újabb indexre lépéssé. A gyorsabb megoldás a befagyasztott külső korpusz kanonikus kulcsainak egyszeri indexelése.  
Confidence: high

SOL-9 | minor | e5_protocol_v1.md §5.3 és §7  
Claim: A másodlagos riport nincs teljesen összehangolva D101/D102-vel: hiányzik a degenerált bootstrap jelölése, illetve nincs kimondva, hogy a permutált és címkekontroll csak korábbi pilotdiagnosztika-e. Az üres diszkordáns halmaz kezeléséhez a kauzális pilot nem követi a protokoll `null` szabályát.  
Evidence: A `scripts\e5_causal.py:55–62` megjelöli a degenerált intervallumot, de `:166–172` üres diszkordáns halmazra nullát ad a logiteltolásra és a flip-rátára. D101(2) diagnosztikaként nevezi meg a két kontrollt; D102(5)–(6) külön kéri a referenciatávolság eloszlását, a közel nulla esetek arányát és a degeneráció jelölését.  
Recommendation: Rögzítsétek, hogy az E3-kontrollokat nem kell újrailleszteni TEST-en, ha ez a szándék. Írjátok elő a referenciatávolság eloszlását és a `<0.01` arányt, a degenerált intervallum jelzését, valamint a `null` értéket és a nevezőt, ha nincs értékelhető bit. A normalizált logiteltolás elhagyása maradjon explicit.  
Confidence: high

SOL-10 | minor | e5_protocol_v1.md:18–23 (§2)  
Claim: A P8-nál a szöveg bitpoolozott eredményt idéz páronkénti átlagként; a pozitív kontroll két precizitása azonos kapudöntést, de nem azonos három közölt értéket ad.  
Evidence: Az `experiments\e5\pilot\P8__shared__none.json:541` bitpoolozott értéke `0.9575104`; a 250 `per_pair` érték átlaga `0.9573145`, három tizedesre `0.957`. A 6. blokk exact match értéke bfloat16-ban `0.9978`, float32-ben `0.9979` (`experiments\e5\kf_control_bfloat16.json:2573`, `kf_control_float32.json:635`; D98). Mindkettő átmegy a `0.99`-es kapun.  
Recommendation: P8-nál `0.957`-et közöljetek páronkénti átlagként, és külön nevezzétek meg a két precizitás eredményét vagy az egyező kapudöntést.  
Confidence: high

### Claims checked

- **holds** — A helyi checkpoint- és generátorfájlok SHA-256 értékei, a checkpoint-revízió provenienciája és az upstream gitlink egyeznek a §3-mal. A modell betöltése CPU-ra, `weights_only=True` beállítással történik (`src\ncm_sudoku\model.py:33–63`).
- **holds** — A 8/9/10 seednévtér, a három RNG-stream, a 30 nyom, az egyedi megoldás és B újrahúzása megfelel a kódnak. A TEST külső szűrése utáni belső vétó helyes D105-szabály: nem állít hibagaranciát az ütközésmentességre kondicionálva. **does not hold** — A PROBE runner változtatás nélkül futtathatná ezt a TEST eljárást.
- **holds** — A 6-os passzindex, a prefix réteg- és cellapozíciók, az fp16→fp32 prefixút, az fp32 Z≤6 cellaállapot és a kezdeti rejtvényből képzett címkék megfelelnek a kódnak (`e5extract.py:18–20,42–71`; `states.py:16–41`; `labels.py:29–37`). A három seed sigmoid-valószínűségeinek átlaga helyes; a pilot `w_auc` viszont nem implementálja az új kényszerdöntetlen- és végességszabályt.
- **holds** — P2/P3: mindkettő 250/250 tökéletes pár, P2 Brierje alacsonyabb; Z≤6: `0.503587`, SD `0.044489`, 96 döntetlen, köztük mind a 88 kódazonos pár. A közölt MDL-arányok és a P8 L-BFGS iterációs plafonja egyeznek a pilotfájlokkal. A P2/P4/P8 súlyfájlok hash-e egyezik, a refit-jelentés eltérése `0.0`; mentett Z≤6 fej még nincs.
- **holds** — A Q SVD-je és rangtesztje, H centerezetlen SVD-je a Q-ról levetített TRAIN-különbségeken, a 20 QR-bázis, a digitderangement, valamint a 18×16-os fp64 softmax és az irányított TV képlete megfelel a kódnak. A kauzális pilot átlagai, koszinuszai és futásideje egyeznek. **does not hold** — A pilot normaküszöbe és érvényességi kapuja azonos lenne a §5.2–6-tal.
- **holds** — Az A1 két `0.47`-es határa, az A2 `0.625`, a B1 `0.505`, a B2–B4 `0.5` határa, a késleltetett variancia, a `0.75/m0` korlát, a szigorú terminális döntés és az AND-kapuk egyeznek az `e5stats.py:28–68` kódjával. A `n_plan=400` explicit átadása szükséges; a függvény alapértelmezésben a tényleges sorhosszt használja.
- **holds** — `N=400`, a rács és a re-check kerekített értékei, a seedek, a heterogén B-erő `0.9005` és a hét nullhatár eredménye megfelel a `power.json`-nak. Ezek a meglévő piloton alapuló tervezési becslések, nem a végleges TEST-runner kalibrációja.
- **could not verify** — A végleges TEST-runner, a zárolt manifest, a mentett Z≤6 fej és a végleges eljárás sikeres dry runja még nem áll rendelkezésre; ezek teljesülése a pilotkódból nem igazolható.

Rendben.

