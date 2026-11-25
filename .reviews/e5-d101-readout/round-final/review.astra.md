Verdict

A D101 jó alap a protokoll kidolgozásához, de a megerősítő döntési szabály még nem fagyasztható be.
A legfontosabb javítás: külön kell meghatározni a prefix plafonjára, a Z ekvivalenciájára és a
párosított Δ kontrasztra érvényes intervallumot; az első kettő ritkaesemény-korlátja nem
automatikusan a harmadiké.

Findings

ASTRA-1 | major | D101/2–3, 56–57. sor
Claim: Nem egyértelmű, melyik bootstrap-intervallumot váltja fel az egzakt korlát. Attól, hogy
minden prefixpár W-AUC-ja 1, a prefix–Z különbség nem állandó; az ismétlődő megoldásorbitok párjait
pedig nem lehet független binomiális megfigyelésként számolni.
Evidence: A P2__shared__none.json:545–795 és a z6__shared__none.json:545–795 alapján P2 mind a 250
páron 1, de a páronkénti különbség 0,3043–0,6619, szórása 0,0445. A hivatkozott
research_plan_v3.7.md:375 és az e2p2.py:503–524 a vizsgált mennyiség nemnulla eltéréseit számolja
független egységeken.
Recommendation: Egy pár/orbit mellett, ha Uₚ a Pᵢ<1 esemény valószínűségének egyoldali
Clopper–Pearson-felső határa, akkor W(P) ≥ 1−Uₚ; a Zᵢ≠0,5 eseményre ugyanígy |W(Z)−0,5| ≤ U𝓏/2. Δ-ra
külön alsó határt rögzítsenek: például a plafonágon együttes lefedettségű Lₚ−U(W(Z)) határt,
egyébként páros bootstrapot. A legegyszerűbb a D99 orbitkizárását TEST-en is megtartani
(scripts\e5_pairs.py:55–69).
Confidence: high

ASTRA-2 | major | D101/2 és 4, 56. és 58. sor
Claim: A csak a Z-ekvivalenciára méretezett minta nem garantálja a két feltétel együttes
teljesülésének kívánt erejét. Az összes párra mért nagy Δ ráadásul részben akkor is elkerülhetetlen,
ha Z minden megkülönböztethető bitet helyesen rangsorol.
Evidence: A probe_val rácsokból és a z6.npy tömbökből, az e5pilot.py:63–82 bitkiválasztásával
számolva, tökéletes prefix mellett a pilotpárokon már a lokális azonosságok miatt legalább
1−0,700447 = 0,299553 a rés. A tényleges Δ 0,496413; a változó lokális állapotú biteken a generált Z
páronként átlagolt W-AUC-ja 0,508637, 162 értékelhető páron.
Recommendation: Rögzítsék, hogy sikerhez Δ egyoldali alsó határának meg kell haladnia a minimális
különbséget, és a Z kétoldali 1−2α intervallumának szigorúan a 0,5±ε sávba kell esnie. A választott
küszöbökkel szimulálják az együttes erőt és a határeseteket, az intervallumváltással együtt. Az
összpáros elsődleges elemzés maradjon; a már tervezett, változó bitekre szűrt eredményt
intervallummal közöljék. Ez különíti el a kényszerű döntetlent a gyenge rangsorolástól.
Confidence: high

ASTRA-3 | minor | 4. megfigyelés és D101/6, 50. és 60. sor
Claim: A 2–8-as legjobb epoch nem igaz minden Z-illesztésre. A kód nem áll le ezeknél az epochoknál,
ezért az sem következik, hogy négyszeres kerettel biztosan ugyanazt a modellt választaná.
Evidence: A kontroll nélküli generált Z-nél a nullától számozott legjobb epochok valóban 5/8/6 és
2/2/2. Viszont z6__shared__labels.json:515–532: 4/10/6; z6_teacher__whole__none.json:515–536:
2/74/77, a teljes rácson any_hit_cap: true. A probes.py:135–172 mind a 80 epochot lefuttatja, majd
visszatölti a legjobb állapotot.
Recommendation: A 2–8-as állítást szűkítsék a kontroll nélküli generált Z-re. A négyszeres futás
elhagyása indokolható azzal, hogy ezeknél nem az utolsó epoch nyert, és lesz konvergált
L-BFGS-referencia; az eredmény változatlanságát ne állítsák.
Confidence: high

ASTRA-4 | minor | D101/2, 56. sor – opcionális empirikus null
Claim: A sok újraillesztés és a hangolócímkék permutálása önmagában még nem teszi az E3-kontrollt a
W(Z)=0,5 hipotézis kalibrált nullmodelljévé.
Evidence: Az e3controls.py:37–52,174–189 egész feladványokat, illetve az összes üres cella között
címkevektorokat permutál. Ezek a műveletek olyan cella- és párfüggéseket is felbontanak, amelyek a
0,5-ös átlag nullhipotézise mellett létezhetnek. Több ismétlés ugyanennek a permutációs eloszlásnak
a becslését pontosítja.
Recommendation: D101-ben maradjanak a kontrollok kizárólag diagnosztikusak. Ha később formális
permutációs próbát akarnak, előbb nevezzék meg a külön nullhipotézist és igazolják, hogy alatta mely
egységek cserélhetők fel.
Confidence: high

ASTRA-5 | minor | 1. megfigyelés, 47. sor
Claim: A 0,50002–0,50004 tartomány nem írja le a kontroll nélküli P0/shared eredményt: az pontosan
0,5, nem kerekítés miatt látszik annak.
Evidence: A P0__shared__none.json:541–545 és a mentett predikciók szerint mind a 25 418 értékelhető
bit döntetlen. A 0,50003934 a permutált P0-é (P0__shared__permuted.json:541); a kontroll nélküli
teacher/shared 0,50001967 (z6_teacher__shared__none.json:541), egyetlen 1 ULP-s eltéréssel.
Recommendation: Nevezzék meg külön a három futást. A szabály maradjon: először a predikciók
végességét ellenőrizni, majd a bitazonos bemeneteket döntetlennek venni. A már float32-ben képzett
értékek float64-re alakítása önmagában nem javítja az eltérést (probes.py:265–276;
e5pilot.py:56–59).
Confidence: high

ASTRA-6 | minor | D101/1, 55. sor – a lineáris kiolvashatóság értelmezése
Claim: Mindkét reprezentáción azonos a próbafejek családja, de a pontozott predikció nem egyetlen
lineáris fejé. Három szigmoidkimenet átlaga általában nem adható meg egyetlen lineáris logit
szigmoidjaként.
Evidence: A probes.py:85–87 egy lineáris réteget és szigmoidot hoz létre; a probes.py:269–287 a
kiválasztott konfiguráció három modelljének valószínűségeit átlagolja. Az e5pilot.py:114–116 erre az
átlagra számít W-AUC-t.
Recommendation: Nevezzék az elsődleges becslést három lineáris fej átlagolt predikcióján mért
kiolvashatóságnak. Az egyetlen lineáris fejre vonatkozó értelmezést a seedenkénti W-AUC vagy a már
tervezett P2-es logisztikus referencia támaszthatja alá.
Confidence: high

Claims checked

 - holds — D101 nincs bejegyezve; az E5-páradatok között csak PROBE-TRAIN és PROBE-VAL van. A D96
bfloat16 futásában az 1–7. blokkonként 30/30, a 8. blokkban 0/30 illesztésnél nyert az utolsó epoch.
Mindkét precizitás átment a kapun; a 6. blokk pontosan kerekítve bfloat16-ban 0,9978, float32-ben
0,9979 (DECISIONS.md:134–138).
 - holds — A prefix nem figyel a querykre; a 18 query a Z-ből indul és figyelhet a prefixre. A
mentett prefix 512, a kumulatív cellaállapot 256 dimenziós. A megoldási arány 85,8–88,0%; a
kódazonos párok aránya TRAIN-en 319/1000, VAL-on 88/250 (next_concept.py:501–518,664–690;
e5extract.py:59–71).
 - holds — A pilottábla négy számoszlopa a közölt kerekítéssel egyezik a JSON-okkal. Az overall és a
codes_differ bitösszesített; a per_pair külön hányados. Csak a mindkét oldalon üres cellák eltérő
jelöltbitjei számítanak, a döntetlen fél pont, a két tag teljes felcserélése nem fordítja meg a
pontszámot (e5pilot.py:63–83). A nem véges érték miatti leállás és az üres pár megszámlálása helyes
új szabály, nem a pilot jelenlegi viselkedése.
 - holds — P0-n a saját üres pozíció bitazonos a két tagban; a whole kiolvasás a húsz szomszéd
állapotát is megkapja, és a jelöltbit éppen a számjegy hiányát jelzi e szomszédok között. A P0/whole
tökéletessége ezért bemeneti kontroll, nem bizonyíték generátorbeli következtetésre
(labels.py:29–37; wholelayer.py:109–140).
 - holds — P1/permuted: páronkénti átlag 0,432009, SE 0,003538, 219/250 pár 0,5 alatt. P2/labels:
0,581235, SE 0,003444. A címkekontroll valódi VAL-címkékkel választ; a reprezentációkontroll
permutált VAL-on hangol, majd eredeti VAL-on pontoz. Az eltolódás pontos okát egyetlen permutáció
nem azonosítja (e3controls.py:144–189). A konfigurációk 23/21/9-es darabszáma is helyes; az
általános epochállítás does not hold.
 - holds — Az 5. megfigyelés számai a rácsokból és a lokális állapotok bitazonosságából
újraszámolva: 15 249/25 418, illetve a kódeltérő párokon 6 313/16 482 kényszerű döntetlen. A
páronként számított felső határok 0,700447 és 0,809332.
 - holds — P2 és P3 mind a 250 páron 1-et ér el; a VAL-Brier 1,9515×10⁻⁶ kontra 9,0382×10⁻⁵, tehát a
szabály P2-t választja. A VAL-újrahasználat a pilot győztesét optimistává teheti, de a független
TEST-en a már befagyasztott réteg becslését nem. A pilot nem dönti el előre a TEST-ekvivalenciát
vagy a kauzális használatot.

