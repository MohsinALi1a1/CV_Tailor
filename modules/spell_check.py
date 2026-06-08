"""
CV Tailor — Lightweight Spell Checker
======================================
Dictionary-based spell checking for resume text. No external API needed.
Uses Python's stdlib + curated tech-term whitelist to avoid false positives
on technical jargon, brand names, and abbreviations.
"""

from __future__ import annotations

import difflib
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any


# A reasonably-sized English word list. We bundle a minimal version inline
# to avoid external dependencies. For higher accuracy users can install
# pyspellchecker — see _try_pyspellchecker.

# Common English words (~10K most frequent). For brevity, we rely on
# a runtime build + tech whitelist + pyspellchecker if available.

# Try optional pyspellchecker
try:
    from spellchecker import SpellChecker as _PSpellChecker  # type: ignore
    _HAS_PYSPELL = True
except ImportError:
    _PSpellChecker = None  # type: ignore
    _HAS_PYSPELL = False


# Curated whitelist: tech terms, brand names, abbreviations we never want flagged
TECH_WHITELIST: set[str] = {
    # Languages
    "python", "java", "javascript", "typescript", "golang", "csharp", "cpp",
    "kotlin", "rust", "scala", "ruby", "php", "swift", "dart",
    # Frameworks/libs
    "react", "angular", "vue", "svelte", "nextjs", "nuxt", "django", "flask",
    "fastapi", "spring", "rails", "laravel", "nodejs", "express", "nestjs",
    "redux", "graphql", "websockets", "webpack", "vite", "tailwind",
    # Cloud/DevOps
    "aws", "azure", "gcp", "kubernetes", "docker", "terraform", "ansible",
    "jenkins", "gitlab", "github", "bitbucket", "argocd", "prometheus",
    "grafana", "datadog", "splunk", "elasticsearch", "kibana", "logstash",
    "kafka", "rabbitmq", "redis", "memcached", "nginx", "apache",
    # Data
    "snowflake", "databricks", "bigquery", "redshift", "postgres", "postgresql",
    "mysql", "mongodb", "cassandra", "dynamodb", "neo4j", "clickhouse",
    "airflow", "dbt", "spark", "hadoop", "pyspark", "pandas", "numpy",
    "scikit", "sklearn", "tensorflow", "pytorch", "keras", "huggingface",
    "langchain", "llamaindex", "pinecone", "weaviate", "qdrant", "chroma",
    # AI/ML
    "llm", "rag", "nlp", "ocr", "asr", "tts", "transformers", "embeddings",
    "openai", "anthropic", "claude", "gpt", "llama", "mistral", "gemini",
    "bert", "roberta", "vit", "yolo", "diffusion",
    # Methodologies
    "agile", "scrum", "kanban", "devops", "devsecops", "sre", "tdd", "bdd",
    "ddd", "kpi", "okr", "kpis", "okrs", "mvp", "poc", "rfc", "rfp",
    # Common abbreviations
    "api", "apis", "sdk", "cli", "gui", "ide", "orm", "crud", "rest",
    "soap", "json", "xml", "yaml", "toml", "csv", "html", "css", "url",
    "uri", "uuid", "guid", "http", "https", "tcp", "udp", "ssh", "ftp",
    "dns", "cdn", "vpn", "vpc", "iam", "rbac", "saas", "paas", "iaas",
    "b2b", "b2c", "etl", "elt", "ci", "cd", "qa", "ux", "ui", "ml", "ai",
    "ar", "vr", "xr", "iot", "ar/vr", "ar/vr/xr",
    # Business
    "saas", "fintech", "edtech", "healthtech", "proptech", "insurtech",
    "ecommerce", "omnichannel", "go-to-market", "gtm", "p&l", "p&l",
    "ebitda", "arr", "mrr", "cac", "ltv", "ndr", "nrr", "csat", "nps",
    "ctr", "cpa", "cpc", "cpm", "roas", "roi", "dau", "mau", "wau",
    # Common resume vocab
    "linkedin", "github", "stackoverflow", "kaggle", "medium", "leetcode",
    "hackerrank", "coursera", "udemy", "pluralsight", "edx",
    # File/format
    "pdf", "docx", "xlsx", "pptx", "jpeg", "jpg", "png", "svg", "gif",
    "mp3", "mp4", "wav", "flac",
}


# Minimal English word list (~3000 common words). We'll add to this dynamically.
# Source: derived from Google's most common English words list (public domain).
_BUILTIN_WORDS = """
the be to of and a in that have i it for not on with he as you do at this but his by from
they we say her she or an will my one all would there their what so up out if about who get
which go me when make can like time no just him know take people into year your good some
could them see other than then now look only come its over think also back after use two how
our work first well way even new want because any these give day most us is was are been were
has had did been have having does doing does made making make makes been being
about above across after against all almost alone along already also although always among an
and another any anybody anyone anything anywhere are area around as away back because been
before behind being below beside between both but by came can cannot center clearly come
could course did differ different do does doing done dont down due during each early either
end enough especially even every everybody everyone everything everywhere face fact far feel
few find first found four from full further get getting give given gives go going gone good
got great group had hand has have having he her here him his home how however i in into is
it its just keep kind know knowing knows large last later least left less like likely line
little long look low made make many may me men might mine more most much must my myself
near never new next no nobody none nor not nothing now of off often on once only or other
others our ours out over own people perhaps place please point possible put quite rather
re really right said same say says second see seem seemed seeming seems seen several she
should show shows side small so some somebody someone something somewhere still such sure
take taken takes taking tell ten than that the their theirs them themselves then there these
they thing think this those though three through till time to together too took toward two
under up upon us use used uses using very want wants was way ways we week well went were what
when where whether which while who whom whose why will with within without world would year
years yes yet you your yours yourself
ability about above academic accept access accommodate accomplish account achieve acquire
act action active activities activity actual actually add added addition additional address
addressed adequate adjust administration adopted advance advanced advice affect after again
against age agency agile agreement agreed ahead align allow allowed almost alone along
already also although always among amount analysis analytical analyze analyzed and
another answer any anyone anything appear application applied apply approach approached
appropriate approximately architect architecture area areas around arrange article aspect
assess assessment asset assets assist assistant associate associated association assume
assure attempt attention attribute audience audit author authority automated automation
available average award aware away back background bank base based basic basis became
because become been before began begin beginning behalf behavior being believe below benefit
benefits best better between beyond billion board body book born both bring brought budget
build building built business but buy by call called came campaign can cannot capability
capable capacity capital care career carried carry case cases catch caught cause causes
center central certain certainly certified chair chairman chairperson chance change changed
changes changing chapter character charge check chief child children choice choose chose
chosen church city civil claim claims class classes clean clear clearly client clients
close closed closely collaboration colleague college combination combine combined come
coming commercial commission commit committed committee common communication communities
community companies company compare compared comparison compete competition competitive
complete completed completely complex compliance complied component components compose
composed comprehensive computer concept concern concerned concerning concerns conclude
conclusion concrete condition conditions conduct conducted conducting conference confidence
confidential configuration confirm conflict connect connected connection consequences
consider considered considering consist consistent consistently constant constantly
construct construction consult consultant consulting consumer consumers contact contacts
contain contained content context continue continued continues continuous continuously
contract contracts contribute contributed contribution control controlled controlling
controls convenient conversation convert converted coordinate coordinated coordinating
copy core corporate corporation correct correctly cost costs could council count counter
countries country couple course court cover covered covers create created creating creation
creative credit critical cross culture current currently customer customers cut cycle daily
data database date day days deal dealing decide decided decision decisions decrease deep
defense define defined definitely definition degree delegate deliver delivered delivering
delivery demand demands demonstrate demonstrated department departments depend depending
depth describe described describes description design designated designed designing despite
detail detailed details determine determined developed developer developers developing
development device different difficult digital direct directed direction directly director
disability disclose disclosure discover discovered discuss discussed discussion display
dispose distance distribute distributed distribution district divided division do document
documentation documented documents does done door down draw drew drive driver driving drop
due during each early earned ease easily east easy economic edge education educational
effect effective effectively effects efficiency efficient effort efforts eight either
electric electronic element elements eliminate else email emerge emergency employee employees
employer employment empty enable enabled enabling encourage end ended ending ends energy
engage engaged engineer engineering enhance enhanced enjoy enough ensure ensured ensuring
enter entered enterprise entire entirely entity entry environment environmental equal
equally equipment error errors especially essential establish established estate
estimate estimated estimating ethics evaluate evaluated evaluating evaluation even evening
event events ever every everybody everyone everything evidence exactly examine example
examples exceed exceeded excellent except exception exchange execute executed executive
exempt exercise exhibit exist existed existing expand expanded expand expect expectations
expected expense expenses experience experienced expert expertise explain explained explore
exposure express extensive external extra extraordinary face facing fact factor factors
fail failed failure fair fall fallen family far farm fast feature features federal feel
feeling felt few field fifth fight figure figures file files fill final finally finance
financial find finding findings fine finish finished firm first fiscal fish five fix fixed
flag flexible floor flow flowing focus focused follow followed following force forced
forecast forecasting foreign forest forget form formal format formation formed forms forth
forward found four fourth frame framework free freedom frequency frequent frequently fresh
friend front fuel full fully function functional functions fund fundamental fundamentally
funded funding funds funeral further future gain gained gas gather gave general generally
generate generated generates generation generic gesture get getting gift girl give given
giving glass global go goal goals god goes going gold gone good government governmental
grade graduate grant granted graphic great greater greatest green ground group groups grow
growing grown growth guarantee guard guess guest guide guidance guidelines hair half hand
handle handled handling hands happen happened happens happy hard harder having head
headed heading health healthcare hear heart held help helped helpful helping helps here
hey hi high higher highest highlight highly history hit hold holding holds home hope hot
hotel hour hours house housing how however huge human hundred husband idea ideas
identification identified identify identifies identifying ignore ill illegal image images
imagine immediate immediately impact implement implementation implemented implementing
implements important improve improved improvement improvements include included includes
including income increase increased increases independent index indicate indicated
individual industry industrial industries inflation influence inform informal information
infrastructure initial initially initiated initiative initiatives inner input inquiry
inside insight install installed installation instance instead institute institution
instruction instructions instrument insurance integrate integrated integration intelligence
intend intended intent intention interaction interactive interest interested interesting
interface internal international internet interpret interview interviewed introduce
introduced introducing investigate investigated investigation investment investments
invited involve involved involvement is issue issues it item items its itself
job jobs join joined joining joint journal judge judgment jump jurisdiction just justice
keep keeping kept key keys kid kids kill kind kinds kitchen knew know knowledge known
labor language large largely larger largest last late later latest law lawyer lay lead
leader leaders leadership leading leads learn learned learning least leave leaving led
left legal less lesson let level levels library license life light like liked likely
limited limits line lines link linked links list listed listing little live lived lives
living local located location long longer look looked looking looks loss lost lot love
low lower lowest machine made magazine main maintain maintained maintenance major majority
make makes making man manage managed management manager managers managing many map mark
market marketing markets master match material matter may maybe me mean meaning means
meantime measure measured measures meat media medical medium meet meeting meetings meets
member members membership memory mention mentioned message messages met method methods
middle might mile military million minimal minimum minor minute mission mix mixed mobile
model modeling models moderate modern modify modified moment money month monthly months
moral more morning most mostly mother motion move moved movement movie much multi multiple
music must my myself name named names national natural nature near nearly necessary need
needed needs negative negotiate negotiating neighbor neither network networks never new
news newspaper next nice night nine no nobody non none nor normal normally north not note
noted notes nothing notice noticed notion novel now nowhere nuclear number numbers
numerous object objective objectives observe observed obtained occur occurred occurring
ocean off offer offered offering office officer officers offices official officials often
oh oil old on once one ones ongoing online only onto open opened opening operate
operated operating operation operations operator opinion opportunity opportunities
opposite opposition optimization optimize optimized option options or oral order ordered
ordering organization organizational organizations organized organizing oriented
original originally other others our ourselves out outcome outcomes output outside
over overall overcome owner ownership package page pages paid pain paint painting pair
panel paper papers parallel parent parents park part participant participants participate
participated particular particularly partner partners partnership parts party pass passed
passing past path patient patients pattern patterns pay paying payment payments peace
people per percent perform performance performances performed performing perhaps period
periods permanent permission permit person personal personality personally personnel
perspective phase phone phones photo photography phrase physical pick picture piece pieces
pilot pipe pipeline place placed places plan planned planning plans plant plants platform
platforms play played playing plays plenty plus pocket point pointed points policy political
politically politics poor pop popular population port portion portfolio position positions
positive possess possible possibly post posted potential potentially power powerful
practical practice practices precise precisely predict prediction prefer preferred
preliminary preparation prepare prepared preparing presence present presentation
presented presenting press pressure prevent previous previously price prices primary
prime principle principles print printed prior priority private probability probable
probably problem problems procedure procedures process processed processes processing
produce produced producing product production productive products professional professionals
professor profile profit profits program programming programs progress progressive
project projected projects promise promote promoted promoting prompt prompted proof proper
properly property proposal proposals propose proposed protect protection prove provide
provided provider providers provides providing public publication publish published
publishing pull purchase pure purpose purposes push put putting quality quantity quarter
question questions quick quickly quiet quite race racial radio raise raised range ranges
rank rapid rapidly rare rarely rate rates rather ratings ratio raw reach reached reaching
react reaction read reader reading ready real reality realize really reason reasonable
reasons receive received recent recently recommend recommendation recommendations
record recorded recording records recover recovery red reduce reduced reduces reducing
reduction refer reference referred refers reflect reflected reform refused regard regarding
regardless region regional regions register registered regular regularly regulation
regulations regulatory reject related relating relation relations relationship
relationships relative relatively release released relevant reliable rely remain remained
remaining remember remind remove removed render rendered repair repeat repeated replace
replaced replacement reply report reported reporting reports represent representative
representatives represented represents reproduce reproduction republic request requested
requests require required requirement requirements requires requiring research researcher
researchers reserve reserved resident residents resist resource resources respect respond
responded response responses responsibility responsibilities responsible rest restaurant
restore result resulted resulting results retain retention retired return returned
returning revenue reverse review reviewed reviewing reviews revolution rich rid right
rights rise risen rising risk risks river road robust role roles roll room rose round
route row rule rules run running rural sad safe safety said sale sales same sample sand
satisfy save saved saw say saying says scale scan scene schedule scheduled scheduling
scheme school schools science scientific scientist scientists scope score scores screen
sea search season seat second secondary section sector secure secured security see
seek seeking seem seemed seems seen segment select selected selection self sell selling
send sending senior sense sent sentence separate sequence series serious seriously serve
served service services serving session set setting settings settle setup seven several
severe shape share shared shares sharing she sheet shift shifted ship shoot shop shopping
short shorter shot should show showed showing shown shows shut side significant
significantly silver similar similarly simple simply since single sister sit site sites
sitting situation situations six size sizes skill skills skin slow small smaller smart
smile so social society soft software soil solar sold solid solution solutions solve solved
solving some somebody somehow someone something sometimes somewhat son song soon sort
sound source sources south space spaces spanish speak speaker speaking special specialist
species specific specifically specification specified specify spell spend spending spent
sport spot spread spring stable staff stage stages stair stand standard standards standing
star start started starting starts state stated statement statements states static station
statistical statistics statue status stay stayed step steps stock stop store stories story
straight strange strategic strategies strategy stream street strength stress stretch
strict strictly strike strong stronger strongly structure structures struggle student
students studied studies study studying style subject submit submitted submitting subsidy
substantial substantially subsequent success successful successfully such suddenly suffer
sufficient suggest suggested suggestion summary summer sun super support supported
supporting supports suppose supposed sure surely surface surprise surrounded survey
suspect sustain sustainable system systems table tag take taken takes taking talk talking
target targeted targets task tasks tax taxes teach teacher teaching team teams tech
technical technique techniques technology teen telephone television tell telling temperature
ten tend term terms test tested testing tests text texts than thank that the their them
themselves then theory therapy there therefore these they thin thing things think thinking
third thirty this those though thought thousand threat three through throughout throw
thrown thus ticket tight time timely times timing tiny tip tire tired title to today
together told tomorrow tonight too took tool tools top topic total totally touch tough
tour toward town track tracking trade tradition traditional traditionally traffic
training transfer transferred transform transformation transition translate transport
travel treasury treat treated treatment tree tremendous trend trends trial trip trouble
true truly trust truth try trying turn turned turning twelve twenty twice two type types
typical typically uncertain under undergo understanding union unique unit united units
universe university unknown unless unlike until up upgrade upon upper urban us use used
useful uses using usually utility valid validate validation value valued values various
vary vehicle venture verbal version very veteran via video view viewed view views
village violation violence violent visible vision visit visited visiting visitor visitors
visual vital voice volume volunteer vote voted voter voters vs wage wait waiting walk
walking wall want wanted wants war warm warning warrant was wash waste watch watched
watching water way ways we weak wealth weapon wear weather web website websites wedding
week weekend weekly weeks weight welcome welfare well went were west western what whatever
when whenever where whereas whether which while white who whole whom whose why wide widely
wider wife will willing win wind window windows wing winner winning winter wire wish with
within without witness woman women won wonder wonderful wood word words work worked worker
workers working works workshop world worldwide worry worse worth would write writer
writing written wrong wrote yard yeah year yearly years yes yesterday yet yield you young
younger your yours yourself zone
""".split()

_BASE_WORDS: set[str] = set(_BUILTIN_WORDS) | TECH_WHITELIST


@lru_cache(maxsize=1)
def _get_spellchecker() -> Any:
    """Return a pyspellchecker instance if installed, else None."""
    if _HAS_PYSPELL and _PSpellChecker is not None:
        try:
            sc = _PSpellChecker(language="en")
            # Add tech terms to dictionary
            sc.word_frequency.load_words(TECH_WHITELIST)
            return sc
        except Exception:
            return None
    return None


@dataclass
class SpellIssue:
    """A single potential spelling issue."""
    word: str
    line: int
    suggestions: list[str] = field(default_factory=list)
    context: str = ""


@dataclass
class SpellCheckResult:
    """Result of spell-checking text."""
    issues: list[SpellIssue] = field(default_factory=list)
    total_words: int = 0
    misspelled_count: int = 0
    accuracy_pct: float = 100.0
    backend: str = "builtin"

    def to_dict(self) -> dict[str, Any]:
        return {
            "issues": [
                {
                    "word": i.word,
                    "line": i.line,
                    "suggestions": i.suggestions,
                    "context": i.context,
                }
                for i in self.issues
            ],
            "total_words": self.total_words,
            "misspelled_count": self.misspelled_count,
            "accuracy_pct": round(self.accuracy_pct, 2),
            "backend": self.backend,
        }


def _is_skippable(word: str) -> bool:
    """Words we should never flag."""
    if len(word) < 3:
        return True
    if word.isupper() and len(word) <= 6:
        # Likely acronym
        return True
    if any(ch.isdigit() for ch in word):
        return True
    if "/" in word or "\\" in word or "@" in word or "." in word:
        return True
    if "-" in word or "_" in word:
        return True
    if not word.isalpha():
        return True
    return False


def spell_check(text: str, max_issues: int = 50) -> SpellCheckResult:
    """Spell-check resume text.

    Args:
        text: The full text to check.
        max_issues: Maximum number of issues to report.

    Returns:
        SpellCheckResult with detected issues.
    """
    if not text or not text.strip():
        return SpellCheckResult()

    sc = _get_spellchecker()
    backend = "pyspellchecker" if sc is not None else "builtin"

    lines = text.split("\n")
    issues: list[SpellIssue] = []
    total_words = 0
    misspelled = 0

    for line_num, line in enumerate(lines, 1):
        words = re.findall(r"[A-Za-z][A-Za-z']+", line)
        for word in words:
            total_words += 1
            word_lower = word.lower().strip("'")
            if _is_skippable(word):
                continue
            if word_lower in _BASE_WORDS or word_lower in TECH_WHITELIST:
                continue
            # Strip plural 's' and try again
            if word_lower.endswith("s") and word_lower[:-1] in _BASE_WORDS:
                continue
            if word_lower.endswith("ing") and word_lower[:-3] in _BASE_WORDS:
                continue
            if word_lower.endswith("ed") and word_lower[:-2] in _BASE_WORDS:
                continue
            if word_lower.endswith("er") and word_lower[:-2] in _BASE_WORDS:
                continue

            # Use pyspellchecker if available
            if sc is not None:
                if word_lower in sc:
                    continue
                misspelled += 1
                if len(issues) < max_issues:
                    suggestions = list(sc.candidates(word_lower) or [])[:5]
                    issues.append(SpellIssue(
                        word=word, line=line_num,
                        suggestions=suggestions,
                        context=line.strip()[:120],
                    ))
            else:
                # Builtin: use difflib for suggestions
                misspelled += 1
                if len(issues) < max_issues:
                    suggestions = difflib.get_close_matches(
                        word_lower, _BASE_WORDS, n=3, cutoff=0.8
                    )
                    issues.append(SpellIssue(
                        word=word, line=line_num,
                        suggestions=suggestions,
                        context=line.strip()[:120],
                    ))

    accuracy = ((total_words - misspelled) / total_words * 100) if total_words > 0 else 100.0

    return SpellCheckResult(
        issues=issues,
        total_words=total_words,
        misspelled_count=misspelled,
        accuracy_pct=accuracy,
        backend=backend,
    )


def quick_spell_score(text: str) -> float:
    """Return a 0-100 spelling quality score."""
    result = spell_check(text, max_issues=100)
    return result.accuracy_pct
