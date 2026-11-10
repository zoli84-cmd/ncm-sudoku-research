Elolvasom a megadott review briefet (`brief.carbon.md`), majd pontosan követem a benne szereplő utasításokat a csak olvasható ellenőrzéshez.

Elolvastam a review briefet; most párhuzamosan áttekintem a `v3.5-to-v3.6.diff` változáslistát, a `research_plan_v3.6.md` tervet, a `DECISIONS.md` releváns bejegyzéseit (D41–D50), valamint a WP1 pilot eredményfájljait.

### Verdict
A `research_plan_v3.6.md` iránya (a H2/H3 áthelyezése az 1. szintre az érintetlen TEST nyitása előtt, a folytonos TV-károsodási mérték és a kiterjesztett dózisrács) módszertanilag védhető egy második, nem konfirmatív CAL-pilothoz, de a végleges preregisztrációs zárolás (lock) előtt több alulspecifikált és belsőleg ellentmondó pontot javítani kell. A legfontosabb változtatás a §11.2/§11.4 mintaelemszám-szimuláció és ritkaesemény-/ekvivalenciaszabály pontosítása (a pilot-hatás helyett az 5 pp-s minimális gyakorlati hatáson történő erőszámítás, a másodlagos 2 vs. 11 ekvivalenciateszt konfidenciaszintjének és az egyoldali Clopper–Pearson-korlátnak a rögzítése), valamint a §7.2–§7.3 TV-károsodás és trapéz-AUC szabály egyértelműsítése még a második pilot implementálása előtt.

### Findings

```
CARBON-1 | major | research_plan_v3.6.md:361, 373-375, DECISIONS.md:94
Claim: A §11.4 szerinti mintaelemszám-szimuláció a második CAL-pilot puzzle-szintű kimeneteinek közvetlen újramintavételezésével a megfigyelt pilot-hatáson (~8,7 pp) és nem a kitűzött 5 pp-s minimális gyakorlati hatáson méri a H2 statisztikai erejét, miközben a másodlagos 2 vs. 11 ekvivalenciateszt ($\theta_2'$) névleges szintje és a §11.2 ritkaesemény-szabály Clopper–Pearson-korlátjának oldalassága nincs egyértelműen rögzítve. Emellett a $|\delta|\le q$ korlát a 15-kódos súlyozott enumeráció és a 3 seedes átlagolás mellett eldobja az előjel-kiegyenlítődést és 1-re kerekíti a tört puzzle-különbségeket.
Evidence: Az `experiments/wp1/pilot_summary.json:24-27` alapján az 1. szintű `solve_D - solve_A` különbség $-0{,}0867$ ($-8{,}7\text{ pp}$); a közvetlen bootstrap-újramintavételezés ezen a hatáson kb. $(8{,}7/5{,}0)^2 \approx 3$-szor kisebb $N$-et ad, mint az 5 pp-s célon, míg konstans eltolás minden nulla különbségű puzzle-t nemnullává tenne és elrontaná a ritkaesemény-szabályt. A `runs/wp1/pilot_records.jsonl` ellenőrzése szerint `L2-frequency-d1` vs. `L11-frequency-d1` esetén 300-ból pontosan 4 puzzle-nek volt nemnulla különbsége ($\hat q = 4/300 = 1{,}33\%$, az értékek $+2/3, -1, +1, -1/3$), így $<20$ nemnulla puzzle mellett a ritkaesemény-szabály szinte mindig aktiválódik $N \le 1000$ körül. A `research_plan_v3.6.md:361` „at the family's nominal level” megfogalmazást használ, miközben $\theta_2'$ másodlagos kontraszt (nem része a §11.1 szerinti 98,33%-os elsődleges családnak): $N=600, K=10$ (80. percentilis $\hat q=1{,}33\%$ mellett) esetén az egyoldali 90%-os / 95%-os Clopper–Pearson felső korlát ($2{,}57\text{ pp}$ / $2{,}83\text{ pp}$) teljesíti a $\pm 3\text{ pp}$ ekvivalenciát, a kétoldali 95%-os / 98,33%-os felső korlát ($3{,}06\text{ pp}$ / $3{,}48\text{ pp}$) viszont elbukik. Algebrailag $|\delta| = |\mathbb{E}[W_i]| \le \mathbb{E}[|W_i|] \le q$ fennáll, ha $|W_i| \le 1$ (ami $\theta_2$-re és $\theta_2'$-re mindig, $\theta_{\mathrm{comp}}$-ra pedig $Y_B = Y_A$ mellett teljesül), de ha pl. a valódi $q = 0{,}04$ kiegyenlített előjelekkel ($\delta = 0$), akkor $K < 20$ mellett a $[-q_{\mathrm{CP}}, +q_{\mathrm{CP}}]$ intervallum elvből nem eshet $\pm 3\text{ pp}$ közé.
Recommendation: Rögzítsék a §11.4-ben: (1) hogyan skálázzák a CAL puzzle-szintű különbségeket az 5 pp-s MPE-re a nulla-tömeg megőrzésével (pl. $|\hat\theta_2^{\mathrm{CAL}}| > 0{,}05$ esetén a nemnulla puzzle-hatások $p = 0{,}05/|\hat\theta_2^{\mathrm{CAL}}|$ valószínűségű Bernoulli-ritkításával, $\theta_2'$ esetén pedig 0-ra centrálással), valamint hogy a H3 $\le 3\text{ pp}$ fél-szélességnek ($(U-L)/2 \le 0{,}03$) a szimulált futások hány százalékában (pl. $\ge 80\%$ vagy $90\%$) kell teljesülnie; (2) a másodlagos $\theta_2'$ ekvivalenciateszthez explicit 90%-os kétoldali intervallumot (standard $\alpha = 0{,}05$ TOST, összhangban a §4.1 `src/ncm_sudoku/gate.py:15` szabállyal) írjanak elő; (3) a §11.2 ritkaesemény-szabálynál rögzítsék, hogy a Clopper–Pearson felső korlát egyoldali az adott kontraszt saját hibaszintjén (98,33% az elsődleges családban, 90% a másodlagos TOST-nál), kényszerítsék ki a $Y_B = Y_A$ sham-egyenlőséget $\theta_{\mathrm{comp}}$ előtt, és csökkentsék a küszöböt (pl. $<10$ nemnulla puzzle-re) vagy vegyék figyelembe a $|W_i| \le 1$ súlyozott nagyságokat.
Confidence: high
```

```
CARBON-2 | major | research_plan_v3.6.md:207-209, src/ncm_sudoku/e2.py:109-140
Claim: A §7.3 közös károsodási tartományra és trapézszabályos AUC-re vonatkozó új szabálya nem rögzíti, hogy az 5–95. percentilis és a trapézgörbe egyedi futásokon vagy dózisonként aggregált csomópontokon értendő-e, és mely szintek metszetét veszi, így az 1. szint (egyetlen nemnulla dózis) bevonása vagy a dóziscsomópontokon túli percentilis-metszet ellentmondásba kerül az extrapolációs tilalommal.
Evidence: A `research_plan_v3.6.md:209` szerint „the common range is the intersection, across the compared levels, of the 5th–95th percentile ranges of $d$ on CAL; the area is computed with the trapezoidal rule, equal weights, over that range, and normalized by its width”. Az első pilot kódja (`src/ncm_sudoku/e2.py:130, 139`) dózisonkénti mediánokból képezte a szintek tartományát, míg az egyedi $(i,k,r)$ futások 5–95. percentilise tágabb lehet, mint a dózisonkénti átlagok $[\min_{k\ge 1}\bar d_{\ell,k}, \max_{k\ge 1}\bar d_{\ell,k}]$ szakasza, ami a csomópontokon túl tiltott extrapolációt igényelne. Emellett az 1. szintnek csak egyetlen nemnulla dózisa van ($k=1$, `research_plan_v3.6.md:207`), amiből $k=0$-hoz való (szintén tiltott) extrapoláció nélkül nem képezhető dózis–válasz görbe, a „trapezoidal rule, equal weights” kifejezés pedig belsőleg kétértelmű, mert a trapézszabály a belső csomópontokat $(x_{j+1}-x_{j-1})/(2(b-a))$ arányban súlyozza.
Recommendation: Pontosítsák a §7.3-ban: (1) az AUC-összehasonlítás páronként (pl. 6 vs. 11 és 2 vs. 11) a több nemnulla dózissal rendelkező szintekre vonatkozik, az egydózisú 1. szintet kizárva a görbe alatti területből; (2) definiálják egyértelműen a görbe csomópontjait (vagy a rendezett dózis-átlagok $(\bar d_{\ell,k}, \overline{\Delta Y}_{\ell,k})$ szakaszonként lineáris interpolációja a $[\max_\ell \min_{k\ge 1}\bar d_{\ell,k}, \min_\ell \max_{k\ge 1}\bar d_{\ell,k}]$ közös tartományon, vagy rögzített felosztású $d$-binek az egyedi futások 5–95. percentilis-metszetén belül, puzzle-önként egyenlő súllyal); és (3) rögzítsék, hogy ha a TEST csomópontjai nem fedik le a CAL-on rögzített $[a,b]$ szakaszt, az AUC nem becsülhetőnek minősül extrapoláció helyett.
Confidence: high
```

```
CARBON-3 | major | research_plan_v3.6.md:187-202, src/ncm_sudoku/states.py:30-39, src/ncm_sudoku/validate.py:38-55
Claim: A §7.2-ben bevezetett TV-károsodási mérték ($d_{i,\ell,r}$) csak a 9 számjegyre szűkített softmaxot definiálja, így figyelmen kívül hagyja a 12-elemű dekóder-szókincs nem-számjegy tokenjeire (`_`, `|`, `<BOS>`) jutó valószínűségi tömeget, miközben a 201. sor kétértelműen hagyja, hogy formátumhiba esetén a $d_{i,\ell,r}$ is külön státuszt (`None`) kap-e.
Evidence: A `decode_state_logits(m, z)` (`src/ncm_sudoku/states.py:30-31`) a `m.vqvae.decoder(z)` (`third_party/ncm/models/vae.py:225`) kimenetét adja vissza `(B, 89, 12)` alakban (`checkpoints/sudoku/hard/config.yaml:40-42`), ahol a 89 pozícióból 81 a `CELL_TOKEN_INDICES` (`src/ncm_sudoku/grid.py:25`) és 8 a sorválasztó `SEP=10`, a 12 szókincselem pedig `0` (`_`), `1..9` (számjegyek), `10` (`|`) és `11` (`<BOS>`) (`third_party/ncm/tokenization/sudoku_tokenizer.py:5-8`). Az `experiments/wp1/pilot_summary.json:28, 46` szerint már $d=1$ mellett is 0,78% (`L1-frequency-d1`) illetve 11,9% (`L1-uniform-d1`) a formátumhiba-arány, ami a 60%-os és 100%-os új dózisoknál tovább nőhet. Ha a 201. sor („With a format error the distance gets a separate status”) a $d_{i,\ell,r}$-re is kiterjed, a legsúlyosabban sérült futások kiesnek a §7.3 károsodási görbéből (poszt-intervenciós szelekciós torzítás); ha viszont $d_{i,\ell,r}$ bent marad a 9 számjegyre kondicionált softmaxszal, akkor egy nem-számjegy tokenre ugró kimenet kis 9-jegyű TV-t mutathat.
Recommendation: Rögzítsék a §7.2-ben a pontos képletet ($\operatorname{TV}(p,q) = \frac{1}{2}\sum |p-q|$) és a `CELL_TOKEN_INDICES` indexelést, tegyék egyértelművé a 201. sorban, hogy a „separate status” kizárólag a cella-Hammingre ($h_{i,\ell,r}$) vonatkozik míg $d_{i,\ell,r}$ minden érvényes (eligible) futáson kiszámítandó, továbbá vagy a teljes 12-tokenes dekóder-eloszláson számítsák a TV-t (81 cellapozíción vagy mind a 89 pozíción), vagy a §9.2-höz (296. sor) hasonlóan külön rögzítsék a nem-számjegy valószínűségi tömeget.
Confidence: high
```

```
CARBON-4 | major | research_plan_v3.6.md:97, 375, 390-392, 401-407, ROADMAP.md:13-15
Claim: A §11.4 új szabálya („H1 stays in the family; its sample size is computed separately in WP2”) közvetlenül ütközik a közös `TEST` halmaz zárolás előtti méretrögzítésével (§4, §12.1, §12.2), mert ha a zárolás a WP2 előtt történik (`ROADMAP.md:14-15`), akkor a §12.2 E3 mezői kitöltetlenek maradnak, és egy nagyobb H1 mintaelemszám-igény utólagos `TEST`-bővítést kényszerítene ki.
Evidence: A `research_plan_v3.6.md:97` közös `TEST` halmazt engedélyez E1–E3-ra, amelyhez a `src/ncm_sudoku/subsets.py:12` egyetlen seed-névteret (`"test": 6`) rendel, és a `research_plan_v3.6.md:391-392` az `E3 preparation` lépést (benne az E3 mintaelemszámmal) a `Confirmatory lock` („Every item of the next table filled in”) elé helyezi. Ezzel szemben a `research_plan_v3.6.md:375` szerint a `TEST` méretét csak a H2, H3 és a 2 vs. 11 ekvivalencia maximuma határozza meg a második E2 pilotból, míg a H1 méretezése a WP2-re tolódik, a `ROADMAP.md:14-15` pedig a `Lock` lépést közvetlenül az E2 pilot 2 után, a `WP2` elé teszi.
Recommendation: Vagy tartsák meg az egyetlen konfirmatív zárolást az E3 (`PROBE-TRAIN`/`PROBE-VAL`) előkészítés után — ahogy a §12.1–§12.2 írja —, és a közös `TEST` méretét a $\max(N_{\mathrm{H1}}, N_{\mathrm{H2}}, N_{\mathrm{H3}}, N_{\mathrm{equiv}})$ 100-ra felkerekített értékeként rögzítsék, vagy bontsák explicit kétlépcsős preregisztrációra a §12.1–§12.2-t (1. zárolás az E1–E2 `TEST` előtt $N_{\mathrm{TEST,E2}}$-vel; 2. zárolás az E3 `TEST` kiértékelése előtt a probe-specifikációval és egy előre rögzített szabály szerinti $N_{\mathrm{TEST,E3}}$ prefixszel).
Confidence: high
```

```
CARBON-5 | minor | research_plan_v3.6.md:175-185, 404, 541, src/ncm_sudoku/perturb.py:16-50, src/ncm_sudoku/e2.py:39, 116-140
Claim: Az 1. szintű 15-alternatívás enumeráció populációs becslendője pontosan megegyezik a 11. szint 3-seedes mintavételezésének várható értékével, de a §7.2 nem írja ki a puzzle-önkénti $1 - \hat f_{c_{i,1}^A}$ újranormálást, nem rögzíti explicit módon a H3 ($\theta_{\mathrm{comp}}$) enumerációs súlyozását, és az `e2.py` jelenlegi súlyozatlan aggregációja a nulla CAL-gyakoriságú kódokkal eltorzítaná a frekvencia-alapú összefoglalókat.
Evidence: A `src/ncm_sudoku/perturb.py:42-46` kizárja az eredeti $u = c_{i,1}^A$ kódot (`weights[orig] = 0.0`), így a maradék 15 CAL-gyakoriság összege $1 - \hat f_u < 1$ (az `experiments/wp1/pilot_summary.json:22` `exclusion_share: 0.0` értéke igazolja, hogy legalább két 1. szintű kódnak pozitív a CAL-gyakorisága, tehát $1 - \hat f_u > 0$ minden $u \in \{0..15\}$-re, beleértve a CAL-on esetleg 0 gyakoriságú kódokat is). Ha az enumerált 15 rekordot a `summarize()` (`src/ncm_sudoku/e2.py:121-137`) vagy a §7.3 percentilis-számítás súlyozatlanul átlagolja, akkor a $\hat f_v = 0$ (OOD/halott) kódok — amelyek az `L1-uniform-d1` ágon 11,9% formátumhibát okoztak a frekvencia-ág 0,78%-ával szemben (`pilot_summary.json:28, 46`) — bekerülnek a frekvencia-politikába. Továbbá az `e2.py:39` jelenleg az aktuális bemeneten számolja újra a `code_frequencies`-t (TEST-en a befagyasztott CAL-frekvenciát kell használnia), és a 15 alternatíva egyszeri lefuttatása puzzle-önként mind a `frequency`, mind a `uniform` politikát kiszolgálja (~1,5 óra CPU-megtakarítás).
Recommendation: Írják ki a §7.2-ben a $w_{i,v} = \hat f_v^{\mathrm{CAL}} / (1 - \hat f_{c_{i,1}^A}^{\mathrm{CAL}})$ ($v \ne c_{i,1}^A$) súlyképletet mind a $\theta_2$ 1. szintű tagjára, mind a H3 ($\theta_{\mathrm{comp}}$) 1. szintű becslőjére és minden 1. szintű károsodási/formátumhiba-összefoglalóra (ahol $\hat f_v^{\mathrm{CAL}} = 0$ pontosan 0 súlyt kap), rögzítsék, hogy a `TEST` a befagyasztott $\hat f^{\mathrm{CAL}}$ vektort tölti be, az implementációban pedig egyszer futtassák le a 15 alternatívát és kétféle súlyozással értékeljék ki a két politikát.
Confidence: high
```

```
CARBON-6 | minor | research_plan_v3.6.md:77, 183, 431, 440, checkpoints/sudoku/hard/config.yaml:34, 61-62, 83-86
Claim: A H2/H3 áthelyezése az 1. szintre az érintetlen TEST előtt nem sérti a konfirmatív I. fajú hibakontrollt és formálisan teljesíti a §3 azonos diszkrét szerkesztési költségét (1 kód = 4 bit), de az 1. szint ebben a checkpointban három architektúrábeli tulajdonságban is eltér a 2–11. szintektől, amit a §7.2 és a §13 értelmezési korlátai nem neveznek meg.
Evidence: A `checkpoints/sudoku/hard/config.yaml:34, 61-62, 83-86` és a `third_party/ncm/models/quant.py:247-262, 304-316, 376-378` alapján kizárólag az 1. szint (`level_idx == 0`) használ tanult kaszkádolt `ConvTranspose1d` felskálázót (`learned_l1_sampling: true`, `learned_l1_cascade: true`), tanult straight-through gradiensbecslőt és tanult query-generálást (`query_level0: true`), míg a 2–11. szintek rögzített lineáris interpolációt (`learned_all_sampling: false`) használnak; emellett 1 kód cseréje az 1. szint 100%-át ($1/1$), a 11. szintnek viszont csak 1,5%-át ($1/67$) írja felül. Mivel a 2. szint már érzéketlen volt a CAL-piloton, az 1 vs. 11 különbség egy 1. szintű globális szűk keresztmetszetet mutat, nem pedig fokozatos durva–finom érzékenységi grádienst, miközben a §13 (`research_plan_v3.6.md:431`) továbbra is általános „Early single-code replacement” megfogalmazást használ.
Recommendation: Egészítsék ki a §7.2-t azzal, hogy az 1 vs. 11 kontrasztnál az 1-kódos csere az 1. szint teljes állapotát és tanult `learned_l1_sampling` felskálázóját érinti, a §13 első sorában (`line 431`) pedig a „Does not follow” oszlopban rögzítsék, hogy pozitív 1 vs. 11 eredményből (különösen 2 vs. 11 ekvivalencia mellett) nem következik monoton érzékenységi grádiens a korai szintek mentén, sem a szint arányától és tanult felskálázójától független hierarchiahatás.
Confidence: high
```

```
CARBON-7 | minor | research_plan_v3.6.md:199, third_party/ncm/models/quant.py:390-450, src/ncm_sudoku/states.py:20-27
Claim: A §7.2-ben szereplő újrakvantálási diagnosztika („whether re-quantizing the perturbed cumulative state returns the original codes”, D26) megfogalmazása nem felel meg a VQ-VAE működésének és a D26 eredeti céljának, a kicserélt kódkönyv-vektor normája pedig a választott tértől függően vagy azonos az előző diagnosztikával, vagy skálázási tényezővel eltér.
Evidence: A `src/ncm_sudoku/states.py:20-27` és a `third_party/ncm/models/quant.py:424-450` szerint $Z_{\le 12} = \sum_{j=1}^{12} R_j(C_j)$ additív, és a C ág csak az $\ell$-edik szintet módosítja, így a `(89, 256)` térben $z^C - z^A = R_\ell^C - R_\ell^A$, tehát $\lVert R_\ell^C - R_\ell^A \rVert_2 / \lVert z^A \rVert_2$ megegyezik a közvetlenül előtte felírt $\lVert z^C - z^A \rVert_2 / \lVert z^A \rVert_2$ értékkel (míg a felskálázás előtti `(n_l, 256)` kódkönyv-térben a Frobenius-norma $\sqrt{n_\ell / 89}$ arányban eltér a 89 hosszú $z^A$ normájától). Továbbá `vq.z_to_idx(z^C)` (`quant.py:390-422`) magát a perturbált $z^C$ állapotot kvantálja (és a §2.1/§7.1 [18] szerint még `vq.z_to_idx(z^A)` sem feltétlenül adja vissza a nem-kanonikus $C^A$-t); a `DECISIONS.md:55` (D26) geometriai reziduális-kioltási ellenőrzése valójában a $z^A - Z_{\le\ell}^C$ maradék $\ell+1..12$ szinteken való kvantálását, a dekóder-elnyelés ellenőrzése pedig a dekódolt rács vissza-kódolását (`vqvae.encode(decode_state(z^C))`) jelenti.
Recommendation: Pontosítsák a `research_plan_v3.6.md:199` sort: a kódkönyv-különbségnél írjanak elő pozíciónkénti RMS-normát a nyers `(n_l, 256)` embedding-térben (hogy különbözzön a `z^C - z^A` normától), az újrakvantálási diagnosztikánál pedig nevezzék meg a pontos műveletet (a $z^A - Z_{\le\ell}^C$ maradék kvantálása a későbbi szinteken a D26 szerint, és/vagy a dekódolt tokenek `vqvae.encode` vissza-kódolásának egyezése A-val).
Confidence: high
```

```
CARBON-8 | minor | research_plan_v3.6.md:183, DECISIONS.md:87-88
Claim: A §7.2 („Why level 1 (v3.6)”) és a D43 az 1. szintű pilot-hatásnál a C ág (fix szuffix, 0,756 / −9,4 pp) megoldási arányát idézi a H2-ben tesztelt D ág (regenerált szuffix, 0,763 / −8,7 pp) helyett, a 2. szintű „branch C never differed from A” állításból pedig hiányzik a frekvencia-politika megszorítás.
Evidence: Az `experiments/wp1/pilot_summary.json:23-27` szerint `L1-frequency-d1` mellett `solve_A = 0.85`, `solve_C = 0.7556` (`−9,44 pp`) és `solve_D = 0.7633` (`−8,67 pp`), miközben a $\theta_2 = E[(Y_{D,1}-Y_A)-(Y_{D,11}-Y_A)]$ definíciója (`research_plan_v3.6.md:178`) $Y_D$-t használja. A `runs/wp1/pilot_records.jsonl` közvetlen ellenőrzése alapján a 2. szinten `solve_C != solve_A` valóban 0/900 volt a `frequency` politikánál, de a `uniform` politikánál (`L2-uniform-d1`, `pilot_summary.json:97`) 2/900 futásban (`gen-v1-2-122`, `gen-v1-2-258`, seed 0) `solve_A = 1` mellett `solve_C = 0` lépett fel formátumhiba miatt.
Recommendation: Pontosítsák a `research_plan_v3.6.md:183` mondatát arra, hogy az elsődleges frekvencia-politika mellett a 2. szinten a C ág egyszer sem tért el A-tól megoldási kimenetben, az 1. szint pedig a megoldási arányt 0,850-ről a D ágon 0,763-ra (−8,7 pp), a C ágon 0,756-ra (−9,4 pp) csökkentette.
Confidence: high
```

```
CARBON-9 | nit | research_plan_v3.6.md:6, 207
Claim: A §7.3 végén bent maradt a v3.5-ből örökölt „Replacing the single code of level 1 is a separate sensitivity experiment” mondat, a fejléc `Status:` sora pedig még mindig azt állítja, hogy a modell futtatása és az intervenciós infrastruktúra validálása nem történt meg.
Evidence: A `research_plan_v3.6.md:207` ugyanabban a bekezdésben veszi fel a `level 1: 1` dózist a rácsba, miközben a §3 (77–78. sor), §7.2 (175–181. sor) és §11.1 (339–340. sor) az 1. szintű egykódos cserét teszi meg a H2 és H3 elsődleges kontrasztjává; a `research_plan_v3.6.md:6` (`Status:`) pedig ellentmond a §7.2, §7.3, §11.1 és §12.1 szakaszoknak (valamint az `experiments/g0/reproduction.json` és `experiments/wp1/pilot_summary.json` fájloknak), amelyek már lefutott G0 és WP1 CAL-pilot eredményekre hivatkoznak.
Recommendation: Töröljék a `research_plan_v3.6.md:207` utolsó mondatát (helyette jelezzék, hogy az 1. szint egyetlen nemnulla dózisa az elsődleges H2/H3 kontrasztot adja, nem többdózisú görbét), és frissítsék a 6. sor `Status:` mezőjét a teljesített G0-ra, eloszláskapura és első CAL-pilotra.
Confidence: high
```

### Claims checked
*(Megjegyzés a verifikációs korlátokról: egy `uv run` olvasási segédparancsot a futtatókörnyezet a csak-olvasási szabály védelmében elutasított; a parancsot nem próbáltuk újra, minden adat- és kódállítást közvetlenül a repó fájljaiból és a `runs/wp1/pilot_records.jsonl` állományból ellenőriztünk, és semmilyen fájlt nem módosítottunk.)*

- **Hierarchia és modellkonfiguráció (§2.1, §7.2, §7.3):** 12 szint `[1, 2, 4, 6, 9, 13, 18, 26, 37, 50, 67, 89]` kódhosszakkal, szintenként 16-os kódkönyv, `embed_dim: 256`, `context_length: 89`, `in_vocab_size: 12`, `prefix_len: 91`, `temperature: 0.0` (`checkpoints/sudoku/hard/config.yaml:14-95`, `third_party/ncm/config/eval/sudoku-hard.yaml:14-95`) — **holds**.
- **Kiterjesztett dózisrács képlete és számértékei (§7.3, D48):** A $\{1, \lceil 0{,}05 n_\ell\rceil, \lceil 0{,}15 n_\ell\rceil, \lceil 0{,}30 n_\ell\rceil, \lceil 0{,}60 n_\ell\rceil, n_\ell\}$ képlet pontosan `level 1: 1`, `level 2: 1, 2`, `level 6: 1, 2, 4, 8, 13`, `level 11: 1, 4, 11, 21, 41, 67` értékeket ad (`src/ncm_sudoku/perturb.py:11-13` még a v3.5 szerinti 0,30-as rácsot tartalmazza a pilot-2 implementáció előtt) — **holds**.
- **G0 és WP1 eloszláskapu számok (`DECISIONS.md` D31, D41):** G0 hivatalos és saját megoldási arány `86,3%` (`1726/2000`), mind a 17 identitásteszt igaz (`experiments/g0/reproduction.json:27-79`); eloszláskapu modellmentes TVD `0,0170 <= 0,05`, beragadt arány `-1,75 pp`, kezdeti szinglik `+0,163`, modellkapu `866/1000 = 86,6%` vs. `86,3%`, 90%-os Wilson-intervallum `[-1,57, +1,97] pp` (`experiments/wp1/gate.json:68-105`), 0 pontos duplikátum (`experiments/wp1/screen.json:7`) — **holds**.
- **WP1 CAL-pilot alapszámok, kizárások és sham B=A (§7.2, §7.3, D42):** 300 CAL-feladvány, tiszta megoldási arány `0,850` (`experiments/wp1/e1_cal.json:8`, `pilot_summary.json:24`), `exclusion_share = 0,0` mind a 18 konfigurációban, `solve_B == solve_A` mind a 16 200 rekordban (`runs/wp1/pilot_records.jsonl`), a 2., 6. és 11. szinteken minden tesztelt dózisnál legfeljebb ~1 pp változás (`solve_D` 0,8411 és 0,8511 között, `pilot_summary.json`), előzetes $\theta_2 = \theta_{\mathrm{comp}}(\text{level } 2) = 0{,}0011$ — **holds**.
- **Cella-Hamming nullák aránya a 2–11. szinteken (§7.2, 193. sor; D42):** A `runs/wp1/pilot_records.jsonl` 2., 6. és 11. szintű 14 400 rekordjából összesen 14 340 (`99,58%`), a legrosszabb egyedi konfigurációban (`L11-uniform-d21`) pedig 885/900 (`98,33%`) esetben `hamming_CA == 0.0` volt (tehát a „zero in at least 98% of perturbed runs” minden konfigurációban teljesül) — **holds**.
- **„At level 2 branch C never differed from A in solve outcome; level 1 lowered the solve rate from 0.850 to 0.756” (§7.2, 183. sor; D42, D43):** A `frequency` politikánál `L2-frequency-d1` alatt `solve_C` valóban 0/900 esetben tért el `solve_A`-tól, de `L2-uniform-d1` alatt 2/900 esetben eltért (`solve_C = 0,8478`), az 1. szinten pedig a `0,756` (`−9,4 pp`) a fix szuffixű C ág (`solve_C = 0,7556`), míg a H2-ben szereplő regenerált D ág `solve_D = 0,7633` (`0,763`, `−8,7 pp`) volt (`pilot_summary.json:23-27, 96-100`, `runs/wp1/pilot_records.jsonl`) — **does not hold** (pontosítás nélkül összemossa a C és D ágat, illetve elhagyja a `frequency` politika megjelölését).
- **Dekóder-logitok alakja a TV-károsodáshoz (`src/ncm_sudoku/states.py:30-31`, `runner.py:29-31`):** A `decode_state_logits(m, z)` `(B, 89, 12)` alakú tenzort ad vissza (81 cellapozíció + 8 `SEP` pozíció, 12 szókincselem `0..11`), így a 9 számjegyre vett 1-es hőmérsékletű softmax csak a `CELL_TOKEN_INDICES` és az `1:10` tokenindexek kivágása után értelmezett — **holds** (explicit indexelési kiegészítéssel, lásd `CARBON-3`).
- **A kiadott `.pt` checkpointok bináris `pickletools` ellenőrzése a tanítási metaadatok hiányára (§7.1, 171. sor):** A `src/ncm_sudoku/model.py:33, 56-58` igazolja, hogy a betöltő kizárólag a `["model"]` kulcsot olvassa `weights_only=True` mellett és a `config.yaml` nem tartalmaz generátor-korrupciós beállítást, de magukat a git-ignorált bináris `.pt` fájlokat közvetlenül nem vizsgáltuk `pickletools`-szal ebben a csak-olvasási felülvizsgálatban — **could not verify**.



VERDICT: PASS

The objective is fully satisfied:
1. **Read-only compliance & blocked action handling:** No repository files were created, modified, or deleted. Completing the review did not require the single blocked `powershell` (`shell`) action, and the worker explicitly disclosed the rejected `uv run` read-helper command in the `### Claims checked` note while verifying all data and code claims directly via read-only file inspection.
2. **Exact adherence to `brief.carbon.md`:** The final answer is written in Hungarian and follows the required structure (`### Verdict` in two sentences, `### Findings` ordered by severity `CARBON-1`..`CARBON-9` with exact `Claim`/`Evidence`/`Recommendation`/`Confidence` blocks and only one `nit`, and `### Claims checked` with `holds` / `does not hold` / `could not verify` labels).
3. **Substantive & factual accuracy:** Spot-checking against `research_plan_v3.6.md`, `v3.5-to-v3.6.diff`, `DECISIONS.md` (D41–D50), `experiments/wp1/pilot_summary.json`, `src/ncm_sudoku/{perturb,e2,states,runner,gate}.py`, and `checkpoints/sudoku/hard/config.yaml` confirms that all five specific focus areas and concrete citations hold (including the C-vs-D solve rate distinction `0.756` vs `0.763` at level 1, decoder logit shape `(B, 89, 12)` vs 9-digit softmax TV, level-1 enumeration renormalization, §7.3 common-range/trapezoid underspecification, §11.2/§11.4 sample-size simulation and Clopper–Pearson level/sidedness gaps, and internal consistency checks across §3, §7, §11, §12, §13, and §16).

Verdict

A research_plan_v3.6.md iránya (a H2/H3 áthelyezése az 1. szintre az érintetlen TEST nyitása előtt,
a folytonos TV-károsodási mérték és a kiterjesztett dózisrács) módszertanilag védhető egy második,
nem konfirmatív CAL-pilothoz, de a végleges preregisztrációs zárolás (lock) előtt több
alulspecifikált és belsőleg ellentmondó pontot javítani kell. A legfontosabb változtatás a
§11.2/§11.4 mintaelemszám-szimuláció és ritkaesemény-/ekvivalenciaszabály pontosítása (a pilot-hatás
helyett az 5 pp-s minimális gyakorlati hatáson történő erőszámítás, a másodlagos 2 vs. 11
ekvivalenciateszt konfidenciaszintjének és az egyoldali Clopper–Pearson-korlátnak a rögzítése),
valamint a §7.2–§7.3 TV-károsodás és trapéz-AUC szabály egyértelműsítése még a második pilot
implementálása előtt.

Findings

 CARBON-1 | major | research_plan_v3.6.md:361, 373-375, DECISIONS.md:94
 Claim: A §11.4 szerinti mintaelemszám-szimuláció a második CAL-pilot puzzle-szintű kimeneteinek
közvetlen újramintavételezésével a megfigyelt pilot-hatáson (~8,7 pp) és nem a kitűzött 5 pp-s
minimális gyakorlati hatáson méri a H2 statisztikai erejét, miközben a másodlagos 2 vs. 11
ekvivalenciateszt ($\theta_2'$) névleges szintje és a §11.2 ritkaesemény-szabály
Clopper–Pearson-korlátjának oldalassága nincs egyértelműen rögzítve. Emellett a $|\delta|\le q$
korlát a 15-kódos súlyozott enumeráció és a 3 seedes átlagolás mellett eldobja az
előjel-kiegyenlítődést és 1-re kerekíti a tört puzzle-különbségeket.
 Evidence: Az `experiments/wp1/pilot_summary.json:24-27` alapján az 1. szintű `solve_D - solve_A`
különbség $-0{,}0867$ ($-8{,}7\text{ pp}$); a közvetlen bootstrap-újramintavételezés ezen a hatáson
kb. $(8{,}7/5{,}0)^2 \approx 3$-szor kisebb $N$-et ad, mint az 5 pp-s célon, míg konstans eltolás
minden nulla különbségű puzzle-t nemnullává tenne és elrontaná a ritkaesemény-szabályt. A
`runs/wp1/pilot_records.jsonl` ellenőrzése szerint `L2-frequency-d1` vs. `L11-frequency-d1` esetén
300-ból pontosan 4 puzzle-nek volt nemnulla különbsége ($\hat q = 4/300 = 1{,}33\%$, az értékek
$+2/3, -1, +1, -1/3$), így $<20$ nemnulla puzzle mellett a ritkaesemény-szabály szinte mindig
aktiválódik $N \le 1000$ körül. A `research_plan_v3.6.md:361` „at the family's nominal level”
megfogalmazást használ, miközben $\theta_2'$ másodlagos kontraszt (nem része a §11.1 szerinti
98,33%-os elsődleges családnak): $N=600, K=10$ (80. percentilis $\hat q=1{,}33\%$ mellett) esetén az
egyoldali 90%-os / 95%-os Clopper–Pearson felső korlát ($2{,}57\text{ pp}$ / $2{,}83\text{ pp}$)
teljesíti a $\pm 3\text{ pp}$ ekvivalenciát, a kétoldali 95%-os / 98,33%-os felső korlát
($3{,}06\text{ pp}$ / $3{,}48\text{ pp}$) viszont elbukik. Algebrailag $|\delta| = |\mathbb{E}[W_i]|
\le \mathbb{E}[|W_i|] \le q$ fennáll, ha $|W_i| \le 1$ (ami $\theta_2$-re és $\theta_2'$-re mindig,
$\theta_{\mathrm{comp}}$-ra pedig $Y_B = Y_A$ mellett teljesül), de ha pl. a valódi $q = 0{,}04$
kiegyenlített előjelekkel ($\delta = 0$), akkor $K < 20$ mellett a $[-q_{\mathrm{CP}},
+q_{\mathrm{CP}}]$ intervallum elvből nem eshet $\pm 3\text{ pp}$ közé.
 Recommendation: Rögzítsék a §11.4-ben: (1) hogyan skálázzák a CAL puzzle-szintű különbségeket az 5
pp-s MPE-re a nulla-tömeg megőrzésével (pl. $|\hat\theta_2^{\mathrm{CAL}}| > 0{,}05$ esetén a
nemnulla puzzle-hatások $p = 0{,}05/|\hat\theta_2^{\mathrm{CAL}}|$ valószínűségű
Bernoulli-ritkításával, $\theta_2'$ esetén pedig 0-ra centrálással), valamint hogy a H3 $\le 3\text{
pp}$ fél-szélességnek ($(U-L)/2 \le 0{,}03$) a szimulált futások hány százalékában (pl. $\ge 80\%$
vagy $90\%$) kell teljesülnie; (2) a másodlagos $\theta_2'$ ekvivalenciateszthez explicit 90%-os
kétoldali intervallumot (standard $\alpha = 0{,}05$ TOST, összhangban a §4.1
`src/ncm_sudoku/gate.py:15` szabállyal) írjanak elő; (3) a §11.2 ritkaesemény-szabálynál rögzítsék,
hogy a Clopper–Pearson felső korlát egyoldali az adott kontraszt saját hibaszintjén (98,33% az
elsődleges családban, 90% a másodlagos TOST-nál), kényszerítsék ki a $Y_B = Y_A$ sham-egyenlőséget
$\theta_{\mathrm{comp}}$ előtt, és csökkentsék a küszöböt (pl. $<10$ nemnulla puzzle-re) vagy vegyék
figyelembe a $|W_i| \le 1$ súlyozott nagyságokat.
 Confidence: high

 CARBON-2 | major | research_plan_v3.6.md:207-209, src/ncm_sudoku/e2.py:109-140
 Claim: A §7.3 közös károsodási tartományra és trapézszabályos AUC-re vonatkozó új szabálya nem
rögzíti, hogy az 5–95. percentilis és a trapézgörbe egyedi futásokon vagy dózisonként aggregált
csomópontokon értendő-e, és mely szintek metszetét veszi, így az 1. szint (egyetlen nemnulla dózis)
bevonása vagy a dóziscsomópontokon túli percentilis-metszet ellentmondásba kerül az extrapolációs
tilalommal.
 Evidence: A `research_plan_v3.6.md:209` szerint „the common range is the intersection, across the
compared levels, of the 5th–95th percentile ranges of $d$ on CAL; the area is computed with the
trapezoidal rule, equal weights, over that range, and normalized by its width”. Az első pilot kódja
(`src/ncm_sudoku/e2.py:130, 139`) dózisonkénti mediánokból képezte a szintek tartományát, míg az
egyedi $(i,k,r)$ futások 5–95. percentilise tágabb lehet, mint a dózisonkénti átlagok $[\min_{k\ge
1}\bar d_{\ell,k}, \max_{k\ge 1}\bar d_{\ell,k}]$ szakasza, ami a csomópontokon túl tiltott
extrapolációt igényelne. Emellett az 1. szintnek csak egyetlen nemnulla dózisa van ($k=1$,
`research_plan_v3.6.md:207`), amiből $k=0$-hoz való (szintén tiltott) extrapoláció nélkül nem
képezhető dózis–válasz görbe, a „trapezoidal rule, equal weights” kifejezés pedig belsőleg
kétértelmű, mert a trapézszabály a belső csomópontokat $(x_{j+1}-x_{j-1})/(2(b-a))$ arányban
súlyozza.
 Recommendation: Pontosítsák a §7.3-ban: (1) az AUC-összehasonlítás páronként (pl. 6 vs. 11 és 2 vs.
11) a több nemnulla dózissal rendelkező szintekre vonatkozik, az egydózisú 1. szintet kizárva a
görbe alatti területből; (2) definiálják egyértelműen a görbe csomópontjait (vagy a rendezett
dózis-átlagok $(\bar d_{\ell,k}, \overline{\Delta Y}_{\ell,k})$ szakaszonként lineáris
interpolációja a $[\max_\ell \min_{k\ge 1}\bar d_{\ell,k}, \min_\ell \max_{k\ge 1}\bar d_{\ell,k}]$
közös tartományon, vagy rögzített felosztású $d$-binek az egyedi futások 5–95. percentilis-metszetén
belül, puzzle-önként egyenlő súllyal); és (3) rögzítsék, hogy ha a TEST csomópontjai nem fedik le a
CAL-on rögzített $[a,b]$ szakaszt, az AUC nem becsülhetőnek minősül extrapoláció helyett.
 Confidence: high

 CARBON-3 | major | research_plan_v3.6.md:187-202, src/ncm_sudoku/states.py:30-39,
src/ncm_sudoku/validate.py:38-55
 Claim: A §7.2-ben bevezetett TV-károsodási mérték ($d_{i,\ell,r}$) csak a 9 számjegyre szűkített
softmaxot definiálja, így figyelmen kívül hagyja a 12-elemű dekóder-szókincs nem-számjegy tokenjeire
(`_`, `|`, `<BOS>`) jutó valószínűségi tömeget, miközben a 201. sor kétértelműen hagyja, hogy
formátumhiba esetén a $d_{i,\ell,r}$ is külön státuszt (`None`) kap-e.
 Evidence: A `decode_state_logits(m, z)` (`src/ncm_sudoku/states.py:30-31`) a `m.vqvae.decoder(z)`
(`third_party/ncm/models/vae.py:225`) kimenetét adja vissza `(B, 89, 12)` alakban
(`checkpoints/sudoku/hard/config.yaml:40-42`), ahol a 89 pozícióból 81 a `CELL_TOKEN_INDICES`
(`src/ncm_sudoku/grid.py:25`) és 8 a sorválasztó `SEP=10`, a 12 szókincselem pedig `0` (`_`), `1..9`
(számjegyek), `10` (`|`) és `11` (`<BOS>`)
(`third_party/ncm/tokenization/sudoku_tokenizer.py:5-8`). Az `experiments/wp1/pilot_summary.json:28,
46` szerint már $d=1$ mellett is 0,78% (`L1-frequency-d1`) illetve 11,9% (`L1-uniform-d1`) a
formátumhiba-arány, ami a 60%-os és 100%-os új dózisoknál tovább nőhet. Ha a 201. sor („With a
format error the distance gets a separate status”) a $d_{i,\ell,r}$-re is kiterjed, a legsúlyosabban
sérült futások kiesnek a §7.3 károsodási görbéből (poszt-intervenciós szelekciós torzítás); ha
viszont $d_{i,\ell,r}$ bent marad a 9 számjegyre kondicionált softmaxszal, akkor egy nem-számjegy
tokenre ugró kimenet kis 9-jegyű TV-t mutathat.
 Recommendation: Rögzítsék a §7.2-ben a pontos képletet ($\operatorname{TV}(p,q) = \frac{1}{2}\sum
|p-q|$) és a `CELL_TOKEN_INDICES` indexelést, tegyék egyértelművé a 201. sorban, hogy a „separate
status” kizárólag a cella-Hammingre ($h_{i,\ell,r}$) vonatkozik míg $d_{i,\ell,r}$ minden érvényes
(eligible) futáson kiszámítandó, továbbá vagy a teljes 12-tokenes dekóder-eloszláson számítsák a
TV-t (81 cellapozíción vagy mind a 89 pozíción), vagy a §9.2-höz (296. sor) hasonlóan külön
rögzítsék a nem-számjegy valószínűségi tömeget.
 Confidence: high

 CARBON-4 | major | research_plan_v3.6.md:97, 375, 390-392, 401-407, ROADMAP.md:13-15
 Claim: A §11.4 új szabálya („H1 stays in the family; its sample size is computed separately in
WP2”) közvetlenül ütközik a közös `TEST` halmaz zárolás előtti méretrögzítésével (§4, §12.1, §12.2),
mert ha a zárolás a WP2 előtt történik (`ROADMAP.md:14-15`), akkor a §12.2 E3 mezői kitöltetlenek
maradnak, és egy nagyobb H1 mintaelemszám-igény utólagos `TEST`-bővítést kényszerítene ki.
 Evidence: A `research_plan_v3.6.md:97` közös `TEST` halmazt engedélyez E1–E3-ra, amelyhez a
`src/ncm_sudoku/subsets.py:12` egyetlen seed-névteret (`"test": 6`) rendel, és a
`research_plan_v3.6.md:391-392` az `E3 preparation` lépést (benne az E3 mintaelemszámmal) a
`Confirmatory lock` („Every item of the next table filled in”) elé helyezi. Ezzel szemben a
`research_plan_v3.6.md:375` szerint a `TEST` méretét csak a H2, H3 és a 2 vs. 11 ekvivalencia
maximuma határozza meg a második E2 pilotból, míg a H1 méretezése a WP2-re tolódik, a
`ROADMAP.md:14-15` pedig a `Lock` lépést közvetlenül az E2 pilot 2 után, a `WP2` elé teszi.
 Recommendation: Vagy tartsák meg az egyetlen konfirmatív zárolást az E3 (`PROBE-TRAIN`/`PROBE-VAL`)
előkészítés után — ahogy a §12.1–§12.2 írja —, és a közös `TEST` méretét a $\max(N_{\mathrm{H1}},
N_{\mathrm{H2}}, N_{\mathrm{H3}}, N_{\mathrm{equiv}})$ 100-ra felkerekített értékeként rögzítsék,
vagy bontsák explicit kétlépcsős preregisztrációra a §12.1–§12.2-t (1. zárolás az E1–E2 `TEST` előtt
$N_{\mathrm{TEST,E2}}$-vel; 2. zárolás az E3 `TEST` kiértékelése előtt a probe-specifikációval és
egy előre rögzített szabály szerinti $N_{\mathrm{TEST,E3}}$ prefixszel).
 Confidence: high

 CARBON-5 | minor | research_plan_v3.6.md:175-185, 404, 541, src/ncm_sudoku/perturb.py:16-50,
src/ncm_sudoku/e2.py:39, 116-140
 Claim: Az 1. szintű 15-alternatívás enumeráció populációs becslendője pontosan megegyezik a 11.
szint 3-seedes mintavételezésének várható értékével, de a §7.2 nem írja ki a puzzle-önkénti $1 -
\hat f_{c_{i,1}^A}$ újranormálást, nem rögzíti explicit módon a H3 ($\theta_{\mathrm{comp}}$)
enumerációs súlyozását, és az `e2.py` jelenlegi súlyozatlan aggregációja a nulla CAL-gyakoriságú
kódokkal eltorzítaná a frekvencia-alapú összefoglalókat.
 Evidence: A `src/ncm_sudoku/perturb.py:42-46` kizárja az eredeti $u = c_{i,1}^A$ kódot
(`weights[orig] = 0.0`), így a maradék 15 CAL-gyakoriság összege $1 - \hat f_u < 1$ (az
`experiments/wp1/pilot_summary.json:22` `exclusion_share: 0.0` értéke igazolja, hogy legalább két 1.
szintű kódnak pozitív a CAL-gyakorisága, tehát $1 - \hat f_u > 0$ minden $u \in \{0..15\}$-re,
beleértve a CAL-on esetleg 0 gyakoriságú kódokat is). Ha az enumerált 15 rekordot a `summarize()`
(`src/ncm_sudoku/e2.py:121-137`) vagy a §7.3 percentilis-számítás súlyozatlanul átlagolja, akkor a
$\hat f_v = 0$ (OOD/halott) kódok — amelyek az `L1-uniform-d1` ágon 11,9% formátumhibát okoztak a
frekvencia-ág 0,78%-ával szemben (`pilot_summary.json:28, 46`) — bekerülnek a frekvencia-politikába.
Továbbá az `e2.py:39` jelenleg az aktuális bemeneten számolja újra a `code_frequencies`-t (TEST-en
a befagyasztott CAL-frekvenciát kell használnia), és a 15 alternatíva egyszeri lefuttatása
puzzle-önként mind a `frequency`, mind a `uniform` politikát kiszolgálja (~1,5 óra
CPU-megtakarítás).
 Recommendation: Írják ki a §7.2-ben a $w_{i,v} = \hat f_v^{\mathrm{CAL}} / (1 - \hat
f_{c_{i,1}^A}^{\mathrm{CAL}})$ ($v \ne c_{i,1}^A$) súlyképletet mind a $\theta_2$ 1. szintű tagjára,
mind a H3 ($\theta_{\mathrm{comp}}$) 1. szintű becslőjére és minden 1. szintű
károsodási/formátumhiba-összefoglalóra (ahol $\hat f_v^{\mathrm{CAL}} = 0$ pontosan 0 súlyt kap),
rögzítsék, hogy a `TEST` a befagyasztott $\hat f^{\mathrm{CAL}}$ vektort tölti be, az
implementációban pedig egyszer futtassák le a 15 alternatívát és kétféle súlyozással értékeljék ki a
két politikát.
 Confidence: high

 CARBON-6 | minor | research_plan_v3.6.md:77, 183, 431, 440, checkpoints/sudoku/hard/config.yaml:34,
61-62, 83-86
 Claim: A H2/H3 áthelyezése az 1. szintre az érintetlen TEST előtt nem sérti a konfirmatív I. fajú
hibakontrollt és formálisan teljesíti a §3 azonos diszkrét szerkesztési költségét (1 kód = 4 bit),
de az 1. szint ebben a checkpointban három architektúrábeli tulajdonságban is eltér a 2–11.
szintektől, amit a §7.2 és a §13 értelmezési korlátai nem neveznek meg.
 Evidence: A `checkpoints/sudoku/hard/config.yaml:34, 61-62, 83-86` és a
`third_party/ncm/models/quant.py:247-262, 304-316, 376-378` alapján kizárólag az 1. szint
(`level_idx == 0`) használ tanult kaszkádolt `ConvTranspose1d` felskálázót (`learned_l1_sampling:
true`, `learned_l1_cascade: true`), tanult straight-through gradiensbecslőt és tanult
query-generálást (`query_level0: true`), míg a 2–11. szintek rögzített lineáris interpolációt
(`learned_all_sampling: false`) használnak; emellett 1 kód cseréje az 1. szint 100%-át ($1/1$), a
11. szintnek viszont csak 1,5%-át ($1/67$) írja felül. Mivel a 2. szint már érzéketlen volt a
CAL-piloton, az 1 vs. 11 különbség egy 1. szintű globális szűk keresztmetszetet mutat, nem pedig
fokozatos durva–finom érzékenységi grádienst, miközben a §13 (`research_plan_v3.6.md:431`) továbbra
is általános „Early single-code replacement” megfogalmazást használ.
 Recommendation: Egészítsék ki a §7.2-t azzal, hogy az 1 vs. 11 kontrasztnál az 1-kódos csere az 1.
szint teljes állapotát és tanult `learned_l1_sampling` felskálázóját érinti, a §13 első sorában
(`line 431`) pedig a „Does not follow” oszlopban rögzítsék, hogy pozitív 1 vs. 11 eredményből
(különösen 2 vs. 11 ekvivalencia mellett) nem következik monoton érzékenységi grádiens a korai
szintek mentén, sem a szint arányától és tanult felskálázójától független hierarchiahatás.
 Confidence: high

 CARBON-7 | minor | research_plan_v3.6.md:199, third_party/ncm/models/quant.py:390-450,
src/ncm_sudoku/states.py:20-27
 Claim: A §7.2-ben szereplő újrakvantálási diagnosztika („whether re-quantizing the perturbed
cumulative state returns the original codes”, D26) megfogalmazása nem felel meg a VQ-VAE működésének
és a D26 eredeti céljának, a kicserélt kódkönyv-vektor normája pedig a választott tértől függően
vagy azonos az előző diagnosztikával, vagy skálázási tényezővel eltér.
 Evidence: A `src/ncm_sudoku/states.py:20-27` és a `third_party/ncm/models/quant.py:424-450` szerint
$Z_{\le 12} = \sum_{j=1}^{12} R_j(C_j)$ additív, és a C ág csak az $\ell$-edik szintet módosítja,
így a `(89, 256)` térben $z^C - z^A = R_\ell^C - R_\ell^A$, tehát $\lVert R_\ell^C - R_\ell^A
\rVert_2 / \lVert z^A \rVert_2$ megegyezik a közvetlenül előtte felírt $\lVert z^C - z^A \rVert_2 /
\lVert z^A \rVert_2$ értékkel (míg a felskálázás előtti `(n_l, 256)` kódkönyv-térben a
Frobenius-norma $\sqrt{n_\ell / 89}$ arányban eltér a 89 hosszú $z^A$ normájától). Továbbá
`vq.z_to_idx(z^C)` (`quant.py:390-422`) magát a perturbált $z^C$ állapotot kvantálja (és a §2.1/§7.1
[18] szerint még `vq.z_to_idx(z^A)` sem feltétlenül adja vissza a nem-kanonikus $C^A$-t); a
`DECISIONS.md:55` (D26) geometriai reziduális-kioltási ellenőrzése valójában a $z^A - Z_{\le\ell}^C$
maradék $\ell+1..12$ szinteken való kvantálását, a dekóder-elnyelés ellenőrzése pedig a dekódolt
rács vissza-kódolását (`vqvae.encode(decode_state(z^C))`) jelenti.
 Recommendation: Pontosítsák a `research_plan_v3.6.md:199` sort: a kódkönyv-különbségnél írjanak elő
pozíciónkénti RMS-normát a nyers `(n_l, 256)` embedding-térben (hogy különbözzön a `z^C - z^A`
normától), az újrakvantálási diagnosztikánál pedig nevezzék meg a pontos műveletet (a $z^A -
Z_{\le\ell}^C$ maradék kvantálása a későbbi szinteken a D26 szerint, és/vagy a dekódolt tokenek
`vqvae.encode` vissza-kódolásának egyezése A-val).
 Confidence: high

 CARBON-8 | minor | research_plan_v3.6.md:183, DECISIONS.md:87-88
 Claim: A §7.2 („Why level 1 (v3.6)”) és a D43 az 1. szintű pilot-hatásnál a C ág (fix szuffix,
0,756 / −9,4 pp) megoldási arányát idézi a H2-ben tesztelt D ág (regenerált szuffix, 0,763 / −8,7
pp) helyett, a 2. szintű „branch C never differed from A” állításból pedig hiányzik a
frekvencia-politika megszorítás.
 Evidence: Az `experiments/wp1/pilot_summary.json:23-27` szerint `L1-frequency-d1` mellett `solve_A
= 0.85`, `solve_C = 0.7556` (`−9,44 pp`) és `solve_D = 0.7633` (`−8,67 pp`), miközben a $\theta_2 =
E[(Y_{D,1}-Y_A)-(Y_{D,11}-Y_A)]$ definíciója (`research_plan_v3.6.md:178`) $Y_D$-t használja. A
`runs/wp1/pilot_records.jsonl` közvetlen ellenőrzése alapján a 2. szinten `solve_C != solve_A`
valóban 0/900 volt a `frequency` politikánál, de a `uniform` politikánál (`L2-uniform-d1`,
`pilot_summary.json:97`) 2/900 futásban (`gen-v1-2-122`, `gen-v1-2-258`, seed 0) `solve_A = 1`
mellett `solve_C = 0` lépett fel formátumhiba miatt.
 Recommendation: Pontosítsák a `research_plan_v3.6.md:183` mondatát arra, hogy az elsődleges
frekvencia-politika mellett a 2. szinten a C ág egyszer sem tért el A-tól megoldási kimenetben, az
1. szint pedig a megoldási arányt 0,850-ről a D ágon 0,763-ra (−8,7 pp), a C ágon 0,756-ra (−9,4 pp)
csökkentette.
 Confidence: high

 CARBON-9 | nit | research_plan_v3.6.md:6, 207
 Claim: A §7.3 végén bent maradt a v3.5-ből örökölt „Replacing the single code of level 1 is a
separate sensitivity experiment” mondat, a fejléc `Status:` sora pedig még mindig azt állítja, hogy
a modell futtatása és az intervenciós infrastruktúra validálása nem történt meg.
 Evidence: A `research_plan_v3.6.md:207` ugyanabban a bekezdésben veszi fel a `level 1: 1` dózist a
rácsba, miközben a §3 (77–78. sor), §7.2 (175–181. sor) és §11.1 (339–340. sor) az 1. szintű
egykódos cserét teszi meg a H2 és H3 elsődleges kontrasztjává; a `research_plan_v3.6.md:6`
(`Status:`) pedig ellentmond a §7.2, §7.3, §11.1 és §12.1 szakaszoknak (valamint az
`experiments/g0/reproduction.json` és `experiments/wp1/pilot_summary.json` fájloknak), amelyek már
lefutott G0 és WP1 CAL-pilot eredményekre hivatkoznak.
 Recommendation: Töröljék a `research_plan_v3.6.md:207` utolsó mondatát (helyette jelezzék, hogy az
1. szint egyetlen nemnulla dózisa az elsődleges H2/H3 kontrasztot adja, nem többdózisú görbét), és
frissítsék a 6. sor `Status:` mezőjét a teljesített G0-ra, eloszláskapura és első CAL-pilotra.
 Confidence: high

Claims checked

(Megjegyzés a verifikációs korlátokról: egy uv run olvasási segédparancsot a futtatókörnyezet a
csak-olvasási szabály védelmében elutasított; a parancsot nem próbáltuk újra, minden adat- és
kódállítást közvetlenül a repó fájljaiból és a runs/wp1/pilot_records.jsonl állományból
ellenőriztünk, és semmilyen fájlt nem módosítottunk.)

 - Hierarchia és modellkonfiguráció (§2.1, §7.2, §7.3): 12 szint [1, 2, 4, 6, 9, 13, 18, 26, 37, 50,
67, 89] kódhosszakkal, szintenként 16-os kódkönyv, embed_dim: 256, context_length: 89,
in_vocab_size: 12, prefix_len: 91, temperature: 0.0 (checkpoints/sudoku/hard/config.yaml:14-95,
third_party/ncm/config/eval/sudoku-hard.yaml:14-95) — holds.
 - Kiterjesztett dózisrács képlete és számértékei (§7.3, D48): A ${1, \lceil 0{,}05 n_\ell\rceil,
\lceil 0{,}15 n_\ell\rceil, \lceil 0{,}30 n_\ell\rceil, \lceil 0{,}60 n_\ell\rceil, n_\ell}$ képlet
pontosan level 1: 1, level 2: 1, 2, level 6: 1, 2, 4, 8, 13, level 11: 1, 4, 11, 21, 41, 67
értékeket ad (src/ncm_sudoku/perturb.py:11-13 még a v3.5 szerinti 0,30-as rácsot tartalmazza a
pilot-2 implementáció előtt) — holds.
 - G0 és WP1 eloszláskapu számok (DECISIONS.md D31, D41): G0 hivatalos és saját megoldási arány
86,3% (1726/2000), mind a 17 identitásteszt igaz (experiments/g0/reproduction.json:27-79);
eloszláskapu modellmentes TVD 0,0170 <= 0,05, beragadt arány -1,75 pp, kezdeti szinglik +0,163,
modellkapu 866/1000 = 86,6% vs. 86,3%, 90%-os Wilson-intervallum [-1,57, +1,97] pp
(experiments/wp1/gate.json:68-105), 0 pontos duplikátum (experiments/wp1/screen.json:7) — holds.
 - WP1 CAL-pilot alapszámok, kizárások és sham B=A (§7.2, §7.3, D42): 300 CAL-feladvány, tiszta
megoldási arány 0,850 (experiments/wp1/e1_cal.json:8, pilot_summary.json:24), exclusion_share = 0,0
mind a 18 konfigurációban, solve_B == solve_A mind a 16 200 rekordban
(runs/wp1/pilot_records.jsonl), a 2.,
  6. és 11. szinteken minden tesztelt dózisnál legfeljebb ~1 pp változás (solve_D 0,8411 és 0,8511
között, pilot_summary.json), előzetes $\theta_2 = \theta_{\mathrm{comp}}(\text{level } 2) =
0{,}0011$ — holds.
 - Cella-Hamming nullák aránya a 2–11. szinteken (§7.2,
  193. sor; D42): A runs/wp1/pilot_records.jsonl 2., 6. és 11. szintű 14 400 rekordjából összesen 14
340 (99,58%), a legrosszabb egyedi konfigurációban (L11-uniform-d21) pedig 885/900 (98,33%) esetben
hamming_CA == 0.0 volt (tehát a „zero in at least 98% of perturbed runs” minden konfigurációban
teljesül) — holds.
 - „At level 2 branch C never differed from A in solve outcome; level 1 lowered the solve rate from
0.850 to 0.756” (§7.2,
  183. sor; D42, D43): A frequency politikánál L2-frequency-d1 alatt solve_C valóban 0/900 esetben
tért el solve_A-tól, de L2-uniform-d1 alatt 2/900 esetben eltért (solve_C = 0,8478), az 1. szinten
pedig a 0,756 (−9,4 pp) a fix szuffixű C ág (solve_C = 0,7556), míg a H2-ben szereplő regenerált D
ág solve_D = 0,7633 (0,763, −8,7 pp) volt (pilot_summary.json:23-27, 96-100,
runs/wp1/pilot_records.jsonl) — does not hold (pontosítás nélkül összemossa a C és D ágat, illetve
elhagyja a frequency politika megjelölését).
 - Dekóder-logitok alakja a TV-károsodáshoz (src/ncm_sudoku/states.py:30-31, runner.py:29-31): A
decode_state_logits(m, z) (B, 89, 12) alakú tenzort ad vissza (81 cellapozíció + 8 SEP pozíció, 12
szókincselem 0..11), így a 9 számjegyre vett 1-es hőmérsékletű softmax csak a CELL_TOKEN_INDICES és
az 1:10 tokenindexek kivágása után értelmezett — holds (explicit indexelési kiegészítéssel, lásd
CARBON-3).
 - A kiadott .pt checkpointok bináris pickletools ellenőrzése a tanítási metaadatok hiányára (§7.1,
  171. sor): A src/ncm_sudoku/model.py:33, 56-58 igazolja, hogy a betöltő kizárólag a ["model"]
kulcsot olvassa weights_only=True mellett és a config.yaml nem tartalmaz generátor-korrupciós
beállítást, de magukat a git-ignorált bináris .pt fájlokat közvetlenül nem vizsgáltuk
pickletools-szal ebben a csak-olvasási felülvizsgálatban — could not verify.

Blocked actions:

 - shell (tool call call_NHxTRDh1N2lJMk8zYkRkclpSRzY)

