Verdict

A második CAL-pilot indokolt, és a H2/H3 áthelyezése az 1. szintre védhető, dokumentált, lock előtti
tervezési döntés; a terv azonban változtatás nélkül még nem lockolható. A legfontosabb javítás a
mintanagyság-szimuláció pontosítása: annak a rögzített 5 százalékpontos alternatívát kell
vizsgálnia, nem egyszerűen a kiválasztott pilotkontraszt empirikus hatását.

Findings

SOL-1 | major | research_plan_v3.6.md:373
Claim: A pilot puzzle-szintű eredményeinek egyszerű újramintázása a pilotban megfigyelt hatás
melletti erőt becsüli, nem szükségképpen az előírt 5 százalékpontos H2-hatás melletti 90%-os erőt. A
szimulációból hiányzik a célalternatíva előállítása, az ekvivalenciavizsgálat döntési szabálya és a
H3-intervallumszélesség teljesülési kritériuma.
Evidence: A 373. sor újramintázást ír elő, de nem definiálja a szimulált eloszlás célparamétereit.
Az első pilotban a releváns D-ági szintkülönbség körülbelül −8,67 százalékpont volt, nem −5:
experiments\wp1\pilot_report.md:12 és :22. A jelenlegi puzzle-szintű becslés a megfigyelt
ágkimenetek átlagából készül: src\ncm_sudoku\e2.py:81-94.
Recommendation: Rögzítsen közös ágkimeneteket és puzzle-függőségeket kezelő szimulációs modellt vagy
újrasúlyozást, amelyben a H2-hatás −0,05; a ritka események pilotbeli bizonytalanságára is legyen
érzékenységvizsgálat. Adja meg az ekvivalencia feltételezett valódi hatását és intervallumszintjét,
valamint azt, milyen valószínűséggel kell a H3 félintervallumának 3 százalékpont alatt maradnia. A
közös TEST végső mérete az E2- és a külön számított H1-követelmény maximuma legyen.
Confidence: high

SOL-2 | major | research_plan_v3.6.md:334-361
Claim: A puzzle-k számából képzett Clopper–Pearson-határ nem általánosan érvényes a terv által
megengedett család-/orbitfüggőség mellett. A seed-átlagolás önmagában nem érvényteleníti a |δ| ≤ q
egyenlőtlenséget; a hiányzó feltétel a binomiális számlálás független egysége.
Evidence: A 334. sor több, közös családba tartozó puzzle-t is megenged, a 361. sor viszont
puzzle-ket számol. Konkrét ellenpélda: 30 független család, családonként 10 azonos kimenetű puzzle,
5%-os eseményvalószínűséggel és eseménykor −1 különbséggel. Nulla esemény valószínűsége 0,95^30 ≈
21,46%; ilyenkor a 300 puzzle-re számolt, egyoldali 98,33%-os CP-felső határ csak 1,36%, tehát nem
fedi az 5%-os valódi hatásnagyságot. H2-nél, illetve B=A mellett H3-nál a súlyozott puzzle-különbség
valóban [−1,1]-beli, ezért az algebrai korlát helyes.
Recommendation: A legegyszerűbb megoldás az elsődleges E2-ben egy puzzle rögzítése minden független
csoportból. Máskülönben csoport- és szükség esetén rétegszintű, a célpopuláció súlyait megőrző
korlát szükséges. A 20-as küszöböt is független egységekre definiálja, rögzítse a CP-farokszintet,
és a bootstrap/CP váltási szabály lefedését ellenőrizze a tervezési szimulációban.
Confidence: high

SOL-3 | major | research_plan_v3.6.md:181-209
Claim: A percentilismetszet és a trapézszabály együtt még nem határoz meg reprodukálható
AUC-becslőt: nincs definiálva, milyen pontokból készül a kár–hatás görbe, és mire vonatkoznak az
„egyenlő súlyok”. A nem üres metszet nem garantál pozitív szélességet vagy mindkét szinten
interpolálható görbetartományt.
Evidence: A 181. sor az 1. szinten 15, CAL-gyakorisággal súlyozott alternatívát, a 11. szinten három
mintavételt ír elő; a 209. sor ezek összesítését, a dózisok keverési súlyait és az integráció
csomópontjait nem rögzíti. A gyakorisági politika ténylegesen nem egyenletes:
src\ncm_sudoku\perturb.py:47-52. A 209. sor csak az üres metszetet tiltja; az [a,a] metszet nem
üres, de a szélességgel történő normalizálás nem értelmezhető.
Recommendation: Definiálja a CAL-percentilisekhez használt dózis-/politika-keveréket, a normalizált
alternatívasúlyokat és a puzzle-szintű aggregálást. Rögzítsen például előre meghatározott
kárbin-ekhez tartozó súlyozott átlagokat vagy pontosan definiált görbecsomópontokat; AUC csak
pozitív szélességű, mindkét görbe által lefedett tartományon készülhessen. A formáthibás futások és
a TEST-en elégtelen támogatás kezelését is rögzítse. Egyszerűbb, elfogadható alternatíva az AUC
elhagyása és a külön érzékenységi görbék megtartása.
Confidence: high

SOL-4 | minor | research_plan_v3.6.md:183-207; DECISIONS.md:80-83
Claim: A szintválasztás indoklása nem különíti el megfelelően a közvetlen C-ági és a H2-ben használt
teljes D-ági hatást. A „C soha nem különbözött A-tól a 2. szinten” állítás csak a gyakorisági
politikára igaz; a „2–11. szintek” megfogalmazás pedig túlterjeszkedik a ténylegesen mért 2., 6. és
11. szinten.
Evidence: Az 1. szint gyakorisági pilotjában A=0,850, C=0,755556, D=0,763333, tehát a C-ági romlás
9,44, a D-ági romlás 8,67 százalékpont. A 2. szint uniform politikájánál C=0,847778, nem 0,850:
experiments\wp1\pilot_report.md:12-15; experiments\wp1\pilot_summary.json:20-150. A futtató
kizárólag az 1., 2., 6. és 11. szintet vizsgálja: src\ncm_sudoku\e2.py:17.
Recommendation: Nevezze meg külön a C- és D-ági pilotértékeket, a C=A állítást korlátozza a
gyakorisági politikára, és az empirikus érzéketlenségi állításokban sorolja fel a ténylegesen mért
szinteket. Ez nem teszi indokolatlanná az 1. szint kiválasztását, de pontosítja annak bizonyítékát.
Confidence: high

Claims checked

 - holds — A pilot 300 CAL-puzzle-ből, 16 200 beavatkozási rekordból áll; nincs kizárás, és minden
rekordban solve_B=solve_A. A mentett 8490,8 másodperc 2,36 óra. A két régi elsődleges pontbecslés
egyaránt 0,001111; a mentett 95%-os intervallumok megfelelnek a jelentésnek. Forrás:
runs\wp1\pilot_records.jsonl; experiments\wp1\pilot_summary.json:1-19, :716-719.
 - holds — A mért 2.,
  6. és 11. szinten a solve-változás legfeljebb körülbelül 1 százalékpont; a legnagyobb abszolút
eltérés 1,11 százalékpont. A nulla C–A Hamming aránya minden ilyen konfigurációban legalább 98%; a
legkisebb 885/900=98,33%. Forrás: a nyers pilotrekordok konfigurációnkénti ellenőrzése;
experiments\wp1\pilot_report.md:14-29. A C/D és politikák közti pontosításokat SOL-4 tartalmazza.
 - holds — Az
  1. és 11. szint összehasonlítása továbbra is azonos diszkrét költséget, egy megváltoztatott
kódpozíciót vizsgál; nem azonos szemantikai vagy vektornorma-hatást. Az enumeráció és a háromseed-es
mintavétel ugyanazt a politikai várható értéket célozhatja, eltérő Monte Carlo-zajjal.
 - holds — Az enumeráció helyes súlya az eredeti a kód mellett w(b|a)=f(b)/Σ[k≠a]f(k), b≠a. Nulla
CAL-gyakoriság nulla súlyt jelent, nem automatikus kizárást; csak a nulla nevező teszi az esetet
alkalmatlanná. Ezt a meglévő mintavételi kód is így kezeli: src\ncm_sudoku\perturb.py:18-22, :47-52.
Az elvárt érték a rögzített CAL-gyakoriságokra feltételes; nem a populációs gyakoriság
bizonytalanságmentes becslése.
 - holds — A kilenc számjegyre korlátozott, T=1 softmax technikailag jól definiálható. A dekóder 89
pozícióra 12 logitot ad; a 81 cellapozíciót és az 1–9 tokenazonosítókat kell kiválasztani. Ez
számjegyre feltételes eloszlás, nem a teljes 12-tokenes kimenet TV-je, ezért önmagában nem méri a
formáthibákhoz kapcsolódó valószínűségtömeget. Forrás: src\ncm_sudoku\states.py:32-33;
src\ncm_sudoku\grid.py:25; tests\test_states.py:50-54;
third_party\ncm\tokenization\sudoku_tokenizer.py:5-8. A generálás T=0 argmax útja ettől különálló:
src\ncm_sudoku\runner.py:19-32.
 - holds — A három elsődleges kontrasztra választott Bonferroni-szint elvileg 1−0,05/3; a
percentilis-bootstrap lefedése azonban közelítő, nem egzakt. Az 5/3 százalékpontos gyakorlati
küszöbök és a külön ±3 százalékpontos ekvivalenciasáv nem ellentmondásosak; a megvalósítandó döntési
és méretezési szabályok hiányait SOL-1–SOL-2 részletezi.
 - holds — A fő H2/H3-szintek a §3, §7.2, §11.1, §12.2 és §16 között következetesen átvezetettek; a
§13 helyesen csak a
  2. és 11. szint politikafüggő solve-különbségére enged ekvivalenciaállítást. A dokumentált
CAL-alapú, lock előtti kiválasztás önmagában nem követel újabb korrekciót a majdani, valóban
független TEST három rögzített elsődleges kontrasztján.
 - holds — D41 ellenőrzött gate-számai és a 173 ütközés összhangban vannak a gate.json-nal; a
későbbi screen.json 205 ütközést tartalmaz, az új 32 mind CAL-puzzle-t érint. A jelenlegi E2-kód
ugyanakkor még a korábbi protokollt valósítja meg: nincs súlyozott enumeráció vagy TV, a dózisrács
30%-ig tart, az alap-bootstrap 2000 ismétlésű és 95%-os. Ezeket a v3.6 tervezett, még nem igazolt
megvalósításaként kell kezelni: src\ncm_sudoku\perturb.py:12-15; src\ncm_sudoku\e2.py:48-66,
:81-109.
 - could not verify — A TEST történeti érintetlensége a repository fájljaiból nem bizonyítható. A
megvizsgált pilotrekordok CAL-azonosítókat tartalmaznak, a seed-névterek elkülönítettek, és D43/D50
érintetlen TEST-et dokumentál; ez konzisztens a feltétellel, de nem teljes hozzáférési audit.
Confidence: low.

