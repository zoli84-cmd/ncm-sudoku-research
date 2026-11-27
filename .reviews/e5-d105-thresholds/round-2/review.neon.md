Reading the review brief to understand the scope, criteria, and required output format.

A review brief elolvasva; most átnézem a revideált D105 specifikációt, a R1→R2 diffet, az előző körös döntési naplót és a hivatkozott E5 előzményeket.

I've read the D105 draft, R1 decision log, R2 diff, and D101/D102 specs. Next, I'll check `DECISIONS.md` (D91–D104), the earlier lock practice in `research_plan_v3.7.md` and `wp2eval.py`/`power.py`, and the pilot JSON data to verify all quoted statistics and claims.

I reviewed the D105 draft, revision diff, R1 decision log, D101/D102 specs, and core modules (`power.py`, `wp2eval.py`, `e5pilot.py`, `e5causal.py`). Next, I will inspect `scripts/e5_causal.py` and `scripts/e5_pairs.py` and run a read-only Python check on the pilot JSON datasets to verify every quoted statistic and analyze the Waudby-Smith & Ramdas (2024) betting bound behavior on the pilot distributions.

Verdict

A revideált D105 tervezet az R1 alapirányait (két állítás 0,025-ös szinten, IUT-szerkezet, véges
mintás betting korlátok, Q − random visszaállítása) jó irányba mozdította, de még nem kész a
preregisztrációs lezárásra négy major statisztikai/specifikációs hiányosság miatt. A legfontosabb
módosítás a 2. pont korlátdefiníciójának kijavítása: a kétoldali „hedged-capital” alak helyett
fedezetlen egyoldali (unhedged one-sided) WSR betting folyamatokat kell előírni, és rögzíteni kell a
megfigyelési sorrendet valamint a tétstratégia paramétereit (különösen $c$-t), mert ezek egyaránt
döntik el a névleges szint érvényességét és a szükséges TEST mintaméretet.

Findings

 NEON-1 | major | docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md:18 (Draft decision
D105, item 2)
 Claim: A 2. pont kétoldali „hedged-capital” betting korlátot ír elő „oldalanként 0,025-ös szinten”
egyoldali döntésekhez, holott kétoldali 95%-os hedged-capital halmaz végpontjai nem garantálják a <=
0,025 egyoldali elsőfajú hibát, a 97,5%-os változat pedig feleslegesen 0,0125-re felezi az
oldalankénti szintet.
 Evidence: Waudby-Smith és Ramdas (2024) hedged-capital folyamata, K_n^±(m) = 0,5·K_n^+(m) +
0,5·K_n^-(m) >= 1/alpha_CI, csak P(mu not in [L, U]) <= alpha_CI-t biztosít, és a halmaz nem
feltétlenül konvex/intervallum. Ha alpha_CI = 0,05 („0,025/oldal”), a pozitív K_n^-(mu) tag miatt a
felső elutasítási esemény valószínűsége meghaladhatja a 0,025-öt (ellenpélda: n = 1, X ~
Bernoulli(0,0252), lambda^+ = 0,99/mu, lambda^- = 0,01/(1−mu) esetén X = 1-nél 0,5·K_1^+ + 0,5·K_1^-
= 20,14 >= 20, tehát P(L > mu) = 0,0252 > 0,025), ami sérti az IUT-hez szükséges oldalankénti <=
0,025 előfeltételt. Ha viszont alpha_CI = 0,025, a küszöb log(80) = 4,382 lesz log(40) = 3,689
helyett (~19%-kal nagyobb N szükséges).
 Recommendation: Cserélje a „hedged-capital form” előírást fedezetlen egyoldali (unhedged one-sided)
tőkefolyamatokra: minden alsó korláthoz (A1 alsó, A2, B1–B4) K_n^+(m_0) >= 40, az A1 felső korláthoz
K_n^-(0,53) >= 40. Predictable plug-in tétekkel K_n^+(m) monoton nem növekvő m-ben, így a küszöbön
történő közvetlen kiértékelés egzakt, intervallum-inverziós probléma nélküli, és véges mintán
garantálja a <= 0,025 egyoldali szintet.
 Confidence: high

 NEON-2 | major | docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md:18,23 (Draft
decision D105, items 2 and 7)
 Claim: A predictable plug-in betting korlát sorrendfüggő és erősen érzékeny a csonkolási
paraméterre (c), a D105 azonban sem a párok feldolgozási sorrendjét, sem a tétképlet paramétereit
(c, fix-n vs. anytime-valid formula, varianciaprior) nem rögzíti.
 Evidence: A 250 PROBE-VAL pilot páron (experiments/e5/pilot/z6__shared__none.json,
experiments/e5/causal/primary_per_pair.json) 20 véletlen permutáció között az egyoldali LCB
0,00052-vel (Q − hv), 0,00067-tel (Q) és 0,00060-nal (W(Z<=6)) szóródik; kimenettel korreláló
rendezés (pl. strátum szerinti csoportosítás) elrontja a martingál-tulajdonságot. A [-1, 1] -> [0,
1] átskálázásnál a 0 küszöb m_s = 0,5-re esik, a Q − hv kicsi szórása (0,0406 / 2 = 0,0203) miatt
lambda_t minden lépésben felütközik a c/m_s = 2c plafonon, így elutasítás csak n·mean(Y) > log(40)/c
fölött lehetséges. A WSR (2024) gyakori c = 0,5 alapértelmezésével a pilot Q − hv (n = 250, átlag
0,0301) log-tőkéje 3,67 < 3,689 (LCB = -0,00016, pilot-újramintázott erő N = 250-nél csak 42,5%,
N_power ~ 350), míg c = 0,75-tel a log-tőke 5,38 (LCB = +0,00923, erő 100% N = 250-nél).
 Recommendation: Rögzítse a D105-ben (1) a feldolgozási sorrendet (a 10-es névtér generálási
indexsorrendje, vagy — a sorrendi zaj eltüntetésére, a véges mintás érvényesség egzakt megőrzésével
— K előre rögzített, adatfüggetlen permutáción átlagolt e-érték: (1/K) sum_k K_n^(pi_k)(m_0)); (2) a
pontos fix-n predictable plug-in képletet, a priorokat (mu_0 = 1/2, sigma_0^2 = 1/4) és a c értékét
(ajánlott c = 0,75).
 Confidence: high

 NEON-3 | major | docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md:21 (Draft decision
D105, item 5)
 Claim: Az N_power kizárólag a PROBE-VAL pilot modell (6a) alapján méretezi a TEST-et, figyelmen
kívül hagyva a 6b gyengébb alternatívát; a [-1, 1]-es betting korlát éles küszöbhatása miatt ez már
mérsékelt pilot–TEST zsugorodásnál is súlyos alulméretezéshez vezet a B állításnál.
 Evidence: A 6. pont maga rögzíti, hogy a fejeket PROBE-VAL-on választották ki, a korábbi zárási
gyakorlat pedig (research_plan_v3.7.md §11.4, 381–389. sor) kifejezetten célalternatívákra, nem a
megfigyelt pilot hatásra méretezett. A pilot Q − hv (experiments/e5/causal/primary_per_pair.json)
újramintázásos szimulációja (400 replikáció, egyoldali WSR) meredek erő-szakadékot mutat: c =
0,75-tel a pilot-alapú N = 250 mellett B3 ereje 1,0× hatásnál 1,00, 0,8×-nél 0,96, 0,7×-nél 0,59,
0,6×-nél 0,06, a 6b felezett hatásnál 0,00 (míg N = 500-nál a felezett hatásnál is 1,00); c =
0,5-tel a pilot-alapú N = 350 mellett 0,7×-nél 0,34, 0,5×-nél 0,00. Az 5. pont emellett nem adja meg
a keresési rácsot és a szimulációs replikációszámot/MC-kritériumot sem.
 Recommendation: Határozza meg N_power-t egy előre rögzített, konzervatív gyengébb alternatívára
(pl. a 6b forgatókönyvre vagy a kauzális kontrasztok 0,7×-esére) a pilot pontbecslés helyett, és
rögzítse a szimuláció rácslépését (50-esével) és minimális replikációszámát (pl. >= 2000, MC SE <=
0,007).
 Confidence: high

 NEON-4 | major | docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md:22 (Draft decision
D105, item 6)
 Claim: A 6. pont (b) és (c) szimulációs forgatókönyvei alulspecifikáltak, a B1 egyetlen feltételt
sértő null-határa (Q = 0,01) pedig belsőleg ellentmondásos a változatlan pilot hv kontrollal.
 Evidence: (1) A pilotban Q átlaga 0,0520, hv átlaga 0,0220, Q − hv átlaga 0,0301
(experiments/e5/causal/primary_per_pair.json). A 6b „causal Q effect halved” megfogalmazás
kétértelmű: ha csak Q feleződik (0,0260), hv változatlanul hagyásával Q − hv 0,0040-re (7,5×-esére)
esik, így B3 ereje N = 1000-nél is csak 0,047 (c = 0,75), míg az összes kauzális kimenet együttes
felezésénél Q − hv = 0,0150 (erő 1,00 N = 500-nál). (2) A 6c B1-határánál (Q = 0,01), ha hv marad
0,0220, akkor Q − hv = -0,012 < 0, tehát B3 is hamis lesz, megsértve a „pontosan egy feltétel hamis”
követelményt. (3) P2 per-pair W-AUC mind a 250 pilot párban egzakt 1,0
(experiments/e5/pilot/P2__shared__none.json), így nincs definiálva, milyen eloszlással csökken
0,85-re (6b) illetve 0,7536-ra (6c, Delta = 0,25). (4) A W(Z) 0,5 ± 0,03 keverék eltolt komponense
és a Delta = W(P) − W(Z) azonosság fenntartása sincs rögzítve; ráadásul pilot-szerű W(Z) = 0,53
határokon a WSR FPR csak 0,000–0,004 (N = 250/500), így a szinttartás tényleges implementációs
stressztesztjéhez kétpontos szélső eloszlások ({0, 1}, {-1, 1}) is kellenek.
 Recommendation: Rögzítse képlettel minden forgatókönyv transzformációját: (b)-ben az összes
kauzális irányított kimenet együttes 0,5× skálázását és a W(P) csökkentésének konkrét eloszlását;
(c)-ben B1 határon hv arányos csökkentését 0,01 alá (B2–B4 határokon a megfelelő kontroll felhúzását
Q-ra), W(Z) határon pl. a 162 kód-különböző pár eltolását (ami megőrzi a 88 kényszerített 0,5
döntetlent és nem vág le [0, 1]-nél) a Delta = W(P) − W(Z) újraszámításával; a 2./7. pont
szintetikus lefedettség-tesztjébe pedig vegyen fel szélső kétpontos Bernoulli-eloszlásokat is.
 Confidence: high

 NEON-5 | minor | docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md:19 (Draft decision
D105, item 3)
 Claim: Az epsilon = 0,03 érdemi indoklásában kettes faktorú számítási hiba van: 0,53-as W-AUC nem
„3 nettó helyes rendezés 100 diszkordáns összehasonlításból”, hanem 6 nettó helyes rendezés.
 Evidence: A döntetlenre 0,5-öt adó W-AUC definíciója (src/ncm_sudoku/e5pilot.py:66) W = p_+ +
0,5·p_0 = 0,5 + (p_+ − p_-)/2, így a helyes és hibás rendezések nettó többlete p_+ − p_- = 2(W −
0,5) = 2·epsilon = 0,06 (pl. 53 helyes vs. 47 hibás = +6 nettó; 3 csak a 50%-hoz viszonyított
százalékpontos eltérés). Emellett a D101 5. megfigyelése szerint a diszkordáns bitek 60%-a (15 249 /
25 418) lokálisan azonos Z<=6 állapotú (kényszerített 0,5 döntetlen), így az összes párra vett 0,03
a nem-azonos állapotú biteken kb. 0,075-ös eltérésnek (+15 nettó / 100 bit) felel meg.
 Recommendation: Javítsa a szöveget „6 nettó helyes rendezés 100 diszkordáns összehasonlításból”
(vagy „3 százalékponttal a 0,5-ös véletlen szint feletti W-AUC”) megfogalmazásra, és röviden jelezze
a kényszerített lokális döntetlenek hatását (amelyet a D101(4) külön jelentése választ szét).
 Confidence: high

 NEON-6 | minor | docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md:18,20,23 (Draft
decision D105, items 2, 4 and 7)
 Claim: A 2. pont csak a befagyasztott probe-fejekre való kondicionálást rögzíti, a B állítás
viszont a PROBE-TRAIN-en illesztett high-variance bázisra, a rögzített derangement-re és a kisorsolt
véletlen alterekre is kondicionált; emellett a D105 nem rögzíti a TEST-en használt véletlen alterek
darabszámát és azt, hogy a pilot 20 bázisát használja-e újra.
 Evidence: A D102 4(b) („10–20 draws”) és 6. pontja („conditional on the drawn random bases”)
eltérően a D105 2., 4., 7. pontjától külön rögzítette a bázisokra való kondicionálást; a pilot
`scripts/e5_causal.py:67,74` `--draws 20` és `random_basis(1000 + j)` értékeket használt
(`experiments/e5/causal/primary.json`).
 Recommendation: Rögzítse a 2. és 7. pontban, hogy a B állítás következtetése a befagyasztott Q fej
mellett a befagyasztott high-variance bázisra, a rögzített derangement-re és a pontosan megnevezett
20 (SHA-256-tal rögzített) véletlen altérre is kondicionált.
 Confidence: high

 NEON-7 | nit | .reviews/e5-d105-thresholds/decisions.md (SOL-6) vs
docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md:21 (item 5)
 Claim: A döntési napló SOL-6 sora strátumonkénti pontossági célok rögzítését vállalja (`N =
max(primary power requirement, committed secondary precision)`), míg a revideált 5. pont
kifejezetten nem vállal másodlagos pontossági célt, hanem fix 250-es padlót vezet be.
 Evidence: `.reviews/e5-d105-thresholds/decisions.md` SOL-6 sor vs.
`docs/superpowers/specs/2026-11-26-e5-d105-thresholds-design.md:21` („No precision target is
committed for secondary strata; they are reported with intervals.”).
 Recommendation: A fix 250-es padló + leíró intervallum önmagában egyszerűbb és koherens döntés;
frissítse a `decisions.md` SOL-6 indoklását (vagy fűzzön rövid megjegyzést az 5. ponthoz), hogy a
napló és a szöveg összhangban legyen.
 Confidence: high

Claims checked

 - Context — W(Z<=6) pilot átlag 0,5036, SD 0,0445, 96 pontosan 0,5 érték, köztük mind a 88
kód-azonos pár (experiments/e5/pilot/z6__shared__none.json, runs/e5/acts/probe_val/{a,b}/codes.npy):
holds (újraszámolva: átlag 0.503587, SD(ddof=1) 0.044489, 96 egzakt 0.5, mind a 88 kód-azonos pár
pontosan 0.5).
 - Context — P2 per-pair W-AUC minden 250 párban 1,0; Delta átlag 0,4964, SD 0,0445, minimum 0,304
(experiments/e5/pilot/P2__shared__none.json, z6__shared__none.json): holds (újraszámolva: mind a 250
P2 érték 1.0, Delta átlag 0.496413, SD 0.044489, min 0.304348).
 - Context — Kauzális pilot statisztikák: Q 0,052 (SD 0,061), Q − hv 0,030 (SD 0,041), Q − random
mean 0,049, Q − shuffled 0,131; 71/500 recipiens TV(clean, full) < 0,01; koszinuszok hv 0,471 vs. Q
0,541 (experiments/e5/causal/primary_per_pair.json, primary.json, cosines.json): holds
(újraszámolva: Q 0.052038 / SD 0.060644; Q − hv 0.030066 / SD 0.040589; Q − random_mean 0.048975; Q
− shuf 0.131348; 0.142 * 500 = 71; koszinuszok 0.471296 és 0.541372).
 - Context — TEST seed namespace 10 és D99 orbit-kizárás (src/ncm_sudoku/e5pairs.py:24,
scripts/e5_pairs.py:60): holds (PAIR_SEEDS["pairs_test"] = 10; a 7. pont külön szabálya az „orbit
collision replaces only the new candidate pair” indokolt, mert scripts/e5_pairs.py:60 jelenleg
minden PAIR_VERSION elemet megjelölne ütközéskor).
 - Item 1 — IUT + Bonferroni szerkezet (két állítás 0,025-ös szinten, FWER <= 0,05): holds
(matematikailag helyes, amennyiben minden részfeltétel valódi egyoldali <= 0,025 szintű tesztet
használ és nem kerül külön megerősítő állításként jelentésre).
 - Item 2 — Értékkészletek: per-pair W-AUC ∈ [0, 1], Delta és a kauzális kontrasztok ∈ [-1, 1]
(src/ncm_sudoku/e5pilot.py:66, src/ncm_sudoku/e5causal.py:139-141, scripts/e5_causal.py:121): holds
(a különbségekben a TV(P_clean, P_full) tag kiesik, így directed(Q) - directed(c) = TV(P_c, P_full)
- TV(P_Q, P_full) ∈ [-1, 1]).
 - Item 2 — „hedged-capital form ... at level 0.025 per side” mint egyoldali 0,025-ös korlát: does
not hold (lásd NEON-1).
 - Item 3 — epsilon = 0,03 mint „3 net correct orderings per 100 discordant comparisons”: does not
hold (valójában 6 nettó helyes rendezés 100-ból; lásd NEON-5).

