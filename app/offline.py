"""Rule-based fallback used when LLM_PROVIDER=offline.

It only fixes common, predictable mistakes (spelling, text-speak, missing apostrophes,
capital letters, spacing). For real rewriting and explanations, use an AI provider.
"""
from __future__ import annotations

import re
from collections import Counter

SPELLING = {
    "teh": "the", "recieve": "receive", "definately": "definitely", "seperate": "separate",
    "occured": "occurred", "untill": "until", "tommorow": "tomorrow", "tomorow": "tomorrow",
    "becuase": "because", "beacuse": "because", "wich": "which", "thier": "their", "alot": "a lot",
    "freind": "friend", "beleive": "believe", "adress": "address", "accomodate": "accommodate",
    "acheive": "achieve", "goverment": "government", "enviroment": "environment", "truely": "truly",
    "wierd": "weird", "neccessary": "necessary", "necesary": "necessary", "begining": "beginning",
    "calender": "calendar", "sucess": "success", "succesful": "successful", "intrested": "interested",
    "knowlege": "knowledge", "oppurtunity": "opportunity", "opportunty": "opportunity",
    "experiance": "experience", "responce": "response", "writting": "writing", "comming": "coming",
    "geting": "getting", "studing": "studying", "minuts": "minutes", "wether": "whether",
    "assigment": "assignment", "assignmet": "assignment", "mam": "ma'am", "maam": "ma'am",
    "attendence": "attendance","exm": "exam", "sylabus": "syllabus",
}

TEXT_SPEAK = {
    "u": "you", "ur": "your", "r": "are", "pls": "please", "plz": "please", "thx": "thanks",
    "tnx": "thanks", "msg": "message", "coz": "because", "cuz": "because", "bcz": "because",
    "bcoz": "because", "b4": "before", "gr8": "great", "tmrw": "tomorrow", "tmr": "tomorrow",
    "abt": "about", "wid": "with", "nd": "and", "n": "and", "frnd": "friend", "frnds": "friends",
    "plzz": "please", "sry": "sorry", "srry": "sorry", "ppl": "people", "bday": "birthday",
}

APOSTROPHE = {
    "dont": "don't", "cant": "can't", "wont": "won't", "didnt": "didn't", "doesnt": "doesn't",
    "isnt": "isn't", "wasnt": "wasn't", "werent": "weren't", "havent": "haven't", "hasnt": "hasn't",
    "im": "I'm", "ive": "I've", "youre": "you're", "theyre": "they're", "thats": "that's",
    "whats": "what's", "couldnt": "couldn't", "shouldnt": "shouldn't", "wouldnt": "wouldn't",
    "arent": "aren't",
}

FORMAL = {
    "don't": "do not", "can't": "cannot", "won't": "will not", "didn't": "did not",
    "doesn't": "does not", "isn't": "is not", "wasn't": "was not", "weren't": "were not",
    "haven't": "have not", "hasn't": "has not", "i'm": "I am", "i've": "I have", "i'll": "I will",
    "i'd": "I would", "you're": "you are", "they're": "they are", "it's": "it is", "that's": "that is",
    "couldn't": "could not", "shouldn't": "should not", "wouldn't": "would not", "aren't": "are not",
    "wanna": "want to", "gonna": "going to", "gotta": "have to", "yeah": "yes", "hey": "hello",
    "hi": "hello", "thanks": "thank you", "ok": "okay", "kindly": "please",
}

TIPS = {
    "spelling": "Turn on spell-check in your keyboard or email app - it catches most of these.",
    "word_choice": "Avoid chat short forms like 'u' or 'pls' outside quick messages to friends.",
    "punctuation": "Words like don't and can't always need an apostrophe (').",
    "capitalization": "Start every sentence - and the word 'I' - with a capital letter.",
    "tone": "In formal writing, use full forms (I am, do not) and polite words like 'please' and 'thank you'.",
    "other": "Read your message once aloud before sending - you will hear most mistakes.",
}

WORD_RE = re.compile(r"[A-Za-z0-9'’]+")


def _match_case(original: str, new: str) -> str:
    if original[:1].isupper() and new[:1].islower():
        return new[:1].upper() + new[1:]
    return new


def rule_based_refine(text: str, tone: str) -> dict:
    corrections: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(original: str, corrected: str, kind: str, explanation: str) -> None:
        key = (original.lower(), corrected.lower())
        if key not in seen:
            seen.add(key)
            corrections.append({"original": original, "corrected": corrected,
                                "type": kind, "explanation": explanation})

    def fix_word(m: re.Match) -> str:
        word = m.group(0)
        low = word.lower().replace("’", "'")
        new = word
        if low in SPELLING:
            new = _match_case(word, SPELLING[low])
            add(word, new, "spelling", f'"{word}" is spelled "{new}".')
        elif low in TEXT_SPEAK:
            new = _match_case(word, TEXT_SPEAK[low])
            add(word, new, "word_choice", "Write the full word instead of a chat short form.")
        elif low in APOSTROPHE:
            new = _match_case(word, APOSTROPHE[low])
            add(word, new, "punctuation", "This short form needs an apostrophe (').")
        elif word == "i":
            new = "I"
            add(word, new, "capitalization", 'The word "I" is always a capital letter.')

        if tone == "formal":
            key = new.lower().replace("’", "'")
            if key in FORMAL:
                formal = _match_case(new, FORMAL[key])
                add(new, formal, "tone", "The full or more polite form sounds more professional.")
                new = formal
        return new

    out = WORD_RE.sub(fix_word, text)

    spaced = re.sub(r"[ \t]{2,}", " ", out)
    spaced = re.sub(r"[ \t]+([,.!?;:])", r"\1", spaced)
    spaced = re.sub(r"([,;!?])(?=[A-Za-z])", r"\1 ", spaced)
    if spaced != out:
        add("", "Spacing around punctuation", "punctuation",
            "Put no space before , . ! ? and one space after them.")
    out = spaced

    if tone == "formal":
        calm = re.sub(r"([!?])\1+", r"\1", out)
        if calm != out:
            add("", "One ! or ? is enough", "tone", "Use a single ! or ? in formal writing.")
        out = calm

    capped = re.sub(r"(^\s*|[.!?]\s+|\n\s*)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    if capped != out:
        add("", "Capital letter at sentence start", "capitalization",
            "Start each sentence with a capital letter.")
    out = capped

    stripped = out.rstrip()
    if stripped and stripped[-1].isalnum():
        out = stripped + "."
        add("", "Full stop at the end", "punctuation", "End the sentence with a full stop.")

    top = Counter(c["type"] for c in corrections).most_common(1)
    tip = TIPS[top[0][0]] if top else "Looks good! Offline mode only checks common mistakes."
    return {"refined": out, "corrections": corrections, "tip": tip}
