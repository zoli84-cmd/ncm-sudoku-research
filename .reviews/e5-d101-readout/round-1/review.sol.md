Verdict

A közös sajátpozíciós próba és a független TEST jó kiindulópont, de a D101 jelen formájában nem
rögzíthető. A legfontosabb változtatás: az érvénytelen páronkénti előjelváltásos teszt helyett
ugyanazokon a TEST-párokon becsüljék a prefix–Z≤6 különbséget, előre rögzített gyakorlati küszöbbel
és párszintű intervallummal.

Findings

SOL-1 | blocker | D101, 2. pont
Claim: A két tag teljes felcserélése nem képezi a W-AUC-t 1 − w-re: a pontszám és a címke együtt
helyet cserél, így a jelölt tag továbbra is ugyanazt a pontszámot kapja. Csak az egyik oldal
felcserélése fordítja meg a statisztikát; ennek nullabeli szimmetriája nem következik abból, hogy az
átlag 0,5.
Evidence: Az e5pilot.py:66–83 a tényleges címke alapján választja ki a jelölt tagot. Az
e5pairs.py:59–70 külön RNG-folyamot használ, de egyező maszk esetén csak B-t húzza újra. Ha adott
megoldásnál a maszk eloszlása q, a különböző (a,b) maszkok rendezett valószínűsége
q(a)q(b)/(1−q(a)), ami általában nem szimmetrikus. A szimmetrikus párgenerálás sem igazolná
önmagában a pontszám és a címke egymáshoz rendelésének felcserélhetőségét.
Recommendation: Az átlagra és a párosított különbségre használjanak előre rögzített intervallumot,
például egész párokat együtt újramintázó bootstrapot, a rögzített próbákra feltételesen. Ez
különálló, közel független megoldásorbitoknál megfelelő; ismétlődő orbitnál az orbit legyen a blokk.
Egzakt permutációs teszt csak külön definiált és igazolt hozzárendelési nullhoz maradjon.
Confidence: high

SOL-2 | major | D101, 4. pont
Claim: A csak kódkülönböző párokon mért Z≤6 és az összes páron mért prefix eltérő populációt céloz.
A kódkülönbség ráadásul nem garantálja, hogy a sajátpozíciós próba bemenete az érintett cellában
különbözik.
Evidence: Az e5pilot.py:28–38,66–83 a teljes első 35 kód azonosságával rétegez; a
states.py:16–28,40–41 ezekből állítja elő a cellaállapotot. A mentett PROBE-VAL tömbökben 88/250 pár
kódazonos. A másik 162 pár 16 482 diszkordáns bitjéből 6 313-nál a helyi Z≤6 állapot is bitazonos.
Ezeket döntetlennek véve a piloton az egyenlő súlyú páronkénti Z≤6 W-AUC elméleti plafonja 0,7004
összesítve, illetve 0,8093 a kódkülönböző rétegben.
Recommendation: Elsődlegesen mindkét reprezentációt ugyanazokon az értékelhető párokon, azonos
súlyozással hasonlítsák össze. Másodlagosan mindkettőt közöljék a kódkülönböző rétegen, és külön
mutassák meg a helyi állapotazonosság arányát, illetve a változó helyi állapotokon elért eredményt.
A kódazonos réteg maradjon negatív kontroll.
Confidence: high

SOL-3 | major | Pilot, 3. megfigyelés; D101, 2. pont
Claim: A bitklaszterezés indokolja a párszintű bizonytalanságbecslést, de nem magyarázza önmagában a
kontrollok 0,5-től való eltolódását. A közel nulla exact match és a gyenge Brier nem zárja ki a
helyes vagy fordított páron belüli rangsort.
Evidence: Az e3controls.py:37–53,144–190 a reprezentációs kontrollt permutált VAL-bemeneten, valódi
VAL-címkékkel hangolja, majd az eredeti bemeneten pontozza. A címkekontroll csak a TRAIN-címkéket
keveri; az epoch és a konfiguráció kiválasztása az eredeti VAL-címkéket használja
(e5pilot.py:104–116; probes.py:157–164,232–263). A P1__shared__permuted.json:541–545 és a
P2__shared__labels.json:541–545 páronkénti átlaga 0,4320, illetve 0,5812, míg a párok közötti
szórásból becsült standard hiba 0,0035, illetve 0,0034. Ez nem azonosítja az eltolódás okát, de a
puszta klaszterezés nem meggyőző magyarázat.
Recommendation: Az E3-kontrollokat diagnosztikaként, ne 0,5-re kalibrált nullként kezeljék. A saját
permutált kontrollal vett különbség maradhat másodlagos, független TEST-en, rögzített hangolással.
Ha a kontrollszórás maga is kérdés, több előre rögzített permutációval ismételjék a teljes
illesztési és kiválasztási eljárást.
Confidence: high

SOL-4 | major | D101, 2. és 5. pont
Claim: A nagy prefix–Z≤6 különbség azonos eloszlású TEST-en várhatóan könnyen reprodukálható, de a
Z≤6 0,5-től való nem szignifikáns eltérése nem igazolja a gyakorlati jelhiányt. A P2/P3 plafonja
miatt a prefix önálló, naiv bootstrap-intervalluma akár [1,1] is lehet, ami nem bizonyít populációs
tökéletességet.
Evidence: A P2__shared__none.json:541–545 és a P3__shared__none.json:541–545 mind a 250 párján W-AUC
= 1; a z6__shared__none.json:541–545 páronkénti átlaga 0,5036. A két Z≤6 próba kiválasztott epochjai
2–8 között vannak, egyik sem éri el a 80 epochos plafont (z6__shared__none.json:515–532;
z6__whole__none.json:515–532).
Recommendation: Rögzítsenek előre egy érdemi alsó küszöböt a párosított prefix–Z≤6 különbségre, és
külön felső határt vagy ekvivalenciatartományt arra, mekkora Z≤6-jel számít még elhanyagolhatónak. A
mintaméretet az utóbbira tervezzék, ne a közel 0,50-os különbségre. Z≤6-on elsőbbséget élvezzen a
konvergált referencia és az illesztési cél ellenőrzése; a B3/P8 többletfuttatásait és az MDL-t
hagyják feltárónak, a kauzális kérdést pedig D102-re.
Confidence: high

SOL-5 | major | D101, 1. pont; Pilot, 2. megfigyelés
Claim: A shared head tisztességes közös mérce a rögzített, cellánként megosztott lineáris
próbacsaládra, de nem azonos kapacitású vagy skálájú összevetés, és nem mér általános
információhiányt. A P0 egészréteges eredménye valóban a bemeneti szabály kiolvasása; ebből nem
következik, hogy minden magasabb prefixréteg egészréteges eredménye is csak nyers bemenetet mér.
Evidence: A probes.py:56–70,85–88,136–164 skálázatlan saját állapothoz fűzi a cella-one-hotot, majd
közös kilenckimenetes fejet illeszt: 3 042 paraméter Z≤6-nál, 5 346 a prefixnél. Z≤6 felmintázott,
reziduálisan transzformált kódkönyvi hozzájárulások összege (states.py:16–28); a pozitív kontroll
untied fejet validált (DECISIONS.md:133–136). P0-n a peer-tokenek kontextus nélküli embeddingjei
hozzáférhetők, a címke pedig a peer-nyomokból számolható (next_concept.py:546–560;
wholelayer.py:109–141,158–171; labels.py:29–37). A későbbi prefix már kontextualizált, de a figyelmi
maszk kizárja a generálási query-k visszahatását a prefixre (next_concept.py:501–518). Z≤6-nál nincs
közvetlen nyerstoken-bemenet a próbához.
Recommendation: Tartsák meg a shared fejet, de korlátozzák az állítást a sajátpozíciós lineáris
olvashatóságra. A gyenge Z≤6-eredményhez használjanak csak TRAIN-en skálázott, konvergált
referenciát, és érzékenységi ellenőrzésként közvetlenül a diszkordáns, azonos cellás
állapotkülönbségekre illesztett lineáris rangsorolót. P0/whole legyen bemeneti plafon; a magasabb
prefixrétegek és a Z/whole legyenek diagnosztikusak, ne bizonyítékok arra, hogy a generátor a
kiolvasott jelet használja.
Confidence: high

SOL-6 | minor | D101, 3. pont; Pilot-táblázat
Claim: Az argmax szabály nem választja ki egyértelműen P2-t: P2 és P3 a páronkénti átlagban is
pontosan holtversenyben van. A VAL többszöri használata a VAL-eredményt optimistává teheti, de a már
kiválasztott próba becslését nem torzítja, ha a TEST valóban érintetlen marad.
Evidence: A probes.py:157–164,178–193,237–263 ugyanazt a VAL-t használja az epoch és a konfiguráció
kiválasztására. A két réteg mentett w_auc.per_pair értékei mind 1-ek (P2__shared__none.json:541–545;
P3__shared__none.json:541–545). Az e5pilot.py:73–83 szerint a táblázat overall és codes_differ mezői
bitszámmal súlyozottak, nem a kiválasztáshoz javasolt páronkénti átlagok.
Recommendation: Rögzítsék a teljes pontosságú páronkénti átlagot és a holtversenyszabályt, például
az alacsonyabb réteg előnyét. A TEST előtt fagyasszák be a réteget, az előfeldolgozást és a
próbaállapotokat. A pilot táblázat jelölje a súlyozást; a teljes réteggörbe maradjon leíró.
Confidence: high

SOL-7 | minor | D101, 2. és 4. pont; Pilot, 1. megfigyelés
Claim: A pilot pontozója a nulla diszkordáns bitű párt NaN-ként tárolja, de egy NaN predikciót
érvényes diszkordáns biten csendben vereségnek vesz. A bitazonos bemenet sem garantálta a mentett
predikciók egzakt azonosságát.
Evidence: Az e5pilot.py:56–83,137–142 szigorú >/== összehasonlítást, nulla nevezőnél NaN-t és
alapértelmezett json.dumps-ot használ. A pilotban a legkisebb bitszám 70 (pairs.json:1339–1344). A
teacher állapotok páronként bitazonosak, de a mentett shared/none és whole/none predikciókban
egyaránt volt 2,98×10⁻⁸ eltérés; mindkét JSON overall értéke 0,500019671
(z6_teacher__shared__none.json:541–545; z6_teacher__whole__none.json:548–552). P0/shared/none
összesítve valóban 0,5 (P0__shared__none.json:541–545).
Recommendation: A nulla diszkordáns bitű párok mindkét reprezentációnál ugyanazzal a szabállyal
maradjanak ki; az elemszámot jelentsék, az üres réteg legyen nem becsülhető (null, ne NaN). A nem
véges pontszám értékelhető biten állítsa le a pontozást. Az igazoltan azonos próbabevitelnél legyen
definíció szerint döntetlen.
Confidence: high

SOL-8 | minor | Pilot, 4. megfigyelés
Claim: Nem igaz, hogy néhány global futás kivételével minden pilotillesztés a (0, 0.003)
konfigurációt választotta. A fő Z≤6-illesztések is más konfigurációt választottak.
Evidence: A 44 nem global eredményből 17 választotta a (0, 0.003) beállítást. A
z6__shared__none.json:3–8 és a z6__whole__none.json:3–8 egyaránt (0.1, 0.001)-et rögzít; ugyanezt
választotta mind a 11 shared/permuted futás. A D96 kapacitáskorlátja a másik modell 1–7. rétegére
vonatkozik (DECISIONS.md:134).
Recommendation: A konfigurációt és az epochplafon elérését külön közöljék reprezentációnként. A Z≤6
konvergencia-ellenőrzését ne egy ott nem megfigyelt epochplafonnal indokolják.
Confidence: high

Claims checked

 - holds — A pilot-tábla mind a 19 sora egyezik a mentett w_auc.overall, w_auc.codes_differ,
summary.val_brier_mean és metrics.exact_match mezőkkel a kijelzett pontosságon. P3 exact match
értéke 0,999529, nem pontosan 1 (P3__shared__none.json:799); a címkekontrollok sem kivétel nélkül
nullák.
 - holds — A pilot W-AUC mindkét tagban üres cellán, pontosan az egyik tagban jelölt biteket
értékel; a szigorúan azonos véges pontszám 0,5. A per_pair páron belül átlagol, az összesítő mezők
biteket súlyoznak (e5pilot.py:63–83). A közös megoldásból egyedül meghatározott pontszám nem adhat
irányt ugyanazon cella és számjegy páron belüli összevetésében.
 - holds — Azonos megoldás, két különböző, 30 nyomos, egyedi megoldású feladvány; 1 000/250 pár. A
rögzített korábbi halmazok és az E5-párok közötti kanonikus szűrés nem zárt ki pilotpárt. A
kontrasztméretek a szövegben közelítő értékek (e5pairs.py:40–70,78–96; scripts/e5_pairs.py:33–77;
pairs.json:1037–1053,1327–1361). A pilot runner csak a PROBE-TRAIN/VAL halmazt tölti
(scripts/e5_pilot.py:28–36).
 - holds — A kinyerés a 7. szintet generáló menet 0–8. rétegét menti, cella- és záró
BOS-pozíciókkal; a megoldási arány 85,8–88,0%. A mentett kódok 319/1 000, illetve 88/250 párban
azonosak az 1–6. szinten; a kódkülönböző pilotpárok mentett Z≤6 tenzorai valóban eltérnek
(e5extract.py:19–50,53–73; extract.json:45–98; e5pilot.py:24–38).
 - holds — A sajátpozíciós fej állapotot és cella-one-hotot kap; a whole head saját állapotot és a
saját cella plusz 20 peer TRAIN-en illesztett, fehérített PCA-ját; a BOS-fej 729 külön kimenetű.
P0/whole W-AUC és exact match egyaránt 1 (probes.py:56–88; wholelayer.py:109–141,158–171;
e5probes.py:65–74; P0__whole__none.json:548–550,806).
 - does not hold — A teacher állapot azonossága igaz, az egzakt 0,5 állítása a mentett pontszámokra
nem; a két tizedespontosságon túli eltérés nem érdemi jel (runner.py:36–38;
extract.json:52,66,80,94; SOL-7). A (0, 0.003)-ra vonatkozó általánosítás és a tagcsere-inverzió sem
áll (SOL-8 és SOL-1).
 - holds — A kézirat a gyenge Z≤6-kiolvasást írja le, és a generátor belső aktivációira vonatkozó
magyarázatot nem teszteli (paper/sections/discussion.tex:7–9,23). A külső pozitív kontroll mindkét
precízión átment; a 6. blokk értéke bfloat16-ban 0,9978, float32-ben 0,9979 kerekítve
(DECISIONS.md:132–136).

