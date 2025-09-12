"""
Normalization Pipeline - Volledig Herschreven Pipeline
-------------------------------------------------------
Werkende normalisatie-pipeline met protected words + preprocessing
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re

# ==========================
# Datatypes & Result object
# ==========================

@dataclass
class NormalizationResult:
    normalized_text: str
    language: str = "nl"
    debug: Dict[str, Any] = None

# ==========================
# Utilities & Helpers
# ==========================

_NUMERIC_RE = re.compile(r"^\d+(?:[.,]\d+)?%?$")
# 1) Algemeen paar 1..4 + 1..8, maar niet als er al 'element ' vóór staat
_ELEMENT_SIMPLE_RE = re.compile(
    r"(?<!\belement\s)\b([1-4])\s*[\- ,]?\s*([1-8])\b",
    re.IGNORECASE
)
_ELEMENT_LIST_FIX_RE = re.compile(r"\belement\s+([1-4])\s*[, ]\s*([1-8])\b", re.IGNORECASE)
# 2) Binnen element-context: 'element 1 4' / 'element 1-4' / 'element 14'
_ELEMENT_WITH_PREFIX_RE = re.compile(r"\belement\s+([1-4])\s*[, \-]?\s*([1-8])\b", re.IGNORECASE)
# 3) Dental context with prefix patterns: 'tand 1 4' / 'kies 1-4' → 'tand 14'
_DENTAL_WITH_PREFIX_RE = re.compile(r"\b(tand|kies|molaar|premolaar)\s+([1-4])\s*[, \-]?\s*([1-8])\b", re.IGNORECASE)
# 4) 'de 11' / 'de element 1-1' → 'element 11'  
_DE_ELEMENT_RE = re.compile(r"\bde\s+(?:element\s+)?([1-4])\s*[, \-]?\s*([1-8])\b", re.IGNORECASE)
# 5) General patterns (element parsing only for now) 
# Note: Complex negative lookbehind removed due to variable width limitations

# --------------------------
# Protected Words Guard
# --------------------------

class ProtectedWordsGuard:
    START = "\uFFF0"
    END = "\uFFF1"

    def __init__(self, protected_words: list[str] | None):
        self.words = [w for w in (protected_words or []) if isinstance(w, str) and w.strip()]
        if self.words:
            alt = "|".join(sorted(map(re.escape, self.words), key=len, reverse=True))
            self.rx = re.compile(rf"\b(?:{alt})\b(?=[,.;:!?)\]]|$)", re.IGNORECASE)
        else:
            self.rx = None

    def wrap(self, text: str) -> str:
        if not self.rx:
            return text
        return self.rx.sub(lambda m: f"{self.START}{m.group(0)}{self.END}", text)

    def unwrap(self, text: str) -> str:
        return text.replace(self.START, "").replace(self.END, "")

    def split_segments(self, text: str) -> list[tuple[bool, str]]:
        parts: list[tuple[bool, str]] = []
        i = 0
        while i < len(text):
            s = text.find(self.START, i)
            if s == -1:
                parts.append((False, text[i:]))
                break
            if s > i:
                parts.append((False, text[i:s]))
            e = text.find(self.END, s + len(self.START))
            if e == -1:
                parts.append((False, text[s:]))
                break
            parts.append((True, text[s + len(self.START):e]))
            i = e + len(self.END)
        return parts

# ==========================
# Default Components
# ==========================

class DefaultTokenizer:
    _SEP_RE = re.compile(r"(\s+|[.,;:/!?()\[\]{}\-])")

    def tokenize(self, text: str) -> List[str]:
        parts: List[str] = []
        idx = 0
        for m in self._SEP_RE.finditer(text):
            if m.start() > idx:
                parts.append(text[idx:m.start()])
            parts.append(m.group(0))
            idx = m.end()
        if idx < len(text):
            parts.append(text[idx:])
        return parts

    def detokenize(self, tokens: Iterable[str]) -> str:
        return "".join(tokens)

class DefaultElementParser:
    def __init__(self, valid_elements: Iterable[str] | None = None):
        if valid_elements is None:
            valid_elements = [f"{a}{b}" for a in range(1, 5) for b in range(1, 9)]
        self.valid = set(valid_elements)
        self.word2digit = {
            "één": "1", "een": "1",
            "twee": "2", "drie": "3", "vier": "4",
            "vijf": "5", "zes": "6", "zeven": "7", "acht": "8",
        }

    def parse(self, text: str) -> str:
        # 0) 'element 1, 2' → 'element 12' (list-fix) — lambda i.p.v. backrefs
        text = _ELEMENT_LIST_FIX_RE.sub(lambda m: f"element {m.group(1)}{m.group(2)}", text)

        # 1) 'de 11' / 'de element 1-1' → 'element 11'
        text = _DE_ELEMENT_RE.sub(lambda m: f"element {m.group(1)}{m.group(2)}", text)

        # 2) Dental-context: 'element/tand/kies/molaar/premolaar een vier' → '... 1 4'
        def _dental_words_to_digits(m: re.Match) -> str:
            context, a, b = m.group(1), m.group(2), m.group(3)
            da = self.word2digit.get(a.lower(), a)
            db = self.word2digit.get(b.lower(), b)
            return f"{context} {da} {db}"
        text = re.sub(r"\b(element|tand|kies|molaar|premolaar)\s+([A-Za-zéÉ]+)\s+([A-Za-zéÉ]+)\b",
                      _dental_words_to_digits, text, flags=re.IGNORECASE)

        # 3) Binnen element-context paren samenvoegen: 'element 1 4' / 'element 1-4' → 'element 14'
        text = _ELEMENT_WITH_PREFIX_RE.sub(lambda m: f"element {m.group(1)}{m.group(2)}", text)

        # 4) Binnen dental-context paren samenvoegen: 'tand 1 4' / 'kies 1-4' → 'tand 14' 
        text = _DENTAL_WITH_PREFIX_RE.sub(lambda m: f"{m.group(1)} {m.group(2)}{m.group(3)}", text)

        # 5) Algemene paren (buiten context), maar check eerst of er al dental context is
        def _repl_simple(m: re.Match) -> str:
            # Check if this match is preceded by dental context words
            start_pos = m.start()
            if start_pos > 0:
                # Look backwards for dental context words (fixed width lookbehind workaround)
                preceding_text = text[max(0, start_pos-20):start_pos]
                if re.search(r"\b(element|tand|kies|molaar|premolaar)\s*$", preceding_text, re.IGNORECASE):
                    return m.group(0)  # Don't modify if in dental context
            
            nn = f"{m.group(1)}{m.group(2)}"
            return f"element {nn}" if nn in self.valid else m.group(0)
        return _ELEMENT_SIMPLE_RE.sub(_repl_simple, text)

class DefaultLearnableNormalizer:
    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None):
        self.compiled: List[Tuple[re.Pattern, str]] = []
        for r in rules or []:
            pat, rep, flags = r.get("pattern"), r.get("replace", ""), r.get("flags", "")
            f = re.IGNORECASE if "i" in flags else 0
            if pat:
                self.compiled.append((re.compile(pat, f), rep))

    def apply(self, text: str) -> str:
        out = text
        for rx, rep in self.compiled:
            out = rx.sub(rep, out)
        return out

class DefaultVariantGenerator:
    def __init__(self, config: Dict[str, Any] | None, lexicon_data: Dict[str, Any] | None):
        cfg = config or {}
        self.separators: List[str] = list(cfg.get("separators", ["-", " ", ",", ";", "/"]))
        self.element_separators: List[str] = list(cfg.get("element_separators", ["-", " ", ",", ";", "/"]))
        self.digit_words: Dict[str, str] = dict(cfg.get("digit_words", {}))
        variants = (lexicon_data or {}).get("variants", {})
        self.variant_pairs: List[Tuple[re.Pattern, str]] = [
            (re.compile(re.escape(k), re.IGNORECASE), v) for k, v in sorted(variants.items(), key=lambda kv: -len(kv[0]))
        ]

    def _replace_digit_words(self, text: str) -> str:
        t = text
        # 1) Één met accent is eenduidig numeriek
        t = re.sub(r"\b[Éé]én\b", "1", t)

        # 2) 'een' alleen in numerieke context omzetten
        #    a) 'dental_context een' -> 'dental_context 1'
        t = re.sub(r"(?i)\b(element|tand|kies|molaar|premolaar)\s+een\b", r"\1 1", t)

        #    b) '... digit SEP een' -> '... digit SEP 1'  en  'een SEP digit' -> '1 SEP digit'
        seps = self.element_separators or ["-", " ", ",", ";", "/"]
        sep_class = re.escape("".join(ch for ch in seps if ch != " "))
        t = re.sub(rf"(?i)(\b[1-9]\b)\s*([{sep_class}])\s*\been\b", r"\1\2 1", t)
        t = re.sub(rf"(?i)\been\b\s*([{sep_class}])\s*(\b[1-9]\b)", r"1\1 \2", t)

        # 3) Overige digit_words (bewust zonder 'een'/'één' hier)
        for w, d in self.digit_words.items():
            if w.lower() in ("een", "één"):
                continue
            t = re.sub(rf"\b{re.escape(w)}\b", d, t, flags=re.IGNORECASE)

        return t

    def _space_separators_between_digits(self, text: str, separators: List[str]) -> str:
        """Ensure consistent spacing around separators between digits"""
        t = text
        for sep in separators:
            if sep != " ":
                # Pattern: digit + optional spaces + separator + optional spaces + digit
                # Replace with: digit + space + separator + space + digit
                pattern = rf"(\b[1-9]\b)\s*{re.escape(sep)}\s*(\b[1-9]\b)"
                replacement = rf"\1 {sep} \2"
                t = re.sub(pattern, replacement, t)
        return t

    def generate(self, text: str) -> str:
        t = self._replace_digit_words(text)
        t = self._space_separators_between_digits(t, self.element_separators)
        for rx, rep in self.variant_pairs:
            t = rx.sub(rep, t)
        return t

class DefaultPhoneticMatcher:
    def __init__(self, lexicon_data: Dict[str, Any] | None, tokenizer: DefaultTokenizer, threshold: float = 0.84):
        self.tokenizer = tokenizer
        self.threshold = threshold
        canonicals: List[str] = []
        if lexicon_data:
            if isinstance(lexicon_data.get("canonicals"), list):
                canonicals = list(lexicon_data.get("canonicals"))
            elif isinstance(lexicon_data.get("lexicon"), dict):
                canonicals = list(lexicon_data.get("lexicon").keys())
        self.canonicals = sorted(set(canonicals), key=str.lower)

    def match(self, text: str) -> str:
        tokens = self.tokenizer.tokenize(text)
        out: List[str] = []
        for tok in tokens:
            raw = tok.strip()
            if not raw or _NUMERIC_RE.match(raw) or all(ch in ",.;:/!?()-[]{}" for ch in raw):
                out.append(tok)
                continue
            best_c, best_s = None, -1.0
            for c in self.canonicals:
                s = 1.0 - (abs(len(raw) - len(c)) / max(len(raw), len(c)))
                if s > best_s:
                    best_s, best_c = s, c
            if best_c and best_s >= self.threshold:
                rep = best_c.title() if raw.istitle() else best_c.upper() if raw.isupper() else best_c
                out.append(rep)
            else:
                out.append(tok)
        return self.tokenizer.detokenize(out)

class DefaultPostProcessor:
    def apply(self, text: str) -> str:
        t = re.sub(r"\s+([,;:])", r"\1", text)
        t = re.sub(r"([(/\[])\s+", r"\1", t)
        t = re.sub(r"\s+([)\]/])", r"\1", t)  # let op: gebruik 't', niet 'text'
        t = re.sub(r"\s{2,}", " ", t)
        # Dedupe oude-stijl: 'element NN element NN' → 'element NN'
        t = re.sub(r'\b(element\s+[1-4][1-8])\s+\1\b', r'\1', t, flags=re.IGNORECASE)
        # 'de element ' → 'element ' (oude flow)
        t = t.replace(" de element ", " element ")
        if t.startswith("de element "):
            t = t[3:]
        return t.strip()

# ==========================
# De Pipeline zelf
# ==========================

class NormalizationPipeline:
    def __init__(self, lexicon_data: Optional[Dict[str, Any]] = None, config: Optional[Dict[str, Any]] = None, *, tokenizer: Optional[DefaultTokenizer] = None):
        self.config = config or {}
        self.lexicon = lexicon_data or {}
        self.tokenizer = tokenizer or DefaultTokenizer()
        self.element_parser = DefaultElementParser()
        self.learnable = DefaultLearnableNormalizer(self.lexicon.get("learnable_rules") or self.config.get("learnable_rules"))
        self.variant_generator = DefaultVariantGenerator(self.config.get("variant_generation"), self.lexicon)
        phon_cfg = self.config.get("phonetic", {})
        self.phonetic_matcher = DefaultPhoneticMatcher(self.lexicon, self.tokenizer, float(phon_cfg.get("threshold", 0.84)))
        self.postprocessor = DefaultPostProcessor()
        self.protected_words = self.lexicon.get("protected_words") or self.config.get("protected_words") or []
        self.guard = ProtectedWordsGuard(self.protected_words)
        self.flags = {
            "enable_element_parsing": True,
            "enable_learnable": True,
            "enable_variant_generation": True,
            "enable_phonetic_matching": True,
            "enable_post_processing": True,
        }
        self.flags.update(self.config.get("normalization", {}))

    def _apply_on_unprotected(self, text: str, fn: callable) -> str:
        segments = self.guard.split_segments(text)
        out = []
        for is_prot, seg in segments:
            out.append(seg if is_prot else fn(seg))
        return "".join(out)

    def normalize(self, text: str, language: str = "nl") -> NormalizationResult:
        dbg: Dict[str, Any] = {"language": language, "input": text}
        current = self.guard.wrap(text)
        current = current.replace("\u00A0", " ")  # NBSP → spatie
        dbg["protected_wrap"] = current
        if self.flags.get("enable_element_parsing", True):
            current = self._apply_on_unprotected(current, self.element_parser.parse)
            dbg["elements"] = current
        if self.flags.get("enable_learnable", True):
            current = self._apply_on_unprotected(current, self.learnable.apply)
            dbg["learnable"] = current
        if self.flags.get("enable_variant_generation", True):
            current = self._apply_on_unprotected(current, self.variant_generator.generate)
            dbg["variants"] = current
        if self.flags.get("enable_phonetic_matching", True):
            current = self._apply_on_unprotected(current, self.phonetic_matcher.match)
            dbg["phonetic"] = current
        if self.flags.get("enable_post_processing", True):
            current = self.postprocessor.apply(current)
            dbg["post"] = current
        current = self.guard.unwrap(current)
        dbg["unwrapped"] = current
        return NormalizationResult(normalized_text=current, language=language, debug=dbg)