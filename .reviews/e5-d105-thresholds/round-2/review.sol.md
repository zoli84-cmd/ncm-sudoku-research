### Verdict

A D105 még nem kész az előregisztrációra. A legfontosabb javítás, hogy a TEST mintavételi szabálya ténylegesen biztosítsa a betting tesztek feltételét: a korábban elfogadott TEST-párok orbitjai alapján végzett pótlás mellett az ígért véges mintás 5%-os családszintű hibakorlát nincs igazolva.

### Findings

SOL-1 | blocker | D105, 2. és 7. pont  
Claim: A fagyasztott fejek és a friss seed-névtér nem garantálják az elfogadott párok állandó feltételes átlagát. Ha egy új jelöltet a már elfogadott TEST-párok miatt dobnak el, a következő elfogadott pár eloszlása függ a korábbiaktól.  
Evidence: A `src\ncm_sudoku\e5pairs.py:59–75` indexenként külön véletlenfolyamot ad a jelölteknek, de a `DECISIONS.md:137` a TEST-en belüli orbitütközést is kizárja. A pilot szűrésében nem volt ütközés (`experiments\e5\pairs.json:1348–1361`); ez nem bizonyítja, hogy az új mintában kizárt. A Waudby–Smith–Ramdas-féle garanciához a megfelelő feltételes átlagra van szükség, nem pusztán külön seedekre.  
Recommendation: Az előre rögzített, korábbi adathalmazokkal ütköző jelölteket továbbra is szűrjék. Az így kapott első \(N\) jelöltnél viszont belső orbitütközés esetén ne legyen megerősítő döntés, pótlás vagy újrahúzás. Ekkor a téves állítás eseménye része a független jelölteken végzett teszt elutasítási eseményének. Ha a pótlás kötelező, a tényleges mintavételhez érvényes hibakorlátot kell igazolni.  
Confidence: high

SOL-2 | major | D105, 2. pont  
Claim: A betting módszer megfelelő választás, de az „egyoldali hedged-capital” nem rögzíti egyértelműen a döntési statisztikát. A két irány között felezett tőke és a teljes tőkével futtatott egyoldali teszt egyaránt lehet érvényes, de eltérő erőt és TEST-méretet ad.  
Evidence: A 2. pont nem rögzíti a tőkesúlyt, a csak korábbi párokból számított tét pontos képletét, a varianciastabilizálást vagy a végpontkezelést; a repóban nem találtam D105-implementációt. Az \((x+1)/2\) transzformáció helyes. A `src\ncm_sudoku\e5pilot.py:63–83` szerinti kötések megengedett értékek, nem igényelnek külön tesztágat. Ha minden érték 0,5, a tőke a 0,5-ös nullnál 1 marad; ha minden érték 1, a felső korlát 1, de ebből nem következik 1-es alsó korlát.  
Recommendation: Rögzítsék a teljes tőkéjű pozitív ágat az alsó korláthoz, a \(1-X\)-re alkalmazott pozitív ágat a felsőhöz, és a kiszámított tőke szigorú összehasonlítását a 40-es küszöbbel a megfelelő nullhatáron. Fagyasszák a tétképletet, a párok sorrendjét és a numerikus szabályokat. A konstans minták mellett teszteljenek ritka szélsőértékeket is: a csupa 1 mintára adott alsó korlát nem lehet nagyobb \(0{,}025^{1/N}\)-nél.  
Confidence: high

SOL-3 | major | D105, 6. pont  
Claim: A teljes sorok újramintázása kijavítja az R1-es problémát a pilótamodellben, de a módosított forgatókönyvek még nem garantálják a kötések, az azonosságok és a többi kapu megőrzését. A \([0,1]\)-ben maradás ehhez nem elég.  
Evidence: A `experiments\e5\pilot\z6__shared__none.json:545` és a `P2__shared__none.json:545` adataiban P2 mindig 1, a legkisebb páronkénti \(\Delta\) pedig 0,30435: puszta újrasúlyozással a \(\Delta=0{,}25\) határ nem érhető el. A `scripts\e5_causal.py:151–202` szerint a kauzális kontrasztok ugyanabból a Q-hatásból és közös referenciából származnak. Ha csak Q átlagát visszük 0,01-re, a változatlan nagy varianciájú kontroll átlaga 0,02197, tehát két kapu kerül a nullba, nem egy.  
Recommendation: A \(W(Z)\)-határokhoz használjanak teljes soros exponenciális újrasúlyozást, a 96 pontosan 0,5-ös sor összsúlyát változatlanul hagyva. A piloton mindkét határt elértem így: \(\Delta\) átlaga rendre 0,53 és 0,47, a B kapui mind teljesülnek a generáló modellben. A \(\Delta\)-határhoz a prefixpontszámot változtassák és \(\Delta\)-t számolják újra; a kauzális esetekben a közös referenciától mért TV-távolságokból képezzék újra az összes kontrasztot. Minden forgatókönyvnél ellenőrizzék a generáló átlagokat. A kapott tévespozitív-arány forgatókönyv-specifikus ellenőrzés, nem a friss TEST kalibrációja.  
Confidence: high

SOL-4 | major | D105, 5–6. pont  
Claim: A 90%-os méretezési szabály csak a kiválasztásra is használt pilótamodellre vonatkozik. A gyengébb alternatívák nem befolyásolják \(N\)-t, a 250-es padló pedig nem teljesíti az R1-ben elfogadott rétegenkénti pontossági vállalást. A full-generation és a rescue/harm kivétele viszont indokolt.  
Evidence: A 6. pont a prefix gyengítését és Q felezését említi, de nem vizsgál sávszélhez közelebbi, még ekvivalens \(W(Z)\)-átlagot. A `experiments\e5\causal\primary_per_pair.json:30–534` alapján Q felezése változatlan nagy varianciájú kontroll mellett csak kb. 0,0040 átlagos többletet hagy. A `src\ncm_sudoku\power.py:66–73` első Monte Carlo-találatot választó precedensében a becslési zaj is befolyásolhatja a kiválasztott \(N\)-t.  
Recommendation: A méretet előre indokolt, a nullhatártól érdemben távol eső tervezési alternatívákra válasszák, köztük egy sávszélhez közelebbi \(W(Z)\)-re. Rögzítsék az 50-es rácsot, az ismétlésszámot és a felső korlátot; a kiválasztott \(N\)-t külön Monte Carlo-futással ellenőrizzék. A 250-et nevezzék költségvetési padlónak, vagy adják meg a ténylegesen fontos réteg intervallum-félszélességi célját. Kisebb \(N\) nem javít egy valódi sávon kívüli probe-eltolódáson.  
Confidence: high

SOL-5 | major | D105, 1. és 3. pont  
Claim: A 0,5-ös középpont és a 0,25-ös különbségküszöb védhető, de az \(\epsilon=0{,}03\) indoklása kétszeresen alábecsüli a megengedett nettó rangsorolási előnyt. Az A állítás szövege emellett általánosabban tagadja az olvashatóságot, mint amit a teszt kimutat.  
Evidence: A `src\ncm_sudoku\e5pilot.py:63–83` szerint \(W=p_{\mathrm{nyer}}+0{,}5p_{\mathrm{köt}}\), ezért \(W-0{,}5=(p_{\mathrm{nyer}}-p_{\mathrm{veszít}})/2\): a 0,03-as eltérés 100 összehasonlításonként **6** nettó nyerésnek felel meg, páronként súlyozva. A \(\Delta>0{,}25\) a sávon belüli \(W(Z)\)-től függően kb. 0,72–0,78 közötti **kötésjóváírásos** prefixküszöböt jelent, nem ugyanekkora nyers nyerési arányt. A D101 eleve a vizsgált, saját pozíciós lineáris próbára korlátozza az állítást (`DECISIONS.md:139`).  
Recommendation: A 0,03-at akkor tartsák meg, ha a hat nettó nyerés száz összehasonlításonként a pilot és a prefix teljesítményétől függetlenül is elhanyagolható; ha három a kívánt határ, az \(\epsilon=0{,}015\). Az A állítást a fagyasztott próbával mért, összes jogosult párra átlagolt gyakorlati ekvivalenciaként fogalmazzák meg, ne az információ hiányaként.  
Confidence: high

SOL-6 | minor | D105, 7. pont  
Claim: A nulla eltérő, értékelhető bittel rendelkező pár kezelése nincs egyértelműen elválasztva a nem véges modellkimenettől.  
Evidence: A `src\ncm_sudoku\e5pilot.py:63–83` ilyen párra `NaN`-t ad, míg a D101 előírja a pár kizárását és megszámlálását (`DECISIONS.md:139`). A D105 bármely nem véges értéknél leállást ír elő; nem mondja meg, hogy a jogosultsági ellenőrzés ezt megelőzi-e.  
Recommendation: A runner modellpontozás előtt, kizárólag a címkékből jelölje a jogosult párokat. Rögzítsék külön az A és B nevezőjét, valamint a kizárt párok jelentését; valódi nem véges modellkimenetnél maradjon a leállás.  
Confidence: high

### Claims checked

- **holds** — A D99 szerinti párok közös megoldást és két eltérő, 30 nyomos maszkot kapnak; a TEST seed-névtere 10 (`src\ncm_sudoku\e5pairs.py:26,39–75`). A meglévő pilot script csak a PROBE-részhalmazokat állítja elő (`scripts\e5_pairs.py:33,47–69`).
- **holds** — A D101 szerinti páron belüli összehasonlítás csak a mindkét tagban üres, eltérő címkéjű biteket használja, a kötés 0,5. A fejeket TRAIN-en illesztik, VAL-on választják; P2 és P3 páronkénti átlaga egyaránt 1, de P2 Brier-értéke kisebb (`src\ncm_sudoku\e5pilot.py:63–113`; `src\ncm_sudoku\probes.py:196–255`; `experiments\e5\pilot\P{2,3}__shared__none.json`). Az E3-kontrollok diagnosztikaiak: a Z-kontrollok átlaga 0,49730 és 0,50757, a P1 permutált és a P2 címkekontrollé 0,43201 és 0,58124. Nem indokolt rájuk központosítani a sávot.
- **holds** — Újraszámolva 250 párból: \(W(Z)=0{,}503587\), minta-SD 0,044489; 96 érték pontosan 0,5, köztük mind a 88 kódazonos pár. P2 mind a 250 párban 1; \(\Delta=0{,}496413\), SD 0,044489, minimum 0,304348 (`experiments\e5\pilot\{z6,P2}__shared__none.json:545`; kódazonosság: a két `codes.npy` első 35 kódja, `src\ncm_sudoku\e5pilot.py:25–40`).
- **holds** — A kauzális runner a 7. szintet méri a címzett első hat szintjének rögzítésével, és a két irányt páronként átlagolja (`scripts\e5_causal.py:102–123,151–202`). Az exportból Q átlaga/SD-je 0,052038/0,060644, Q−HV-é 0,030066/0,040589; Q−random 0,048975, Q−shuffled 0,131348. A Q/HV koszinusz 0,54137/0,47130. A teljes csere átlagos referencia-távolsága 0,061337, és a címzettenként összesített arány 71/500 (`primary_per_pair.json:30–1542`, `primary.json:33–45`, `cosines.json:5–10`, az `experiments\e5\causal` könyvtárban). A 0,01 védhető abszolút átlagküszöb, a pilot referenciaátlagának kb. 16%-a; nem címzettenkénti elvárás. A véletlen kontroll visszaállítása és a mechanisztikus állítás szűkítése helyes.
- **holds** — Két állításra a 0,025–0,025 felosztás megfelelő. Egy hamis konjunkció elfogadásához legalább egy igaz résznullt el kell utasítani, ezért érvényes komponenspróbák mellett sem A, sem B feltételei között nem kell tovább osztani az alfát. A v3.7 három külön elsődleges kontrasztot kezelt; a `wp2eval` ott \(0{,}05/3\)-ot használ, és a TOST szokásos ágában \(1-2\alpha\) szintet (`research_plan_v3.7.md:346–356,383–389`; `src\ncm_sudoku\wp2eval.py:21,55–69`).
- **holds** — A közelebbi sávhatárra adott korábbi durva normálközelítés reprodukálható. Mindkét határt beszámítva, a pilot átlagával és SD-jével, 90%-os **önálló TOST-erőhöz** \(\epsilon=0{,}02/0{,}03/0{,}05\) mellett 65/26/9 pár adódik oldalanként 0,05-nél, illetve 79/32/11 pár 0,025-nél. Ezek nem betting-alapú méretek és nem a teljes A állítás erőszámításai.
- **could not verify** — A fagyasztott TEST-runner, a betting implementáció és a végleges TEST-méret még nem ellenőrizhető. A pilot AUC-kód pontszámegyenlőséget vizsgál, nem bemenetazonosságot; a pilot kauzális bootstrap fix 95%-os és eldobja a nem véges értékeket (`src\ncm_sudoku\e5pilot.py:63–83`; `scripts\e5_causal.py:56–63`). A két pilotút ezért nem tekinthető a tervezett TEST-eljárásnak.

A teljes magyar nyelvű R2 felülvizsgálat elkészült és a végső válaszban szerepel. A felülvizsgálat
során nem módosítottam fájlt.

