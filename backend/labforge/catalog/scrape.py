"""Strand B: one-off vendor scrape into data/catalog.json. Owner: Max.

Plan (once, then commit the cached JSON so nobody depends on the network at demo time):
1. VENDOR_PAGES lists product pages for every instrument in docs/pipelines.md.
2. A Modal function fetches each page in parallel and asks Claude to fill a CatalogItem,
   recording every number's source and confidence under `provenance`.
3. Results are validated with labforge.contracts.validate(item, "catalog_item") and merged.

Run:  cd backend && modal run labforge/catalog/scrape_modal.py   (needs `pip install -e .[modal]`,
      `modal token new`, and ANTHROPIC_API_KEY in the repo-root .env). This file has no Modal import so the
      rest of the backend works without it.

Prices: vendors almost never publish them, so PRICE_REFERENCES records where each price came from
(researched 3 Oct 2026). Each entry is a common.schema.json `uncertain_number` plus a `note`, ready to
drop into provenance["price_usd_estimate"]. Sources, best first: vendor/distributor list price
("datasheet"); US federal purchase records (usaspending.gov award pages need JavaScript to render),
NIH grants, state contract price lists, news, used listings ("estimated"). Notes marked WEAK are
agent estimates anchored on related figures, not quotes. Non-USD converted at ~1.17 USD/EUR,
~1.34 USD/GBP. Human operators are not here (no vendor page); they are added to the catalog directly.
"""
VENDOR_PAGES: dict[str, str] = {
    # --- Liquid handling, dispensing and plate handling (both pipelines) ---
    # Opentrons: Opentrons Flex
    "opentrons_flex": "https://opentrons.com/products/opentrons-flex-robot",
    # Opentrons: OT-2
    "opentrons_ot2": "https://opentrons.com/products/ot-2-robot",
    # Hamilton Company: Microlab STAR
    "hamilton_microlab_star": "https://www.hamiltoncompany.com/microlab-star",
    # Tecan: Fluent 780
    "tecan_fluent": "https://lifesciences.tecan.com/fluent-laboratory-automation-workstation",
    # Beckman Coulter Life Sciences: Biomek i7 Hybrid (MC + Span-8)
    "beckman_biomek_i7": "https://www.beckman.com/liquid-handlers/biomek-i-series-automated-workstations/biomek-i7",
    # Thermo Fisher Scientific: Multidrop Combi+ (5840330)
    "thermo_multidrop_combi": "https://www.thermofisher.com/order/catalog/product/5840330",
    # Beckman Coulter Life Sciences: Echo 650 (successor: Echo 650 Plus)
    "beckman_echo_650": "https://www.beckman.com/liquid-handlers/echo-acoustic/echo-650-plus-series",
    # Beckman Coulter Life Sciences: Echo 525 (001-10080)
    "beckman_echo_525": "https://store.beckman.com/en/p/001-10080?countryCode=US",
    # Agilent Technologies: PlateLoc Thermal Microplate Sealer (G5585BA)
    "agilent_plateloc": "https://www.agilent.com/en/product/automated-liquid-handling/automated-microplate-management/plateloc-thermal-microplate-sealer",
    # Azenta Life Sciences: Automated Plate Seal Remover (formerly XPeel)
    "azenta_xpeel": "https://www.azenta.com/products/automated-plate-seal-remover-formerly-xpeel",
    # BioNex Solutions: HiG4 automated centrifuge
    "bionex_hig4": "https://www.bionexsolutions.com/hig-centrifuge/",
    # IKA: IKA Plate (RCT digital), 0025005389
    "ika_rct_digital": "https://www.ika.com/en/Products-LabEq/Magnetic-Stirrers-pg188/IKA-Plate-25004735/",
    # --- Chemistry: powder dosing, synthesis, workup, evaporation, LC-MS, ventilation ---
    # Mettler Toledo: Quantos QB5 automated powder dosing
    "mettler_quantos": "https://www.mt.com/us/en/home/products/Laboratory_Weighing_Solutions/Automated_Sample_Preparation/Automated_Powder_Liquid_Dispensing.html",
    # Chemspeed Technologies (Bruker): SWING XL with gravimetric dispensing unit
    "chemspeed_swing_xl": "https://www.chemspeed.com/configurable-solutions/",
    # Chemspeed Technologies (Bruker): ISYNTH parallel synthesis workstation (now a SWING/FLEX 'migrated workflow')
    "chemspeed_isynth": "https://www.chemspeed.com/example-solutions/automated-library-synthesis/",
    # Unchained Labs: Big Kahuna
    "unchained_big_kahuna": "https://www.unchainedlabs.com/big-kahuna/",
    # Biotage: PRESSURE+ 96 positive pressure manifold (PPM-96)
    "biotage_pressure_plus_96": "https://www.biotage.com/positive-pressure-processing",
    # SP Genevac: EZ-2 4.0 personal centrifugal evaporator
    "genevac_ez2": "https://scientificproducts.com/products/genevac-ez-2-4-0-series-centrifugal-evaporators-2/",
    # SP Genevac: HT-6 Series 3i centrifugal evaporator
    "genevac_ht6": "https://scientificproducts.com/products/genevac-ht-series-3i-vacuum-evaporator/",
    # Waters: ACQUITY UPLC I-Class PLUS + SM-FTN-I plate sampler + ACQUITY QDa
    "waters_acquity_uplc_qda": "https://www.waters.com/nextgen/us/en/products/mass-spectrometry/mass-spectrometry-systems/acquity-qda-ii-mass-detector.html",
    # Agilent: 1290 Infinity II LC + InfinityLab LC/MSD iQ (G6160AA)
    "agilent_1290_lcmsd_iq": "https://www.agilent.com/en/product/liquid-chromatography-mass-spectrometry-lc-ms/lc-ms-instruments/single-quadrupole-lc-ms",
    # MBRAUN: LABstar pro / UNIlab Pro inert gas glovebox
    "mbraun_glovebox": "https://www.mbraun.com/en/glovebox/glovebox-systems.html",
    # Labconco: Protector XStream 6 ft laboratory hood
    "labconco_fume_hood": "https://www.labconco.com/product/6-protector-xstream-laboratory-hood-with-2-service-fixtures",
    # Justrite: Sure-Grip EX 45 gal flammable safety cabinet (894500)
    "justrite_flammable_cabinet": "https://www.justrite.com/894500-45-gallon-sure-grip-ex-flammable-safety-cabinet-yellow",
    # --- Readers, incubators, storage and furniture ---
    # BMG LABTECH: PHERAstar FSX
    "bmg_pherastar_fsx": "https://www.bmglabtech.com/en/pherastar-fsx/",
    # BMG LABTECH: CLARIOstar Plus
    "bmg_clariostar": "https://www.bmglabtech.com/en/clariostar-plus/",
    # LiCONiC: StoreX STX44
    "liconic_stx44": "https://www.liconic.com/stx44.html",
    # Thermo Fisher Scientific: Cytomat 2 C-LiN automated incubator
    "thermo_cytomat_2": "https://www.thermofisher.com/order/catalog/product/51032950",
    # Tecnoflo (via LabsRobots): Hotel Rack, Universal, Side Grip (14/21 SBS plates)
    "generic_plate_hotel": "https://www.labsrobots.com/product-page/hotel-rack-side-grip",
    # Azenta Life Sciences: SampleStore automated sample storage (ambient to -20 C)
    "compound_store": "https://web.azenta.com/samplestore-automated-sample-storage-system",
    # Thermo Fisher Scientific: TSX Universal -86 C upright freezer (TSX40086FA; succeeds TSX40086A)
    "thermo_tsx_minus80": "https://www.thermofisher.com/order/catalog/product/TSX40086FA",
    # Thermo Fisher Scientific: TSX High-Performance Lab Refrigerator TSX2305GA (23 cu ft, 2-8 C)
    "thermo_lab_fridge": "https://www.thermofisher.com/order/catalog/product/TSX2305GA",
    # Nor-Lake: Kold Locker KLB7788-C 8x8 ft walk-in cooler
    "walk_in_cold_room": "https://www.norlake.com/products/kold-locker",
    # Thermo Fisher Scientific: 1300 Series Class II A2 BSC, 6 ft (model 1377)
    "thermo_1300_bsc": "https://www.thermofisher.com/order/catalog/product/1377",
    # Fisherbrand: Adjustable Height Basic Work Bench, 30x72 in, phenolic top
    "lab_bench": "https://www.fishersci.com/shop/products/adjustable-height-basic-work-bench-leveling-glides-3/06000654",
    # TMC (AMETEK): CleanBench 63-500 Series, 750x900 mm
    "tmc_vibration_table": "https://www.techmfg.com/products/labtables/cleanbench63series",
    # --- Biology: expression, harvest, lysis, purification, protein QC ---
    # Infors HT: Multitron Pro incubated shaker (single unit)
    "infors_multitron_pro": "https://infors-ht.com/en/products/incubator-shakers/multitron",
    # Sartorius: Ambr 250 High Throughput (12-way)
    "sartorius_ambr250": "https://www.sartorius.com/en/products/fermentation-bioreactors/ambr-multi-parallel-bioreactors/ambr-250-high-throughput",
    # Beckman Coulter: Avanti JXN-26 (B34183, no rotor)
    "beckman_avanti_jxn26": "https://www.beckman.com/centrifuges/high-speed/avanti-jxn-26",
    # Eppendorf: Centrifuge 5810 R with 4x750 mL + plate rotor package
    "eppendorf_5810r": "https://www.eppendorf.com/us-en/Products/Centrifugation/Multipurpose-Centrifuges/Centrifuge-5810-5810R-p-PF-240994",
    # Avestin: EmulsiFlex-C3 high pressure homogenizer
    "avestin_emulsiflex_c3": "https://avestin.com/products/EmulsiFlex-C3",
    # QSonica: Q700 Sonicator with 1/2 in probe
    "qsonica_q700": "https://www.sonicator.com/products/q700-sonicator",
    # Cytiva: AKTA pure 25 M (29018226)
    "cytiva_akta_pure_25": "https://www.cytivalifesciences.com/en/us/products/items/akta-pure-p-05844",
    # Cytiva: AKTA avant 150 (28976337)
    "cytiva_akta_avant_150": "https://www.cytivalifesciences.com/en/us/products/items/akta-avant-p-06264",
    # Revvity: LabChip GXII Touch HT (CLS138160)
    "revvity_labchip_gx_touch": "https://www.revvity.com/product/ship-level-labchip-gx-ii-touch-ht-cls138160",
    # Thermo Fisher Scientific: NanoDrop Ultra (successor to discontinued NanoDrop One)
    "thermo_nanodrop_one": "https://www.thermofisher.com/us/en/home/industrial/spectroscopy-elemental-isotope-analysis/molecular-spectroscopy/uv-vis-spectrophotometry/instruments/nanodrop/instruments/nanodrop-ultra.html",
    # Unchained Labs: Lunatic plate-based UV/Vis
    "unchained_lunatic": "https://www.unchainedlabs.com/lunatic/",
    # Bio-Rad: Mini-PROTEAN Tetra Cell with PowerPac Basic (1658025FC)
    "biorad_mini_protean_tetra": "https://www.bio-rad.com/en-us/sku/1658025FC-mini-protean-tetra-vertical-electrophoresis-cell-4-gel-for-1-0-mm-thick-handcast-gels-with-powerpac-basic-power-supply?ID=1658025FC",
    # --- Crystallography, cryo, synchrotron, and transporters (arms, rail, mobile) ---
    # SPT Labtech: mosquito Xtal3
    "sptlabtech_mosquito_xtal3": "https://www.sptlabtech.com/products/mosquito/mosquito-xtal3",
    # Formulatrix: NT8 drop setter (current: NT8 v4)
    "formulatrix_nt8": "https://formulatrix.com/protein-crystallization-systems/nt8-drop-setter/",
    # Formulatrix: Rock Imager 1000
    "formulatrix_rock_imager_1000": "https://formulatrix.com/protein-crystallization-systems/rock-imager-protein-images/",
    # Oxford Lab Technologies: Crystal Shifter
    "olt_crystal_shifter": "https://www.oxfordlabtech.com/en/crystal-shifter",
    # IC Biomedical (Worthington/Taylor-Wharton): ICB35-10 LN2 freezer, 35 L, 10 canisters
    "ln2_storage_dewar": "https://www.mitegen.com/product/tw35-10-cryogenic-freezer/",
    # IC Biomedical (Worthington/Taylor-Wharton): CX100 Cryo Express dry shipper
    "taylor_wharton_cx100": "https://www.mitegen.com/product/cryo-express-dry-shipper-cx100/",
    # Diamond Light Source (external service): I04-1 unattended MX, proprietary beamtime
    "diamond_i04_1": "https://www.diamond.ac.uk/Instruments/Mx/I04-1.html",
    # Universal Robots: UR5e (renamed UR7e in 2025)
    "ur5e": "https://www.universal-robots.com/products/e-series/",
    # Brooks Automation (PreciseFlex): PreciseFlex 400 (PF400) collaborative SCARA
    "precise_pf400": "https://www.preciseflexrobots.com/lab-automation-applicable-products/#preciseflex400_labproducts",
    # Brooks Automation (PreciseFlex): PreciseFlex Linear Rail for PF400, 1.5 m
    "lab_linear_rail": "https://www.preciseflexrobots.com/software-and-accessories/#linear-rails",
    # KUKA: KMR iiwa mobile manipulator
    "kuka_kmr_iiwa": "https://www.kuka.com/en-us/products/amr-autonomous-mobile-robotics/mobile-robot-systems/kmr-iiwa",
    # Omron: LD-250 autonomous mobile robot (37222-00000)
    "omron_ld250": "https://robotics.omron.com/products/mobile-robots/ld-series/ld-250/",
}

PRICE_REFERENCES: dict[str, dict] = {
    # --- Liquid handling, dispensing and plate handling (both pipelines) ---
    "opentrons_flex": {
        "value": 24950,
        "low": 24950,
        "high": 125000,
        "confidence": "datasheet",
        "source": "https://opentrons.com/products/opentrons-flex-robot",
        "note": "Vendor page (2026): 'Starting at $24,950' base robot. Federal full workstation packages $68-124K (2025-26).",
    },
    "opentrons_ot2": {
        "value": 15950,
        "low": 11335,
        "high": 30000,
        "confidence": "datasheet",
        "source": "https://opentrons.com/products/ot-2-robot",
        "note": "Vendor page (2026): 'Starting at $15,950'. Federal buys $11,335 (2022) to $24,127 with modules (2023).",
    },
    "hamilton_microlab_star": {
        "value": 247215,
        "low": 135000,
        "high": 302000,
        "confidence": "estimated",
        "source": "https://reporter.nih.gov/project-details/10424767",
        "note": "NIH S10 grant 1S10OD032282-01 (FY2022): Hamilton NGS STAR incl. install/training/warranty $247,215. Federal STAR buys $182K (2021) to $302K (2025); STARlet $135-193K.",
    },
    "tecan_fluent": {
        "value": 339999,
        "low": 209000,
        "high": 500000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N98026P01440_7529_-NONE-_-NONE-",
        "note": "NIH Aug 2026: Tecan Fluent 780 $339,999. Fluent 480 $209,528 (2022); Fluent 1080 workstation $500,483 (CDC 2019).",
    },
    "beckman_biomek_i7": {
        "value": 335519,
        "low": 191683,
        "high": 403000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N98026F00188_7529_GS07F0636W_4730",
        "note": "NIH/NHGRI Jun 2026 (GSA): Biomek i7 Hybrid with enclosure $335,519. Other federal buys $191,683 (2024) to $402,992 (2026).",
    },
    "thermo_multidrop_combi": {
        "value": 24191,
        "low": 17187,
        "high": 28700,
        "confidence": "datasheet",
        "source": "https://www.fishersci.com/shop/products/NC2237227/NC2237227",
        "note": "Fisher US list $24,191 (web $22,743), 2026. Thermo UK GBP 21,431 (~$28.7K at 1.34). NIH 2020 older model $17,187.",
    },
    "beckman_echo_650": {
        "value": 374093,
        "low": 250000,
        "high": 420000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N98026F00251_7529_GS07F0636W_4730",
        "note": "NIH Jul 2026 (GSA): Echo 650 system $374,093; NIH S10 grants 2020/2025 ~$375-379K. Low reflects 2025 promo of up to 1/3 off.",
    },
    "beckman_echo_525": {
        "value": 246083,
        "low": 165000,
        "high": 340000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_W911QX19P0132_9700_-NONE-_-NONE-",
        "note": "US Army 2019 order: Echo 525 $246,083; Navy 2018 Echo 525 system $338,376. Low reflects 2025 promo of up to 1/3 off.",
    },
    "agilent_plateloc": {
        "value": 45143,
        "low": 29872,
        "high": 45143,
        "confidence": "datasheet",
        "source": "https://search.testmart.com/search/sitesearch.cfm/~q%60%20Family%20Code%201260~p2%6040000btw50000~s%60SELLING_PRICE",
        "note": "TestMart/GSAMart open-market price $45,143 (2026). Federal buys $29,872 (2019), $31,811 (2021).",
    },
    "azenta_xpeel": {
        "value": 36400,
        "low": 34000,
        "high": 61450,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_SPE2D621F1NUP_9700_SPE2DE20D0006_9700",
        "note": "DLA 2021 via Thomas Scientific: XPeel $36,400; NIH 2021 $34,124. Current list ~$52.9-61.4K seen only in search snippets (not opened).",
    },
    "bionex_hig4": {
        "value": 100000,
        "low": 50000,
        "high": 150000,
        "confidence": "estimated",
        "source": "https://labautomation.io/t/integrated-microplate-centrifuge-bionex-hig-or-hettich-sbs300/3521",
        "note": "WEAK. No list price or purchase record. Derived from a 2025 forum post: HiG3 ~3x a Hettich SBS300 and ~100K more (implies ~150K, currency unstated); HiG4 assumed lower. Used HiG4 $20.7K is a floor.",
    },
    "ika_rct_digital": {
        "value": 1280,
        "low": 1216,
        "high": 1300,
        "confidence": "datasheet",
        "source": "https://www.msesupplies.com/products/ika-plate-rct-digital-magnetic-stirrers-1500rpm-310-c",
        "note": "MSE Supplies $1,279.95 (2026); IKA list $1,280.",
    },
    # --- Chemistry: powder dosing, synthesis, workup, evaporation, LC-MS, ventilation ---
    "mettler_quantos": {
        "value": 72900,
        "low": 43665,
        "high": 100000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_W81XWH12F0057_9700_GS24F1286C_4730",
        "note": "US Army GSA order Feb 2012: QB5 automated powder dispensing system $72,900. Other federal buys $43.7K (2014) to $99.4K (2016). 2009-2014 prices likely 30-40% below today's.",
    },
    "chemspeed_swing_xl": {
        "value": 594301,
        "low": 395000,
        "high": 1100000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_HHSF223201710103P_7524_-NONE-_-NONE-",
        "note": "FDA 2017 PO: Chemspeed SWING automated workstation $594,301. NASA 2022 $601,850; Strathclyde 2025 dosing platform GBP 293,760 (~$394K); DTU 2024-25 synthesis platform ~$0.93-1.09M. Configuration-dependent.",
    },
    "chemspeed_isynth": {
        "value": 500000,
        "low": 300000,
        "high": 750000,
        "confidence": "estimated",
        "source": "https://www.york.ac.uk/news-and-events/news/2012/research/chemspeed/",
        "note": "WEAK. No direct ISYNTH price. Derived from Univ. York 2012: GBP 750K for two older Chemspeed parallel-synthesis platforms (~GBP 375K / ~$500K each).",
    },
    "unchained_big_kahuna": {
        "value": 800000,
        "low": 600000,
        "high": 1500000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N95019P00423_7529_-NONE-_-NONE-",
        "note": "WEAK. No direct Big Kahuna price; $800K is an agent estimate. Anchor: NIH/NCATS 2019 PO for the smaller Unchained Junior $677,898; FDA 2020 Unchained formulation system $777,090 (model unstated).",
    },
    "biotage_pressure_plus_96": {
        "value": 7834,
        "low": 3671,
        "high": 8000,
        "confidence": "datasheet",
        "source": "https://www.fishersci.com/shop/products/NC1872591/NC1872591",
        "note": "Fisher NC1872591 $7,834.08 (2026). EPA 2016 PO $3,671. Gas supply not included.",
    },
    "genevac_ez2": {
        "value": 52500,
        "low": 40000,
        "high": 86239,
        "confidence": "estimated",
        "source": "https://www.labx.com/resources/the-best-evaporators-and-concentrators-a-buyers-review-of-price-and-features/4827",
        "note": "Midpoint of LabX buyer's guide (Jan 2026) range $45-60K. NIH POs $44.9K (2020) and $54.2K (2017); Fisher EZ-2.4 Elite $86,239 (high).",
    },
    "genevac_ht6": {
        "value": 80000,
        "low": 45000,
        "high": 100000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N94025P00513_7529_-NONE-_-NONE-",
        "note": "WEAK. No HT-6 list price; $80K is an agent estimate. Nearest: NIH/NIAAA Aug 2025 PO to SP Industries for a solvent evaporator system $85,270 (model unstated).",
    },
    "waters_acquity_uplc_qda": {
        "value": 156700,
        "low": 95900,
        "high": 210000,
        "confidence": "datasheet",
        "source": "https://online.ogs.ny.gov/purchase/spg/pdfdocs/3870022962PL_Waters.pdf",
        "note": "NY State contract list prices (Jun 2023): I-Class PLUS w/ SM-FTN-I $83,300 + QDa Performance $73,400. Low = H-Class + QDa at NYS net; high adds PDA and software. QDa II is now current.",
    },
    "agilent_1290_lcmsd_iq": {
        "value": 214184,
        "low": 136000,
        "high": 250000,
        "confidence": "datasheet",
        "source": "https://online.ogs.ny.gov/purchase/spg/pdfdocs/3870022962PL_Agilent.pdf",
        "note": "NY State contract list prices (Jul 2023): pump $56,302 + multisampler $35,011 + thermostat $8,641 + LC/MSD iQ $114,230. Low = NYS net (36.5% off); high adds DAD. Succeeded by InfinityLab Pro iQ.",
    },
    "mbraun_glovebox": {
        "value": 60303,
        "low": 38500,
        "high": 90000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_80NSSC24PC077_8000_-NONE-_-NONE-",
        "note": "NASA Aug 2024 PO: MBRAUN LABstar pro SP glove box $60,303. Other federal POs $38.5K (2017) to $84.9K (2023).",
    },
    "labconco_fume_hood": {
        "value": 16560,
        "low": 12000,
        "high": 30000,
        "confidence": "datasheet",
        "source": "https://www.fishersci.com/shop/products/labconco-protector-xstream-high-performance-by-pass-hoods-6-ft-width-230v/10369110",
        "note": "Fisher 10-369-110 (6 ft, 230V) $16,560 (2026). Hood only; base cabinets, ductwork and install extra (high).",
    },
    "justrite_flammable_cabinet": {
        "value": 1873,
        "low": 1450,
        "high": 2100,
        "confidence": "datasheet",
        "source": "https://www.justrite.com/894500-45-gallon-sure-grip-ex-flammable-safety-cabinet-yellow",
        "note": "Justrite store base price $1,873 (2026); Jendco $1,591.",
    },
    # --- Readers, incubators, storage and furniture ---
    "bmg_pherastar_fsx": {
        "value": 102551,
        "low": 86120,
        "high": 158785,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75F40122F80457_7524_GS07F057DA_4732",
        "note": "FDA award 75F40122F80457 (Sep 2022): 3 PHERAstar FSX for $307,653.75 (~$102.6K each). Range: NIH 2017 basic unit $86,120; NIH 2020 2 readers with options ~$158.8K each. Vendor price is quote-only.",
    },
    "bmg_clariostar": {
        "value": 44450,
        "low": 37589,
        "high": 67055,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N98026F00453_7529_GS07F057DA_4732",
        "note": "NIH award 75N98026F00453 (Sep 2026): CLARIOstar Plus base unit, $44,450 (GSA schedule). >15 federal buys 2019-2026 span $37,589-$67,055 by configuration.",
    },
    "liconic_stx44": {
        "value": 40000,
        "low": 16400,
        "high": 60000,
        "confidence": "estimated",
        "source": "https://www.labmakelaar.eu/shop/all/saleable/ovens-incubators-and-climate/incubator/incubators/liconic-instruments-stx44-hrsa-incubators-for-robotic-integration/",
        "note": "No new price found. Source is a USED STX44-HRSA at EUR 14,000 (~$16.4K, 2026) = lower bound. $40K new is extrapolated from the comparable Thermo Cytomat 2C (NIH 2020, $44,787); close to a placeholder.",
    },
    "thermo_cytomat_2": {
        "value": 44787,
        "low": 35000,
        "high": 80000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N92020P00205_7529_-NONE-_-NONE-",
        "note": "NIH award 75N92020P00205 (Aug 2020): Cytomat 2C automated incubator, $44,787. Range is agent judgement of configuration spread.",
    },
    "generic_plate_hotel": {
        "value": 1486,
        "low": 1200,
        "high": 4000,
        "confidence": "datasheet",
        "source": "https://www.labsrobots.com/product-page/hotel-rack-side-grip",
        "note": "Online store list price EUR 1,270.40 (2026), ~$1,486 at 1.17 USD/EUR. High bound from other plate hotels plus margin.",
    },
    "compound_store": {
        "value": 3161424,
        "low": 206330,
        "high": 3500000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N95020P00654_7529_-NONE-_-NONE-",
        "note": "NIH award 75N95020P00654 (Sep 2020): SampleStore system + C18 upgrade, $3,161,424 (large library scale). Low bound: CDC 75D30119P06795 (2019) LiCONiC STX110 -20 C plate store, $206,330. Pick a small store for small labs.",
    },
    "thermo_tsx_minus80": {
        "value": 24985,
        "low": 10710,
        "high": 35150,
        "confidence": "datasheet",
        "source": "https://labproinc.com/products/ult-fz-tsx40086a-115v-60hz-tsx40086a",
        "note": "LabPro TSX40086A new $24,985 (list $26,300); model now discontinued. Federal buys $10.7-21.7K (2023-24); Fisher TSX60086RAK package $35,150.",
    },
    "thermo_lab_fridge": {
        "value": 13930,
        "low": 8000,
        "high": 18300,
        "confidence": "datasheet",
        "source": "https://www.fishersci.com/shop/products/thermo-scientific-tsx-series-high-performance-lab-refrigerators/TSX2305GA",
        "note": "Fisher list $13,930 (2026). Other resellers reportedly $8.2K-18.3K (not opened).",
    },
    "walk_in_cold_room": {
        "value": 14144,
        "low": 13000,
        "high": 60000,
        "confidence": "estimated",
        "source": "https://www.rewonline.com/restaurant-equipment-new/Nor-Lake-KLB7788-C-Walk-In-Cooler-Modular-Self-Contained/NOR-KLB7788-C.html",
        "note": "REW price $14,144 (2026), food-service grade, no installation. High ($60K) is an agent estimate for an installed lab-grade cold room with monitoring.",
    },
    "thermo_1300_bsc": {
        "value": 21480,
        "low": 15000,
        "high": 25000,
        "confidence": "datasheet",
        "source": "https://www.fishersci.com/shop/products/1300-series-class-ii-type-a2-biological-safety-cabinet-packages/13261223",
        "note": "Fisher cat. 13-261-223, stainless package with stand, $21,480 list (2026). Range is agent estimate of discounts/options.",
    },
    "lab_bench": {
        "value": 5530,
        "low": 2800,
        "high": 8000,
        "confidence": "datasheet",
        "source": "https://www.fishersci.com/shop/products/adjustable-height-basic-work-bench-leveling-glides-3/06000654",
        "note": "Fisher cat. 06-000-654, $5,530 list (2026). Range: cheaper phenolic tables to epoxy/casework (agent estimate).",
    },
    "tmc_vibration_table": {
        "value": 6155,
        "low": 6010,
        "high": 9665,
        "confidence": "datasheet",
        "source": "https://empireoptics.com/products/tmc-cleanbench-63-500-series-vibration-isolation-laboratory-table",
        "note": "Empire Optics list (2026): $6,010-6,910 smooth tops, $7,155-9,065 tapped tops. Needs compressed air/N2.",
    },
    # --- Biology: expression, harvest, lysis, purification, protein QC ---
    "infors_multitron_pro": {
        "value": 25000,
        "low": 20000,
        "high": 56000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_HHSN268201700311PC_7529_-NONE-_-NONE-",
        "note": "NIH PO 2017: Multitron Pro 25 mm incubated shaker $24,988.50. Recent single 'Multitron' orders with accessories ~$49-56K (2023-26). Pro appears superseded by current Multitron (unconfirmed).",
    },
    "sartorius_ambr250": {
        "value": 1135000,
        "low": 1000000,
        "high": 2300000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_HT942525PE019_9700_-NONE-_-NONE-",
        "note": "DHA/Walter Reed Aug 2025: one Ambr 250 HT (12-way + sampling, chiller, CIP, qualification, 1st-year service) $1,134,892. NIAID 2024: two 24-way systems $4.51M (~$2.26M each).",
    },
    "beckman_avanti_jxn26": {
        "value": 60108,
        "low": 30000,
        "high": 80000,
        "confidence": "datasheet",
        "source": "https://www.geneseesci.com/product/95-145-avanti-jxn-26-floor-centrifuge-rotor-not-included-1-centrifuge-unit/",
        "note": "Genesee Scientific online $60,107.79 (list $67,037.60), rotor not included (2026). Rotor adds ~$10-20K (agent estimate). Federal buys $32-56K (2021-23).",
    },
    "eppendorf_5810r": {
        "value": 21619,
        "low": 18224,
        "high": 22800,
        "confidence": "datasheet",
        "source": "https://www.fishersci.com/shop/products/eppendorf-5810r-centrifuge-rotor-packages-16/0540061",
        "note": "Fisher $21,619 (2026) for rotor package. Genesee: $18,224 without rotor, $22,799 with 4x750 mL rotor.",
    },
    "avestin_emulsiflex_c3": {
        "value": 34258,
        "low": 28979,
        "high": 36229,
        "confidence": "datasheet",
        "source": "https://www.fishersci.com/shop/products/emulsifx-c3-hg-pres-homogeniz/NC1538390",
        "note": "Fisher NC1538390 $34,258 (2026). Federal direct buys $28,979 (2019) to $36,229 (2026). Heat exchanger +$2,818.",
    },
    "qsonica_q700": {
        "value": 6100,
        "low": 5500,
        "high": 9201,
        "confidence": "datasheet",
        "source": "https://www.sonicator.com/products/q700-sonicator",
        "note": "Vendor online price (2026): $6,100 with standard probe, $5,500 no probe. Distributors up to ~$9.2K (not opened).",
    },
    "cytiva_akta_pure_25": {
        "value": 79873,
        "low": 44200,
        "high": 110000,
        "confidence": "datasheet",
        "source": "https://www.govsci.com/product-detail/Cytiva/29018226/EA/",
        "note": "Government Scientific Source list $79,872.87 (2026); 25 L base $44,200. Configured NIH buys $106-111K (2025).",
    },
    "cytiva_akta_avant_150": {
        "value": 190500,
        "low": 130000,
        "high": 200000,
        "confidence": "datasheet",
        "source": "https://www.govsci.com/product-detail/Cytiva/28976337/EA/",
        "note": "Government Scientific Source list $190,500 (2026). Federal buys $132-149K (2021-23).",
    },
    "revvity_labchip_gx_touch": {
        "value": 140000,
        "low": 100000,
        "high": 160000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_SPE2D620F0Q7Z_9700_SPE2DE19D0004_9700",
        "note": "DLA 2020: HT LabChip GX II Touch $153,302; CDC 2018: $134,202 (may include accessories). No public list price.",
    },
    "thermo_nanodrop_one": {
        "value": 15167,
        "low": 15167,
        "high": 19140,
        "confidence": "datasheet",
        "source": "https://www.fishersci.com/shop/products/nanodrop-ultra-31/13400603",
        "note": "Fisher NanoDrop Ultra $15,167 (2026). NanoDrop One discontinued; last Fisher price $19,140.",
    },
    "unchained_lunatic": {
        "value": 45000,
        "low": 16500,
        "high": 65000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N95019P00349_7529_-NONE-_-NONE-",
        "note": "No new price for standard Lunatic. Bounds: NIH 2019 Big Lunatic $57,647; used Lunatic EUR 14,130 (~$16.5K). $45K is agent midpoint.",
    },
    "biorad_mini_protean_tetra": {
        "value": 1568,
        "low": 1342,
        "high": 1700,
        "confidence": "datasheet",
        "source": "https://www.flinnsci.com/mini-protean-tetra-cell-for-4-handcast-or-precast-gels/fb2366/",
        "note": "Flinn Scientific (2026): Tetra cell $1,149 + PowerPac Basic $419 (https://www.flinnsci.com/powerpac-basic-power-supply/fb2564/).",
    },
    # --- Crystallography, cryo, synchrotron, and transporters (arms, rail, mobile) ---
    "sptlabtech_mosquito_xtal3": {
        "value": 95573,
        "low": 80000,
        "high": 110000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N93023P01298_7529_-NONE-_-NONE-",
        "note": "NIH/NIAID PO Sep 2023: mosquito Xtal3 plus accessories and training $95,573. NIH 2024 PO $95,137.",
    },
    "formulatrix_nt8": {
        "value": 70450,
        "low": 60000,
        "high": 100000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_75N92018P00116_7529_-NONE-_-NONE-",
        "note": "NIH/NHLBI PO May 2018: NT8 drop setter $70,450. High allows for options and inflation since 2018.",
    },
    "formulatrix_rock_imager_1000": {
        "value": 350000,
        "low": 250000,
        "high": 450000,
        "confidence": "estimated",
        "source": "https://www.usaspending.gov/award/CONT_AWD_HHSN275201400443P_7529_-NONE-_-NONE-",
        "note": "NIH PO Sep 2014: Rock Imager 1000 4 C $385,105 (optics unknown). Rock Imager 182 $240,144 (NIH 2022). $350K is an agent central figure in that range, not a quote.",
    },
    "olt_crystal_shifter": {
        "value": 13400,
        "low": 13400,
        "high": 27000,
        "confidence": "estimated",
        "source": "https://www.oxfordlabtech.com/en/crystal-shifter",
        "note": "Vendor page machine-readable offer data: GBP 9,999.99 (~$13.4K at 1.34); not shown as visible text, so possibly a web-shop placeholder. High is agent allowance for accessories/installation.",
    },
    "ln2_storage_dewar": {
        "value": 2049,
        "low": 1500,
        "high": 4000,
        "confidence": "datasheet",
        "source": "https://www.mitegen.com/product/tw35-10-cryogenic-freezer/",
        "note": "MiTeGen list $2,049 (2026). UniPuck canes/cassettes extra (in high).",
    },
    "taylor_wharton_cx100": {
        "value": 1398,
        "low": 1250,
        "high": 2500,
        "confidence": "datasheet",
        "source": "https://www.mitegen.com/product/cryo-express-dry-shipper-cx100/",
        "note": "MiTeGen list $1,398 (2026); puck shipping canes extra.",
    },
    "diamond_i04_1": {
        "value": 6320,
        "low": 4000,
        "high": 12000,
        "confidence": "estimated",
        "source": "https://www.bnl.gov/nsls2/docs/pdf/proprietaryresearchpolicyandprocedure.pdf",
        "note": "PER 8 h SHIFT, not a purchase price. PROXY: Diamond does not publish its proprietary rate; this is NSLS-II's published FY2026 full-cost-recovery rate of $790/h x 8 h. Academic access via peer review is free.",
    },
    "ur5e": {
        "value": 39083,
        "low": 32000,
        "high": 48000,
        "confidence": "datasheet",
        "source": "https://automationdistribution.com/universal-robots-ur5e/",
        "note": "Automation Distribution list $39,083 (arm, controller, pendant). US Army 2024 PO W911QX24P0135: UR5e with gripper $41,555.",
    },
    "precise_pf400": {
        "value": 30000,
        "low": 12995,
        "high": 45000,
        "confidence": "estimated",
        "source": "https://www.dotmed.com/listing/liquid-handling/brooks/preciseflex-400/4915093",
        "note": "WEAK. Source is a USED PF400 at $12,995 (Sep 2026) = lower bound. $30K new is an agent estimate (~2-2.5x used), not a quote.",
    },
    "lab_linear_rail": {
        "value": 13236,
        "low": 12626,
        "high": 18000,
        "confidence": "estimated",
        "source": "https://www.labx.com/item/precise-automation-linear-axis-rail-for-pf400-1-5m/13998109",
        "note": "New 1.5 m rail listed by a reseller on LabX $13,236; 1.0 m $12,626. High is agent estimate for 2.0 m plus install.",
    },
    "kuka_kmr_iiwa": {
        "value": 134000,
        "low": 100000,
        "high": 200000,
        "confidence": "estimated",
        "source": "https://www.newsweek.com/ai-autonomous-robot-scientist-created-1516255",
        "note": "Newsweek Jul 2020: Cooper's mobile robotic chemist (KMR iiwa + custom tooling) cost ~GBP 100,000; ~$134K at 1.34.",
    },
    "omron_ld250": {
        "value": 57191,
        "low": 55000,
        "high": 75000,
        "confidence": "estimated",
        "source": "https://www.kingbarcode.com/37222-00000",
        "note": "King Barcode $57,191 (no battery), seen via search index only; page returned 403 so not directly confirmed. Battery, fleet manager, integration push toward high.",
    },
}

# Category and capabilities each item must provide, so scraped items line up with the workflow
# templates in docs/pipelines.md. Claude may add capabilities, never drop these.
CAPABILITY_HINTS: dict[str, tuple[str, list[str]]] = {
    "opentrons_flex": ("instrument", ["liquid_handling"]),
    "opentrons_ot2": ("instrument", ["liquid_handling"]),
    "hamilton_microlab_star": ("instrument", ["liquid_handling"]),
    "tecan_fluent": ("instrument", ["liquid_handling"]),
    "beckman_biomek_i7": ("instrument", ["liquid_handling"]),
    "thermo_multidrop_combi": ("instrument", ["reagent_dispensing"]),
    "beckman_echo_650": ("instrument", ["acoustic_dispensing"]),
    "beckman_echo_525": ("instrument", ["acoustic_dispensing", "crystal_soaking"]),
    "agilent_plateloc": ("instrument", ["plate_sealing"]),
    "azenta_xpeel": ("instrument", ["plate_peeling"]),
    "bionex_hig4": ("instrument", ["centrifugation"]),
    "ika_rct_digital": ("instrument", ["heating_stirring"]),
    "mettler_quantos": ("instrument", ["powder_dosing"]),
    "chemspeed_swing_xl": ("instrument", ["powder_dosing", "liquid_dosing", "reaction", "inert_atmosphere"]),
    "chemspeed_isynth": ("instrument", ["reaction", "heating_stirring", "liquid_dosing"]),
    "unchained_big_kahuna": ("instrument", ["powder_dosing", "liquid_dosing", "reaction"]),
    "biotage_pressure_plus_96": ("instrument", ["solid_phase_extraction", "filtration"]),
    "genevac_ez2": ("instrument", ["evaporation"]),
    "genevac_ht6": ("instrument", ["evaporation"]),
    "waters_acquity_uplc_qda": ("instrument", ["lcms", "hplc"]),
    "agilent_1290_lcmsd_iq": ("instrument", ["lcms", "hplc"]),
    "mbraun_glovebox": ("furniture", ["inert_atmosphere"]),
    "labconco_fume_hood": ("furniture", ["ventilated_enclosure"]),
    "justrite_flammable_cabinet": ("storage", ["waste"]),
    "bmg_pherastar_fsx": ("instrument", ["fluorescence_read", "luminescence_read", "absorbance_read"]),
    "bmg_clariostar": ("instrument", ["absorbance_read", "fluorescence_read", "luminescence_read"]),
    "liconic_stx44": ("instrument", ["incubation", "plate_storage"]),
    "thermo_cytomat_2": ("instrument", ["incubation", "plate_storage"]),
    "generic_plate_hotel": ("storage", ["plate_storage"]),
    "compound_store": ("storage", ["compound_storage", "cold_storage"]),
    "thermo_tsx_minus80": ("storage", ["cold_storage"]),
    "thermo_lab_fridge": ("storage", ["cold_storage"]),
    "walk_in_cold_room": ("furniture", ["cold_storage"]),
    "thermo_1300_bsc": ("furniture", ["manual_bench"]),
    "lab_bench": ("furniture", ["manual_bench"]),
    "tmc_vibration_table": ("furniture", ["manual_bench"]),
    "infors_multitron_pro": ("instrument", ["cell_culture", "shaking", "incubation"]),
    "sartorius_ambr250": ("instrument", ["bioreactor", "cell_culture"]),
    "beckman_avanti_jxn26": ("instrument", ["centrifugation"]),
    "eppendorf_5810r": ("instrument", ["centrifugation"]),
    "avestin_emulsiflex_c3": ("instrument", ["cell_lysis"]),
    "qsonica_q700": ("instrument", ["cell_lysis"]),
    "cytiva_akta_pure_25": ("instrument", ["protein_purification"]),
    "cytiva_akta_avant_150": ("instrument", ["protein_purification"]),
    "revvity_labchip_gx_touch": ("instrument", ["protein_qc"]),
    "thermo_nanodrop_one": ("instrument", ["concentration_measurement"]),
    "unchained_lunatic": ("instrument", ["concentration_measurement"]),
    "biorad_mini_protean_tetra": ("instrument", ["protein_qc"]),
    "sptlabtech_mosquito_xtal3": ("instrument", ["crystallization_setup"]),
    "formulatrix_nt8": ("instrument", ["crystallization_setup"]),
    "formulatrix_rock_imager_1000": ("instrument", ["crystal_imaging", "plate_storage"]),
    "olt_crystal_shifter": ("instrument", ["crystal_harvesting"]),
    "ln2_storage_dewar": ("storage", ["cryo_cooling", "cold_storage"]),
    "taylor_wharton_cx100": ("storage", ["cold_storage"]),
    "diamond_i04_1": ("instrument", ["external_service", "xray_diffraction"]),
    "ur5e": ("transporter", ["plate_transport_arm"]),
    "precise_pf400": ("transporter", ["plate_transport_arm"]),
    "lab_linear_rail": ("transporter", ["plate_transport_rail"]),
    "kuka_kmr_iiwa": ("transporter", ["plate_transport_mobile"]),
    "omron_ld250": ("transporter", ["plate_transport_mobile"]),
}

assert VENDOR_PAGES.keys() == PRICE_REFERENCES.keys() == CAPABILITY_HINTS.keys()


def apply_price_reference(item: dict) -> dict:
    """Set price_usd_estimate and its provenance from PRICE_REFERENCES (overrides any scraped price)."""
    ref = PRICE_REFERENCES.get(item["id"])
    if ref:
        item["price_usd_estimate"] = ref["value"]
        item.setdefault("provenance", {})["price_usd_estimate"] = dict(ref)
        item.setdefault("source_urls", [])
        for url in (VENDOR_PAGES[item["id"]], ref["source"]):
            if url not in item["source_urls"]:
                item["source_urls"].append(url)
    return item

