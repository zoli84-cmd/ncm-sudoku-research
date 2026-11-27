Újraszámolom a pilot eredményeit a nyers páronkénti adatokból, és ellenőrzöm, hogy a javasolt hibakontroll milyen állításokra érvényes.

Verdict

A D105 tervezet tervezési alapnak megfelelő, de még nem zárolható. A legfontosabb változtatás: olyan
döntési szabályt kell rögzíteni, amelynek az elsőfajú hibája a ritka eseményes és a bootstrap-ágon
együtt is védhető; ezt a pilot eltolásos szimulációja önmagában nem igazolja.

Findings

SOL-1 | blocker | D105 §4 és §6; D101 §3
Claim: A Bonferroni-korrekció nem biztosít 5%-os családszintű hibakontrollt, ha az elemi tesztek nem
tartják a névleges szintet. Az egzakt Clopper–Pearson-ág nem teszi egzakttá a teljes, adatfüggően
váltó eljárást.
Evidence: A D101 a nem plafonos Δ-ágon páronkénti bootstrapot ír elő
(2026-11-25-e5-d101-readout-design.md:56–57); a v3.7 precedense percentilis-bootstrapot használ
(src\ncm_sudoku\e2p2.py:502–526). Ellenpélda 500 párra: legyen minden W(Z) = 0,5; az 1/301
valószínűségű ritka párnál Δ = −0,50, egyébként Δ = 0,25 vagy 0,26, 3:1 arányban. Ekkor E[Δ] = 0,25.
Az esetek 18,9%-ában nincs ritka pár, de van legalább 20 darab 0,26-os pár: a bootstrap alsó határa
0,25 fölé kerül, a Z-ekvivalencia pedig teljesül. Ez nem a pilot eloszlására vonatkozó becslés,
hanem ellenpélda az általános hibagaranciára.
Recommendation: A döntéshez használjanak korlátos páronkénti átlagra érvényes egyoldali teszteket; a
bootstrap maradhat becslésre. Ha a Δ plafonágán megmarad az L_P − U_Z konstrukció, osszák meg a Δ-ra
jutó hibakeretet a két korlát között (például fele-fele), és a teljes ágváltásra igazolják a
szintet. Ha csak közelítő kontrollt vállalnak, a preregisztráció ne ígérjen egzakt 5%-ot.
Confidence: high

SOL-2 | major | D105 §6 (22. sor)
Claim: Az egyszerű oszlopeltolás a pilotból olyan nullmintákat képezhet, amelyek megsértik a döntési
szabály által használt azonosságokat és eltüntetik a ritka eseményes ágat. A kiválasztásra is
használt PROBE-VAL csak feltételes tervezési modell, nem független hibakalibráció.
Evidence: A per_pair listákban P2 mind a 250 párnál 1; Z-nél 96 érték pontosan 0,5, köztük mind a 88
kódazonos pár (experiments\e5\pilot\P2__shared__none.json:545,
experiments\e5\pilot\z6__shared__none.json:545; kódstrátum: src\ncm_sudoku\e5pilot.py:28–38). Z
additív eltolása bármelyik sávhatárra mind a 96 kötést eltünteti. Ha csak Δ-t toljuk 0,25-re, nem
marad azonos a P2−Z különbséggel; ha belőle számoljuk vissza P2-t, minden érték 0,753587 lesz. A
fejek és a réteg kiválasztása ugyanazon a PROBE-VAL-on történt (scripts\e5_pilot.py:35–38;
src\ncm_sudoku\probes.py:259–287; D101:57).
Recommendation: Egész páronkénti eredményvektorokat mintázzanak újra. Több előre leírt, érvényes
forgatókönyv tartsa meg a kényszerű kötéseket, a [0,1] tartományt, a Δ=P−Z azonosságot és az oksági
feltételek közös referenciáját. Vizsgálják külön-külön azokat a nullhatárokat, ahol csak egy
feltétel éppen hamis, a többi pedig teljesül, valamint a 19/20-as ágváltás környékét; közöljék a
Monte Carlo-hibát is. Az erőt a pilothatások mellett előre indokolt, gyengébb alternatívákon
becsüljék. Friss TEST-en a befagyasztott fejekre feltételes következtetés helyes cél; a fejeket
ezért nem kell újrailleszteni a bootstrapban.
Confidence: high

SOL-3 | major | D105 §4 (20. sor)
Claim: A 0,05/3-as osztás konzervatív, ha két külön megerősítő állítás van: az állapot
kiolvashatóságáról szóló és az oksági. A kapukon belüli feltételek csak együtt jogosítanak
állításra, ezért ott nem kell újra osztani az alfát.
Evidence: D101(2) mind az ekvivalenciát, mind a Δ-küszöb átlépését előírja (DECISIONS.md:139); D105
§3 ugyanezt teszi a három oksági feltétellel. Egy konjunkció hamis elfogadásához legalább egy igaz
komponensnullát el kell utasítani, így érvényes komponenspróbák mellett a kapu szintje legfeljebb az
egyes komponensek szintje. A v3.7 három külön főkontrasztra osztott (research_plan_v3.7.md:346–356);
a wp2eval.tost a kapott alfát mindkét oldalra használja (src\ncm_sudoku\wp2eval.py:21,55–69).
Recommendation: Ha a két állítás külön közölhető, mindkét kapu kapjon α=0,025-öt: a TOST kétoldali
intervalluma 95%-os, az egyoldali alsó korlátok 97,5%-osak. Mindhárom oksági komponens futhat a
teljes 0,025-ön; az újabb harmadolás nem szükséges. A komponenseket ne jelentsék önálló megerősítő
eredményként külön hibakeret nélkül.
Confidence: high

SOL-4 | major | D105 §1–2 (17–18. sor)
Claim: A 0,03-as ekvivalenciatűréshez a pilot kontrollértékei nem adnak érdemi indokot. A 0,25-ös
Δ-küszöbnek van értelmezhető skálahorgonya, de a pilottól függetlenül meg kell indokolni, miért
éppen ekkora előny számít; a pilot minden párja már meghaladta.
Evidence: A Z-kontrollok páronkénti átlagai 0,49730 és 0,50757, a P1-permutált és P2-címkekontrolléi
0,43201 és 0,58124 (experiments\e5\pilot\{z6__shared__permuted,z6__shared__labels,P1__shared__permut
ed,P2__shared__labels}.json:545). A címkekontroll csak a tanítócímkéket permutálja, a hangolási
címkéket nem (src\ncm_sudoku\e5pilot.py:107–115; src\ncm_sudoku\e3controls.py:144–169). D101 a
kontrollokat diagnosztikának tekinti és a helyileg azonos állapotok miatt kényszerű kötéseket
dokumentál (2026-11-25-e5-d101-readout-design.md:51,56).
Recommendation: A közép maradjon 0,5: a jelölt és nem jelölt bit megkülönböztetése nélküli,
kötéseket felesen számoló rangsorolás referenciája ez, nem a kontrollok empirikus átlaga. A ±0,03-at
csak akkor rögzítsék, ha igazolható, hogy páronként súlyozva száz diszkordáns összevetésre vetítve
három nettó találatnyi eltérés még elhanyagolható, a kényszerű kötések beszámításával is. A Δ=0,25
külön, nagy hatásként védhető: W(Z)≈0,5 mellett legalább kb. 0,75-ös prefixrangsorolást kér. A
küszöbök előzetes pilotismerete nem TEST-szivárgás, de az indoklás ne a várható siker legyen.
Confidence: high

SOL-5 | major | D105 §3 (19. sor)
Claim: A véletlen altérrel szembeni kapufeltétel elhagyása módosítja D102-t; ezt D105 nem mondja ki.
A Q és a kontrollok közötti különbség az adott beavatkozásra érvényes, de az eltérő igazodás miatt
nem választja el egyértelműen a számjegyspecifikus hatást az általános irányérzékenységtől.
Evidence: D102(7) a véletlen kontrollt is megköveteli (2026-11-25-e5-d102-causal-design.md:24); D104
a nagy varianciájú kontrollt emeli ki, de nem törli a korábbi kritériumot (DECISIONS.md:140–142). A
kód a lépésnormát egyezteti és egyetlen rögzített számjegy-derangementet használ
(src\ncm_sudoku\e5causal.py:67–99). A lépések átlagos koszinusza Q-nál 0,541, a nagy varianciájú
kontrollnál 0,471, a kevertnél −0,002 (experiments\e5\causal\cosines.json:5–18).
Recommendation: Vagy tartsák meg a Q−véletlen feltételt ugyanabban a konjunktív kapuban, vagy
dokumentáltan módosítsák D102-t, és nevezzék a véletlen kontrollt diagnosztikának. A megerősítő
állítás a 7. szint kódeloszlásának referencia felé mozdulására és a megnevezett kontrollokra
szorítkozzon. Erősebb számjegyspecifikus mechanizmusállításhoz az igazodást is egyeztető kontroll
kellene.
Confidence: high

SOL-6 | major | D105 §5–6 (21–22. sor)
Claim: Az 500 pár védhető lehet másodlagos pontossági célból, de a várható rétegméret önmagában nem
ilyen cél. A kisebb TEST nem helyes eszköz a befagyasztott próba tartós eltolódásának elfedésére.
Evidence: A PROBE-VAL nyers tömbjeiből 162/250 pár kódkülönböző és 51/250 pár pontosan egy tagja
megoldott (runs\e5\acts\probe_val\{a,b}\{codes,solved}.npy; a kódszelet:
src\ncm_sudoku\e5pilot.py:28–38). A 20,4%-os pilotarányt rögzítettnek véve 500 párból csak kb. 61%
eséllyel lesz legalább 100 ilyen pár. Száz független párnál egy bináris arány 95%-os
Wilson-intervallumának maximális félhossza kb. 9,6 százalékpont. A nagyobb minta keskenyebb
intervallumot ad, nem tolja el az átlagot: valódi sávon kívüli eltérésnél az ekvivalencia ne
teljesüljön. A rescue/harm ráadásul teljes generálást igényel, nem a D105-ben árazott egyetlen 7.
szintű futást (2026-11-25-e5-d102-causal-design.md:22,25).
Recommendation: Zárolás előtt adják meg a rétegenkénti kívánt pontosságot és annak elérési
valószínűségét konzervatív rétegaránnyal. A rögzített N legyen az elsődleges erő és a vállalt
másodlagos pontosság mintaméret-igényének maximuma. Ha a rescue csak leíró és nincs pontossági
vállalás, kisebb TEST is indokolt lehet. A teljes generálást külön árazzák vagy hagyják ki;
TEST-eredmény alapján ne növeljék N-t.
Confidence: high

SOL-7 | minor | D105 §3 (19. sor); nyitott kérdés (28. sor)
Claim: A 0,01 TV értelmes lehet abszolút átlagküszöbként, de nem jelenti azt, hogy az irányított
hatás egy tipikus vagy minden recipiensnél ekkora, és nem mér argmax- vagy megoldási javulást.
Evidence: A nyers adatokban a teljes csere átlagos TV-je 0,06134, mediánja 0,02894; 71/500
recipiensnél 0,01 alatt van (runs\e5\causal\primary.npz; experiments\e5\causal\primary.json:41–44).
Az irányított hatás TV(clean, full) − TV(cond, full), így az utóbbi recipienseknél matematikailag
nem érheti el a 0,01-et (scripts\e5_causal.py:153–165). Ez nem akadálya a teljes populáció átlagára
tett állításnak; a küszöb a pilot átlagos referenciatávolságának kb. 16%-a.
Recommendation: Ha 0,01 marad, indokolják átlagosan egy százalékpontnyi, referencia felé történő
TV-távolságcsökkenésként, ne a pilot hatásának hányadaként. A kis referenciatávolságú recipiensek
maradjanak az elsődleges átlagban; a heterogenitást külön, leíróan közöljék, közel nullával való
osztás nélkül.
Confidence: high

SOL-8 | minor | D105 §5–6; D101 §5
Claim: A pilot futtatók nem helyettesítik a befagyasztott TEST-eljárást. Változtatás nélküli
újrahasználatuk eltérne a tervezett pontozástól, hibakezeléstől és intervallumoktól.
Evidence: Az E5-párgeneráló csak a két PROBE-halmazt állítja elő (scripts\e5_pairs.py:33–34,45–69).
A pilot W-AUC a predikciók egyenlőségét figyeli, nem az igazoltan azonos bemenetet, és nincs hibával
leálló nemvégesérték-ellenőrzése (src\ncm_sudoku\e5pilot.py:56–83). A kauzális pilot fix 95%-os
intervallumot ad és eldobja a nem véges értékeket (scripts\e5_causal.py:56–63).
Recommendation: A zárolás előtt rögzítsék a külön TEST-futtatót, a befagyasztott fejek és kontrollok
azonosítóit, a párazonosítókat és a kizárási naplót. Ütközéskor csak az új TEST-jelöltet cseréljék;
pontozási hibánál ne csökkenjen csendben a nevező. Az ágváltást és a kényszerű kötéseket szintetikus
adatokon ellenőrizzék még TEST-generálás előtt.
Confidence: high

Claims checked

 - holds — Két különböző, 30 megadott cellás maszk ugyanarra az egyedi megoldásra; a TEST-hez a
10-es névtér van kijelölve. Az egzakt orbit-szűrés a PROBE-generálóban megvan; az E5 TEST-re
alkalmazása még terv (src\ncm_sudoku\e5pairs.py:26,40–75; scripts\e5_pairs.py:45–69;
DECISIONS.md:137).
 - holds — Három mag predikcióinak átlaga, saját pozíciós megosztott fej, diszkordáns bitek
W-AUC-ja; overall bitösszevont, per_pair páronkénti. P2 és P3 páronkénti átlaga egyaránt 1, P2
mentett validációs Brier-értéke kisebb (src\ncm_sudoku\probes.py:269–288;
src\ncm_sudoku\e5pilot.py:63–115; experiments\e5\pilot\P{2,3}__shared__none.json:540–545).
 - holds — Újraszámolva 250 páron, minta-SD-vel: Z 0,503587 / 0,044489; Δ 0,496413 / 0,044489,
minimum 0,304348 (a két per_pair lista alapján). A durva TOST-méretek 5%-os egyoldali alfánál a
közelebbi határ alapján 63 / 25 / 8. Mindkét határt figyelembe véve, ismert szórású
normálközelítéssel, 90%-hoz 65 / 26 / 9 pár kell ε=0,02 / 0,03 / 0,05 mellett; 0,05/3-nál 87 / 35 /
12, 0,025-nél 79 / 32 / 11. Ezek nem a végleges bootstrapos eljárás erőbecslései.
 - does not hold — A „legfeljebb ±0,07” nem pontos felső korlát: a P2 címkekontroll eltérése
+0,08124. A Z-kontrollokra áll a kerekített 0,497 és 0,508
(experiments\e5\pilot\{P2,z6}__shared__labels.json:545;
experiments\e5\pilot\z6__shared__permuted.json:545).
 - holds — A 7. szinten, a recipiens első hat szintjének kódjait rögzítve fut a patch; a nyers
NPZ-ben mindkét sorrend megvan mind a 250 párra. A két sorrendet átlagolva Q 0,052038 / 0,060644 SD,
Q−nagy varianciájú 0,030066 / 0,040589 SD, Q−véletlen 0,048975, Q−kevert 0,131348. A 0,06134
teljescsere-referencia, a 14,2% alacsony referenciatávolság és a 0,541 / 0,471 koszinuszok is
egyeznek (scripts\e5_causal.py:102–126,153–214; runs\e5\causal\primary.npz;
experiments\e5\causal\cosines.json:5–18).
 - holds — A v3.7 numerikus precedense 0,05/3 és TOST-nál 1−2α; a ritka ágon egyoldali 1−α korlát.
Ez nem precedens a D105 konjunktív feltételeinek külön családtagként számolására
(research_plan_v3.7.md:265,346–356,458–461; src\ncm_sudoku\wp2eval.py:21,55–69;
src\ncm_sudoku\power.py:237–278).
 - could not verify — A tényleges E5 TEST-futásidő még nem mérhető a pilotnaplókból. Az 1 844,3
másodperces, 250 páros kauzális futás lineárisan kb. 61,5 percet ad 500 párra; a kivonatolási idők
1000 rejtvényre kb. 14–43 percet jeleznek. Ezek az elsődleges futás becslései; a befagyasztott
TEST-próbák pontozási idejére és a teljes generálásra nincs mért TEST-adat
(experiments\e5\causal\primary.json:539; experiments\e5\extract.json:44–88).

