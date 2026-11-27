A pilot számai reprodukálhatók. A nullhatárok és az N-választás ellenőrzéséhez külön megnézem, milyen páronkénti eloszlást hoznak létre a leírt transzformációk.

Verdict

A két állításra osztott hibakeret és a belső orbitütközéskor elmaradó megerősítő döntés
statisztikailag védhető, de a D105 még nem zárolható. A legfontosabb javítás a B2–B4
nullforgatókönyvek pontos meghatározása: a jelenlegi szöveg alapján a hibaarány ellenőrzése akkor is
hibátlan nullát mutathat, ha érdemben nem tesztelt semmit.

Findings

 ASTRA-1 | major | D105, 6(c), 22. sor
 Claim: A kontroll „Q felé emelése” nem definiál egyértelmű, változékonyságot megtartó nullmodellt.
A B4 esetén a páronként Q felé mozgatott kontroll csak úgy érheti el Q átlagát, ha minden párban
pontosan Q lesz. Ekkor minden kontraszt nulla, a tőke mindig 1, a mért tévespozitív-arány
szükségszerűen nulla.
 Evidence: Az experiments\e5\causal\primary_per_pair.json:31–786 szerint Q−shuffled mind a 250
párban pozitív. Az átlagkülönbség konstans hozzáadása sem jó megoldás: 133/250 párban a módosított
shuffled hatás meghaladná az adott pár teljes cseréjének referencia-távolságát, ami a
scripts\e5_causal.py:154–164 képlete szerint lehetetlen.
 Recommendation: A 6(c) minden esetét külön, név szerint megadott alapmodellből képezzék. Például
F=full_be mellett C′=(1−t)C+tF, ahol t=(E[Q]−E[C])/(E[F]−E[C]); minden más oszlop változatlan. A
pilotban t rendre 0,8404 / 0,7638 / 0,9339 a random / high-variance / shuffled kontrollra: mindhárom
kontraszt átlaga nulla, mindkét előjel előfordul, és a referenciahatár megmarad.
Tévespozitív-aránynak csak a ténylegesen nullán álló feltétel és az azt tartalmazó állítás döntési
arányát nevezzék.
 Confidence: high

 ASTRA-2 | major | D105, 2. pont, 18. sor
 Claim: A tét képlete nem rögzíti a futó variancia rekurzióját. Az előző vagy az aktuális
futóátlagtól vett négyzetes eltérés egyaránt megfelel a leírásnak a következő tét számításakor, de
más tőkét, döntést és tervezett N-et adhat. Az „eléri a 40-et” sem ugyanaz a végrehajtási szabály,
mint a kizárólag utolsó pár utáni szigorú összehasonlítás.
 Evidence: A D105:18 csak a két kezdőértéket adja meg. A skálázásnál a nyers B1-et is név szerint
kell kezelni: az experiments\e5\causal\primary_per_pair.json:31–282 két negatív Q-értéket tartalmaz;
ez nem [0,1]-beli TV-távolság, hanem két távolság különbsége (scripts\e5_causal.py:164).
 Recommendation: Egyetlen, a szimulációban és a TEST-en közös függvényt zároljanak. Például
μᵢ=(0,5+Σⱼ≤ᵢXⱼ)/(i+1), vᵢ=(0,25+Σⱼ≤ᵢ(Xⱼ−μⱼ)²)/(i+1); a következő tét vᵢ-t használja. Rögzítsék c
végleges értékét és a terminális log K > log 40 döntést, ne a korábbi maximumot. A transzformált
nullhatárok legyenek tételesek: A1 mindkét irányban 0,47; A2 0,625; B1 0,505; B2–B4 0,5. A tervezett
N és a ténylegesen beszorzott jogosult párok száma külön változó legyen.
 Confidence: high

 ASTRA-3 | major | D105, 5. pont, 21. sor
 Claim: N nincs definiálva, ha 1000-ig nincs megfelelő rácspont, vagy ha a kiválasztott N független
újraellenőrzése 0,90 alá esik. A 2000 ismétlésre írt 0,007-es MC-standardhiba csak a célérték körül
igaz, nem minden rácsponton.
 Evidence: SE=√[p(1−p)/R]; R=2000 mellett ez p=0,90-nél 0,00671, p=0,50-nél 0,01118. A korábbi
src\ncm_sudoku\power.py:66–72 kifejezetten None-t ad, ha nincs megfelelő N; a D105-ben szereplő
max(N_power,250) ilyen esetben nem szabály.
 Recommendation: Rögzítsék az ismétlésszámot, a két szimulációs seedet és a sikertelen ellenőrzés
következményét. Egyszerű szabály: ha nincs találat vagy az előírt független ellenőrzés nem sikerül,
nincs zárolás és nincs TEST-generálás. A 0,007-et korlátozzák a 0,90 környezetére, vagy használjanak
legalább 5103 ismétlést az egész rácsra vállalt korláthoz.
 Confidence: high

 ASTRA-4 | major | D105, 5. és 7. pont, 21–23. sor
 Claim: A „csak nem véges modellkimenet állítja le a futást” megengedi, hogy véges, de hibás helyen
vagy hibás kontrollal végrehajtott beavatkozásból szülessen B állítás. Ez nem jogosultsági kizárás,
hanem a mérés érvénytelensége.
 Evidence: A scripts\e5_causal.py:102–111 a hibás hook-hívásszámot és a query-izoláció sérülését
csak jelzőbe írja; a 147–151. sor viszont véges self-donor eltérésnél is leáll. A
src\ncm_sudoku\e5causal.py:75–85 pozitív célnormához tartozó nulla kontrollprojekciónál hibát jelez.
Ezek a D102-terv 21. sorában előírt ellenőrzések; a DECISIONS.md:142 minden feltételre
irányilleszkedési naplót is kér.
 Recommendation: Különítsék el a címke alapján nem jogosult párt az érvénytelen futástól.
Hash-eltérés, hibás hook-hívásszám, izolációs, identitási vagy normaellenőrzési hiba esetén ne
lehessen B-t megerősíteni; a hibás pár elhagyásával se. A feltételenkénti irányilleszkedés maradjon
naplózott diagnosztika, ne új szignifikanciateszt.
 Confidence: high

 ASTRA-5 | minor | D105, 5–6(b), 21–22. sor
 Claim: A 6(b) az átlaghatásra konzervatív, a párok közötti változékonyságra nem feltétlenül: minden
hatás felezése a szórását is pontosan felezi. Ez a különbség a tervezett N-nél már számít.
 Evidence: Az experiments\e5\causal\primary_per_pair.json:30–1542 sorain, a 0,515-re újrasúlyozott
modellen összevetettem a felezést azzal, hogy páronként 1/2 valószínűséggel minden feltétel eredeti
marad, egyébként minden hatás nulla. A két modell várható értékei azonosak. N=400, c=0,75, az
ASTRA-2-ben megadott rekurzió, 333-as seed és 2500 ismétlés mellett B becsült ereje 0,9944, illetve
0,9000 volt.
 Recommendation: A felezést nevezzék a választott tervezési modellnek, ne általános konzervatív
korlátnak. A kiválasztott N mellett közöljék ezt az egy azonos átlagú, heterogénebb érzékenységi
esetet is; ehhez nem kell új TEST-adat vagy új végpont.
 Confidence: high

 ASTRA-6 | minor | D105, 2. pont és Review, 18. és 27. sor
 Claim: Az „index 0..N−1” nem lehet egyszerre nyers generálási index és a külső szűrésen átjutott N
pár sorszáma. A Review „without replacement” rövidítése a régi D99 pótlási szabállyal együtt
félreérthető.
 Evidence: A src\ncm_sudoku\e5pairs.py:59–70 a nyers indexet a pár azonosítójába írja; a régi
scripts\e5_pairs.py:53–69 kizárás után N-től tovább generál. Ha például a 0. jelölt korábbi
adathalmazzal ütközik, az első N átjutó pár már nem a 0..N−1 nyers indexű sor.
 Recommendation: A nyers index növekedjen 0-tól az N-edik külsőleg elfogadott párig; a fogadási
sorrend ezek nyers index szerinti sorrendje. Mondják ki, hogy a D105 TEST-re felülírja a D99 belső
pótlását: belső ütközéskor egyik állítás sem tehető meg, újrahúzás nincs. A hibagarancia erre a
teljes eljárásra vonatkozik, nem az ütközésmentességre feltételesen.
 Confidence: high

 ASTRA-7 | minor | D105, 1. és 3. pont, 17. és 19. sor
 Claim: Az elfogadott R2-es hatókörszűkítés a 3. pontban szerepel, de az állítás hivatalos
felsorolásában még mindig „not from Z<=6” áll. A „15 nettó helyes a maradék 100 biten” átváltás
súlyozása sem azonos a D101 külön közölt, jogosult páronként egyenlő súlyú mutatójával.
 Evidence: A D101-terv:51,55–58 és a src\ncm_sudoku\e5pilot.py:63–83 szerinti újraszámításban a nem
kényszerített bitek páronkénti átlagos hányada 0,40089. A 0,06/0,40089≈0,15 átváltás e hányaddal
súlyoz; a maradék biteken a súlyozott W 0,50895, a D101-ben jelentett egyenlő pársúlyú W 0,50864 a
162 jogosult páron.
 Recommendation: Már az 1. pontban is a befagyasztott saját pozíciós próba gyakorlati
ekvivalenciáját nevezzék meg. A 15/100-at jelöljék a pilot kötési arányával számolt, súlyozott
szemléltetésnek, nem a külön rétegre érvényes ekvivalenciahatárnak.
 Confidence: high

Claims checked

 - holds — A 250 pár adataiból W(Z)=0,503587, mintaszórása 0,044489; 96 érték pontosan 0,5, köztük
mind a 88 kódazonos pár. P2 mind a 250 párban 1; Δ átlaga 0,496413, szórása 0,044489, minimuma
0,304348. P2 és P3 W-je azonos, az alacsonyabb Brier P2-t választja. Forrás: experiments\e5\pilot
megosztott fejű JSON-jainak w_auc.per_pair mezője; src\ncm_sudoku\e5pilot.py:24–37,63–83.
 - holds — A két irányt páronként átlagolva Q=0,052038 (SD 0,060644), Q−high-variance=0,030066 (SD
0,040589), Q−random=0,048975, Q−shuffled=0,131348. A referencia átlaga 0,061337; 71/500 recipiens
marad 0,01 alatt. A 0,01 így az átlagos referencia-távolság mintegy 16%-a, nem recipiensenkénti
minimum. A kozínuszok 0,54137 és 0,47130; a 20 véletlen bázis seedje 1000–1019
(scripts\e5_causal.py:79–89,113–140,184–212; experiments\e5\causal\cosines.json:5–11).
 - holds — A 0,5-ös közép indokolt: a döntetlen fél pont, az E3-kontrollok nem kalibrált nullok. A
0,03 sáv 6 nettó helyes sorrendezés/100 összehasonlítás; a Δ>0,25 az aktuális Z-átlagtól függően
0,72–0,78 feletti prefix-W-t igényel. Ezek értelmezhető gyakorlati küszöbök, nem a pilotból
következő állandók. A nagyobb N nem indok a sávon kívülre eső valódi próbaeltérés elfedésére.
 - holds — Nemnegatív, előre jelezhető, megfelelően korlátozott tétekkel a null alatti tőke várható
értéke legfeljebb 1. Egy hamis konjunktív állítás megerősítéséhez legalább egy igaz nullt el kell
utasítani: így állításonként 0,025, együtt legfeljebb 0,05 a hiba, függetlenség nélkül az állítások
között. A korábbi wp2eval.py:21,55–67 három állításra használt 0,05/3-at, a TOST-on belül viszont
ugyanígy a teljes állításszintet használta oldalanként (1−2α).
 - holds — A korábbi durva normálközelítés 5%-os egyoldali szinten, 90%-os erőnél és
ε=0,02/0,03/0,05 mellett 63/25/8 párt ad a közelebbi határra. Mindkét TOST-feltételt együtt
számítva, ismertnek vett pilot-SD-vel ez 65/26/9; a mostani 0,025-ös szinten 79/32/11. Egyik sem a
fogadási próba TEST-mérete. A 250-es leíró költségminimum és a másodlagos precizitásvállalás
elhagyása megfelel az R2-ben módosított döntésnek.
 - holds — A 96 pontosan 0,5-ös sor összsúlyát megtartó exponenciális újrasúlyozással mindhárom
Z-célátlag elérhető: 0,47, 0,515 és 0,53. A teljes sorok újramintázása és a kontrasztok
újraszámítása megőrzi a párosítást. Az így mért hibaarány a választott tervezési modellé, nem a
friss TEST empirikus kalibrációja.
 - does not hold — A rács egészére írt 0,007-es MC-standardhiba nem következik 2000 ismétlésből.
could not verify — A végleges TEST-futtató, fogadási implementáció, összes hash és zárolt N még nem
ellenőrizhető kész eredményként; a dokumentum ezeket jövőbeli zárolási feltételként írja le.

