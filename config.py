import os
import re
from typing import List

# === CONFIGURAÇÃO BÁSICA ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_RAW = r"D:\EP1\1_RAW"
PASTA_FILTRADO = r"D:\EP1\2_FILTRADO"

# ==============================================================================
#           CONFIGURAÇÃO DE REGRAS ESTRITAS (Filtros de Extração)
# ==============================================================================

# Regex para filtrar "lixo" que não precisa de tradução (números, IDs, URLs, códigos)
REGEX = re.compile(
    r'^[\d\s\W_]+$|'              # Apenas números, espaços e símbolos (ex: "10/10", ":", "100")
    r'^[a-zA-Z]$|'                # Apenas uma letra única (ex: "L", "R", "X")
    r'^www\..*|^https?://.*|'     # URLs
    r'^#\d+$'                     # IDs de cor ou número (ex: #15)
)

# 1. OBRIGATÓRIO: Define quais tipos de 'History' são válidos para tradução
REQUIRED_HISTORY_TYPE = { "Base", "None", "NamedFormat" }

# 2. PROIBIDO: Se o objeto tiver esta flag, ele é considerado "imutável" (não pode ser traduzido)
FORBIDDEN_FLAG = "Immutable"

# 3. WHITELIST: Define quais tipos de objetos JSON podem conter texto traduzível
WHITELIST_TYPES = {
    "TextProperty", 
    "TextPropertyData", 
    "FStringTable", 
    "StringTableExport",
    "StrProperty"
}

# 4. BLACKLIST TÉCNICA: Palavras que a IA pode confundir, mas que não devem ser traduzidas
BLACKLIST_CONTEUDO = {
    "sprite", "local", "linear", "camerafollow();", "enddialog();", "startpatrol();", "fadeout(0);", "callautosave();", "stopobjectmovement();", "enablemovement();", "endcharactercreator();", "playvoiceover();", "pullwalktelanimation();", "showgroup();", "hidegroup();", "stopmontage();", "incomingtelesense(, , 0);", "showui();", "setstringvariable(,);", "hideui();", "setintvariable(,0);", "showsevenhud();", "stopfollowby();", "starttutorial();", "followby(, );", "disablemovement();", "unlockachievement(, 0);", "calleventonend();", "gotodistance(, , 0, 0);", "goto(, , 0);", "setboolvariable(,true);", "resetcharactercreator();", "teleport(, , true);", "stoppatrol();", "lookat(, );", "showtextbubble();", "putwalktelanimation();", "fadein(0);", "callevent();", "moveto(,, 0);", "hidetextbubble();", "qr-code", "physician _icon_normal", "telesense", "void stars", "telesens nanette - ap03", "bliss", "ap01", "telesens haggis - ap03", "telesens - jester", "haggis telesens - ap01", "tv", "telesens haggis - ap05", "ap02", "ken v-ghost - ap04", "ap03", "|<i>hmm... </>|", "[warsaw city]", "[spam 1]", "|<i>...</>|", "<i>...</>", "[ken zhou]", "bliss?", "[whisky]", "[high city]", "[low city]", "[ken]", "//tutorial", "//walkatel", "//clue am: realium", "callevent(kenmessage);", "//customvo", "callevent(endscene);", "//codex - pneumobil", "//codex - undercity", "//codex - motomby", "//tankred", "//codex - goodabads", "//codex - gaja wiki", "//codex - novatronics", "//codex creators club", "callevent(showblissbar);", "//yetis bar", "//music sex", "//sleeves?", "haggis", "idris", "axis mundi", "do not translate", "jester", "codebreaker", "jiiiihaaaa", "howdy", "|khm, khm...|", "|infotainer|", "|howdy, howdy, howdy!|", "||ironia", "[gamedec]", "||edge runner", "|firewall|", "[atmosfera]", "am office open", "vghosttalk", "am office_open", "dedu", "forcred deduction", "riftcrossing", "//clue am: side", "//codex", "//clue am: eleonora", "//snd event", "//event", "//clue am: axis mundi", "//codex - v-runners", "fhtagn!", "//ken", "ken", "t&p", "kenclownresolution", "clownresponding", "hub", "[n]", "ph’nglui mglw’nafh…", "callevent(jesterdisolve);", "cthulhu", "azari", "ken zhou", "the josh", "myra", "shivani", "daemons", "lady firefly", "seven: the days long gone", "ryan", "dungeongeek", "zola", "shivani thana", "studnia", "savaash", "teriel&artanak", "footstepslast", "start-virtualiumnpc", "bao", "daemon", "avatar", "alex", "thejosh", "dungeon geek", "holo", "vito", "footstepsstash-04", "minigamestart", "book395", "daemonpopin", "book771", "artanak solo", "footstepsstash-01", "intro", "virtualium", "console", "talk-start", "brunosummons", "main-hub", "inf", "gates", "login-check", "bruno-mod", "brunodaemons", "real", "demons2", "winda", "chg-cmd", "console", "ids", "alexmain", "user-id", "mod-comment", "onbruno", "cmds", "alexinfo", "scenka", "brunoondaemons", "wezquest", "queststart", "demons", "brunoquest", "to-main-qs", "kent1", "consoleunlocked", "kenout", "nextround", "hub2", "hubquestions", "alex-not-met", "azariannoyed", "groupstart", "nextto", "ai-tests", "themt3", "placeobject", "dymki-okoncu", "step2", "hub1", "scans-for-alex", "artanak", "bao-dymki", "nimeesha-dymki", "deadman", "nimeesha-start", "dymki-bardzi", "test-daemonsfail", "kenknows", "daemonmain", "azariquestions", "savaashscripts", "coniose", "test-daemons", "themt1", "ai-testsintro", "askwhattodo", "3keyscheck", "emotest", "afteraquestion", "kencorrect", "stop-pursuer-choice", "quest-explanation", "endingshivani", "calmher", "kendoesnotknow", "cognitest", "daemonafterperson", "safeendtechnician", "questy", "shivani-questions", "hub3", "alex-met", "pytaniatest", "ryanmain", "testnpcend", "q2", "baoafterchase", "themt5", "joshintro", "qs", "jukebox-end", "analysebehaviour", "pt3", "azariopen", "aspectchoicenimeesha", "compswitch", "techfirst", "teriel", "nimeesha", "brainstorming", "interface", "callevent(back2office);", "callevent(savaashfreeze);", "callevent(musicmapai);", "callevent(musicladytalk);", "callevent(showjoshbar);", "cpt. barnaba basilides", "killthemall", "starlet", "mack boar", "inl", "dj", "pey", "lit", "sad", "venon vera", "tick", "wkt", "medmat", "yet", "beowulf", "tankred brut", "brainfix", "dad", "ramona", "rick", "naaba", "cam grozny", "bar", "ckm", "marten", "random(0,1) == 1;", "//codex - reizm", "callevent(dronein);", "callevent(endumpalumpa);", "callevent(brokendrone);", "//codex - bateria vaghera", "callevent(rickcomes);", "callevent(ending);", "//codex - out-rangers", "callevent(starlettdebug);", "callevent(udohit);", "callevent(stayatbar);", "callevent(brokennewbuoy);", "//codex - l-pill", "callevent(fredon);", "callevent(umpalumpa);", "//codex - zoeneci", "callevent(tankredon);", "// codex way dao", "callevent(paintonposter);", "//codex - ckm", "//codex - genglish", "callevent(enterthebar);", "callevent(groznyout);", "callevent(joebrainfixed);", "callevent(brokenmedmat);", "callevent(momenttobar);", "callevent(spawnnaaba);", "callevent(stophacking);", "callevent(entrancefee);", "callevent(starthacking);", "hidegroup(hiddenkey);", "callevent(showtickbar);", "callevent(yetgotoplayer);", "callevent(udolookatjoe);", "callevent(gogodance);", "callevent(showclanbar);", "callevent(quitterhit);", "callevent(boyaturnoff);", "callevent(hideramonabar);", "callevent(kidescape);", "callevent(behemoton);", "callevent(taketickout);", "callevent(naabaappearsw);", "callevent(hidetickbar);", "callevent(hideclanbar);", "callevent(trollstojoe);", "callevent(rickaway);", "callevent(repairrick);", "//infotainer", "//sleeves", "//glazier", "//cracker", "//brainfixer", "//scalpel", "//mqreisticsystems", "//gobacktotheapartment", "//theend", "//sqmakeadeduction", "//mqken'sdeath", "//mq3", "//paxquest", "//mqenterthecrimescene", "//captainquest", "//mqpsychoskan", "howdy!", "|..::n0 513m4nk000::..|", "|..::?c20 +4m?::..|", "[great scott!]", "|great scott!|", "lea-anne", "[nanette]", "|mooo!|", "...killthemall.", "outlaw_relation +5", "bobbye", "outlaw_relation -1", "outlaw_relation +2", "hilda", "walajirahub", "sleeves", "outlaw_relation +1", "outlaw_relation -2", "mmquestionsstart", "aaa", "hubszeryf", "jiha", "outlaw_relation 0", "outlaw_relation -3", "kidssilent", "mmquestionsend", "lynchinfo", "break1", "outlaw_relation -4", "hub4", "kidshappy", "hub5", "outlaw_relation +3", "mmquestionsmid", "tumbleweed", "ht_act_2, 3", "break2", "//joe macha", "callevent(duelaudiostop);", "myspot", "tanto", "mia - dps", "umbra", "golem", "jail-jester", "maya", "debug", "||gomuin", "|golem, hot or not?|", "|gamedec|", "#fb00ff", "jester2", "hubfluff", "pt2", "hub-q", "negative2", "poem2", "negative1", "queststandard", "signsask", "end", "ask2", "poem1", "zappa2son", "zappahub", "zdradzplanyszpiegow", "jestercheck", "koniecquesta", "escape", "dailydebug", "gomuin", "aardvark", "jester1", "questioncount", "trybutariusz", "questwachlarz", "|tanto met 1|", "callevent(pupaout);", "callevent(eaglekilled3);", "showgroup(bowlplace);", "callevent(froze314);", "//coddex - lex occulta", "callevent(gamedecgetout);", "callevent(jestercomes);", "callevent(jesterbypupa);", "callevent(dailysend);", "callevent(showplaza);", "callevent(eaglelogout);", "callevent(fakenpclogout);", "callevent(showforge);", "showgroup(ginsengitem);", "callevent(showbridge);", "callevent(hideginsengs);", "callevent(miaspeech);", "callevent(tothejail);", "callevent(eaglekilled1);", "callevent(lordcentre);", "showgroup(lordfan);", "callevent(miaspeechend);", "callevent(jesterleaves);", "callevent(golemroars);", "callevent(showtreasury);", "callevent(eaglekilled2);", "//codex - poteto gomuin", "callevent(turnintocat);", "//studygroup", "//brokennpc", "//regainingtheartefact", "//theloot", "//carrotvengance", "//carrotvengance3", "//carrotvengance2", "//carrotvengance1", "//cv3a", "//thelootbook", "glitch", "fredo", "outro", "mia & maya", "timmy", "panisantor", "panda", "zed", "zed - ken - gamedec", "bob zappa", "nappa lona", "|admin|", "ccc", "[geoffrey?]", "|panda|", "[fredo]", "|axis mundi|", "[geoffrey haggis]", "admin", "cheat", "exploit", "[fredo haggis]", "ramon", "tuchajbej", "askworld", "umbraintrigued", "pozleceniu", "umbraend", "positivecluetestq", "askfriends", "umbrastart", "umbraexcited", "umbrafollow", "askher", "pytamofredo", "askfredo", "negativecluetestq", "drunkfrustration", "askcult", "negativecluetestu", "umbralogout", "umbrareaction", "askpanisantor", "gdsober", "endconversation", "gddrunk", "panisantorend", "umbrabored", "panisantorlastwords", "positivecluetestu", "jeremiaszjump", "eleonore start", "o4", "comfort tim 4", "comfort tim 2", "paradisecluehi", "comfort hi 5+", "paradisecluelow", "comfort tim 3", "negativecluecheckq", "comfort hi 2", "zappamain", "comfort tim 6", "comfort tim 1", "comfort hi 1", "wifecaseforced", "humanhorse", "givenegativeclue", "textbubble", "comfort hi 3", "slayer t&p exit", "bob zappa t&p exit", "givepositiveclue", "comfort tim 5", "timstart", "positivecluecheckc", "comfort hi 0", "negativecluecheckc", "positivecluecheckq", "callevent(zedkillplayer);", "callevent(gdkneel);", "hidegroup(hidewoman);", "callevent(playerkillzed);", "hidegroup(hidestranger);", "camerafollow(player);", "hidegroup(glithchair);", "showgroup(kenpartner);", "callevent(haggisgosit);", "//codex - infotainer", "hidegroup(lovebed);", "//codex - aurocary", "callevent(zedkillken);", "callevent(kaboom);", "callevent(playerkillken);", "callevent(kenkillzed);", "//codex - wirtualia", "//codex - hotka", "//codex - nlsd", "//influencer", "callevent(horseisback);", "callevent(jestersadend);", "callevent(talkwoman);", "callevent(kidcalling);", "callevent(twinsstart);", "stopfollowby(player);", "showgroup(afterhaggis);", "callevent(breaketheloop);", "callevent(talkfredo);", "//codex - realium", "callevent(jesterisback);", "callevent(kenwakeup);", "callevent(ramonadies);", "//codex - high city", "callevent(kencavalery);", "callevent(horsetohuman);", "callevent(runelevator);", "callevent(icant);", "callevent(cultdooropen);", "hidegroup(pileofgarbage);", "callevent(faseterbed);", "//codex - infolia", "callevent(kenkillplayer);", "callevent(alleydooropen);", "callevent(guardianangel);", "//codex - lord", "//codex - void stars", "callevent(kenstopfollow);", "hidegroup(throne);", "callevent(hidetimmybar);", "hidegroup(brazier);", "callevent(duplicate);", "showgroup(fakeexit);", "callevent(miamayaangry);", "callevent(jesterending);", "showgroup(brazier);", "callevent(hideumbrabar);", "//talkwiththetroll", "//usetheelevator", "//findpanel", "//tickmirror", "//backtoramon", "//debugingtheunicorn", "//tickmirrorb", "//backtotherhonda", "//informbobzappa", "//opentheater", "//tickredcar; tickquest", "//ticknailcarb", "//solveramonaproblem", "//ticknailkid", "//lieforrhonda", "//tickredcarb", "//ticknailb", "//investigatetrollcamp;", "//ticknailcar", "//breaktheloop", "//ticknail", "//ticknumberplatea", "//sq3findwitness", "//ticknumberplateb", "//findoutifwifeisint&p", "//interviewumbra", "//questionunicorn", "//whathappendinallye", "//findgrandpa", "//q2", "//ticknailcara", "//q1", "//tickredcar", "//tickquest", "//sq3findpanel", "//tickmirrora", "//whatcultmaketofredo", "//sq3findtrack", "//sq3findwitnes", "//interviewramona", "//exploitagregat", "//trollmarch", "//watchthetrick", "//escapethealley", "//ticknaila", "//findbobzappawife", "//tickredcara", "//fredohealth", "cutscene"
}

# 5. NOMES DE PROPRIEDADE: Variáveis de sistema que não devem sofrer alteração
BLACKLIST_NOMES_VARIAVEL = {
    "internalname", "classname", "tagname"
}

# --- CONFIGURAÇÕES DE REENVIO (Resiliência) ---
TIMEOUT_LIMITE = 180  # Tempo máximo (segundos) que o script aguarda a resposta da IA
MAX_TENTATIVAS = 5    # Tentativas de reenvio caso a IA falhe por instabilidade

# === CONFIGURAÇÃO DE FERRAMENTAS EXTERNAS (Unreal Engine) ===
# Caminho para o executável do UAssetGUI (usado para converter JSON <-> UAsset)
UASSET_GUI_PATH = r"D:\Ferramentas\UAssetGUI.exe"
UE_VERSION = "VER_UE4_26"    # Versão usada no processo fromjson

# Define o tamanho máximo de caracteres por arquivo de parte (evita erro de contexto da IA)
LIMITE_CARACTERES_POR_PARTE = 8000

# === CONFIGURAÇÃO DA IA (Local) ===
# Modelos gratis recomendados (do mais recomendado ao menos recomendado): "gemini-2.5-flash-lite" | "gemini-2.5-flash" | "gemini-3-flash-preview" | "gemini-3.1-flash-lite-preview"
MODELO_IA = "gemini-3.1-flash-lite-preview"
TEMP_TRADUCAO = 1.0 # Recomendado 0.6

API_KEY = ""

# === ESTRUTURA DE PASTAS (Fluxo de trabalho) ===
PASTA_JSON_ORIGINAL = os.path.join(BASE_DIR, "3_JSON_ORIGINAL") # Onde os JSONs extraídos ficam
PASTA_MOD_FINAL = os.path.join(BASE_DIR, "Traducao_PTBR_P")     # Onde os UAssets prontos são salvos

# Pastas de processamento intermediário (Pipeline)
PASTA_PARTES_1 = os.path.join(BASE_DIR, "4_partes_para_traduzir")      # JSON dividido em pedaços
PASTA_PARTES_2 = os.path.join(BASE_DIR, "5_partes_traduzidas")         # Retorno da IA
PASTA_PARTES_3 = os.path.join(BASE_DIR, "6_partes_verificadas")       # Validado e pronto para injetar

# === ARQUIVOS DE CONTROLE ===
ARQUIVO_JSON_TRADUZIDO = os.path.join(BASE_DIR, "json_PTBR.json")      # Arquivo final de injeção
ARQUIVO_STATUS = os.path.join(BASE_DIR, "projeto_status.json")        # Guarda o progresso do loop

# === KEYWORDS PARA FILTRO BINÁRIO (Passo 0) ===
# Estas keywords são usadas para escanear arquivos .uasset rapidamente antes de converter.
# Servem para descartar arquivos que não possuem texto.
KEYWORDS_BINARIAS: List[bytes] = {
    # Versões em UTF-8 (texto puro)
    b"LocalizedString",
    b"CultureInvariantString",
    b"TextPropertyData", 
    b"TextProperty",
    b"SourceString",
    b"FStringTable",
    b"StringTableExport",
    b"StrProperty",
    b"DisplayString",

    # Versões em UTF-16 (como a Unreal Engine salva internamente nos binários)
    b'L\x00o\x00c\x00a\x00l\x00i\x00z\x00e\x00d\x00S\x00t\x00r\x00i\x00n\x00g\x00',
    b'C\x00u\x00l\x00t\x00u\x00r\x00e\x00I\x00n\x00v\x00a\x00r\x00i\x00a\x00n\x00t\x00S\x00t\x00r\x00i\x00n\x00g\x00',
    b'T\x00e\x00x\x00t\x00P\x00r\x00o\x00p\x00e\x00r\x00t\x00y\x00D\x00a\x00t\x00a\x00',
    b'T\x00e\x00x\x00t\x00P\x00r\x00o\x00p\x00e\x00r\x00t\x00y\x00',
    b'S\x00o\x00u\x00r\x00c\x00e\x00S\x00t\x00r\x00i\x00n\x00g\x00',
    b'F\x00S\x00t\x00r\x00i\x00n\x00g\x00T\x00a\x00b\x00l\x00e\x00',
    b'S\x00t\x00r\x00i\x00n\x00g\x00T\x00a\x00b\x00l\x00e\x00E\x00x\x00p\x00o\x00r\x00t\x00',
    b'S\x00t\x00r\x00P\x00r\x00o\x00p\x00e\x00r\x00t\x00y\x00',
    b'D\x00i\x00s\x00p\x00l\x00a\x00y\x00S\x00t\x00r\x00i\x00n\x00g\x00',
}

# Chaves reais no JSON que possuem texto traduzível para o script de injeção
CHAVES_DE_TEXTO = {
    "SourceString",
    "LocalizedString",
    "CultureInvariantString",
    "DisplayString"
}