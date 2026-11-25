A generálási útvonalat ellenőriztem. Most a mentett pilotadatokból ellenőrzöm a páronkénti számokat és azt, hogy a javasolt beavatkozás reprodukálható-e a meglévő artefaktumokból.

Verdict

A beavatkozás megvalósítható, de a terv jelen formájában nem különíti el a jelöltinformáció
használatát a reprezentáció általános megzavarásától. A legfontosabb változtatás: elsődlegesen csak
a 7. menetben avatkozzatok be, a recipiens tiszta Z≤6 állapotát rögzítve, és az argmax előtti
kódeloszlást mérjétek.

Findings

SOL-1 | major | D102 §1, §3–5
Claim: A 12 menetes csere után a 7–12. szint kódváltozása nem különíti el a korai kódokon át
közvetített hatást a későbbi közvetlen prefixhatástól. Az argmax-váltás hiánya nem zárja ki a
kódeloszlás változását.
Evidence: A next_concept.py:501–519, 660–691 szerint minden későbbi menet az előző kódokból
frissített állapotot és a prefixet is olvassa. Az intervene.py:135–170 a rögzített előzménykódokból
ugyanazon a blokksoron számolja ki az argmax előtti logitokat.
Recommendation: Elsődlegesen level_logits(..., clean_codes, level=7) mellett, csak P2-n cseréljetek,
és a 18 query tiszta és módosított 16-os kódeloszlása közti átlagos Jensen–Shannon-távolságot
mérjétek. Az argmax-váltás legyen másodlagos. A 7–12. menetes csere rögzíti Z≤6-ot, de a 8. menettől
már továbbviheti a módosított kódok hatását; a 12 menetes csere teljes hatást mér. Ha a Z≤6-on át
közvetített út külön érdekes, csak az 1–6. menetben cseréljetek, majd folytassátok tiszta
prefixszel.
Confidence: high

SOL-2 | major | D102 §1, §4
Claim: Az azonos rangú izotróp véletlen altér nem azonos erősségű kontroll. A probe előnye
származhat abból, hogy nagyobb vagy a generátor számára érzékenyebb eltérést visz át.
Evidence: Az e5extract.py:53–68 szerint mentett PROBE-VAL P2-állapotokon a mindkét oldalon üres
cellák donor–recipiens különbségeinek első kilenc jobb szinguláris iránya a teljes négyzetes energia
49,5%-át viszi; egy izotróp 9/512-es vetület várható részesedése 1,76%. Ez az anizotrópiát igazolja,
nem a hiányzó probe-súlyok tényleges vetítési energiáját.
Recommendation: Jelentsétek a beadott eltérés normáját cellánként és recipiensenként. Az izotróp
kontroll mellé kerüljön legalább egy, a tényleges normához illesztett kontroll, előre rögzített
szabállyal a közel nulla vetületekre. Érzékenységi ellenőrzésként használjatok PROBE-TRAIN
különbségekből becsült, hasonló varianciájú irányokat is.
Confidence: high

SOL-3 | major | D102 §1, §4–5
Claim: A probe-altér érzékenysége nem azonos a jelöltmaszk szemantikus használatával. A
teljesvektor-csere nem felső korlát, és a nullhatás nem bizonyítja, hogy a modell nem használja
ezeket az irányokat.
Evidence: A jelöltcímke a megadott számok determinisztikus függvénye (labels.py:29–37); a
probes.py:85–91 lineáris feje megkülönbözteti a címkéket, de nem választja szét a velük korreláló
információkat. A common.py:87–132, 197–213 nemlineáris blokkjai nem adnak monotonitást a részleges
és teljes csere között. A D102 csak a mindkét oldalon üres cellákat módosítja, így a recipiens
eltérő clue-tokenjei megmaradnak, bár későbbi reprezentációjuk változhat.
Recommendation: A teljes cserét nevezzétek referenciának, ne plafonnak. Tartsátok meg a mindkét
oldalon üres maszkot elsődlegesnek: az egyoldalúan üres helyeken a csere clue-tartalmat is átvihet,
a probe pedig csak üres cellákon tanult. Erősebb szemantikus állításhoz hasonlítsátok össze
ugyanabban az altérben, azonos helyeken és illesztett normával a donor diszkordáns bitjei felé
célzott és a digitcélok megkeverésével képzett perturbációt. Enélkül csak a vizsgált beavatkozásra
mért érzékenységet vagy az észlelhető hatás hiányát állítsátok.
Confidence: high

SOL-4 | major | D102 §1–2
Claim: A pilot nem mentette ki a hivatkozott befagyasztott fejeket, és a D101 három seed
szigmoidkimenetét átlagolja, nem egyetlen kilencsoros fejet használ. A 512 × 9 ortonormált bázishoz
szükséges teljes sorrang nincs igazolva.
Evidence: A probes.py:55–68, 85–87, 269–290 nyers állapotot és pozíciós one-hotot fűz össze; a
súlyokat visszaadja a hívónak. Az e5pilot.py:97–116, 137–142 eldobja a súlyokat, és csak
összesítést, illetve predikciókat ment. Azonos cellán a pozíciótag és a bias kiesik a
donor–recipiens logitkülönbségből, így egy konkrét fej állapotsorainak tere értelmes beavatkozási
cél.
Recommendation: Rögzített adatokból és pilotbeállításokkal állítsátok elő újra a P2/P4/P8 fejeket,
ellenőrizzétek a mentett predikciók reprodukcióját, és verziózzátok a súlyokat, biasokat és az
előfeldolgozást. A P2-cseréhez jelöljetek ki előre egy seedet, a többivel végezzetek érzékenységi
ellenőrzést. SVD-vel állapítsátok meg a tényleges rangot, ahhoz illesszétek a kontrollokat, és
közvetlenül ellenőrizzétek, hogy az adott P2-fej a cserélt pozíciókon a donor logitjait adja.
Confidence: high

SOL-5 | major | D102 §2, §4
Claim: A donor felé mozdulás puszta aránya a tetszőlegesen kis és a jelentős változást egyformán
számolja, a telített szigmoid pedig elfedhet valódi elmozdulást. Ez a tényleges végpontnál is
fennáll, nem csak P2-n.
Evidence: A probes.py:85–87, 268–290 float32 szigmoidpredikciókat átlagol. A mentett
P4__shared__none.npy tömbben a diszkordáns bitek 50 836 irányított tiszta predikciójából 2 090
pontosan 0 vagy 1.
Recommendation: Elsődlegesen a donor címkéje szerint előjelezett logitváltozást mérjétek,
(2*y_d−1)*(logit_patch−logit_clean), a szigmoid előtti értékekből. Másodlagosan adjátok meg a donor
felé, ellenkező irányba és a numerikus tolerancián belül elmozduló bitek arányát. Rögzítsétek a
toleranciát, a nem véges értékek kezelését és a diszkordáns bit nélküli párok kizárását; a mostani
pilotban ilyen pár nincs.
Confidence: high

SOL-6 | minor | D102 §1, §2, §6
Claim: A nulla-delta sham önmagában nem deríti ki, hogy rossz blokkra, menetre, cellára vagy
batch-sorra került-e a csere. A már mentett donoraktivációk nem alkalmasak a 12 menetes, azonos
pontosságú cserére.
Evidence: Az e5extract.py:20–50, 60–68 egyetlen menetet ment fp16-ban, és a hookokat finally ágban
távolítja el. A cost.json:100–112 P2-n is mér menetközi numerikus eltérést. A next_concept.py:528,
702 írja a modell _cfg állapotát, a hook pedig a közös modulra kerül.
Recommendation: A P2-horog a blocks[1] kimenetére kerüljön. Take­rékos, tiszta fp32 futásból, azonos
menetből és batch-elrendezésből gyűjtsétek a donorértékeket. Legyen külön hook nélküli és öncserés
referencia, valamint nem nulla csere, amelynél ellenőrzitek a menet- és cellamaszkot, illetve hogy a
hook visszatérési értékében a query-k és a maszkon kívüli prefixsorok bitazonosak. Ne fusson
párhuzamos hívás ugyanazon a modellen; a hookok kivételnél is kerüljenek le.
Confidence: high

SOL-7 | minor | D102 §3–5
Claim: A páronkénti bootstrap helyes a rögzített öt véletlen altérre feltételes kontraszthoz, de nem
méri az altérválasztás bizonytalanságát. Az 500 irányított futás 250 független pár; az 51
mentés/ártalom pár feltáró mérésre elég, kis hatások kizárására nem.
Evidence: Az e5pilot.py:28–39, 63–84 a két irányt közös párhoz rendeli; a nyers codes.npy és
solved.npy tömbökből 88 azonos korai kódú, 194 mindkét oldalon megoldott és 51 egyoldalúan megoldott
pár adódik. A runner.py:29–33 a kódokat prefix nélkül dekódolja; a két tagnál a helyes rács ugyanaz.
Recommendation: A két irány átlagát páronként súlyozzátok egyenlően, jelentsétek az öt altér
eredményét külön, az intervallumot pedig nevezzétek feltételesnek. Ritka vagy nulla eseménynél ne
értelmezzétek a degenerált bootstrapot a hatás hiányaként. A kódváltás mechanisztikus diagnosztika,
a rács-Hamming pedig leíró mérés legyen; a mentést és ártalmat darabszámmal és intervallummal
közöljétek, ne döntési feltételként. Az érdemi hatásküszöböt és a későbbi mintaméretet a pilot
alapján, a friss TEST előtt rögzítsétek.
Confidence: high

SOL-8 | minor | D102 §6
Claim: Az 1,9 óra aritmetikailag helyes, de a nyolc feltétel tiszta generálási idejét vetíti ki; nem
tartalmazza a külön tiszta referencia és donorgyűjtés, valamint az új hookok és kiolvasások
költségét.
Evidence: A cost.json:3–5, 81–112 húszas batchben 1,7052 s/puzzle tiszta és 1,769 s/puzzle
kiolvasásos referenciát mér. Ezekkel egy közös, további 500 elemű tiszta/donorfutás hozzáadása kb.
2,14 órára emelné a becslést, az új hookköltség előtt.
Recommendation: Először a tényleges batchmérettel mérjetek egy kis futást, és ugyanabból a tiszta
batchből gyűjtsétek a referenciát és a donorokat. Csak a szükséges P2-szeleteket, logitokat és
összesítéseket tartsátok meg. A teljes 12 menetes futást halasszátok az egymenetes mérés és az
identitásellenőrzések utánra.
Confidence: high

Claims checked

 - holds — A vizsgált Sudoku-hard út 12 eager menetet futtat, menetenként 91 prefixtokennel és az
adott szint query-jeivel. Az első szint külön m0 maszkot, a többi gen_mask-ot használ; mindkettő
tiltja a prefix→query figyelmet, és engedi a query→prefix, illetve query→query figyelmet
(config.yaml:9–36, 80–93; next_concept.py:501–519, 581–626, 660–691).
 - holds — P2 a blocks[1] kimenete; a PREFIX_CELLS a 81 cellát jelöli, a BOS és sorelválasztók
nélkül. A cserétől a query-k csak későbbi blokkok figyelmén át változhatnak ugyanabban a menetben;
szintek között az előző kódok is továbbvihetik a hatást. Az azonos pozíción végzett csere nem
módosítja a RoPE-indexeket vagy rotációs puffereket (e5extract.py:20–50; grid.py:24–25, 128–130;
next_concept.py:94–115; common.py:87–132, 197–213).
 - holds — A projekt futtatója temperature=0.0-val argmaxot használ, és a modell betöltéskor eval
módba kerül. Ez a rögzített futtatási beállításra vonatkozik, nem a generate alapértelmezésére vagy
különböző batchalakok bitazonosságára (runner.py:19–33; model.py:46–64; next_concept.py:487–522;
cost.json:100–112).
 - holds — Egy megoldásból két különböző, 30 clue-s, egyedi megoldású maszk készül. A mentett 250
párból 88-nál egyezik az 1–6. szint kódja, 194-nél mindkét tag megoldott (77,6%), 51-nél pontosan az
egyik (e5pairs.py:40–70; e5pilot.py:23–39; PROBE-VAL solutions.npy, codes.npy, solved.npy).
 - holds — A közölt pilotértékek kerekítve egyeznek: P2/P3 W-AUC 1,000, P8 0,958; Z≤6 0,504
AdamW-vel és standardizált L-BFGS-szel; MDL P2 195,6, P0 1,049, Z≤6 1,029
(experiments\e5\pilot\*__shared__none.json:541, z6__shared__lbfgs.json:13–42,
*__shared__mdl.json:67).
 - holds — Az AdamW shared fej kilenc kimenetű, és a state plusz cella-one-hot bemenet nincs
standardizálva (probes.py:55–87; e3controls.py:144–171).
 - does not hold — A jelenlegi mentett pilotkimenetből egy kész, befagyasztott P2/P4/P8 fej
visszatölthető (probes.py:269–290; e5pilot.py:97–116, 137–142). could not verify — A P2
állapotsúlyok tényleges rangja és vetítési energiája; a súlyokat a pilot nem mentette el.
 - holds — A mérési alap 1,7052 s/puzzle és a 8 × 500 tiszta futásra számolt 1,9 óra (cost.json:3–5,
81–99); a teljes beavatkozás futási ideje ebből még nem igazolt.

