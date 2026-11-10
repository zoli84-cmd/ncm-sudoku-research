Verdict

A második CAL-pilot adatgyűjtése folytatható, de a mintanagyság meghatározása és a konfirmatív
zárolás előtt javítani kell a §11.4 szimulációját. A legfontosabb változtatás: az
ekvivalenciaszimuláció őrizze meg a nulla különbségeket és a lehetséges kimenetek tartományát, ne
egyszerű átlaglevonással állítsa elő a nulla hatást.

Findings

ASTRA-1 | major | research_plan_v3.6.md:375

Claim: A feladatszintű különbségek központosítása nem kompatibilis a §11.2 ritkaesemény-szabályával:
a valódi nullákat nemnullává alakítja, és lehetetlen különbségeket is létrehozhat. Így a tervezési
szimuláció más intervallumeljárást alkalmazhat, mint amelyet a tényleges adatok indokolnának.

Evidence: Az első pilot 2–11 kontrasztjának eloszlása: 296 nulla, valamint −1, −1/3, 2/3 és 1;
átlaga 1/900. Ezt a runs\wp1\pilot_records.jsonl:1801–2700,9001–9900 rekordjaiból, a
src\ncm_sudoku\e2.py:81–87 aggregálásával ellenőriztem. Az átlag kivonása után a nemnulla feladatok
száma 4 helyett 300, tehát eltűnik a Clopper–Pearson-ág; a −1 érték pedig −901/900 lesz, megsértve a
research_plan_v3.6.md:363 által megkövetelt [−1,1] tartományt. Ez az R1-javítás konkrét
ellenpéldája, nem a korábbi kifogás megismétlése.

Recommendation: Nulla várható értékű, de nullatömeget és megengedett kimeneteket megőrző eloszlást
használjanak, például a különbségek előjel-szimmetrizált empirikus keverékét. Minden szimulált
mintán a tényleges bootstrap/ritkaesemény-váltás fusson; az ekvivalenciaeljárás hibaarányát a ±3 pp
határokon is ellenőrizzék.

Confidence: high

ASTRA-2 | major | research_plan_v3.6.md:375

Claim: A H2-ritkítás matematikailag helyes 5 pp-os alternatívát állít elő, de egyúttal csökkenti a
nemnulla különbségek arányát és a második momentumot. A terv említ diszkordancia-érzékenységi
futást, de nem rögzíti annak tartományát vagy azt, mikor kell az eredménye miatt növelni a TEST
méretét; a 90%-os erő így csak a választott ritkított modellre támasztható alá.

Evidence: Ha X a pilotkülönbség és B független Bernoulli(p), akkor E[BX]=pE[X], de E[(BX)²]=pE[X²]
is. Az első pilot 1–11 kontrasztján p=0,576923: a nemnulla arány 18,67%-ról 10,77%-ra, az 5 pp-os
alternatíva varianciája 0,04494-re csökken. Ugyanazon eredeti abszolút különbségeket megtartó,
előjelkeveréssel 5 pp-ra állított modell varianciája 0,07972. Ezek szemléltető elsőpilot-számítások,
nem másodikpilot-eredmények (runs\wp1\pilot_records.jsonl:1–900,9001–9900). A §11.4 maximumszabálya
az endpointokra vonatkozik, az érzékenységi forgatókönyvekre nincs döntési szabály.

Recommendation: A ritkítást nevezzék meg egy tervezési forgatókönyvként. Előre rögzítsenek legalább
egy, a pilot diszkordanciáját/második momentumát megőrző alternatívát és a vizsgált tartományt; a
TEST méretét az elfogadott forgatókönyvek legnagyobb követelményéből válasszák, vagy egyértelműen
korlátozzák az erőre vonatkozó állítást.

Confidence: high

ASTRA-3 | minor | research_plan_v3.6.md:211

Claim: Az új AUC-szabály nem kezeli az azonos átlagos kárral, de eltérő solve-változással rendelkező
dóziscsomópontokat. Két nemnulla dózis és pozitív közös tartományszélesség mellett is maradhat
ilyen holtverseny, amelyből nem adódik egyértelmű, darabonként lineáris függvény.

Evidence: A §7.3 kizárólag a csomópontok kár szerinti rendezését írja elő; nincs holtverseny-kezelés
vagy különböző x-koordinátákra vonatkozó feltétel. Egy belső, azonos x-hez tartozó két különböző y
sorrendje a szomszédos szakaszokat és az integrált is megváltoztathatja. Másodikpilotos TV-adat még
nincs, ezért tényleges előfordulást nem állítok.

Recommendation: Rögzítsék az azonos kárértékű csomópontok összevonását és súlyozását, vagy ilyen
konfliktus esetén ne közöljenek AUC-t. A görbéhez legalább két különböző kárértéket követeljenek
meg.

Confidence: high

Claims checked

 - does not hold — SOL-1 / CARBON-1 teljes lezárása: a célalternatíva és az ekvivalenciaszimuláció
javítása nem teljes; lásd ASTRA-1–2. holds: a H3 félintervallum-szélesség ≤3 pp követelménye a
futások legalább 80%-ára már egyértelmű. A szokásos, megfelelő lefedettségű 90%-os intervallum ±3
pp-on belülisége helyes TOST-szabály.
 - holds — SOL-2: a feladat mint független egység megfelel a generálásnak
(src\ncm_sudoku\generate.py:64–93). [−1,1]-beli különbségre |E[X]|≤P(X≠0); a megadott egyoldali
CP-szintek megfelelő konzervatív korlátot adnak. H3-nál ehhez a tervezett B=A azonosság szükséges. A
hibrid eljárás tényleges lefedettsége még nem igazolt.
 - holds — SOL-3 / CARBON-2 fő javításai: páronkénti összehasonlítás, feladaton belüli átlagolás,
dóziscsomópontok, közös tartomány, pozitív szélesség, TEST-lefedettség és az
  1. szint kizárása mind szerepelnek. Az ASTRA-3 peremeset még hiányzik.
 - holds — CARBON-3: a 12-tokenes TV implementálható, formátumhibánál is definiált. A konfiguráció
in_vocab_size: 12 értéke, a src\ncm_sudoku\states.py:32–33 logitkimenete és a
src\ncm_sudoku\grid.py:23–25 cellapozíciói egyeznek a definícióval. A mérés még tervezett, nem
meglévő piloteredmény.
 - holds — CARBON-4: az E3-előkészítés megelőzi a zárolást; egyetlen TEST-méret lesz a H1 és E2
követelményeinek maximumából (research_plan_v3.6.md:375,393–394; ROADMAP.md:13–14). D51 kifejezetten
felülírja D47–D49 érintett részeit, ezért a történeti bejegyzések nem új ellentmondások.
 - holds — CARBON-5: az eredeti kód kizárása utáni renormalizálás, nulla súly, nulla nevező és
befagyasztott CAL-vektor szabálya helyes; megfelel a jelenlegi mintavételi politikának
(src\ncm_sudoku\perturb.py:47–52). Az enumeráló végrehajtás még elkészítendő.
 - holds — CARBON-6: a tanult elsőszintű felmintavételezés ténylegesen aktív
(checkpoints\sudoku\hard\config.yaml:72; third_party\ncm\models\quant.py:404–411). A §13 értelmezési
korlátozása ezt megfelelően tükrözi.
 - holds — CARBON-7: a módosított prefixhez viszonyított reziduum későbbi kódkönyvekkel történő
kvantálása értelmes geometriai diagnosztika. Megvalósításakor a későbbi szintek
downsample–kódválasztás–upsample–reziduális transzformáció lépéseit kell követni
(third_party\ncm\models\quant.py:588–610); a teljes z_to_idx változatlan hívása az első szintről
indulna.
 - holds — SOL-4 / CARBON-8: a nyers rekordok minden közölt solve-átlagot visszaadnak; L1-frequency
esetén A=0,850, C=0,755556, D=0,763333. L2-frequency esetén C=A minden futásban; a mért 2/6/11
szinteken a nulla Hamming-arány konfigurációnként legalább 98,33%. A policy- és ágmegkülönböztetés
javítása helyes.
 - holds — CARBON-9: a státusz javítása összhangban van a G0 és a kapu sikeres eredményével
(experiments\g0\reproduction.json:79–85; experiments\wp1\gate.json:100–103); az
  1. szint már elsődleges H2/H3 vizsgálatként szerepel. A §3, §7, §11, §12 és §16 fő kontrasztjai
egyeznek.
 - could not verify: a TEST történeti érintetlensége a fájlokból önmagában nem bizonyítható. A
megvizsgált pilotrekordok kizárólag a 300 CAL-feladatot tartalmazzák; másodikpilotos erő- vagy
lefedettségi eredményt nem állítok.

Eljárási eltérés: a brief megismerése előtti első párhuzamos olvasásban a tárhelyen kívüli AGENTS.md
is megnyílt. Szakmai bizonyítékként nem használtam; fájlt nem módosítottam.

