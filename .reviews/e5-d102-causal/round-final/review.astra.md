Verdict

A rögzített Z≤6 melletti, 7. szintű mérés alkalmas pilotnak: megmutathatja, hogy a beavatkozás a
teljes csere felé mozdítja-e a kódeloszlást. A legfontosabb javítás a számjegyspecifikus értelmezés
leválasztása arról a geometriai előnyről, hogy a próba lépése eleve jobban igazodhat a teljes
cseréhez, mint az azonos normájú kontrollok.

Findings

ASTRA-1 | major | D102, 4(b–e), 5–7. pont
Claim: A normák illesztése nem illeszti a teljes csere irányával való egyezést. A Q feltétel ezért
akkor is jobban közelítheti a referenciát, ha a generátor nem kezeli kitüntetetten a jelölt
számjegyeket.
Evidence: A terv 19–22. sorában a cél a teljes Δ = x_d − x_r csere kimenete. Ha az S altérre
vetített lépést s = ‖P_QΔ‖ hosszúra skálázzuk, akkor Δ·lépés = s‖P_SΔ‖. Amikor ‖P_QΔ‖ > ‖P_SΔ‖, a
Q-val módosított állapot már a következő blokk előtt közelebb van a teljes cseréhez. A
számjegykeverés is ronthatja ezt az igazodást pusztán az irány megváltoztatásával.
Recommendation: A normán kívül közöljék a tényleges lépés és Δ koszinuszát is. Számjegyspecifikus
következtetéshez használjanak irányilleszkedésben is összevethető kontrollt vagy független
számjegyspecifikus célkimenetet. Enélkül a védhető állítás: „a Q-csere jobban reprodukálja a teljes
csere kimeneti hatását”.
Confidence: high

ASTRA-2 | major | D102, 1., 4(d) és 6. pont
Claim: A kevert számjegyes kontrollhoz nincs egyértelműen meghatározva az aktivációs lépés. A Q
oszlopai nem számjegytengelyek; az oszlopok vagy a fej sorainak egyszerű permutálása ugyanazt a
projektort adja vissza.
Evidence: A számjegyek a lineáris fej kilenc kimenetéhez tartoznak (probes.py:85–88), nem a sortér
tetszőleges ortonormált bázisához. A pilot ráadásul a három szigmoidkimenetet átlagolja
(probes.py:269–289); a kontroll célterét ezért az átlagolt logitra külön meg kell adni.
Recommendation: Egy reprodukálható választás: W legyen az átlagolt állapotsúlymátrix, Π előre
rögzített, fixpont nélküli számjegypermutáció, a nyers lépés pedig W⁺Π(WΔ). Ezt skálázzák a Q-lépés
normájára; ekkor a permutált logitváltozás irányát, nem feltétlenül a nagyságát érik el. Egy húzáson
belül ugyanazt a Π-t használják minden cellán és mindkét párirányban; ellenőrizzék az elért
logitirányt, és a Q–kevert kontrasztot is vegyék fel a páros elemzésbe.
Confidence: high

ASTRA-3 | major | D102, 3., 4(f) és 5. pont
Claim: A query-sorok bitazonossága a tiszta generálással csak azonos korábbi kódok mellett
elvárható. A javasolt ön-donor teszteken ugyanakkor egy soha nem aktiválódó hook is átmehet.
Evidence: A continue_generation a már adott szinteken kihagyja a blokkokat, majd a saját korábbi
argmaxából építi a következő queryt (intervene.py:106–125). A level_logits(..., level=7) egyetlen
blokkvermet futtat (intervene.py:160–169); az e5extract.py:27–43 lokális passzszámlálójában ez a 0.,
nem a 6. hívás. Ha a 7. kód megváltozik, a 8. query már a hook előtt eltérhet a tiszta futástól.
Recommendation: Az izolációt ugyanazon hívás hook előtti és utáni kimenetén ellenőrizzék.
Ellenőrizzék az abszolút szintet és az 1/6/12 alkalmazást az egypasszos/folytatásos/teljes ágban;
valódi, eltérő donorral legalább egy kijelölt cellán az elvárt csereértéket is. Az R1-ben elfogadott
P4/P8 kiolvasást nevezzék meg pontosan: a 7. szintet generáló hívásban a blocks[3] és blocks[7]
kimenete.
Confidence: high

ASTRA-4 | major | D102, 5–7. pont
Claim: A kontrollok felülmúlása nem jelenti, hogy Q a referencia felé mozdult: a változatlan
Q-kimenet is nyer, ha minden kontroll távolodik. Fordítva, a nulla irányított hatásból nem
következik, hogy a kódválasztás nem változott.
Evidence: A terv 22–24. sorának kontrasztjában a TV(P_clean,P_full) tag kiesik. Két különböző
eloszlás egyformán távol lehet a referenciától, akár eltérő argmaxszal. A level_logits nyers logitot
ad (intervene.py:135–140); a tényleges dekódolás T=0-nál argmax (next_concept.py:487–490), míg a
repo folytonos kódvalószínűséghez T=1 softmaxot használ (e2p2.py:92,109).
Recommendation: Rögzítsék a 16 kódon vett T=1 softmaxot, és a „közeledés” állításához a
kontrollkontrasztokon túl követeljék meg Q saját pozitív irányított hatását is. Negatív eredménynél
„nincs kimutatható referenciairányú elmozdulás” legyen a következtetés; az egyéb eloszlás- és
argmaxváltozásokról a külön diagnosztikák alapján nyilatkozzanak.
Confidence: high

ASTRA-5 | minor | D102, Context és 4(e)–5. pont
Claim: A 7–12. szint 287, nem 252 kód. A 249 eltérő tiszta folytatás sem igazolja, hogy a rögzített
Z≤6 melletti, kétoldalt üres cellákra korlátozott 7. szintű referencia érdemben eltér a
recipienstől.
Evidence: A szinthosszak 18+26+37+50+67+89 (checkpoints\sudoku\hard\config.yaml:88–93). A két
PROBE-VAL codes.npy közvetlen összevetésében a helyes suffixátlag 31,832/287; a tiszta 7. szint
argmaxa 153/250 párban, az azonos korai kódúak között 25/88 párban tér el. Ezek nem a beavatkozott
referencia értékei: a teljes donorinput már az első két blokkban hat a querykre, a réteg-2-es
részleges csere nem (next_concept.py:501–518).
Recommendation: Javítsák a nevezőt. P_full és c_full jelölje kifejezetten a kétoldalt üres cellák
teljes vektorcseréjét; a teljes donorinput kapjon külön nevet. Közöljék a tényleges
TV(P_clean,P_full) eloszlását és a közel nulla esetek arányát. A c_cond = c_full váltás
referenciakövető, nem feltétlenül a tiszta donor kódját követi.
Confidence: high

ASTRA-6 | minor | D102, 1. és 4(b–f) pont
Claim: A normaskálázásnak nincs nullaeseti szabálya, a naplózandó képlet pedig minden feltételre a Q
célnormáját adja, nem a ténylegesen beinjektált lépést. A főirányok használata önmagában nem
garantálja, hogy az átskálázott állapot az adatmanifoldon marad.
Evidence: Ön-donornál Δ=0, így a közvetlen normahányados 0/0; teljes cserénél a valódi norma ‖Δ‖,
nem ‖P_QΔ‖ (a terv 19–21. sora). A Q-ra merőlegesség az átlagolt P2-logitokat őrzi meg egzakt
aritmetikában, nem szükségképpen az egyes seedek logitjait vagy a mentett átlagvalószínűséget
(probes.py:269–289).
Recommendation: Nulla célnorma adjon pontosan nulla lépést; pozitív célnorma és numerikusan nulla
kontrollvetület legyen jelzett hiba. Relatív rangtoleranciát használjanak, és naplózzák a
skálafaktort, valamint az FP32-visszaírás utáni ‖x_after−x_before‖ értéket. A PCA-kontroll legyen
például a Q-ra merőlegesen vetített TRAIN-különbségek első kilenc főiránya; nevezzék nagy
varianciájú kontrollnak, és ellenőrizzék az átlaglogit változatlanságát megadott toleranciával.
Confidence: high

ASTRA-7 | minor | D102, 5–6. pont
Claim: A „rare-event and zero-count rules as in D101” nem határoz meg intervallumot ezekre a
végpontokra. Különösen a korlátlan előjeles logiteltolásra nem vihető át a W-AUC korlátosságára
épülő szabály.
Evidence: A D101-specifikáció 57. sora külön határokat vezet le a W-AUC 1-es plafonjára és a 0,5-től
való eltérésére; az 59. sor az üres réteget nem becsülhetőként kezeli. A D102 22–23. sora ezzel
szemben TV-különbséget, logiteltolást és bináris rescue/harm eseményt is mér.
Recommendation: A folytonos kontrasztokra páronkénti bootstrapot adjanak, degenerált mintánál ezt
jelezzék, ne tekintsék a hatást bizonyítottan nullának. A rescue és harm külön kapjon binomiális
intervallumot az 51 jogosult párra, nulla eseménynél is. A normalizált logiteltolás nevezőjéhez
rögzítsenek minimális abszolút értéket, és közöljék a kizárt bitek számát.
Confidence: high

Claims checked

 - holds — A Sudoku-konfigurációban 12 passz, 91 prefixtoken, 8 blokk és a 7. szinten 18×16 logit
van. A maszk kizárja a query→prefix információáramlást; a blokk kimenetén módosított prefix csak
későbbi figyelmi műveleten át érheti el ugyanazon passz queryjeit. Az azonos pozíciójú csere a RoPE
pozícióindexét nem módosítja (next_concept.py:501–518,590–596,622–627; common.py:104–110,197–210).
 - holds — PREFIX_CELLS kihagyja a BOS- és szeparátorpozíciókat; P2 a blocks[1] kimenete. A mentett
prefixaktiváció csak a 7. szint passzából származik és FP16; a passzonkénti online FP32 donor
indokolt (grid.py:24–25,128–130; e5extract.py:20–43,59–68; experiments\e5\cost.json:100–111).
 - holds — A megosztott fej standardizálatlan állapotot és cella-one-hotot olvas, csak üres
cellákon; azonos cellán a pozíciós tag kiesik a logitkülönbségből. A három seed súlyai
újrailleszthetők, de a pilot csak az átlagolt predikciókat mentette (probes.py:53–71,85–88,269–289;
e5pilot.py:97–116,137–143). could not verify — Az újraillesztés tényleges predikcióegyezése és az új
módosító hook bitazonossága még végrehajtandó pilotellenőrzés.
 - holds — A két API valóban rögzíteni tudja Z≤6-ot: continue_generation pontosan az első 35 kódot
várja, a level_logits(..., level=7) a további oszlopokat figyelmen kívül hagyja
(intervene.py:88–91,106–125,145–169). Csak a 7. szintű eredmény mentes a korábbi beavatkozott
szintek közvetítésétől; a 8–12. szintű folytatás már nem.
 - holds — A nyers PROBE-VAL tömbökből: 250 pár, tagonként 30 megadott szám; 88 azonos korai kódsor;
249 eltérő tiszta folytatás; 194 mindkét oldalon és 51 pontosan egy oldalon megoldott pár. A 8 103
kétoldalt üres cella P2-különbségeinek kilenc vezető szinguláris iránya az energia 49,514%-át
hordozza; az izotróp várakozás 9/512 = 1,758%. does not hold — A suffix hossza 252 (ASTRA-5).
 - holds — A két irány páron belüli átlagolásával 250, nem 500 mintavételi egység van; ez alkalmas
feltételes pilotbecslésre, önmagában nem igazol teszterőt. Az 1,7052 s/feladvány valóban mért teljes
generálási alapidő, 20-as CPU-batchen, nem a módosító hookok mért költsége
(experiments\e5\cost.json:5,85–100).

