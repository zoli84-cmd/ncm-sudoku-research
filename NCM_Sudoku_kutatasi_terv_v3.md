# NCM–Sudoku: hierarchikus érzékenység, hibaterjedés és logikai reprezentációk

**Kutatási terv v3.0 — a két szakmai review alapján átdolgozva**  
**Dátum:** 2026-11-08  
**Előzmény:** `NCM_Sudoku_kutatasi_terv_v2.md`, annak részletes szakmai bírálata és a kiegészítő review.  
**Státusz:** végrehajtásra előkészített pilotprotokoll. A forrásellenőrzés megtörtént; a modell futtatása, a checkpointok numerikus reprodukciója és a beavatkozási infrastruktúra validálása még nem. A megerősítő vizsgálat előregisztrációja a G0 és a külön pilot után zárható le.  
**Verziókezelés:** új, önálló v3 dokumentum; a v2 változatlan előzmény.

## 1. Cél, kutatási sorrend és állítási határok

A kutatás azt vizsgálja, hogy a Next-Concept Modeling (NCM) Sudoku-generálásában a különböző hierarchikus szintek módosítása hogyan változtatja meg a kimenetet, milyen logikai tulajdonságok olvashatók ki a köztes reprezentációkból, és ezek közül mi kapcsolható célzott oksági hatáshoz.

A bizonyítási szintek elkülönülnek: **dekódolhatóság → szimmetriák alatti általánosítás → célzott oksági szerep**. Egyik szint sem bizonyít önmagában explicit keresést, emberi Sudoku-stratégiát vagy teljes algoritmikus tervet. A tömörítés és a logikai tartalom együtt is jelen lehet.

Az első végrehajtási egység egy checkpoint reprodukciója és szűk E1–E2 pilot. Az első publikációs cél az **E1 + E2 + E3 integrált eredménye**, megfelelő kontrollokkal és negatív eredményekkel együtt. Ez kutatási cél, nem előzetes ígéret a publikálhatóságra. Az E3 elindítása nem függ pozitív E2-hatástól; validált reprezentációkinyerés és megfelelő adatfelosztás szükséges hozzá. Az E4 külön, feltételes fázis.

A teljesítmény végső változása **érzékenységet** mér. „Hibaterjedésről” akkor beszélünk, ha a beavatkozás utáni szintek állapotváltozását, a köztes rekonstrukciókat és a térbeli hibamintázatot is követjük. A „kompenzáció” az eredeti hibahatás későbbi mérséklődésének operacionális neve; nem azonos bizonyított logikai hibajavítással.

## 2. Ellenőrzött források és még nyitott reprodukciós tételek

### 2.1 Forrásazonosítás

A publikáció, a projektoldal, a hivatalos repository és a checkpoint-gyűjtemény elérhető forrásként azonosítható [1–4]. Az arXiv-bejegyzés 2026. október 9-i, a projektbejegyzés 2026. október 12-i. Ezek a terv 2026. november 8-i dátumához képest **nem jövőbeliek**. A kiegészítő review helyőrzőkre vonatkozó gyanúját ezért nem vesszük át.

**A kódvizsgálat rögzített referenciája:** `HazyResearch/ncm`, commit `c70274273f489abc73832b2b98584a8483b6b203` (2026-10-14). Ez ellenőrzött repository-azonosító, nem annak bizonyítéka, hogy egy checkpointot már reprodukáltunk ezen a commiton.

| Tétel | Forrásból ellenőrzött kiindulópont | Futás előtt rögzítendő |
|---|---|---|
| Első checkpoint | A kiadott Sudoku-hard konfiguráció | Pontos checkpointfájlok, letöltési revision és SHA-256; licenc |
| Hierarchia | 12 szint; kódhosszak: 1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89; szintenként 16 kód | A betöltött modell és a konfiguráció egyezése |
| Ábrázolás | 256 dimenziós embedding; 89 hosszú kimeneti tokenreprezentáció; a konfigurációban `compression_factor=1` | Tensoralakok, cella–token megfeleltetés, kumulatív és reziduális állapotok |
| Generálás | A Sudoku-konfiguráció `temperature=0.0`; a generátor ezen az ágon argmaxot használ | `.eval()` mód, numerikus determinisztikusság, pontos sampling-beállítások |
| Kondicionálás | A generátor későbbi szintjei is megkapják a feladvány prefixét | A wrapper változatlanul továbbítja-e ezt minden ágon |
| Beavatkozás | Kód- és állapotkinyerés kialakítható a vizsgált kódból | Tetszőleges szinttől folytató, tesztelt saját wrapper |

A fenti konfigurációs tételek a kiadott fájlokra és statikus forráskód-olvasásra támaszkodnak [4–9]. A hard/easy/medium címke nem helyettesíti a független solverrel mért logikai nehézséget. Külön checkpointok összehasonlítása a modell és az adatok együttes különbségét tartalmazza.

Az eredeti tanulmány már tárgyal korai kódokhoz és coarse reprezentációkhoz kapcsolódó beavatkozásokat, valamint korábbi szintek korrupciójával végzett tanítást [1, függelék F.3 és H]. Az újdonságot ezért a Sudoku-specifikus mérési konstrukció, a kontrollált kompenzációs kontraszt, a logikai címkézés és a célzott oksági teszt adhatja; a korai kódok perturbálása önmagában nem új módszer.

### 2.2 G0: reprodukció és instrumentáció

1. **Környezet és eredet:** commit, függőségek, Python/PyTorch/CUDA, eszköz, pontosság, konfiguráció, checkpoint- és adatfájl-hash, licencek, seedek rögzítése.
2. **Eredeti futás:** kis technikai mintán hibakeresés, majd a hivatalos értékelés reprodukciója az eredeti metrikával és az önálló Sudoku-metrikákkal. Az elfogadható eltérés szabályát az összevetés előtt, az eredeti értékelés és az adatok ismeretében kell lezárni.
3. **Adatút:** ellenőrizni, hogy az encoder mit kódol, a generátor mit lát, és mely reprezentációkon halad át a beavatkozás. A teacher-kód a megoldásból, a generated-kód a feladvány feltétele mellett készül.
4. **Wrapper:** tervezett saját interfész: `forward_with_intervention()`. A név új implementációs javaslat, nem állítás meglévő upstream API-ról. Támogatnia kell a prefix rögzítését, a szintcserét, az eredeti suffix visszajátszását és a suffix újragenerálását.
5. **Azonossági tesztek:** kikapcsolt hookokkal az eredeti futás egyezése; saját kód visszaírásakor változatlan eredmény; azonos szintről történő sham újraindítás; RNG-állapot megőrzése, ha később sztochasztikus módot is használunk.
6. **Állapotmentés:** a teljes hosszú kumulatív állapotokról külön másolat készüljön. A vizsgált `idx_to_zhats` kódban az in-place frissítés és a listába mentés miatt aliasing-kockázatot kell futásidőben ellenőrizni [7]. A későbbi állapot módosítása nem írhatja át a korábban mentett állapotokat.
7. **Dekódolási út:** a rövidebb szintreprezentáció nem automatikusan teljes Sudoku-rekonstrukció. A részleges kumulatív állapotot a végső dekóder által elvárt teljes tokenhosszra kell előállítani, vagy az eredményt nem szabad cellaszintű részmegoldásként értelmezni [7–9].
8. **Validator:** tesztesetek helyes táblára, clue-megváltoztatásra, sor/oszlop/blokk ismétlésre, csonka és túl hosszú kimenetre, hibás karakterre, nem egyedi és kielégíthetetlen bemenetre. A parser nem javíthatja csendben a modell hibáit.
9. **Futtatási költség:** mérni a baseline, az állapotmentés, a rögzített suffix és az újragenerált suffix idejét, memóriáját és tárhelyét. A munkaterv ezek után kap időbecslést.

**G0 kapu:** az E2/E4 csak validált beavatkozási útvonallal értelmezhető. Az E1/E3 külön folytatható, ha a reprezentációkinyerés megbízható, de a beavatkozási rész még nincs kész. Nem reprodukálható baseline esetén a további eredmény előzetes diagnosztika; az eltérést fel kell oldani vagy új, egyértelműen eltérő vizsgálati protokollt kell rögzíteni.

## 3. Definíciók, reprezentációk és hipotézisek

Legyen $P$ a bemeneti feladvány, $S$ egy ellenőrzött referencia-megoldás, $U(P)$ az eredetileg üres cellák halmaza, $L$ a hierarchia szintszáma. A dokumentum **1-től indexeli a szinteket**; a kód 0-alapú indexeivel való megfeleltetést a futási konfiguráció tartalmazza.

| Jelölés / fogalom | Operacionális jelentés |
|---|---|
| $C_\ell^T$ | A megoldás encoderrel képzett teacher-kódjai a $\ell$. szinten |
| $C_\ell^G$ | A feladványból generált diszkrét kódok ugyanott |
| $R_\ell$ | Egy szint reziduális hozzájárulása a dekóder terében |
| $Z_{\leq\ell}$ | Az első $\ell$ szint teljes hosszú kumulatív állapota |
| $H_\ell$ | A generátor külön megjelölt belső aktivációja; nem azonos a kóddal |
| Coarse/fine | A hierarchia korai/késői szintje; nem előre igazolt globális/lokális szemantika |
| Solve | Teljes, jól formált 81 cellás tábla, az összes clue és Sudoku-kényszer megőrzésével |

A kódindex kategória: numerikus sorrendjének nincs magától értetődő geometriai jelentése. Egy codebook következetes átnevezése invertálható művelet, ezért nem információt eltávolító nullkontroll. A hard konfiguráció legelső, 16 értékű diszkrét kódja legfeljebb 4 bitet hordozhat; a hozzá tartozó nagy dimenziós embedding nem növeli a diszkrét változó lehetséges állapotainak számát.

**Teacher és logikai címke:** ugyanaz a megoldás több clue-maszkkal más jelöltkészleteket adhat, miközben a teacher-kód azonos. Emiatt a feladvány logikai állapotának elsődleges probe-jai **generated reprezentációkon** futnak. A teacher ág megoldástartalmi kontroll. A „bemenet + teacher” probe külön vizsgálat, amelynél a bemenet önálló hozzájárulását is mérni kell.

| Hipotézis | Tesztelhető állítás | Elsődleges vagy feltételes értékelés |
|---|---|---|
| H1: kiolvashatóság | Rögzített kapacitású probe a generated reprezentációból a megfelelő nullkontrollnál jobban olvassa ki a logikai címkét | E3 jelöltmaszk-Brier javulás; a nyers bemeneti kontroll külön kötelező összehasonlítás |
| H2: szintérzékenység | Azonos, pontosan definiált diszkrét szerkesztési költség mellett eltér a korai és késői beavatkozás solve-hatása | E2 egykódos, 2. és 11. szintű beavatkozás párosított kontrasztja |
| H3: alkalmazkodás | A suffix újragenerálása módosítja a perturbáció hatását a rögzített suffixhez képest | E2 négyágú interakció; elsődlegesen a 2. szinten, egykódos cserénél |
| H4: általánosítás | A kiolvasott címkék szimmetriák és új feladványcsaládok mellett is követik az elvárt transzformációt | E3 elkülönített ekvivariancia- és család-holdout eredmények |
| H5: oksági relevancia | Egy előre kiválasztott beavatkozás a célcellán specifikusabb változást okoz, mint az illesztett kontroll | Feltételes E4a; E4b esetén külön kontrafaktuális protokoll |

A H1 nem állít a bemenetnél több információt: a címkék a feladvány determinisztikus függvényei. A kérdés az információ hozzáférhetősége az adott probe-család és tanítási keret mellett [10–11]. H5 a v2-ben szereplő általános „mediáció bizonyítása” helyett szűkebb, ellenőrizhető célt kap; mediációs állítás további feltevéseket és előre specifikált oksági modellt igényel [12–13].

## 4. Adatképzés és felosztás

Minden feladvány kap stabil azonosítót, clue-számot, forrásazonosítót, megoldásellenőrzést, elérhető generálási családazonosítót, solverjellemzőket és szimmetriacsoport-azonosítót. A főelemzés ellenőrzötten egyedi megoldású, konzisztens feladványokon fut; a több megoldású esetek külön, opcionális rétegbe kerülnek.

**Csoportosítás a felosztás előtt:** azonos feladványok, ismert szimmetrikus variánsok, azonos teljes megoldásból képzett clue-maszkok és minimális kontrafaktuális párok ugyanabba a felső szintű csoportba kerülnek. A csoportosítást követi a split, és csak ezután az augmentáció. A Sudoku-szimmetriák: számjegy-permutáció; sorcsere egy sávon belül; oszlopcsere egy oszlopcsoporton belül; sáv- és oszlopcsoport-csere; transzponálás.

Az orbitazonosítást ellenőrzött kanonizálás vagy teljes generálási eredet követése biztosítja. Ha egy külső adathalmaznál csak részleges duplikációkeresés lehetséges, a protokoll ezt részleges védelemként jelenti, és nem nevezi a splitet bizonyítottan orbitfüggetlennek. A probe-split javítása nem oldja meg a pretrained modell tanítóadatainak esetleges átfedését; annak feltárhatóságát külön dokumentáljuk.

| Részhalmaz | Feladat | Korlát |
|---|---|---|
| CAL / technikai pilot | Metrikák, dózistartomány, futási költség, power-bemenetek | Nem megerősítő eredmény |
| PROBE-TRAIN | Probe-ok és tanítási kontrollok illesztése | Csak saját tanítási csoportok |
| PROBE-VAL | Regularizáció, küszöbök, tanítási leállítás | Nem használható végső teljesítményként |
| SELECT | E4 cél, régió, donorpolitika és kontrollok kiválasztása | Az itt optimalizált hatás nem E4 bizonyíték |
| TEST | Lezárt E1–E3 megerősítő értékelés | Nincs utólagos szint-, címke- vagy dózisválasztás |
| E4-TEST | A kiválasztott E4 specifikáció friss értékelése | A donorok és párok teljes csoportja ide tartozik |

A részhalmazok csoport szinten diszjunktak. A TEST közös használata előre rögzített E1–E3 végpontokra megengedett, de a kapcsolódó hipotéziseket közös többszörös tesztelési terv kezeli. Az elemszámokat, rétegezést és az elérhetetlen strata kezelését a pilot után, a TEST megnyitása előtt rögzítjük.

## 5. Logikai címkék: jelöltmaszk és következtetési mélység

### 5.1 Kezdeti állapot

Az eredetileg üres $c$ cella és a $d\in\{1,\ldots,9\}$ számjegy címkéje:

$$
y_{c,d}^{(0)}=\mathbf{1}\{d\text{ nem szerepel }c\text{ kitöltött sor-, oszlop- vagy blokk-szomszédai között}\}.
$$

Ez a **kilencbites, közvetlen szabályok szerinti jelöltmaszk**, nem az összes globálisan lehetséges megoldásból képzett támogatási halmaz. Az utóbbi más, erősebb címke lenne. A naked single pontosan a maszkban aktív bitek számának egyenlősége eggyel; a jelöltszám és a naked single ezért nem független bizonyíték.

A hidden single egység–számjegy szinten definiált: egy hiányzó számjegynek pontosan egy jelöltcellája marad az adott sorban, oszlopban vagy blokkban. Tároljuk az egységet, a számjegyet és azt is, ha ugyanaz a cella naked single. A kizárólag hidden single eset külön riportolható.

A jelöltmaszk gazdagabb címke a bináris single-jelzőnél, de sekély szabályt mér. A megfelelő peer-számjegyszámlálásból a címke determinisztikusan, küszöböléssel előállítható. Emiatt egy alkalmas nyersbemeneti vagy szabályalapú kontroll elérheti a plafont. Nem követelmény, hogy a látens probe felülmúljon egy pontos szabályimplementációt. A single-címkék gyakoriságát a pilot méri; ritkaságukat nem feltételezzük előre.

### 5.2 Determinisztikus, szinkron következtetési hullámok

A solver a bemenetből indul, és kizárólag naked/hidden single szabályokat használ; nincs találgatás vagy a referencia-megoldásból átvett számjegy.

1. $P^{(0)}=P$. A $k$. hullám a $P^{(k-1)}$ állapot jelöltmaszkjaiból számol.
2. Az összes alkalmazható naked/hidden single egyszerre kerül azonosításra, még bármelyik új érték beírása előtt.
3. Az egyező levezetések összevonhatók. Ellentmondó levezetés vagy együttes kényszersértés bemeneti/implementációs hibajelzés; nem önkényes szabályprioritással oldjuk fel.
4. Az új értékeket egyszerre írjuk be. Rögzítjük a cella első meghatározásának mélységét $d(c)=k$ és a levezető szabályokat.
5. Megállunk, ha nincs új kitöltés. A szabályrendszer által meg nem oldott cellák „elakadt” státuszt kapnak, nem hamis negatív vagy nulla mélységű címkét. Technikai lépéskorlát esetén a cenzorált státusz ettől különbözik.

A teljes megoldás az inputellenőrzéshez használható, de a címkealkotás nem olvassa azt. A hullámindex 1 az első, kezdeti állapotból következő kitöltési hullám. A fő másodlagos mélységi bontás: 1, 2, 3, legalább 4, elakadt; az elemszám és a címkearány mindegyikhez jár.

A kísérlet mérheti a későbbi $P^{(k)}$ állapotok jelöltmaszkját is, kizárólag az akkor még üres cellákon, külön végpontként. A modell minden esetben az eredeti $P$-t kapja; a solver köztes állapotát nem tápláljuk vissza. A modell $\ell$. szintjét nem azonosítjuk automatikusan a solver $k$. hullámával.

## 6. E1 — Tokenizer, generátor és köztes rekonstrukciók

Ugyanazon feladványokon elkészítjük a referencia-megoldás teacher-kódjait és a feladványból generált kódokat. Külön értékeljük a teljes teacher-rekonstrukciót, a teljes generated-kimenetet és — validált útvonal esetén — a teljes hosszú kumulatív állapotok dekódolását minden kiválasztott szinten.

Az E1 fő kimenete a tokenizer rekonstrukciós hibájának és a generálás teljesítményének külön riportja. A teacher-rekonstrukció minősége **nem szigorú felső korlát** a generated-kimenetre: más kódsorozat is dekódolódhat helyes megoldássá. A teacher/generated kódindexek eltérése sem önmagában logikai hiba.

Kötelező metrikák: hivatalos referenciaegyezés; saját solve; valid-grid; clue-megőrzés; cellapontosság az összes és az eredetileg üres cellán; formátumhiba; szabálysértés; token- és cella-Hamming külön. A referenciaegyezés és a saját solve között a nem egyedi feladvány és a szerializáció különbsége is eltérést okozhat.

A kód vizsgálata alapján az eredeti `exact` és a cellametrikák definícióját külön auditálni kell: a szövegegyezés nem önálló Sudoku-validator, a csonka kimenet páronkénti bejárása pedig hibás nevezőt eredményezhet [9]. A publikált metrikát a reprodukcióhoz megtartjuk; a tudományos főelemzés a független validatorra támaszkodik.

## 7. E2 — Szintérzékenység és négyágú kompenzációs vizsgálat

### 7.1 Négy ág ugyanazon feladványon

Rögzítjük a tiszta futás teljes kódsorozatát. A beavatkozási szint előtti kódok minden ágban azonosak. A suffix a későbbi szintek kódjait jelenti.

| Ág | Beavatkozási szint | Későbbi szintek | Szerep |
|---|---|---|---|
| A | Eredeti kód | Eredeti suffix visszajátszva | Tiszta referencia |
| B | Eredeti kód | Újragenerált suffix | Sham újraindítás |
| C | Perturbált kód | Eredeti suffix visszajátszva | Közvetlen dekódolási hatás, alkalmazkodás nélkül |
| D | Ugyanaz a perturbáció | Újragenerált suffix | Teljes beavatkozási hatás |

Legyen $Y_A,\ldots,Y_D$ az adott ág bináris solve-kimenete. A teljes hatás $E[Y_D-Y_A]$; a shamhoz viszonyított változat $E[Y_D-Y_B]$. A kompenzációs kontraszt:

$$
\theta_{\mathrm{comp}}=E[(Y_D-Y_C)-(Y_B-Y_A)].
$$

Pozitív érték a rögzített suffixhez képest kedvezőbb alkalmazkodást jelez. A determinisztikus, hibátlanul újraindított futásban B=A; az eltérés instrumentációs vagy numerikus hibajel. A C ág reziduális kódjai nem feltétlenül illenek a megváltozott prefixhez, ezért D javulása lehet reprezentációs újrailleszkedés. A minden szinten elérhető puzzle-prefix miatt az eredmény önmagában nem bizonyítja, hogy a coarse kód végrehajtható logikai terv.

### 7.2 Két külön kérdés: szerkesztési költség és kezdeti károsodás

**Elsődleges, azonos költségű vizsgálat:** egy kódpozíció egyenletes kiválasztása és cseréje az adott szint CAL-on becsült generated kódgyakorisága szerint, az eredeti érték kizárásával. A hard checkpoint 2. és 11. szintjének kontrasztja:

$$
\theta_2=E[(Y_{D,2}-Y_A)-(Y_{D,11}-Y_A)].
$$

A negatív érték a korai szinten nagyobb romlást jelent. Ez azonos diszkrét szerkesztésszám, **nem azonos szemantikai hatáserősség**. Az eltérő vektornormát, gyakoriságot és feltételes valószínűséget jelentjük. Ha a gyakorisági eloszlásban nincs alternatív érték, az eset nem cserélhető e politika szerint: nem pótoljuk titokban uniform cserével. A szintkontraszt közös, előre definiált jogosult populáción fut; a kieső arány és a teljes populáció külön látszik.

**Másodlagos, kezdeti károsodáshoz rendelt vizsgálat:** a közvetlen dekódolt változást C és A között mérjük, az újragenerálás előtt. Jól formált kimenetek esetén:

$$
h_{i,\ell,r}=\frac{1}{81}\sum_{c=1}^{81}\mathbf{1}\{\widehat S^C_{i,c}\ne\widehat S^A_{i,c}\}.
$$

Ez a tiszta generated-kimenettől való cella-Hamming, nem a referencia-megoldáshoz képesti hiba. A teacher-rekonstrukción mért analóg távolság külön tokenizer-kontroll lehet. Formátumhiba esetén a távolság külön státuszt kap; a hibás futás a solve nevezőjében marad, és nem lesz automatikusan „kis károsodású”.

A CAL adatokon választunk perturbációs politikákat és dózisokat, majd a választást befagyasztjuk. A TEST végső solve-eredménye nem használható illesztésre. A kezdeti károsodás beavatkozás utáni változó, ezért az erre kondicionált eredmény **kalibrált leíró összehasonlítás**, nem automatikusan kontrollált direkt oksági hatás. Nem csak az átlagos Hamminget, hanem a teljes eloszlást és a formátumhiba arányát is összevetjük.

### 7.3 Dózisgörbék és az átfedés hiánya

A dózis a szinten cserélt pozíciók száma. A pilot jelölt rácsa, ismétlődések elhagyásával: $0,1,\lceil0{,}05n_\ell\rceil,\lceil0{,}15n_\ell\rceil,\lceil0{,}30n_\ell\rceil$, ahol $n_\ell$ a szint kódhossza. A rövid coarse szinteken ezért nem feltétlenül létezik négy–öt különböző nemnulla dózis. Az 1. szint egyetlen kódjának cseréje külön érzékenységi kísérlet.

Rétegenként ábrázoljuk a solve-változást a szerkesztésszám és a kezdeti Hamming függvényében. A görbe alatti terület csak **közös, CAL-on előre kijelölt és a TEST-en diagnosztikával ellenőrzött tartományon**, azonos integrálási szabállyal és súlyozással hasonlítható össze. AUC esetén megadjuk a tartományt és a normalizálást. Nincs extrapoláció a nem megfigyelt kis coarse perturbációkra. Átfedés hiányában külön érzékenységi görbéket közlünk; az azonos károsodásra vonatkozó szintkontraszt nem becsülhető. A meredekség csak lokális, másodlagos összegzés lehet.

További perturbációk: uniform kódcsere; azonos darabszámú összefüggő vagy szétszórt pozíciók, amennyiben a topológia ezt indokolja; validált donorpolitika. A marginális kódgyakoriság vagy vektornorma illesztése nem garantálja, hogy a csere a puzzle és prefix feltétele mellett természetes marad.

**Folytonos perturbáció:** opcionális külön kísérlet. A tokenizer pre-quantization zajozása a tokenizert teszteli; nem azonos a generátor diszkrét kódcseréjével. Egy generátoron belüli aktiváció vagy codebook-hozzájárulás folytonos módosításánál rögzíteni kell a beavatkozási helyet, a normát, az irányt, az esetleges újrakvantálást és a folytatás módját. Ez nem használható a diszkrét kísérlet hiányzó átfedésének utólagos pótlására.

### 7.4 Terjedési diagnosztika

Mentjük a későbbi szintek kódváltozását, a külön másolt teljes hosszú kumulatív állapotokat és az elérhető köztes dekódolásokat. A hibát szint × cella térképen, a sor/oszlop/blokk kapcsolatok mentén és az eredetileg üres versus adott cellákon külön követjük. Jelentjük, ha csak a végső érzékenység becsülhető. A helyes baseline-ról induló esetek külön másodlagos bontás; az elsődleges hatást nem szűkítjük utólag csak a sikeres baseline-okra.

## 8. E3 — Kiolvashatóság, mélység és ekvivariancia

### 8.1 Elsődleges reprezentáció és probe

Az elsődleges reprezentáció a generated ág teljes hosszú, kumulatív $Z_{\leq\ell}$ állapota. G0-ban rögzítjük a szerializáció cella–token leképezését, és az adott cellához rendelt pozíció embeddingjét olvassuk ki. Ez technikai pozíció-hozzárendelés; nem bizonyítja a látens információ szemantikai lokalitását.

Az elsődleges probe **cellák között megosztott lineáris, kilenc sigmoid kimenetű modell**, cellapozíció-kódolással. A tanítható paraméterek, regularizáció és tanítási budget minden összehasonlításnál dokumentált. A javasolt másodlagos modell egy 64 rejtett egységes MLP; a konkrét optimalizáló és regularizációs rács a PROBE-VAL előtt rögzítendő. Három tanítási seed kiinduló terv; ezek ismételt illesztések, nem háromszoros számú független feladvány.

Ha a cellához rendelt állapot nem hozzáférhető vagy nem megfelelő alakú, G0 után külön specifikációval egész réteget látó probe használható. Ekkor az összes szint azonos, előre rögzített dimenzióra vetített reprezentációt kap, és a nyersbemeneti kontrollhoz vetített **és vetítés nélküli** eredmény is szükséges. A váltást a TEST előtt dokumentáljuk. Nem tanítunk és választunk ki utólag 81 független cellaosztályozót.

A reziduális szintkód, a kumulatív állapot és a transformer aktiváció külön kísérleti feltétel. Közös „coarse representation” címke alatt nem vonjuk össze őket. A teljes feladványt közvetlenül látó aktiváció probe-eredménye nem automatikusan a szűk diszkrét kódsorozat eredménye.

### 8.2 Kontrollok

| Kontroll | Mit különít el? | Előírás |
|---|---|---|
| Nyers feladvány, lineáris és kis MLP readout | A reprezentáció előnyét a tanítható bemeneti kiolvasáshoz képest | Azonos adat, tanítási budget; paraméterszám és kapacitáskülönbség jelentése |
| Peer-számjegyszámok és pontos szabályimplementáció | A kezdeti maszk sekély, közvetlen számíthatóságát | Referencia a plafonhoz; nem tanult mechanizmusbizonyíték |
| Clue-szám, cellapozíció, globális számjegygyakoriság | Felszíni korrelációkat | Önálló eredmény |
| Reprezentációk feladványok közötti permutációja | A feladvány és reprezentáció közötti tanulási kapcsolatot | PROBE-TRAIN/VAL-on belül, előre rögzített clue-rétegezéssel; a teljes tábla szerkezete együtt marad |
| Véletlen, méretben illesztett jellemző | A tanulási keret és véletlen illeszkedés hatását | Azonos tanítási költség |
| Címkepermutációs kontroll | A probe kapacitását és memorálási hajlamát | Train/val/test között nincs átvitt párosítás; kontroll-feladat pontosan dokumentált |
| Teacher reprezentáció | A megoldástartalom és a feladványállapot különbségét | Külön riport; azonos megoldásból eltérő clue-maszkokkal is ellenőrizve |

A nullkontrollok nem választhatók ki utólag aszerint, melyiket a legkönnyebb megverni. A H1 elsődleges kontrollja a feladványok között permutált reprezentáció–címke párokon, azonos eljárással újratanított probe. A permutációt a train és val adatokon, egymástól függetlenül végezzük; a végső összehasonlítás mindkét probe esetén az érintetlen TEST párokon történik. Így a kontroll nem hoz létre új függést a tesztfeladványok között. A nyersbemeneti és szabályalapú eredmény ugyanabban a főtáblázatban szerepel. Tanítóméret-görbe szükséges annak megítélésére, hogy a különbséget főként a kiolvasó adatigénye magyarázza-e.

### 8.3 Végpontok

A kezdeti jelöltmaszk elsődleges metrikája a **Brier-veszteség**: a kilenc bit négyzetes valószínűségi hibáját előbb cellánként, utána az eredetileg üres cellákon feladványonként, végül feladványok között átlagoljuk. Így a több üres cella nem ad automatikusan nagyobb súlyt.

H1 elsődleges hatásmérete a 2. szinten:

$$
\theta_1=E[B_{\mathrm{permutált}}-B_{\mathrm{generated}}],
$$

ahol a pozitív érték jobb generated-kiolvasást jelez. A nyersbemeneti különbség külön becslés; pozitív H1 akkor sem nevezhető a nyers bemenet feletti előnynek, ha ezt az utóbbi összehasonlítás nem támasztja alá.

Másodlagos metrikák: számjegyenkénti és makro-F1; pozitív osztályra számolt PR-AUC; teljes jelöltmaszk-egyezés; jelöltszám MAE; a maszkból származtatott naked single; külön hidden single; mélységi bontás. Minden PR-AUC mellett szerepel a pozitív címke aránya. Hiányzó pozitív/negatív osztály esetén az érintett metrika nem értelmezhető, nem nulla. A valószínűségi küszöb alapértéke 0,5; eltérő küszöb kizárólag PROBE-VAL-on választható és befagyasztandó.

A solvermélységre irányuló elemzés külön feladat: például az eredetileg üres cella meghatározódik-e legkésőbb a 2. vagy 3. hullámig. Az elakadt esetek státuszát megőrizzük. Mélységenként összevetjük a látens és a nyersbemeneti readoutot; az eltérő címkagyakoriság és mintaszám miatt puszta F1-rangsorból nem következtetünk mélyebb algoritmusra.

### 8.4 Szimmetriák és általánosítás

Cellánkénti vagy számjegyenkénti kimenetnél a megfelelő követelmény **ekvivariancia**: a tábla átrendezésével a célcellák, számjegycsatornák és címkék is átrendeződnek. Invariancia a teljes táblára vonatkozó skalárra értelmezhető. A predikciókat a transzformáció inverzével közös koordinátákba hozzuk, és mérjük az eltérést, valamint a prediktív teljesítményt.

Két eredmény kötelezően külön marad: augmentáció nélkül tanult probe tesztje új transzformációkon; illetve augmentációval tanult probe általánosítása új, csoport szerint elkülönített feladványokra. A transzformált táblákat újra lefuttatjuk a modellen; nem csak a régi reprezentációt permutáljuk át. Logikai mélység és clue-szám szerinti holdout külön diagnosztika.

## 9. E4 — Célzott oksági vizsgálat, feltételesen

### 9.1 Belépési feltétel és célváltozó

E4 akkor indulhat, ha G0 validált, a SELECT adatokon van reprodukálható és értelmezhető logikai kiolvasás, az ekvivariancia elfogadható, elég célcella és független feladvány áll rendelkezésre, valamint a választott kimenet nem teljesen padló- vagy plafonhelyzetű. A szükséges gyakorlati hatásméretet és ezek numerikus feltételeit a célváltozó, pilotvariancia és költség alapján, az E4-TEST megnyitása előtt rögzítjük.

**Nem alkalmazunk univerzális +0,10 macro-F1 küszöböt a nyersbemeneti baseline felett.** Ezt sem általános statisztikai érv, sem a feladat plafonja nem indokolja. Ha nincs kellő célváltozó vagy mintaszám, az E4 elmarad; az E1–E3 önállóan értékelhető.

A rögzített bemeneten a „naked single” címke a belső patchtől nem változik meg. Az oksági kimenet ezért az előre kiválasztott, eredetileg üres célcella **helyes, szabály által kikényszerített számjegyének kibocsátása**, nem a bemenetből számított címke újraszámolása.

### 9.2 E4a: ugyanazon feladványon korrupció és helyreállító patch

A SELECT halmazon kiválasztjuk a logikai tulajdonsághoz kapcsolódó régiót és a korrupció módját. Friss E4-TEST feladványokon tiszta és korrumpált futást készítünk. A korrumpált futás kijelölt régiójába a **saját tiszta futásból** másolunk vissza reprezentációt, majd ugyanonnan folytatjuk a generálást.

A kontrollágak: tiszta baseline; korrupció patch nélkül; célzott helyreállító patch; azonos méretű és hasonló normájú kontrollrégió helyreállítása; véletlen vagy más célhoz rendelt, előre specifikált patch. A célrégiót és kontrollt nem a végső tesztbeli hatás alapján választjuk ki. A tiszta állapot saját magába másolása csak no-op teszt, nem oksági kísérlet.

Az elsődleges kontraszt a célzott és kontroll-helyreállítás különbsége a célcella helyességében. Ha a célcellák száma feladványonként eltér, előbb feladványon belül átlagolunk. A másodlagos végpont a dekóder célcellához rendelt számjegylogit-marginja:

$$
m_c=z_{c,d^\ast}-\log\sum_{d\ne d^\ast}\exp(z_{c,d}),
$$

ahol a halmaz kizárólag a kilenc számjegy; a nem számjegy kimenetek valószínűségét és a formátumhibát külön mérjük. A generátor 16 kódkategória feletti logitja nem azonos a végső dekóder számjegylogitjával. A logit-endpoint csak ellenőrzött cella–token–számjegy megfeleltetéssel használható.

Mérjük a nem célzott cellák változását, clue-sértést, valid-gridet, solve-t, normákat és elérhető eloszlási diagnosztikákat. Ezek eredményeit nem használjuk a kedvezőtlen tesztesetek utólagos kizárására. A pontosan lokalizált abláció legfeljebb az adott régió oksági relevanciáját támasztja alá; egy probe-irányhoz tartozó szemantikai mediáció ennél erősebb állítás.

### 9.3 E4b: minimális kontrafaktuális feladványpárok

Második lépésként képezhetők $P^-$ és $P^+$ párok, amelyek 1–2 clue-szerkesztéssel különböznek, és egy előre kijelölt $c^\ast$ cellában például $\{2,5\}\rightarrow\{2\}$ jelöltváltozást hoznak létre. Ellenőrizzük mindkét feladvány konzisztenciáját és egyediségét, a célcella ürességét és a pontos célváltozást.

Elsőként közös megoldású párokat használunk. **Ebben az esetben a helyes számjegy nem változik meg**: a példa mindkét tagjában 2 lehet a megoldás. Az elvárt hatás a 2 melletti belső bizonyíték vagy kimeneti margin eltolódása; nem szükségszerű válaszváltás 5-ről 2-re. Plafonhelyzetben a hiányzó eltolódás sem önmagában negatív mechanisztikus bizonyíték.

Clue-hozzáadásnál a clue-szám is változik. Ha megvalósítható, két szerkesztéses clue-áthelyezéssel tartjuk azt állandón; egyébként illesztett, azonos clueszám-változású kontrollpárok szükségesek. A kontroll-szerkesztés a célcellában nem okozza a kiválasztott jelöltváltozást.

A donor és recipient számjegyeit, pozícióit és reprezentációs indexeit összehangoljuk. A természetes végpontok közelsége nem garantálja a patch utáni hibrid állapot eloszláson belüliségét. Jelentjük a párelőállítás sikerarányát, az összes előzetes kizárást és a patch utáni globális károsodást. Eltérő megoldású, tényleges válaszváltást célzó párok külön protokollt igényelnek.

Az E4b pontos célmodellje és irányított kontrasztja a párok pilotja után kerül lezárásra. A „logikai változó mediálja a generálást” állítás csak akkor mérlegelhető, ha a beavatkozás megfeleltetése, a negatív kontrollok és az alternatív magyarázatok vizsgálata ezt külön alátámasztja [12–13].

## 10. Közös metrikaszótár és hibakezelés

| Metrika | Rögzített jelentés |
|---|---|
| Official exact match | Az eredeti értékelő szerinti referenciaegyezés; reprodukciós végpont |
| Solve rate | Jól formált, teljes tábla, minden clue megőrzésével és mind a 27 Sudoku-egység helyességével |
| Valid-grid | Jól formált teljes tábla, érvényes sorokkal/oszlopokkal/blokkokkal; a clue-egyezéstől külön |
| Clue preservation | Minden adott cella megőrzésének aránya, és külön az összes clue-t megőrző táblák aránya |
| Cell accuracy | Fix 81 cellás nevező; külön az eredetileg üres cellákon is; referencia- és szerializációszabály dokumentált |
| Constraint violations | Jól formált táblán a hibás sorok, oszlopok és blokkok száma, összesen 0–27; a formátumhiba külön státusz |
| Cell Hamming | Eltérő cellák aránya az előre megnevezett két tábla között; teljes és eredetileg üres cellákra külön |
| Token Hamming | Tokenpozíciók eltérése; nem helyettesíti a cellaszintű távolságot |
| Célcella-helyesség | Az előre megjelölt, eredetileg üres célcellán a kikényszerített helyes számjegy kibocsátása |
| Brier, F1, PR-AUC | A pontos címke, aggregálás, pozitív osztály és küszöb feltüntetésével |

A formátumhibás modellkimenet solve=0 és valid-grid=0; nem kerül ki a fő nevezőből. Cellapontosság akkor számítható részlegesen, ha az előre rögzített parser egyértelműen azonosítja a pozíciókat: a hiányzó/érvénytelen pozíciók hibásak, a nevező marad 81. Ha a pozíciók nem rendelhetők hozzá egyértelműen, a szigorú cellapontosság 0, és a formátumhibát külön jelentjük. Nincs solveres javítás vagy utólagos clue-visszaírás.

Infrastruktúrahiba — például megszakadt GPU-futás — különbözik a modellhibától. Az előre rögzített újrafuttatási szabály minden ágra azonos. Végleg hiányzó kimeneteknél a hiány okát és arányát feltüntetjük; a párosított főelemzésből kieső csoportok számát és az ebből eredő korlátot jelentjük. Nem minősítünk át modellhibát technikai hibává.

## 11. Statisztikai terv

### 11.1 Becslési egység és bizonytalanság

A fő estimand a kiválasztott feladványpopuláció átlagos párosított hatása. A cellák, szintek, perturbációs ismétlések és tanítási seedek nem független feladványok. Előbb feladványon belül, az előre rögzített súlyokkal átlagolunk, majd a feladványok között. Ha egy családból több puzzle vagy transzformáció származik, a legmagasabb közös család/orbit az újramintavételi egység. A probe-intervallum a rögzített tanítóhalmazra és illesztett modellekre feltételes; a tanítási seedek közötti stabilitást külön jelentjük, és nem keverjük a tesztfeladványok mintavételi bizonytalanságával.

Az elsődleges intervallumeljárás 10 000 ismétléses klaszter-bootstrap, amely együtt tartja az összetartozó ágakat, párokat és ismétléseket. A rétegezett mintavételt a bootstrap is megőrzi. A jelentett kétoldali 95%-os egyedi intervallumok mellett az elsődleges család három kontrasztjára családszintű 5%-os hibakontrollt célzó Bonferroni-intervallumot adunk, egyenként 98,33%-os nominális lefedéssel:

1. H1: $\theta_1$, a 2. szint kezdeti jelöltmaszk-Brier javulása a rögzített nullkontrollhoz képest.
2. H2: $\theta_2$, a 2. és 11. szint egykódos perturbációjának solve-kontrasztja.
3. H3: $\theta_{\mathrm{comp}}$, a 2. szint egykódos perturbációjának négyágú interakciója.

Az alkalmazott bootstrap-intervallum konkrét változatát és a ritka események kezelését a pilot alapján, a TEST előtt rögzítjük. A közelítő lefedés korlátait kevés klaszter esetén jelentjük. A többi szint, dózis, probe és címke másodlagos/exploratív; nem lesz belőle utólag elsődleges pozitív eredmény. H4 teljesítményt és eltérést becsül, nem univerzális invarianciatételt tesztel. E4 saját, friss adaton vizsgált elsődleges kontrasztot kap.

### 11.2 Párosított bináris kimenetek

Egyetlen bináris baseline–beavatkozás pár esetén legyen $b$ a baseline=1, beavatkozás=0, és $c$ a baseline=0, beavatkozás=1 darabszám; $n$ a független párok száma. Ekkor

$$
\widehat\delta=\frac{c-b}{n},\qquad
\widehat q=\frac{b+c}{n}.
$$

Az irányok közötti aszimmetriát az **egzakt McNemar-próba** vizsgálhatja [14]. Ezt csak előre kijelölt, egyetlen bináris pár/független egység esetén használjuk. Nem alkalmazzuk a perturbációs átlagokra, a négyágú interakcióra vagy ugyanannak a determinisztikus baseline-nak ismételt másolataira.

A diszkordáns párok fontosak, de a statisztikai erőt nem kizárólag a számuk határozza meg: az irányok aránya, a hatás, a mintaszám és a függőségi szerkezet is számít. Független párokra, $\delta=E[Y_D-Y_A]$ és $q=P(Y_D\ne Y_A)$ mellett saját levezetésként:

$$
\operatorname{Var}(\widehat\delta)=\frac{q-\delta^2}{n}.
$$

Ezt nem alkalmazzuk változtatás nélkül csoportosított, több ismétléses adatokra. Nulla vagy nagyon kevés diszkordáns párnál a szokásos bootstrap degenerálódhat. Ilyenkor a diszkordanciaszámot és a bizonytalansági korlátot közöljük; előre kiválasztott kis mintás intervallumeljárás szükséges. Nem állítunk ekvivalenciát egy nulla szélességű empirikus bootstrap-intervallum alapján.

### 11.3 GLMM: kiegészítő elemzés

A több szintet és dózist együttesen vizsgáló kiegészítő modell binomiális, logit linkű kevert hatású regresszió lehet [15]. A fix hatások a szint, dózis, ág és előre kijelölt interakcióik; a random szerkezet a feladványon belüli ismétlést, illetve szükség esetén a közös családot kezeli. Becsülhető adatmennyiségnél releváns véletlen meredekség is szerepelhet.

A modellképletet, referencia-kategóriákat és az egyszerűsítési sorrendet előre lezárjuk. Konvergenciahiba, szingularitás vagy szeparáció esetén ezt jelentjük; nem választunk a szignifikanciához igazodó modellt. A determinisztikus baseline egy megfigyelés marad, nem minden dózishoz lemásolt független sor. Az odds ratio mellett modellből standardizált **valószínűségkülönbséget** adunk; az odds ratio nem százalékpontos solve-változás. A klaszterezett párosított elemzés marad az elsődleges.

### 11.4 Mintaszám, hatásküszöb és leállítás

A pilot néhány száz független feladványa tervezési adatot adhat, de nem bizonyítottan elegendő. A megerősítő mintaszámot a kívánt minimális gyakorlati hatás, az intervallum elvárt szélessége, a pilotban mért diszkordancia és családfüggőség alapján, lehetőleg az egész tervezett eljárás szimulációjával határozzuk meg. Az E3 és E4 eltérő végpontjai külön számítást igényelnek.

A számításnak tartalmaznia kell a többszörös összehasonlítást, a várható jogosult célcellákat, a perturbációs ismétlések számát és az esetleges kontrafaktuális párelőállítási veszteséget. Nincs eredményfüggő korai leállítás vagy ismételt tesztelés új szabály nélkül. A nem szignifikáns eredmény korlátozott bizonyíték; gyakorlati hatáshiányhoz előre megadott ekvivalenciatartomány és megfelelő pontosság szükséges.

## 12. Végrehajtási terv és lezárási pontok

### 12.1 Szűk első pilot

Az alábbi értékek **javasolt munkaszervezési kiindulópontok**, nem mért kapacitások vagy igazolt mintaszámok.

| Lépés | Kiinduló terjedelem | Ellenőrizhető kimenet |
|---|---|---|
| Technikai próba | Egy hard checkpoint; körülbelül 20 különböző feladvány | Parser, validator, tensoralakok, no-op és sham egyezése |
| G0 reprodukció | A checkpoint eredeti értékelőhalmaza és beállítása | Eredeti és saját metrikák; eltérések oka; környezetjegyzék |
| E1–E2 pilot | Körülbelül 300 önálló csoportból egy-egy puzzle; 2., 6. és 11. szint; először egykódos csere | A/B/C/D ágak és párosított kontrasztok |
| Perturbációs ismétlés | Kiindulásként 3 beavatkozási seed | A hely- és csereválasztás varianciája; argmax esetén nincs mesterséges generálási seed-variancia |
| Dózis-kalibráció | CAL-on az elérhető diszkrét dózisok; gyakorisági, majd uniform politika | Átfedési tartomány vagy annak hiánya; költség |
| E3 előkészítés | Solverhullámok, címke- és mélységgyűjtés; probe- és baseline-tanítóméret-görbék | Címkeprevalencia, plafonhatás, végleges readout és mintaszám |
| Megerősítő lezárás | A következő táblázat minden tétele kitöltve | Dátumozott protokoll és érintetlen TEST |
| E4 pilot | Csak a kapu teljesülése után, SELECT-en | Konkrét cél, régió, kontroll, margin és új mintaszám |

A 300 puzzle × 3 szint × 1 dózis × 1 cserepolitika × 3 ismétlés **2700 perturbációs beállítás**; ez saját tervezési szorzat, nem 2700 független adatpont és nem futásidő-becslés. A C és D ág eltérő költségű; a tiszta A eredmény újrahasználható. A teljes dózisrács méretét az egyes szinteken ténylegesen elérhető különböző dózisokból kell számolni.

### 12.2 Előregisztrációs lezárási jegyzék

| Tétel | A v3-ban rögzített döntés | Még kitöltendő a megerősítő futás előtt |
|---|---|---|
| Modell | Elsőként hard; rögzített kódcommit | Checkpoint revision, fájlhash, környezet és reprodukciós eredmény |
| Adatok | Csoportos split; kezdetben egyedi megoldások | Adatforrások, licencek, csoportképzés, split-hash és pontos elemszám |
| Logikai címke | Kezdeti jelöltmaszk; szinkron single-hullámok másodlagosan | Címkéző verzió, tesztek, prevalenciák és elakadt arány |
| E2 főkontraszt | Egykódos csere, 2. vs. 11. szint; kompenzáció a 2. szinten | Gyakoriságbecslés, jogosultsági szabály, seedek, validált wrapper |
| E2 dózisgörbe | Kezdeti C–A károsodás; csak közös tartomány | Végleges dózisok, átfedésdiagnosztika, integrálási szabály |
| E3 főkontraszt | Generated kumulatív állapot, megosztott lineáris probe, Brier | Tokenleképezés, inputdimenziók, baseline-architektúrák, tanítási és regularizációs terv |
| Statisztika | Párosított, csoportos elemzés; három főkontraszt | Gyakorlati hatásküszöbök, power, bootstrap-változat, ritka események terve |
| Szimmetria | Ekvivariancia; augmentált és augmentáció nélküli teszt külön | Transzformációk mintavétele, súlyozása és elfogadható eltérés |
| E4 | Feltételes, külön friss teszthalmaz | Célváltozó, célrégió, korrupció, kontrollok, számszerű kapu, mintaszám |
| Riport | Minden ág és negatív eredmény; kizárások naplózása | Végleges futásjegyzék, táblázat- és ábraséma |

A nyitott mezők szándékosan nem kapnak kitalált hash-t, erőbecslést vagy eredményt. A lezárás után tett módszertani módosítás új verziót és eltérésnaplót igényel. A TEST adatai alapján született új hipotézis exploratív, és friss adaton erősíthető meg.

### 12.3 Munkacsomagok és megállási szabályok

| Csomag | Függőség | Kimenet / döntés |
|---|---|---|
| WP0: forrás, reprodukció, instrumentáció | Hozzáférhető modell és adatok | G0 jegyzőkönyv; igazolt beavatkozási út |
| WP1: E1 és E2 | WP0 megfelelő részei | Tokenizer/generátor bontás; érzékenység; négyágú alkalmazkodás; dózistámogatás |
| WP2: E3 | Validált adatút és split | Címkéző, probe-kontroll mátrix, mélységi és ekvivariancia-eredmények |
| WP3: E4a, majd opcionális E4b | Lezárt E4 kapu és friss adatok | Célzott oksági hatás vagy dokumentált negatív eredmény |
| WP4: integrált elemzés | E1–E3 lezárása | Állításonkénti bizonyíték, korlátok, reprodukálható ábrák |
| E5: opcionális kiterjesztés | Indokolt következő kutatási kérdés | Más checkpoint, célzott újratanítás vagy más formális feladat; új protokoll |

WP0 idejére nincs megalapozott 1–2 napos vállalás: azt a checkpointok, a futtatókörnyezet és a szükséges wrapper határozza meg. A költségbecslés a mért pilot után készül. Pozitív E2-hatás hiánya nem állítja le automatikusan E3-at. Közös kalibrációs tartomány hiánya csak az azonos károsodású összevetést zárja ki. Értelmezhető E4-cél hiánya esetén az oksági fázis elmarad.

## 13. Előre rögzített értelmezési szabályok

| Eredmény | Indokolt állítás | Nem következik belőle |
|---|---|---|
| Korai egykódos csere nagyobb romlást okoz | Az adott politika mellett nagyobb szintérzékenység | A coarse kód explicit algoritmust tervez |
| D kedvezőbb C-nél, shamra korrigálva | A későbbi generálás mérsékli a beavatkozás hatását | A javulás biztosan logikai hibajavítás |
| Generated probe veri a nullkontrollt | A címke kiolvasható a vizsgált readouttal | A modell a bemenetnél több információt tartalmaz, vagy a generátor használja a kiolvasott jellemzőt |
| A nyersbemeneti baseline eléri a plafont | A kezdeti címke közvetlenül hozzáférhető a bemenetből | A látens térben nincs logikai információ |
| Későbbi solverhullám címkéje jól kiolvasható | Több lépés eredményével összefüggő reprezentáció | A modell ugyanazokat a lépéseket ugyanabban a sorrendben hajtja végre |
| Ekvivariancia és család-holdout sikeres | Stabilabb, általánosítható kiolvasás | Általános reasoning-képesség bizonyított |
| Specifikus helyreállító patch-hatás | Az adott reprezentációs régió releváns a kijelölt kimenethez | A probe által megnevezett teljes szemantikai mechanizmus bizonyított |
| Minimális donorpatch is rontja a valid-gridet | A hibrid állapot következménye és konzisztenciakorlátja mérhető | A logikai hipotézis önmagában megcáfolódott |
| Nem szignifikáns eredmény | Az adott tervvel nincs elegendő bizonyíték a kijelölt hatásra | A hatás vagy a logikai reprezentáció biztosan hiányzik |

Az eredményeket checkpoint- és beavatkozáspolitika-feltételesen fogalmazzuk meg. A fő kockázatok — kódcsere utáni eloszláseltérés, teacher/generated összemosás, adatátfedés, readout-kapacitás, formátumhiba és utólagos célválasztás — a hozzájuk rendelt kontrollokkal együtt szerepelnek a végső riportban. Egyetlen diagnosztika sem igazolja általánosan, hogy egy patch „eloszláson belüli”.

## 14. A review-k alapján hozott verziódöntések

### 14.1 A kiegészítő review értékelése

| Javaslat | Döntés a v3-ban | Indoklás / beépítés |
|---|---|---|
| A coarse/fine diszkrét dózisoknak nem biztos, hogy van közös tartománya | Átvéve | Közös tartomány ellenőrzése; nincs extrapoláció; külön szerkesztési költség és kezdeti kár |
| Teacher-Hamming és dose–response AUC | Pontosítva | Az elsődleges generátorkísérletben C–A generated-Hamming; teacher külön kontroll; AUC csak azonos tartományon |
| Folytonos pre-quantization perturbáció | Opcionális, elkülönített kísérlet | Encoder, generátoraktiváció és codebook-tér külön beavatkozási hely; nem a diszkrét vizsgálat helyettesítője |
| Kilencbites jelöltmaszk elsődleges címkének | Átvéve, plafonkontrollal | Sűrűbb címke, de sekély szabály; Brier elsődleges, single és jelöltszám származtatott |
| Következtetési mélység szerinti címkézés | Átvéve | Sorrendfüggetlen szinkron single-hullámok; elakadt és cenzorált esetek külön |
| A probe térbeli hozzáférésének rögzítése | Átvéve | Kumulatív, reziduális és aktivációs állapot külön; cellák közt megosztott readout |
| Minimális kontrafaktuális párok | Átvéve, E4b-ként | Célzott clue-változás, egyediség, clueszám-kontroll; közös megoldásnál nincs elvárt válaszváltás |
| Logit-/valószínűségi végpont | Átvéve | A végső dekóder számjegy-marginja; nem a látens kódgenerátor logitja |
| A dátumok és URL-ek valószínűleg helyőrzők | Elvetve az ellenőrzés alapján | A források feloldhatók, dátumuk 2026-11-08 előtti; a commit rögzített |
| McNemar és GLMM | Átvéve, feltételekkel | McNemar egy független bináris párra; GLMM kiegészítő; klaszterezett párosított becslés elsődleges |
| Az erőt kizárólag a diszkordáns párok száma határozza meg | Pontosítva | Az irányaszimmetria, hatásméret, mintaszám és függőségi szerkezet is számít |
| E1 + E2 + E3 integrált publikációs cél | Átvéve | E2 szűk pilot, integrált későbbi eredmény; publikálhatóság előre nem garantálható |
| Saját wrapper, 1–2 nap alatt | Wrapper átvéve; időígéret nélkül | Új, validálandó interfész; ráfordítás csak mért pilot alapján |
| E4 kapu: legalább +0,10 macro-F1 a nyers MLP felett | Nem átvett univerzális küszöb | Címkefüggő plafon és gyakorlati hatás; pilot után, friss teszt előtt számszerűsített kapu |

### 14.2 Az előző részletes bírálatból átvett fő javítások

A v3 megkülönbözteti a megoldást kódoló teacher ágat a feladványállapotot vizsgáló generated ágtól; bevezeti az A/B/C/D kompenzációs tervet; elkülöníti a szerkesztési költséget a dekódolt kezdeti kártól; a bemeneti logikai címke helyett tényleges kimeneti oksági végpontot határoz meg; pontosítja a parser és validator szerepét; kezeli a kumulatív állapotmentés technikai kockázatát; valamint a teljes információ és a korlátozott probe számára hozzáférhető információ különbségét.

A v2 nyitott napirendjére így konkrét iránydöntések születtek. Ami futási eredményt igényel — például checkpoint-hash, reprodukciós eltérés, tényleges dózisátfedés, címkeprevalencia vagy mintaszám — a 12.2. pontban explicit lezárási feladat marad. Ezek megoldása nélkül a v3 nem nevezhető végleges megerősítő előregisztrációnak.

## 15. Források és hivatkozások

A források ellenőrzési dátuma 2026-11-08. A repository-források a rögzített commitra mutatnak. A mozgó checkpoint-hivatkozásokat a tényleges letöltéskor revisionnel és fájlhash-sel kell kiegészíteni. A módszertani specifikációk a jelen kutatási terv döntései; a hivatkozott munkák nem igazolják előre a várt Sudoku-eredményeket.

1. Kumbong és mtsai. (2026): **Next-Concept Modeling: Fast, Parallel Coarse-to-Fine Text Generation**. [arXiv:2610.14162](https://arxiv.org/abs/2610.14162); [v1 teljes szöveg és függelékek](https://arxiv.org/html/2610.14162v1).
2. Hazy Research: [NCM projektbejegyzés, 2026-10-12](https://hazyresearch.stanford.edu/blog/2026-10-12-ncm).
3. Hivatalos repository: [HazyResearch/ncm — rögzített commit](https://github.com/HazyResearch/ncm/tree/c70274273f489abc73832b2b98584a8483b6b203).
4. Hivatalos checkpointok: [hazyresearch/ncm-checkpoints](https://huggingface.co/hazyresearch/ncm-checkpoints); [Sudoku-hard konfiguráció](https://huggingface.co/hazyresearch/ncm-checkpoints/blob/main/sudoku/hard/config.yaml).
5. Generátor és mintavételezés: [models/next_concept.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/next_concept.py).
6. Értékelési konfiguráció: [config/eval/sudoku-hard.yaml](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/config/eval/sudoku-hard.yaml).
7. Kvantálás és kumulatív állapotok: [models/quant.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/quant.py).
8. Tokenizer és dekóder: [tokenization/vqvae_tokenizer.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/tokenization/vqvae_tokenizer.py); [models/vqvae.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/vqvae.py); [models/vae.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/vae.py).
9. Eredeti értékelő: [scripts/eval_merge.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/scripts/eval_merge.py); [scripts/eval_shard.py](https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/scripts/eval_shard.py).
10. Hewitt és Liang (2019): [Designing and Interpreting Probes with Control Tasks](https://aclanthology.org/D19-1275/).
11. Belinkov (2022): [Probing Classifiers: Promises, Shortcomings, and Advances](https://aclanthology.org/2022.cl-1.7/).
12. Zhang és Nanda (2024): [Towards Best Practices of Activation Patching in Language Models: Metrics and Methods](https://proceedings.iclr.cc/paper_files/paper/2024/hash/06a52a54c8ee03cd86771136bc91eb1f-Abstract-Conference.html).
13. Geiger és mtsai. (2021): [Causal Abstractions of Neural Networks](https://papers.neurips.cc/paper_files/paper/2021/hash/4f5c422f4d49a5a807eda27434231040-Abstract.html).
14. statsmodels: [McNemar-próba dokumentáció](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html).
15. lme4: [Binomiális és más általánosított kevert modellek — glmer](https://lme4.github.io/lme4/reference/glmer.html).


