Verdict

A két megerősítő állítás statisztikai terve megalapozott, de a protokoll jelen formájában még nem
zárolható. A legfontosabb javítás egy olyan PROBE-VAL elfogadási próba rögzítése, amely az eredeti
pilotfájloktól a páronkénti pontszámokon át a döntésig ellenőrzi pontosan azt a kódot, amely a tagbe
kerül.

Findings

ASTRA-1 | blocker | e5_protocol_v1.md:154,160 (§9.4, §10)
Claim: A manifest az azonosítókra olyan hash-eljárást ír elő, amely a tényleges párazonosítókon nem
fut le. Így a sorrendhez kötött PROBE-VAL-ellenőrzés szó szerint nem hajtható végre.
Evidence: A src\ncm_sudoku\subsets.py:35–41 szerint a sha256_array előbb uint8-ra konvertál; az
e5pair-v1-9-0 nem konvertálható így. A pilot az ID-listára a sorrendtartó, UTF-8 JSON-t hashelő
sha256_ids-t használja, és csak az a, b, solutions tömbökre a sha256_array-t
(scripts\e5_pairs.py:78–90).
Recommendation: §10 külön nevezze meg az ID-lista logikai hashét (sha256_ids), a rácstömbök tartalmi
hashét és a fájlok bájthashét. A dry run első ellenőrzése legyen az eredeti pairs.json PROBE-VAL
ID-hashének reprodukciója.
Confidence: high

ASTRA-2 | major | e5_protocol_v1.md:57,78,151–155 (§4.4, §5.2, §9)
Claim: A „max abs diff 0” elfogadási feltétel nem határozza meg teljesen, mit és milyen numerikus
elrendezésben kell összehasonlítani. A teljes fájlra vett maximum nem működik; az 50 feladványos
inferencia bitazonossága pedig nem következik a sikeres pilot-refitből.
Evidence: Mindkét mentett elsődleges predikció alakja (500,81,9), és mindegyikben 135 000 szabályos
NaN van a megadott cellákon (src\ncm_sudoku\e5pilot.py:56–60). A refit egyszerre értékeli a 25 500
ürescellasort és nanmax-ot használ (src\ncm_sudoku\e5causal.py:29–41); a TEST-elrendezés hívásonként
2 550 sort értékel. A kauzális pilot két, már lekérdezéseken átlagolt TV-t von ki
(src\ncm_sudoku\e5causal.py:164–171; scripts\e5_causal.py:163–165); a különbségek előzetes képzése
matematikailag egyenértékű, de nem bitazonos műveletsor.
Recommendation: Írjátok elő az alak és a kitöltőmaszk egyezését, mindkét oldalon minden elvárt
predikció végességét, majd az egzakt összehasonlítást ezeken a helyeken. Külön kapu legyen a régi
elrendezésű refit és az 50-es TEST-útvonal egyezése; rögzítsétek a TV-műveletek sorrendjét és azt a
permutációt, amely ténylegesen megváltoztatja a batch-szomszédokat és a pozíciót. Eltérés ne legyen
utólag választott toleranciával elfogadható.
Confidence: high

ASTRA-3 | major | e5_protocol_v1.md:153–155 (§9.3–5)
Claim: Egyező predikciók mellett hibás A-pontozás is átmehet a dry runon: a szerződés jelentést kér
a kötési szabály hatásáról, de nem követeli az A döntésébe kerülő rendezett értékvektor egyezését
független referenciával. B-nél a két irány átlaga elfedhet egy ab/ba felcserélést.
Evidence: A pilot külön tárol bitpoolozott és páronkénti W-AUC-t (src\ncm_sudoku\e5pilot.py:63–83);
Z-nél ezek ténylegesen eltérnek: 0,503482 és 0,503587. A mentett adatok 4 847 mindkét oldalon üres,
bitazonos helyi Z-bemenetén egyetlen valószínűség sem tér el, így ezen a piloton a kötési szabály
nem indokol eltérést. A primary.npz 500 recipiens × 25 feltételt tárol (párindex, irány)
metaadattal; a 250 párátlag csak később képződik (scripts\e5_causal.py:174–193).
Recommendation: A-nál pár-ID szerint ellenőrizzétek a diszkordáns bitek számát, W(P2), W(Z) és Delta
értékét, majd a sorrendhelyes döntési bemenetet. B-nél előbb az (ID, irány, feltétel) értékek
egyezzenek, csak azután a párátlagok. Egy kézzel kiszámolható, eltérő bitszámú párokat tartalmazó
eset ellenőrizze a súlyozást, az előjelet és a végső döntést is.
Confidence: high

ASTRA-4 | major | e5_protocol_v1.md:104–119,153–160 (§6, §9–10)
Claim: A sikeres dry run nincs egyértelműen a később zárolt runnerhez, döntési kódhoz és eredeti
nyers referenciafájlokhoz kötve. A közös hibák felsorolásából maga az e5stats is hiányzik, pedig
módosulása mindkét döntést érintheti.
Evidence: §9.4 a P2- és Z-predikciót, valamint a primary.npz-t nevezi meg összehasonlítási alapként;
§10 ezek eredeti fájlhashét és a dry-run-jegyzőkönyv hashét nem sorolja fel. Van kész projektminta:
src\ncm_sudoku\wp2.py:215–256,259–281 ellenőrzi a tagelt és tiszta fő- és upstream kódot, a
jóváhagyott fájlok hashét, valamint az indulási, folytatási és befejezési állapotot.
Recommendation: A dry-run-jegyzőkönyv rögzítse a három eredeti referencia, a rendezett ID-k, a
fejek/bázisok, a runner és az e5stats hashét. A tag és a TEST ugyanazt a jóváhagyott készletet
használja; a közös döntési kód vagy a jóváhagyás eltérése egyik állítást se engedje kiadni.
Confidence: high

ASTRA-5 | major | e5_protocol_v1.md:98,154 (§5.4, §9.4)
Claim: Ha a végleges pontozás megváltoztat egy pilotértéket, a megnevezett D106-script egyszerű
újrafuttatása nem vizsgálja meg a változást. Az sem egyértelmű, mi történik, ha a korrigált rács
sikeres, de másik legkisebb N-et ad, miközben a protokoll többi része 400-at ír elő.
Evidence: A scripts\e5_power.py:38–44 rögzített útvonalról a régi pilot-JSON-okat olvassa, nem a
végleges scorer kimenetét. A rácsban a tényleges mag 2026112701 + N; a keresés az első sikeres
pontnál áll meg, és azt ellenőrzi újra (scripts\e5_power.py:116–139). A mostani, helyes D106-ban is
több korábbi rácspont 0,9 alatti.
Recommendation: Újratervezéskor a szimuláció bemenete a végleges scorer hash-elt, ID szerint
illesztett sorállománya legyen. Mondjátok ki: nincs lock, ha 1 000-ig egyetlen pont sem megfelelő
vagy a kiválasztott pont újraellenőrzése sikertelen; más sikeres N esetén a tag előtt minden N-et és
n_plan-t együtt kell átvezetni.
Confidence: high

ASTRA-6 | major | e5_protocol_v1.md:138–143 (§8)
Claim: Az A+B sor feltétel nélküli „a jelöltmaszk kódolva van” megfogalmazása többet sugallhat a
tesztelt rangsorolásnál. A teszt nem igazolja a teljes kilencbites maszk visszanyerhetőségét, és az
elsődleges prediktor nem egyetlen lineáris fej.
Evidence: A pontozó csak az azonos cella és számjegy diszkordáns pártagjainak sorrendjét vizsgálja
(src\ncm_sudoku\e5pilot.py:65–76). Akár minden predikció lehet 0,5 alatti, miközben a sorrend mindig
helyes. Az elsődleges predikció három szigmoid-kimenet átlaga (src\ncm_sudoku\e5causal.py:31–38); az
egyetlen fejre vonatkozó evidenciát D101(1) külön kezeli.
Recommendation: A közös sor mondja ki: „A P2-re illesztett három fagyasztott fej átlaga az alkalmas
párok diszkordáns jelöltbitjeit jobban rangsorolja, mint a Z≤6-kiolvasás.” Ettől külön maradjon B
állítása a referencia felé mutató eloszlásváltozásról. A teljes maszk pontos vagy kalibrált
dekódolása nem következik.
Confidence: high

ASTRA-7 | minor | e5_protocol_v1.md:105–113 (§6)
Claim: A „failed extraction check” közös vétó, de nincs meghatározva, mely extrakciós ellenőrzések
kötelezők. A „minden hívásban pontosan egy hook” szó szerint a szándékosan hook nélküli
referenciahívásra sem alkalmazható.
Evidence: Az extraktor futásidőben az elmentett rétegek számát ellenőrzi
(src\ncm_sudoku\e5extract.py:25–49); a tiszta generálással azonos kódokat és a passz alakját külön
teszt ellenőrzi (tests\test_e5extract.py:10–28). A kauzális tesztben a tiszta referencia ténylegesen
hook nélkül, a capture-változat egy hookalkalmazással fut (tests\test_e5causal.py:74–80).
Recommendation: Soroljátok fel az extrakciós kapukat és azt, melyik dry-run-, illetve
TEST-ellenőrzés. A hívásszámot szerepenként adjátok meg: tiszta referencia 0, capture és patch 1.
Belső orbitütközésnél a végleges vétó mellett mindkét érintett ID maradjon a naplóban.
Confidence: high

ASTRA-8 | minor | e5_protocol_v1.md:51–52,96–98,124–130 (§4.3, §5.4, §7)
Claim: Néhány korábbi döntés sorsa nincs kimondva: a magonkénti Q-bázisok érzékenységvizsgálata nem
azonos a magonkénti W-AUC-val, és a P4/P8 előjeles eltolódás Q–kontroll kontrasztjai sincsenek név
szerint megtartva vagy elhagyva. A 0,25-ös A2-küszöb pilottól független indoklása is kimaradt.
Evidence: A D102-specifikáció 18. és 23. sora külön nevezi meg a két diagnosztikát; a pilot shift4
és shift8 esetén is kiszámítja a három kontrasztot (scripts\e5_causal.py:193–205). A
D105-specifikáció 19. sora szerint a 0,25-ös különbség az ekvivalenciasávban körülbelül 0,72–0,78-as
prefix-W küszöbnek felel meg.
Recommendation: A diagnosztikákat jelöljétek „megtartott”, „csak pilot” vagy „elhagyott” státusszal;
nem szükséges miattuk bővíteni a TEST-et. Az A2 indoklását egy mondatban emeljétek át az OSF-re
kerülő protokollba.
Confidence: high

Claims checked

 - holds — A három checkpointfájl és a két generátorfájl tényleges SHA-256-a egyezik §3-mal. Az
upstream submodule a megadott c7027427… commiton tiszta; a betöltő CPU-t és weights_only=True-t
használ (experiments\provenance\checkpoints.json:4–21; src\ncm_sudoku\model.py:33–64).
 - holds — A párok egy megoldásból, külön véletlenfolyamokkal, két különböző, 30 megadott cellás,
egyértelmű maszkkal készülnek. A pilot 1 000/250 párja és nulla kizárása egyezik a rekorddal. A TEST
szabálya helyesen különíti el a külső elutasítást a belső, pótlás nélküli vétótól; a hibagarancia
nem az ütközésmentességre feltételes. B-re minden szabályos pár alkalmas: legalább 81−30−30=21 cella
mindkét oldalon üres (src\ncm_sudoku\e5pairs.py:40–74; experiments\e5\pairs.json:1350–1361).
 - holds — A pozitív kontroll mindkét precizitáson átment. A 250 páron P2 és P3 végig 1; a Brier
alapján P2 nyer. Z átlaga 0,503587, SD-je 0,044489; a 96 pontosan 0,5-ös pár tartalmazza mind a 88
kódazonos párt. P8 páronkénti átlaga 0,957315. Az MDL-, permutációs és címkekontroll-számok,
valamint a P8 L-BFGS iterációs korlátja egyeznek a pilotfájlokkal.
 - holds — A 6-os passzindex, a blocks[1] kimenete, az fp16-prefix/fp32-Z tárolás, az online fp32
donor saját kódjaival, a két irány, a 20 véletlen bázis és a relatív nullnormaszabály megfelel a
kódnak. A 250 páros irányított TV-átlagok és a D104 koszinuszai egyeznek §2-vel
(src\ncm_sudoku\e5extract.py:20–72; scripts\e5_causal.py:77–91,114–165;
experiments\e5\causal\cosines.json:2–17).
 - holds — Az e5stats a korábbi párok alapján fogad, a terminális log K > log 40 feltételt és a
megadott hét határt használja. A és B külön konjunkció: egyetlen sikeres részeredmény sem önálló
megerősítő állítás. A D106 rácsa, a 400-as N, a külön újraellenőrzés, a 0,9005-ös heterogén B-erő és
a közölt nullhatári gyakoriságok egyeznek a power.json-nal. A kb. 50 perces kauzális idő a mért
1 844,3 másodpercből helyesen skálázott becslés, nem az új ellenőrzésekkel mért idő.
 - does not hold — A §10-ben megadott sha256_array nem az ID-k hashformátuma. A nyers kauzális fájl
sem eleve páronkénti: recipiensenkénti, az irányok összevonását explicit módon kell elvégezni.
 - could not verify — A végleges runner, a mentett Z≤6-fej, a teljes fagyasztott manifest, a tiszta
környezetből történt helyreállítás és a sikeres, végleges dry run még nem áll rendelkezésre. A pilot
hookja valóban kihagyja az izolációellenőrzésből az összes cellasort
(src\ncm_sudoku\e5causal.py:124–132); a pilot sikere ezért nem igazolja előre az új §6-os kapukat.

