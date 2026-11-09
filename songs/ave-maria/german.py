"""Sung German (classical diction) for the score's syllables, as explicit engine syllables
(docs/language-front-ends.md, "The one format"). Each entry: "onset | nucleus | coda", segments
space-separated, IPA from the engine's inventory. r is tapped (ɾ); final -er is ɐ; ich/ach are ç/x;
ü, ö are y, ø/œ (the inventory has no ʏ); ei, au, eu are aɪ, aʊ, ɔɪ."""
SUNG = {
    "a": "|a|", "ve": "v|e|", "ma": "m|a|", "ri": "ɾ|i|", "jung": "j|ʊ|ŋ", "frau": "f ɾ|aʊ|",
    "mild": "m|ɪ|l t", "er": "|ɛ|ɾ", "hö": "h|ø|", "re": "ɾ|ə|", "ei": "|aɪ|", "ner": "n|ɐ|",
    "fle": "f l|e|", "hen": "|ə|n", "aus": "|aʊ|s", "die": "d|i|", "sem": "z|ə|m", "fel": "f|ɛ|l",
    "sen": "z|ə|n", "starr": "ʃ t|a|ɾ", "und": "|ʊ|n t", "wild": "v|ɪ|l t", "soll": "z|ɔ|l",
    "mein": "m|aɪ|n", "ge": "g|ə|", "bet": "b|e|t", "zu": "ts|u|", "dir": "d|i|ɾ", "hin": "h|ɪ|n",
    "we": "v|e|", "wir": "v|i|ɾ", "schla": "ʃ l|a|", "fen": "f|ə|n", "si": "z|ɪ|", "cher": "ç|ɐ|",
    "bis": "b|ɪ|s", "zum": "ts|ʊ|m", "mor": "m|ɔ|ɾ", "gen": "g|ə|n", "ob": "|ɔ|p", "men": "m|ɛ|n",
    "schen": "ʃ|ə|n", "noch": "n|ɔ|x", "so": "z|o|", "grau": "g ɾ|aʊ|", "sam": "z|a|m",
    "sind": "z|ɪ|n t", "o": "|o|", "sieh": "z|i|", "der": "d|e|ɾ", "sor": "z|ɔ|ɾ", "mut": "m|ʊ|t",
    "ter": "t|ɐ|", "hör": "h|ø|ɾ", "ein": "|aɪ|n", "bit": "b|ɪ|t", "tend": "t|ə|n t",
    "kind": "k|ɪ|n t", "un": "|ʊ|n", "be": "b|ə|", "fleckt": "f l|ɛ|k t", "wenn": "v|ɛ|n",
    "auf": "|aʊ|f", "fels": "f|ɛ|l s", "sin": "z|ɪ|n", "ken": "k|ə|n", "schlaf": "ʃ l|a|f",
    "uns": "|ʊ|n s", "dein": "d|aɪ|n", "schutz": "ʃ|ʊ|ts", "deckt": "d|ɛ|k t", "wird": "v|ɪ|ɾ t",
    "weich": "v|aɪ|ç", "har": "h|a|ɾ", "te": "t|ə|", "dün": "d|y|ŋ", "du": "d|u|", "lä": "l|ɛ|",
    "chelst": "ç|ə|l s t", "ro": "ɾ|o|", "düf": "d|y|f", "in": "|ɪ|n", "ser": "z|ɐ|",
    "dump": "d|ʊ|m p", "kluft": "k l|ʊ|f t", "kin": "k|ɪ|n", "des": "d|ə|s", "ne": "n|ə|",
    "ruft": "ɾ|u|f t", "rei": "ɾ|aɪ|", "magd": "m|a|k t", "de": "d|ə|", "luft": "l|ʊ|f t",
    "dä": "d|ɛ|", "mo": "m|o|", "nen": "n|ə|n", "von": "f|ɔ|n", "dei": "d|aɪ|", "nes": "n|ə|s",
    "au": "|aʊ|", "ges": "g|ə|s", "huld": "h|ʊ|l t", "ver": "f|ɛ|ɾ", "jagt": "j|a|k t",
    "sie": "z|i|", "kön": "k|œ|n", "hier": "h|i|ɾ", "nicht": "n|ɪ|ç t", "bei": "b|aɪ|",
    "woh": "v|o|", "woll'n": "v|ɔ|l n", "still": "ʃ t|ɪ|l", "dem": "d|e|m", "schick": "ʃ|ɪ|k",
    "sal": "z|a|l", "beu": "b|ɔɪ|", "da": "d|a|", "heil'": "h|aɪ|l", "ger": "g|ɐ|",
    "trost": "t ɾ|o|s t", "an": "|a|n", "weht": "v|e|t", "wol": "v|ɔ|l", "le": "l|ə|",
    "hold": "h|ɔ|l t", "dich": "d|ɪ|ç", "nei": "n|aɪ|", "das": "d|a|s", "für": "f|y|ɾ",
    "den": "d|e|n", "va": "f|a|", "fleht": "f l|e|t",
}
PUNCT = ",.!;:"


def syllable(text, word_end):
    """a score syllable ("Hö", "a!", "heil'") -> the engine's Syllable JSON"""
    bare = text.strip(PUNCT)
    on, nuc, co = (x.split() for x in SUNG[bare.lower()].split("|"))
    weak = nuc[0] in ("ə", "ɐ")
    seg = lambda s: {"ipa": s, "stress": 0}
    return {"text": bare, "onset": [seg(s) for s in on], "nucleus": {"ipa": nuc[0], "stress": 0 if weak else 1},
            "coda": [seg(s) for s in co], "wordEnd": word_end, "phraseEnd": any(c in PUNCT for c in text)}


def melisma(prev):
    """a note that carries the previous syllable's vowel on (its coda waits for the last such note)"""
    return {"text": "~", "onset": [], "nucleus": dict(prev["nucleus"]), "coda": [], "melisma": True,
            "wordEnd": prev["wordEnd"], "phraseEnd": False}
