"""
Normalization Pipeline - Volledig Herschreven Pipeline
-------------------------------------------------------
Werkende normalisatie-pipeline met protected words + preprocessing
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re
import unicodedata
try:
    from app.ai.normalization.core.phonetic_matcher import DutchPhoneticMatcher
    from app.ai.normalization.learnable import DentalNormalizerLearnable
except Exception:
    from normalization.core.phonetic_matcher import DutchPhoneticMatcher
    from normalization.learnable import DentalNormalizerLearnable

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
# Unit guard: detect units that follow numbers (prevent element conversion for measurements)
_UNIT_AFTER_RE = re.compile(r'^\\s*(mm|cm|m|ml|mg|g|kg|µm|μm|um|%|°c|°f|week|weken|maand|maanden|jaar|jaren|dag|dagen|uur|u|minuut|minuten|min|seconde|seconden|sec)\\b', re.IGNORECASE)
# 1) Algemeen paar 1..4 + 1..8, maar niet als er al 'element ' vóór staat
_ELEMENT_SIMPLE_RE = re.compile(
    r"(?<!\belement\s)\b([1-4])\s*(?:-\s*|,\s+|\s+)?([1-8])\b(?!\s*,\s*[1-8]\b)",
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


# --- gedeelde token-aware vervanger (voor variants & custom patterns) ---
class TokenAwareReplacer:
    """
    Eén engine voor literal en regex vervangingen:
    - literal 'src' → token-aware (spatie of '-'), met trailing punct preserve
    - regex 'pattern' → gebruikt zoals aangeleverd; optioneel punct-preserve via named group (?P<_p>...)
    """
    def __init__(self, rules: list[dict] | dict | None, *, literal_key="src", dst_key="dst",
                 regex_key="pattern", flags_key="flags", preserve_key="preserve_punct",
                 sort_longest_first: bool = True):
        self._re = re
        self.compiled: list[tuple[re.Pattern, str, bool]] = []
        if not rules:
            return
        # mapping {k:v} → [{"src":k,"dst":v}, ...]
        if isinstance(rules, dict):
            rules = [{"src": k, "dst": v} for k, v in rules.items()]
        # sorteer langste eerst (en meest woorden)
        if sort_longest_first:
            def _key(r):
                s = r.get(literal_key) or r.get(regex_key) or ""
                return (-len(str(s)), -(len(str(s).split())))
            rules = sorted(rules, key=_key)
        for r in rules:
            # (1) regexregel
            if isinstance(r.get(regex_key), str):
                flags = r.get(flags_key, "")
                f = self._re.IGNORECASE if "i" in str(flags).lower() else 0
                try:
                    rx = self._re.compile(r[regex_key], f)
                except self._re.error:
                    continue
                dst = str(r.get("replace", r.get(dst_key, "")))
                preserve = bool(r.get(preserve_key, False))
                self.compiled.append((rx, dst, preserve))
                continue
            # (2) literal 'src'
            if isinstance(r.get(literal_key), str):
                rx = self._compile_literal(r[literal_key])
                dst = str(r.get(dst_key, ""))
                self.compiled.append((rx, dst, True))
                continue

    @staticmethod
    def _flex_gap() -> str:
        # spaties of koppelteken (incl. extra spaties rondom '-')
        return r"(?:\s*-\s*|\s+)"

    def _compile_literal(self, src: str) -> re.Pattern:
        s = (src or "").strip()
        if not s:
            return self._re.compile(r"(?!x)")
        toks = s.split()
        if len(toks) == 1:
            return self._re.compile(rf"(?i)\b{self._re.escape(s)}\b([^\w\s\-\/]*)")
        body = self._flex_gap().join(self._re.escape(t) for t in toks)
        return self._re.compile(rf"(?i)\b{body}\b([^\w\s\-\/]*)")

    @staticmethod
    def _suffix_from_match(m: re.Match) -> str:
        if "_p" in m.re.groupindex:
            return m.group("_p") or ""
        try:
            return (m.group(m.lastindex) or "") if m.lastindex else ""
        except IndexError:
            return ""

    def apply(self, text: str) -> str:
        out = text
        for rx, dst, preserve in self.compiled:
            if preserve:
                out = rx.sub(lambda m: f"{dst}{self._suffix_from_match(m)}", out)
            else:
                out = rx.sub(dst, out)
        return out
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
            self.rx = re.compile(rf"\b(?:{alt})\b", re.IGNORECASE)
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

        # 5) First protect units by temporarily replacing them
        # This prevents patterns like "12 %" from being parsed as element patterns
        protected_text = text
        unit_protection_map = {}
        unit_counter = 0
        
        def protect_unit(match):
            nonlocal unit_counter
            placeholder = f"〔UNIT{unit_counter}〕"
            unit_protection_map[placeholder] = match.group(0)
            unit_counter += 1
            return placeholder
        
        # Protect number-unit patterns (includes all units from _UNIT_AFTER_RE)
        protected_text = re.sub(r'(\d+)\s+(mm|cm|m|ml|mg|g|kg|µm|μm|um|%|°c|°f|week|weken|maand|maanden|jaar|jaren|dag|dagen|uur|u|minuut|minuten|min|seconde|seconden|sec)(?=\s|$)', 
                               protect_unit, protected_text, flags=re.IGNORECASE)
        
        # 6) Algemene paren (buiten context), maar check eerst of er al dental context is
        def _repl_simple(m: re.Match) -> str:
            # Check if this match is preceded by dental context words
            start_pos = m.start()
            if start_pos > 0:
                # Look backwards for dental context words (fixed width lookbehind workaround)
                preceding_text = text[max(0, start_pos-20):start_pos]
                if re.search(r"\b(element|tand|kies|molaar|premolaar)\s*$", preceding_text, re.IGNORECASE):
                    return m.group(0)  # Don't modify if in dental context
            
            # Unit protection now happens earlier in step 5, so no need to check here

            nn = f"{m.group(1)}{m.group(2)}"
            return f"element {nn}" if nn in self.valid else m.group(0)
        
        # Apply element parsing on protected text
        result = _ELEMENT_SIMPLE_RE.sub(_repl_simple, protected_text)
        
        # Restore protected units
        for placeholder, original in unit_protection_map.items():
            result = result.replace(placeholder, original)
            
        return result

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

class DefaultCustomPatternNormalizer:
    def __init__(self, patterns=None, preserve_punctuation=True):
        # Accept dict formats from Supabase or list of rules
        rules = []
        if isinstance(patterns, dict):
            # Supabase style: direct_mappings + multi_word_mappings
            dm = patterns.get('direct_mappings', {}) if patterns else {}
            mw = patterns.get('multi_word_mappings', {}) if patterns else {}
            if isinstance(dm, dict):
                for k, v in dm.items():
                    rules.append({'src': k, 'dst': v})
            if isinstance(mw, dict):
                for k, v in mw.items():
                    rules.append({'src': k, 'dst': v})
        elif isinstance(patterns, list):
            # Already rule-like entries (may contain 'pattern')
            rules = patterns
        elif patterns:
            # Treat as simple mapping
            try:
                for k, v in dict(patterns).items():
                    rules.append({'src': k, 'dst': v})
            except Exception:
                rules = []
        self._replacer = TokenAwareReplacer(rules)

    def apply(self, text: str) -> str:
        return self._replacer.apply(text)

class DefaultVariantGenerator:
    def __init__(self, config: Dict[str, Any] | None, lexicon_data: Dict[str, Any] | None):
        cfg = config or {}
        self.separators: List[str] = list(cfg.get("separators", ["-", " ", ",", ";", "/"]))
        self.element_separators: List[str] = list(cfg.get("element_separators", ["-", " ", ",", ";", "/"]))
        self.digit_words: Dict[str, str] = dict(cfg.get("digit_words", {}))
        
        # Debug: Check what variants are being loaded
        config_variants = (config or {}).get('variants', {})
        lexicon_variants = (lexicon_data or {}).get('variants', {})
        
        # Log the variants we're getting
        if 'bot verlies' in config_variants:
            print(f"[DEBUG] Found 'bot verlies' in config variants: {config_variants['bot verlies']}")
        if 'bot verlies' in lexicon_variants:
            print(f"[DEBUG] Found 'bot verlies' in lexicon variants: {lexicon_variants['bot verlies']}")
            
        variants = {**config_variants, **lexicon_variants}
        
        # Log total variants loaded
        print(f"[DEBUG] DefaultVariantGenerator loaded {len(variants)} variants")
        if 'bot verlies' in variants:
            print(f"[DEBUG] ✅ 'bot verlies' → '{variants['bot verlies']}' mapping loaded")
        else:
            print(f"[DEBUG] ❌ 'bot verlies' NOT in variants")
            # Show first few variants as sample
            if variants:
                sample = list(variants.items())[:5]
                print(f"[DEBUG] Sample variants: {sample}")
        
        # Gebruik gedeelde engine - IMPORTANT: TokenAwareReplacer expects the SOURCE (what to match) as the key
        # But Supabase stores it as "bot verlies" → "botverlies" where the key is what we want to match
        # So we DON'T need to reverse, the mapping is already correct
        self._replacer = TokenAwareReplacer(variants)

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
            if sep not in (' ', '-'):
                # Pattern: digit + optional spaces + separator + optional spaces + digit
                # Replace with: digit + space + separator + space + digit
                pattern = rf"(\b[1-9]\b)\s*{re.escape(sep)}\s*(\b[1-9]\b)"
                replacement = rf"\1 {sep} \2"
                t = re.sub(pattern, replacement, t)
        return t

    def generate(self, text: str) -> str:
        t = self._replace_digit_words(text)
        # TEMPORARILY COMMENTED OUT FOR TESTING - adds spaces around commas between digits
        # t = self._space_separators_between_digits(t, self.element_separators)
        t = self._replacer.apply(t)
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
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional postprocessing configuration
        
        Args:
            config: Dict with postprocessing options:
                - remove_exclamations: bool (default False)
                - remove_question_marks: bool (default False)
                - remove_semicolons: bool (default False)
                - remove_trailing_dots: bool (default False)
                - remove_trailing_word_commas: bool (default False)
        """
        self.config = config or {}
        
    def apply(self, text: str) -> str:
        t = re.sub(r"\s+([,;:])", r"\1", text)
        t = re.sub(r"([(/\[])\s+", r"\1", t)
        t = re.sub(r"\s+([)\]/])", r"\1", t)  # let op: gebruik 't', niet 'text'
        # Collapse spaces around hyphens in numeric ranges: '1 - 4' -> '1-4'
        t = re.sub(r'(?<=\d)\s*-\s*(?=\d)', '-', t)
        t = re.sub(r"\s{2,}", " ", t)
        
        
        # Remove ! and sentence dots (but keep decimal/thousand separators)
        t = re.sub(r"\s{2,}", " ", t)
# Unit compaction: remove spaces between numbers and units
        # Symbolic units (% and temperature units)
        t = re.sub(r'(?<=\d)\s+(?=(?:%|‰|°c|°f))', '', t, flags=re.IGNORECASE)
        # Alphabetic units (mm, cm, mg, etc.)
        t = re.sub(r'(?i)(?<=\d)\s+(?=(?:mm|cm|m|ml|mg|g|kg|µm|μm|um)\b)', '', t)
        
        # Dedupe oude-stijl: 'element NN element NN' → 'element NN'
        t = re.sub(r'\b(element\s+[1-4][1-8])\s+\1\b', r'\1', t, flags=re.IGNORECASE)
        # 'de element ' → 'element ' (oude flow)
        t = t.replace(" de element ", " element ")
        if t.startswith("de element "):
            t = t[3:]
        
        # Configurable punctuation removal with safer patterns
        
        # -- Optioneel: uitroeptekens weg --
        if self.config.get('remove_exclamations', False):
            t = t.replace("!", "")
        
        if self.config.get('remove_question_marks', False):
            t = re.sub(r'\?', '', t)
        
        if self.config.get('remove_semicolons', False):
            t = re.sub(r';', '', t)
        
        # -- Optioneel: trailing komma's weg (alleen aan EOL), spaart decimalen/lijsten --
        #   'karius,' -> 'cariës'
        #   '1,5 jaar' blijft intact; '1, 2, 3' blijft intact
        if self.config.get('remove_trailing_commas_eol', False):
            t = re.sub(r',\s*$', '', t)
        
        # -- Optioneel: zinseinde-punten weg, maar laat decimalen ('0.5') staan --
        if self.config.get('remove_sentence_dots', False):
            t = re.sub(r'(?<!\d)\.(?!\d)', '', t)
        
        # Keep existing trailing word comma removal for backwards compatibility
        if self.config.get('remove_trailing_dots', False):
            # Remove sentence-ending dots (not decimal points)
            # Only remove dots at word boundaries, not in numbers
            t = re.sub(r'(?<!\d)\.(?!\d)', '', t)
        
        if self.config.get('remove_trailing_word_commas', False):
            # Remove commas after letters when followed by space or end of string
            t = re.sub(r'(?<=[A-Za-zÀ-ÿ]),(?=\s|$)', '', t)
        
        # Final cleanup: collapse any double spaces created by punctuation removal
        t = re.sub(r'\s{2,}', ' ', t)
        
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
        # Initialize learnable normalizer (only DentalNormalizerLearnable exists now)
        self.learnable = None  # Disabled by default since DentalNormalizerLearnable requires specific config
        self.custom_patterns = DefaultCustomPatternNormalizer(self.lexicon.get("custom_patterns") or self.config.get("custom_patterns") or [])
        self.variant_generator = DefaultVariantGenerator(self.config.get("variant_generation"), self.lexicon)
        
        # Geavanceerde multi-woord matcher (zoals oude systeem) — zonder fallback
        phon_cfg = dict(self.config.get("phonetic", {}) or {})
        # Defaults zoals in het oude systeem
        phon_cfg.setdefault("threshold", 0.84)
        mw = phon_cfg.setdefault("matching", {}).setdefault("multi_word", {})
        mw.setdefault("word_veto_threshold", 0.6)
        mw.setdefault("two_word_min", 0.7)
        mw.setdefault("overall_min", 0.75)
        mw.setdefault("require_all_words", True)
        
        try:
            self.phonetic_matcher = DutchPhoneticMatcher(
                config_data=phon_cfg,
                tokenizer=self.tokenizer
            )
        except TypeError:
            # Fallback to basic initialization
            self.phonetic_matcher = DutchPhoneticMatcher(tokenizer=self.tokenizer)
        
        # Set up phonetic matching using the new normalize method with canonicals
        if hasattr(self.phonetic_matcher, 'normalize') and callable(getattr(self.phonetic_matcher, 'normalize')):
            # Create a wrapper that passes canonicals to the normalize method
            def _phonetic_normalize(text: str) -> str:
                return self.phonetic_matcher.normalize(text, self.canonicals)
            self._phonetic_call = _phonetic_normalize
        else:
            raise RuntimeError('DutchPhoneticMatcher must expose normalize(text, canonicals)')
        # Initialize postprocessor with config
        postprocess_config = self.config.get('postprocess', {})
        self.postprocessor = DefaultPostProcessor(postprocess_config)
        self.protected_words = self.lexicon.get("protected_words") or self.config.get("protected_words") or []
        self.guard = ProtectedWordsGuard(self.protected_words)
        
        # Build diacritics restoration map
        self._diacritics_restore_map = {}
        canonicals = []

        # Extract canonicals from lexicon - handle category-based structure
        if isinstance(self.lexicon.get("canonicals"), list):
            canonicals = self.lexicon["canonicals"]
        elif isinstance(self.lexicon.get("lexicon"), dict):
            canonicals = list(self.lexicon["lexicon"].keys())
        else:
            # Extract from category-based lexicon structure (pathologie, rx_findings, etc.)
            for category_name, category_data in self.lexicon.items():
                if isinstance(category_data, list):
                    # Category contains a list of terms
                    canonicals.extend(category_data)
                elif isinstance(category_data, dict):
                    # Category contains a dictionary of terms
                    canonicals.extend(category_data.keys())

        # Custom patterns are handled as transformations before fuzzy matching
        # NOT as fuzzy matching targets, so we don't add them to canonicals

        # Store canonicals for phonetic matching
        # Add variant destination values to canonicals so they're recognized as canonical
        # This prevents the phonetic matcher from trying to retokenize compound words like "botverlies"
        if lexicon_data and 'variants' in lexicon_data:
            for source, dest in lexicon_data['variants'].items():
                if isinstance(dest, str) and dest.strip():
                    canonicals.append(dest.strip())
        
        # Deduplicate and sort
        self.canonicals = sorted(set(c for c in canonicals if isinstance(c, str)), key=str.lower)
        
        # Build the map
        for canonical in canonicals:
            if isinstance(canonical, str):
                # Check if the canonical form has diacritics
                if any(unicodedata.combining(ch) for ch in unicodedata.normalize("NFD", canonical)):
                    # Create folded key (no accents, lowercase)
                    folded = "".join(ch for ch in unicodedata.normalize("NFD", canonical) 
                                   if not unicodedata.combining(ch)).lower()
                    if folded and folded != canonical.lower():
                        self._diacritics_restore_map[folded] = canonical
        
        self.flags = {
            "enable_element_parsing": True,
            "enable_learnable": True,
            "enable_custom_patterns": True,
            "enable_variant_generation": True,
            "enable_phonetic_matching": True,  # Controls whether phonetic matching is applied in the pipeline
            "enable_post_processing": True,
        }
        self.flags.update(self.config.get("normalization", {}))

    def _apply_on_unprotected(self, text: str, fn: callable) -> str:
        segments = self.guard.split_segments(text)
        out = []
        for is_prot, seg in segments:
            out.append(seg if is_prot else fn(seg))
        return "".join(out)

    def _restore_canonical_diacritics(self, text: str) -> str:
        """Restore canonical diacritics to words that lost them during processing"""
        if not hasattr(self, '_diacritics_restore_map') or not self._diacritics_restore_map:
            return text
        
        tokens = self.tokenizer.tokenize(text)
        out = []
        
        for tok in tokens:
            raw = tok.strip()
            if raw and raw.isalpha():
                # Create folded version (no accents, lowercase)
                folded = "".join(ch for ch in unicodedata.normalize("NFD", raw) 
                               if not unicodedata.combining(ch)).lower()
                
                # Check if we have a canonical form
                canonical = self._diacritics_restore_map.get(folded)
                if canonical:
                    # Preserve original casing
                    if raw.istitle():
                        out.append(canonical.title())
                    elif raw.isupper():
                        out.append(canonical.upper())
                    else:
                        out.append(canonical)
                else:
                    out.append(tok)
            else:
                out.append(tok)
        
        return self.tokenizer.detokenize(out)

    def _split_noncanonical_hyphens(self, text: str) -> str:
        """
        Split non-canonical hyphens before fuzzy matching to enable veto thresholds on individual words.
        
        This fixes issues like:
        - "vestibuleer" incorrectly matching "vestibulum" 
        - "interproximaal" incorrectly matching "intermaxillair"
        
        By splitting "licht-mucosaal" → "licht mucosaal", the veto threshold can reject 
        "licht" (score < 0.60) and prevent incorrect matches.
        
        Uses tokenizer behavior: "licht-mucosaal" → ['licht', '-', 'mucosaal']
        """
        if not text or '-' not in text:
            return text
        
        # Define canonical hyphenated terms that should keep their hyphens
        canonical_hyphenated = {
            'peri-apicaal', 'peri-apicale', 'inter-occlusaal', 'inter-occlusale',
            'supra-gingivaal', 'sub-gingivaal', 'pre-molaar', 'post-operatief',
            'extra-oraal', 'intra-oraal', 'co-morbiditeit', 're-interventie'
        }
        
        # Tokenize: "licht-mucosaal" → ['licht', '-', 'mucosaal']
        tokens = self.tokenizer.tokenize(text)
        result_tokens = []
        i = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            # Look for pattern: word + hyphen + word
            if (i + 2 < len(tokens) and 
                token.strip() and any(c.isalpha() for c in token) and  # Current token is a word
                tokens[i + 1] == '-' and                               # Next token is hyphen
                tokens[i + 2].strip() and any(c.isalpha() for c in tokens[i + 2])):  # Token after hyphen is word
                
                # Reconstruct the hyphenated term to check if it's canonical
                hyphenated_term = token + '-' + tokens[i + 2]
                
                if hyphenated_term.lower() in canonical_hyphenated:
                    # Keep canonical hyphenated terms unchanged
                    result_tokens.extend([token, tokens[i + 1], tokens[i + 2]])
                else:
                    # Split non-canonical hyphens: replace hyphen with space
                    result_tokens.extend([token, ' ', tokens[i + 2]])
                
                i += 3  # Skip the word-hyphen-word group we just processed
            else:
                # Regular token, add as-is
                result_tokens.append(token)
                i += 1
        
        return self.tokenizer.detokenize(result_tokens)

    def normalize(self, text: str, language: str = "nl") -> NormalizationResult:
        dbg: Dict[str, Any] = {"language": language, "input": text}
        text = unicodedata.normalize('NFC', text)
        current = self.guard.wrap(text)
        current = current.replace("\u00A0", " ")  # NBSP → spatie
        dbg["protected_wrap"] = current
        if self.flags.get("enable_element_parsing", True):
            current = self._apply_on_unprotected(current, self.element_parser.parse)
            dbg["elements"] = current
        if self.flags.get("enable_learnable", True) and self.learnable:
            current = self._apply_on_unprotected(current, self.learnable.apply)
            dbg["learnable"] = current
        if self.flags.get("enable_custom_patterns", True):
            current = self._apply_on_unprotected(current, self.custom_patterns.apply)
            dbg["custom_patterns"] = current
        # Add hyphen splitting BEFORE variant generation to avoid splitting compound results
        current = self._apply_on_unprotected(current, self._split_noncanonical_hyphens)
        dbg["hyphen_split"] = current
        
        if self.flags.get("enable_variant_generation", True):
            current = self._apply_on_unprotected(current, self.variant_generator.generate)
            dbg["variants"] = current
        
        # Apply phonetic matching if enabled (uses the proper threshold 0.70)
        if self.flags.get("enable_phonetic_matching", True):
            current = self._apply_on_unprotected(current, self._phonetic_call)
            dbg["phonetic"] = current
        
        # Safety net: restore any lost diacritics after all processing steps
        current = self._apply_on_unprotected(current, self._restore_canonical_diacritics)
        dbg["diacritics_safety_net"] = current
        
        if self.flags.get("enable_post_processing", True):
            current = self.postprocessor.apply(current)
            dbg["post"] = current
        current = self.guard.unwrap(current)
        dbg["unwrapped"] = current
        return NormalizationResult(normalized_text=current, language=language, debug=dbg)