"""Master shot list for the ORIGINAL chapter 'DNA: From Gene to Protein' (8:22, narration laid out in ../out/dna/timing.json).
Every cut sits on a sentence boundary of timing.json (the shot starts exactly where its first sentence starts); the six
section cards sit at their card_t0.  mode '3d' = Blender plate, '2d' = compositor (card / outro).  rfps = rendered fps.

STORYBOARD.  A cold open on the hero double helix turning in the navy void under the title, then (under the topic table) a
translucent cell with its purple nucleus.  Section 1 dives: through the cell membrane, up to a nuclear pore, through it into
the nucleus where the 46 chromosomes drift; one chromosome unravels into beaded chromatin and then a naked helix that runs
off to the horizon ('2 metres'), and the camera pushes into that helix.  We orbit the helix (double helix), it untwists into
a flat ladder and twists back (twisted ladder), we track along a backbone reading sugar-phosphate-sugar beads, then the
rungs; the four bases stand alone in their four colours as they are named and lettered; one nucleotide slides out of the
helix and turns; A-T and G-C sit side by side with two and three glowing hydrogen bonds while the focus racks between them;
the helix unzips and the second strand rebuilds itself base by base (complementarity); the 1953 beat is a slow orbit with a
Photo-51 X of light behind the helix and text pills; a pull-back down the axis of a very long helix for 'three billion'.
Section 2 lights a gene as a glowing segment while we dolly along the helix (then more segments for 20,000), pans across a
protein gallery (four-lobed haemoglobin with its O2, an enzyme with a substrate in its pocket, keratin coiled coils) and ends
inside the cell pushing toward the nuclear envelope wall that the instruction must cross, ribosomes waiting outside.
Section 3 is transcription on one continuous rig: RNA polymerase lands on the lit gene, opens a bubble in the helix, builds
the amber mRNA base by base (U violet where T would be), a close-up compares the template with the new strand (A -> U), the
polymerase reaches the gene end, the mRNA lets go and the helix closes, and the mRNA threads out through a nuclear pore as
the camera follows it into the cytoplasm.  Section 4 reads the message: the four letters against a chain of twenty amino
acids, triplets lit three at a time (codons), GGU -> glycine and CCU -> proline with their beads, an orbit of the 64-tile
codon wall where glycine's four tiles pulse, AUG lit green at the start, the three stop codons lit red, and a bacterium beside
a human cell sharing the same code.  Section 5 is translation on one ribosome rig: the mRNA slides into the two-subunit
ribosome (the subunits part to show small and large), a hero tRNA turns in the void (amino acid on top, anticodon below), its
anticodon pairs with a codon, Met docks on AUG, the second tRNA arrives, a peptide bond glows, the empty tRNA leaves as the
ribosome steps one codon, the chain grows codon by codon, and at UAA everything releases; a crane up reveals a field of
ribosomes at work.  Section 6 folds the chain into a globule, assembles haemoglobin's four chains around an oxygen pocket,
flips one base GAG -> GUG, swaps glutamic acid for valine, morphs a stream of red cells into sickles, returns to one base pair
on the helix, and lays out DNA -> RNA -> protein as a three-station diagram the camera dollies past.  Outro: the helix again,
then the whole dogma set in one wide orbit, then the channel outro card."""

SECTION_TITLES = ['1. Structure of DNA', '2. Genes', '3. Transcription', '4. The Genetic Code', '5. Translation', '6. From Chain to Protein']

SHOTS = [
    # ---- intro (0-30.5): cold open helix, then the cell under the topic table
    dict(id='s01', t0=0.0,    t1=13.29,  mode='3d', rfps=12, builder='cold_open'),
    dict(id='s02', t0=13.29,  t1=30.5,   mode='3d', rfps=12, builder='cell_preview'),
    dict(id='s03', t0=30.5,   t1=33.1,   mode='2d', rfps=1,  builder='card', text='1. Structure of DNA', bg='s04'),
    # ---- 1. Structure of DNA (33.1-138.94)
    dict(id='s04', t0=33.1,   t1=46.75,  mode='3d', rfps=12, builder='dive_to_chromosomes', anchors='auto'),
    dict(id='s05', t0=46.75,  t1=56.92,  mode='3d', rfps=12, builder='unravel_two_metres'),
    dict(id='s06', t0=56.92,  t1=70.04,  mode='3d', rfps=12, builder='double_helix_ladder'),
    dict(id='s07', t0=70.04,  t1=80.93,  mode='3d', rfps=12, builder='backbone_rungs', anchors='auto'),
    dict(id='s08', t0=80.93,  t1=92.39,  mode='3d', rfps=12, builder='four_bases', anchors='auto'),
    dict(id='s09', t0=92.39,  t1=100.03, mode='3d', rfps=12, builder='nucleotide', anchors='auto'),
    dict(id='s10', t0=100.03, t1=112.32, mode='3d', rfps=12, builder='pairing_rule', anchors='auto'),
    dict(id='s11', t0=112.32, t1=122.11, mode='3d', rfps=12, builder='complementary', anchors='auto'),
    dict(id='s12', t0=122.11, t1=134.0,  mode='3d', rfps=12, builder='watson_crick'),
    dict(id='s13', t0=134.0,  t1=138.94, mode='3d', rfps=12, builder='three_billion'),
    # ---- 2. Genes (141.54-183.78)
    dict(id='s14', t0=138.94, t1=141.54, mode='2d', rfps=1,  builder='card', text='2. Genes', bg='s15'),
    dict(id='s15', t0=141.54, t1=156.38, mode='3d', rfps=12, builder='gene_segment', anchors='auto'),
    dict(id='s16', t0=156.38, t1=168.81, mode='3d', rfps=12, builder='protein_gallery', anchors='auto'),
    dict(id='s17', t0=168.81, t1=183.78, mode='3d', rfps=12, builder='nucleus_barrier', anchors='auto'),
    # ---- 3. Transcription (186.38-247.44)
    dict(id='s18', t0=183.78, t1=186.38, mode='2d', rfps=1,  builder='card', text='3. Transcription', bg='s19'),
    dict(id='s19', t0=186.38, t1=196.46, mode='3d', rfps=12, builder='polymerase_lands', anchors='auto'),
    dict(id='s20', t0=196.46, t1=207.17, mode='3d', rfps=12, builder='unzip_build', anchors='auto'),
    dict(id='s21', t0=207.17, t1=225.22, mode='3d', rfps=12, builder='rna_vs_dna', anchors='auto'),
    dict(id='s22', t0=225.22, t1=238.14, mode='3d', rfps=12, builder='mrna_release', anchors='auto'),
    dict(id='s23', t0=238.14, t1=247.44, mode='3d', rfps=12, builder='pore_exit', anchors='auto'),
    # ---- 4. The Genetic Code (250.04-313.02)
    dict(id='s24', t0=247.44, t1=250.04, mode='2d', rfps=1,  builder='card', text='4. The Genetic Code', bg='s25'),
    dict(id='s25', t0=250.04, t1=262.42, mode='3d', rfps=12, builder='two_languages', anchors='auto'),
    dict(id='s26', t0=262.42, t1=273.0,  mode='3d', rfps=12, builder='codons_lit', anchors='auto'),
    dict(id='s27', t0=273.0,  t1=279.96, mode='3d', rfps=12, builder='ggu_ccu', anchors='auto'),
    dict(id='s28', t0=279.96, t1=289.85, mode='3d', rfps=12, builder='codon_wall'),
    dict(id='s29', t0=289.85, t1=297.0,  mode='3d', rfps=12, builder='start_codon', anchors='auto'),
    dict(id='s30', t0=297.0,  t1=306.54, mode='3d', rfps=12, builder='stop_codons', anchors='auto'),
    dict(id='s31', t0=306.54, t1=313.02, mode='3d', rfps=12, builder='universal_code', anchors='auto'),
    # ---- 5. Translation (315.62-399.62)
    dict(id='s32', t0=313.02, t1=315.62, mode='2d', rfps=1,  builder='card', text='5. Translation', bg='s33'),
    dict(id='s33', t0=315.62, t1=322.59, mode='3d', rfps=12, builder='ribosome_binds', anchors='auto'),
    dict(id='s34', t0=322.59, t1=330.98, mode='3d', rfps=12, builder='two_subunits', anchors='auto'),
    dict(id='s35', t0=330.98, t1=346.36, mode='3d', rfps=12, builder='trna_hero', anchors='auto'),
    dict(id='s36', t0=346.36, t1=352.27, mode='3d', rfps=12, builder='anticodon_match', anchors='auto'),
    dict(id='s37', t0=352.27, t1=361.32, mode='3d', rfps=12, builder='start_met', anchors='auto'),
    dict(id='s38', t0=361.32, t1=374.3,  mode='3d', rfps=12, builder='peptide_bond', anchors='auto'),
    dict(id='s39', t0=374.3,  t1=383.27, mode='3d', rfps=12, builder='elongation', anchors='auto'),
    dict(id='s40', t0=383.27, t1=394.46, mode='3d', rfps=12, builder='stop_release', anchors='auto'),
    dict(id='s41', t0=394.46, t1=399.62, mode='3d', rfps=12, builder='ribosome_field'),
    # ---- 6. From Chain to Protein (402.22-469.76)
    dict(id='s42', t0=399.62, t1=402.22, mode='2d', rfps=1,  builder='card', text='6. From Chain to Protein', bg='s43'),
    dict(id='s43', t0=402.22, t1=414.81, mode='3d', rfps=12, builder='chain_folds', anchors='auto'),
    dict(id='s44', t0=414.81, t1=423.99, mode='3d', rfps=12, builder='haemoglobin_pocket', anchors='auto'),
    dict(id='s45', t0=423.99, t1=435.56, mode='3d', rfps=12, builder='one_base_change', anchors='auto'),
    dict(id='s46', t0=435.56, t1=441.4,  mode='3d', rfps=12, builder='glu_to_val', anchors='auto'),
    dict(id='s47', t0=441.4,  t1=454.32, mode='3d', rfps=12, builder='sickle_cells', anchors='auto'),
    dict(id='s48', t0=454.32, t1=459.46, mode='3d', rfps=12, builder='one_base_pair', anchors='auto'),
    dict(id='s49', t0=459.46, t1=469.76, mode='3d', rfps=12, builder='central_dogma', anchors='auto'),
    # ---- outro (469.76-502.2)
    dict(id='s50', t0=469.76, t1=477.09, mode='3d', rfps=12, builder='recap_helix'),
    dict(id='s51', t0=477.09, t1=490.71, mode='3d', rfps=12, builder='recap_dogma', anchors='auto'),
    dict(id='s52', t0=490.71, t1=502.2,  mode='2d', rfps=1,  builder='outro'),
]

TOTAL = 502.2
assert abs(SHOTS[-1]['t1'] - TOTAL) < 1e-6 and all(a['t1'] == b['t0'] for a, b in zip(SHOTS[:-1], SHOTS[1:]))
