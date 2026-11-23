"""Built-in starter words so the vocabulary section works even without an API key.
Each entry: word, level, meaning (simple English), hindi, example, synonyms, antonyms."""

WORDS = [
    # ---------------- Beginner ----------------
    ("happy", "Beginner", "Feeling good and pleased.", "खुश", "She was happy to see her friend.", "glad, cheerful", "sad, unhappy"),
    ("friend", "Beginner", "A person you like and know well.", "दोस्त", "My friend helps me study.", "buddy, pal", "enemy, stranger"),
    ("kind", "Beginner", "Caring and gentle towards others.", "दयालु", "He is kind to everyone.", "gentle, caring", "cruel, rude"),
    ("quick", "Beginner", "Done in a short time; fast.", "तेज़", "Take a quick look at this.", "fast, rapid", "slow, late"),
    ("begin", "Beginner", "To start something.", "शुरू करना", "Let us begin the lesson.", "start, commence", "end, finish"),
    ("help", "Beginner", "To make something easier for someone.", "मदद करना", "Can you help me with this bag?", "assist, support", "harm, hinder"),
    ("simple", "Beginner", "Easy to understand or do.", "सरल", "The question was very simple.", "easy, plain", "difficult, complex"),
    ("strong", "Beginner", "Having a lot of power or strength.", "मज़बूत", "He is strong enough to lift the box.", "powerful, sturdy", "weak, fragile"),
    ("clean", "Beginner", "Not dirty.", "साफ़", "Please keep your room clean.", "tidy, spotless", "dirty, messy"),
    ("brave", "Beginner", "Not afraid to do something dangerous or hard.", "बहादुर", "The brave boy saved the puppy.", "fearless, bold", "cowardly, timid"),
    ("early", "Beginner", "Before the usual or expected time.", "जल्दी", "I wake up early every day.", "soon, ahead of time", "late, delayed"),
    ("tired", "Beginner", "Needing rest or sleep.", "थका हुआ", "I was tired after the long walk.", "sleepy, exhausted", "energetic, fresh"),

    # ---------------- Intermediate ----------------
    ("curious", "Intermediate", "Wanting to know or learn about things.", "जिज्ञासु", "Children are curious about everything.", "inquisitive, interested", "indifferent, uninterested"),
    ("improve", "Intermediate", "To become better or make something better.", "सुधारना", "Reading daily will improve your English.", "enhance, upgrade", "worsen, decline"),
    ("achieve", "Intermediate", "To succeed in doing something after effort.", "हासिल करना", "She worked hard to achieve her goal.", "accomplish, attain", "fail, lose"),
    ("challenge", "Intermediate", "Something difficult that tests your ability.", "चुनौती", "Learning a new language is a challenge.", "test, obstacle", "ease, help"),
    ("confident", "Intermediate", "Sure about your own abilities.", "आत्मविश्वासी", "He felt confident before the interview.", "assured, self-assured", "doubtful, insecure"),
    ("decision", "Intermediate", "A choice made after thinking.", "निर्णय", "It was a difficult decision to make.", "choice, resolution", "hesitation, doubt"),
    ("opportunity", "Intermediate", "A chance to do something good.", "अवसर", "This job is a great opportunity.", "chance, opening", "obstacle, setback"),
    ("responsible", "Intermediate", "Able to be trusted to do the right thing.", "ज़िम्मेदार", "She is a responsible student.", "dependable, accountable", "careless, irresponsible"),
    ("journey", "Intermediate", "A trip from one place to another.", "यात्रा", "The journey to Shimla took five hours.", "trip, voyage", "stay, arrival"),
    ("patient", "Intermediate", "Able to wait calmly without getting angry.", "धैर्यवान", "A good teacher is patient with students.", "calm, tolerant", "impatient, restless"),
    ("prefer", "Intermediate", "To like one thing more than another.", "पसंद करना", "I prefer tea to coffee.", "favour, choose", "dislike, reject"),
    ("reliable", "Intermediate", "Can be trusted to work well or tell the truth.", "भरोसेमंद", "He is a reliable friend.", "dependable, trustworthy", "unreliable, unsafe"),

    # ---------------- Advanced ----------------
    ("reluctant", "Advanced", "Not willing to do something.", "अनिच्छुक", "She was reluctant to share her plan.", "unwilling, hesitant", "eager, willing"),
    ("meticulous", "Advanced", "Very careful about small details.", "बारीकी से ध्यान रखने वाला", "He is meticulous about his notes.", "thorough, precise", "careless, sloppy"),
    ("resilient", "Advanced", "Able to recover quickly after problems.", "लचीला / हार न मानने वाला", "Resilient people learn from failure.", "tough, adaptable", "fragile, vulnerable"),
    ("ambiguous", "Advanced", "Having more than one possible meaning.", "अस्पष्ट", "The instructions were ambiguous.", "unclear, vague", "clear, explicit"),
    ("pragmatic", "Advanced", "Focused on practical results rather than theory.", "व्यावहारिक", "She took a pragmatic approach to the problem.", "practical, realistic", "idealistic, impractical"),
    ("inevitable", "Advanced", "Certain to happen; cannot be avoided.", "अपरिहार्य", "Change is inevitable in life.", "unavoidable, certain", "avoidable, uncertain"),
    ("eloquent", "Advanced", "Able to speak clearly and persuasively.", "वाक्पटु", "He gave an eloquent speech.", "articulate, expressive", "inarticulate, tongue-tied"),
    ("diligent", "Advanced", "Working carefully and with steady effort.", "मेहनती", "A diligent student revises every day.", "hardworking, industrious", "lazy, negligent"),
    ("substantial", "Advanced", "Large in amount or importance.", "काफ़ी / पर्याप्त", "She made a substantial improvement.", "considerable, significant", "tiny, insignificant"),
    ("scrutinize", "Advanced", "To examine something very carefully.", "बारीकी से जाँचना", "Auditors scrutinize every document.", "inspect, examine", "ignore, overlook"),
    ("mitigate", "Advanced", "To make something less harmful or severe.", "कम करना", "Trees help mitigate the effects of heat.", "reduce, lessen", "worsen, aggravate"),
    ("profound", "Advanced", "Very deep or strongly felt.", "गहरा", "The book had a profound effect on me.", "deep, intense", "shallow, superficial"),
]

FIELDS = ("word", "level", "meaning", "hindi", "example", "synonyms", "antonyms")
BANK = [dict(zip(FIELDS, w)) for w in WORDS]
