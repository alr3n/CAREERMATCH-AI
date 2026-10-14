"""Curated skill taxonomy.

Each entry has a canonical name, a category and aliases. Matching modes:

* default — case-insensitive, whole-word.
* ``case_sensitive=True`` — the canonical name must match case-sensitively
  ("React" the library vs. "react" the verb).
* alias prefixed with ``=`` — that alias is matched case-sensitively
  ("Excel" the product vs. "excel in a fast-paced team").
* ``strict=True`` — short or ambiguous names ("R", "Go", "C") are matched
  case-sensitively and only in contexts that look like a skills list (see
  ``skill_extractor``), to avoid false positives.

``RELATED_GROUPS`` lists skills that are closely related (e.g. different SQL
databases). A related skill earns *partial* credit during matching and is
always reported as "related", never as an exact match — the matcher must not
claim the user has a skill that is not in their resume.

The taxonomy is intentionally editable: add entries here to extend coverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SkillDef:
    name: str
    category: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    strict: bool = False
    case_sensitive: bool = False


def _s(name: str, category: str, *aliases: str, strict: bool = False, case_sensitive: bool = False) -> SkillDef:
    return SkillDef(
        name=name, category=category, aliases=tuple(aliases), strict=strict, case_sensitive=case_sensitive
    )


LANG = "Programming Languages"
WEB = "Web Development"
DATA = "Data & Analytics"
ML = "Machine Learning & AI"
DB = "Databases"
CLOUD = "Cloud & DevOps"
MOBILE = "Mobile Development"
DESIGN = "Design"
SEC = "Security & IT"
BIZ = "Business & Office"
MKT = "Marketing & Content"
FIN = "Finance & Accounting"
SUPPORT = "Customer Support"
PM = "Project & Product Management"
SOFT = "Soft Skills"
ENG = "Engineering Tools"

SKILLS: tuple[SkillDef, ...] = (
    # Programming languages
    _s("Python", LANG, "python3"),
    _s("Java", LANG),
    _s("JavaScript", LANG, "javascript", "js", "ecmascript", "es6"),
    _s("TypeScript", LANG, "typescript", "ts"),
    _s("C++", LANG, "cpp", "c plus plus"),
    _s("C#", LANG, "c sharp", "csharp"),
    _s("C", LANG, strict=True),
    _s("Go", LANG, "golang", strict=True),
    _s("Rust", LANG, strict=True),
    _s("Kotlin", LANG),
    _s("Swift", LANG, "swiftui", strict=True),
    _s("PHP", LANG),
    _s("Ruby", LANG),
    _s("R", LANG, "R programming", "RStudio", strict=True),
    _s("Scala", LANG),
    _s("Dart", LANG, strict=True),
    _s("MATLAB", LANG, "matlab"),
    _s("Bash", LANG, "shell scripting", "bash scripting", "shell script"),
    _s("PowerShell", LANG, "powershell"),
    _s("SQL", DB, "structured query language", "t-sql", "tsql", "pl/sql", "plsql"),
    _s("VBA", LANG, "excel vba", "visual basic for applications"),
    # Web
    _s("HTML", WEB, "html5"),
    _s("CSS", WEB, "css3"),
    _s("React", WEB, "react.js", "reactjs", "React JS", case_sensitive=True),
    _s("Next.js", WEB, "nextjs", "next js"),
    _s("Vue.js", WEB, "vue", "vuejs", "vue js"),
    _s("Angular", WEB, "angularjs", "angular.js"),
    _s("Svelte", WEB),
    _s("Node.js", WEB, "nodejs", "node js", "=Node"),
    _s("Express.js", WEB, "expressjs", "express js"),
    _s("Django", WEB),
    _s("Flask", WEB),
    _s("FastAPI", WEB, "fast api"),
    _s("Spring Boot", WEB, "spring framework", "springboot"),
    _s("Laravel", WEB),
    _s("Ruby on Rails", WEB, "=Rails", "ror"),
    _s("ASP.NET", WEB, "asp.net core", "aspnet"),
    _s(".NET", WEB, "dotnet", ".net core", ".net framework"),
    _s("Tailwind CSS", WEB, "tailwind", "tailwindcss"),
    _s("Bootstrap", WEB),
    _s("jQuery", WEB, "jquery"),
    _s("REST APIs", WEB, "rest api", "restful", "restful api", "restful apis", "=REST"),
    _s("GraphQL", WEB, "graphql"),
    _s("WordPress", WEB, "wordpress"),
    _s("Redux", WEB),
    _s("Web Accessibility", WEB, "accessibility", "wcag", "a11y"),
    # Mobile
    _s("Android Development", MOBILE, "android"),
    _s("iOS Development", MOBILE, "ios"),
    _s("Flutter", MOBILE),
    _s("React Native", MOBILE, "react-native"),
    # Data & analytics
    _s("Pandas", DATA, "pandas"),
    _s("NumPy", DATA, "numpy"),
    _s("Data Analysis", DATA, "data analytics", "analyzing data", "analyse data", "analyze data"),
    _s("Data Cleaning", DATA, "data wrangling", "data cleansing", "data preparation"),
    _s("Data Visualization", DATA, "data visualisation", "visualization", "dashboards", "dashboarding", "dashboard design"),
    _s("Statistics", DATA, "statistical analysis", "statistical", "hypothesis testing", "a/b testing"),
    _s("Microsoft Excel", BIZ, "=Excel", "ms excel", "advanced excel", "pivot tables", "vlookup", "xlookup"),
    _s("Google Sheets", BIZ, "google spreadsheets"),
    _s("Power BI", DATA, "powerbi", "power-bi", "microsoft power bi"),
    _s("Tableau", DATA),
    _s("Looker", DATA, "looker studio", "google data studio", "data studio"),
    _s("ETL", DATA, "etl pipelines", "elt", "data pipelines", "data pipeline"),
    _s("Apache Spark", DATA, "=Spark", "pyspark"),
    _s("Apache Airflow", DATA, "airflow"),
    _s("dbt", DATA, "data build tool", strict=True),
    _s("Hadoop", DATA),
    _s("Kafka", DATA, "apache kafka"),
    _s("Data Engineering", DATA),
    _s("Data Warehousing", DATA, "data warehouse", "snowflake", "bigquery", "redshift"),
    _s("Jupyter", DATA, "jupyter notebook", "jupyter notebooks", "jupyterlab"),
    _s("SAS", DATA, strict=True),
    _s("SPSS", DATA, "ibm spss"),
    _s("Google Analytics", MKT, "ga4", "google analytics 4"),
    # Machine learning
    _s("Machine Learning", ML, "=ML", "machine-learning"),
    _s("Deep Learning", ML, "neural networks", "neural network"),
    _s("scikit-learn", ML, "sklearn", "scikit learn"),
    _s("TensorFlow", ML, "tensorflow", "keras"),
    _s("PyTorch", ML, "pytorch", "torch"),
    _s("Natural Language Processing", ML, "nlp", "natural-language processing", "text mining"),
    _s("Computer Vision", ML, "opencv", "image processing"),
    _s("Large Language Models", ML, "llm", "llms", "generative ai", "genai", "prompt engineering"),
    _s("MLOps", ML, "mlflow", "model deployment"),
    _s("Feature Engineering", ML),
    # Databases
    _s("PostgreSQL", DB, "postgres", "postgresql", "psql"),
    _s("MySQL", DB, "mysql", "mariadb"),
    _s("SQL Server", DB, "microsoft sql server", "mssql", "ms sql"),
    _s("SQLite", DB),
    _s("Oracle Database", DB, "oracle db", "oracle sql"),
    _s("MongoDB", DB, "mongo"),
    _s("Redis", DB),
    _s("Firebase", DB, "firestore"),
    _s("Elasticsearch", DB, "elastic search", "opensearch"),
    # Cloud & DevOps
    _s("AWS", CLOUD, "amazon web services", "aws lambda", "ec2", "s3"),
    _s("Microsoft Azure", CLOUD, "azure"),
    _s("Google Cloud", CLOUD, "gcp", "google cloud platform"),
    _s("Docker", CLOUD, "containers", "containerization"),
    _s("Kubernetes", CLOUD, "k8s"),
    _s("Terraform", CLOUD),
    _s("CI/CD", CLOUD, "continuous integration", "continuous delivery", "continuous deployment", "github actions", "gitlab ci", "jenkins"),
    _s("Git", ENG, "github", "gitlab", "version control", "bitbucket"),
    _s("Linux", SEC, "unix", "ubuntu", "centos", "red hat"),
    _s("Unit Testing", ENG, "pytest", "jest", "junit", "automated testing", "test automation", "unit tests"),
    _s("Software Testing", ENG, "quality assurance", "qa testing", "manual testing", "selenium", "cypress", "playwright"),
    _s("Object-Oriented Programming", ENG, "oop", "object oriented programming", "object-oriented"),
    _s("Data Structures and Algorithms", ENG, "data structures", "algorithms", "dsa"),
    _s("Microservices", ENG, "microservice"),
    _s("System Design", ENG),
    _s("Agile", PM, "agile methodology", "agile development"),
    _s("Scrum", PM),
    _s("Jira", PM),
    # Security & IT
    _s("Cybersecurity", SEC, "cyber security", "information security", "infosec", "security operations"),
    _s("Networking", SEC, "computer networking", "tcp/ip", "network administration", "ccna", "lan/wan"),
    _s("Technical Support", SUPPORT, "it support", "help desk", "helpdesk", "desktop support", "troubleshooting"),
    _s("Windows Server", SEC, "active directory"),
    # Design
    _s("Figma", DESIGN),
    _s("UI/UX Design", DESIGN, "ui/ux", "ux design", "ui design", "user experience", "user interface design", "ux research", "wireframing", "prototyping"),
    _s("Adobe Photoshop", DESIGN, "photoshop"),
    _s("Adobe Illustrator", DESIGN, "illustrator"),
    _s("Adobe Premiere Pro", DESIGN, "premiere pro", "premiere"),
    _s("Canva", DESIGN),
    _s("Graphic Design", DESIGN, "visual design"),
    _s("Video Editing", DESIGN, "video production"),
    _s("AutoCAD", DESIGN, "autocad"),
    _s("SketchUp", DESIGN, "sketchup"),
    # Business / office
    _s("Microsoft Office", BIZ, "ms office", "microsoft 365", "office 365", "microsoft word", "ms word", "powerpoint"),
    _s("Google Workspace", BIZ, "g suite", "gsuite", "google docs"),
    _s("Data Entry", BIZ),
    _s("Business Analysis", BIZ, "business analyst", "requirements gathering", "requirements analysis"),
    _s("Technical Writing", BIZ, "technical documentation"),
    _s("Market Research", BIZ, "research skills"),
    # Marketing
    _s("Digital Marketing", MKT, "online marketing"),
    _s("Social Media Marketing", MKT, "social media management", "social media"),
    _s("SEO", MKT, "search engine optimization", "search engine optimisation"),
    _s("Content Writing", MKT, "content creation", "blog writing", "copywriting"),
    _s("Email Marketing", MKT, "mailchimp"),
    _s("Sales", BIZ, "selling", "business development", "lead generation", case_sensitive=True),
    _s("CRM", BIZ, "salesforce", "hubspot", "customer relationship management"),
    # Finance & accounting
    _s("Accounting", FIN, "general ledger", "accounts payable", "accounts receivable"),
    _s("Bookkeeping", FIN),
    _s("Financial Analysis", FIN, "financial modeling", "financial modelling", "budgeting", "forecasting"),
    _s("QuickBooks", FIN, "quickbooks"),
    _s("Xero", FIN),
    _s("Auditing", FIN, "audit", "internal audit"),
    _s("Taxation", FIN, "tax preparation", "tax compliance"),
    # Customer support / BPO
    _s("Customer Service", SUPPORT, "customer support", "customer care", "client support", "customer experience"),
    _s("Call Center Operations", SUPPORT, "call center", "call centre", "contact center", "bpo", "inbound calls", "outbound calls"),
    _s("Zendesk", SUPPORT),
    # HR
    _s("Recruitment", BIZ, "recruiting", "talent acquisition", "sourcing candidates"),
    _s("Human Resources", BIZ, "hr management", "human resource management"),
    # PM
    _s("Project Management", PM, "project coordination", "pmp"),
    _s("Product Management", PM, "product roadmap", "product owner"),
    # Soft skills
    _s("Communication", SOFT, "communication skills", "written communication", "verbal communication", "oral communication"),
    _s("English Proficiency", SOFT, "excellent english", "fluent in english", "english communication"),
    _s("Teamwork", SOFT, "collaboration", "team player"),
    _s("Leadership", SOFT, "team leadership", "led a team"),
    _s("Problem Solving", SOFT, "problem-solving", "analytical thinking", "critical thinking"),
    _s("Time Management", SOFT, "prioritization", "organizational skills", "multitasking"),
    _s("Attention to Detail", SOFT, "detail-oriented", "detail oriented"),
    _s("Presentation Skills", SOFT, "public speaking", "presentations"),
)

RELATED_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"SQL", "PostgreSQL", "MySQL", "SQL Server", "SQLite", "Oracle Database"}),
    frozenset({"MongoDB", "Firebase", "Redis", "Elasticsearch"}),
    frozenset({"Python", "Pandas", "NumPy", "Jupyter"}),
    frozenset({"Pandas", "Data Cleaning", "Data Analysis"}),
    frozenset({"Power BI", "Tableau", "Looker", "Data Visualization"}),
    frozenset({"Microsoft Excel", "Google Sheets"}),
    frozenset({"Microsoft Office", "Google Workspace"}),
    frozenset({"React", "Vue.js", "Angular", "Svelte", "Next.js"}),
    frozenset({"JavaScript", "TypeScript"}),
    frozenset({"HTML", "CSS", "Tailwind CSS", "Bootstrap"}),
    frozenset({"Django", "Flask", "FastAPI"}),
    frozenset({"Node.js", "Express.js"}),
    frozenset({"Java", "Kotlin", "Spring Boot"}),
    frozenset({"C#", ".NET", "ASP.NET"}),
    frozenset({"AWS", "Microsoft Azure", "Google Cloud"}),
    frozenset({"Docker", "Kubernetes"}),
    frozenset({"TensorFlow", "PyTorch", "Deep Learning"}),
    frozenset({"Machine Learning", "scikit-learn", "Deep Learning"}),
    frozenset({"Flutter", "React Native", "Android Development", "iOS Development"}),
    frozenset({"Figma", "UI/UX Design"}),
    frozenset({"Adobe Photoshop", "Adobe Illustrator", "Canva", "Graphic Design"}),
    frozenset({"Accounting", "Bookkeeping", "QuickBooks", "Xero"}),
    frozenset({"Customer Service", "Call Center Operations", "Technical Support", "Zendesk"}),
    frozenset({"Unit Testing", "Software Testing"}),
    frozenset({"Agile", "Scrum", "Jira"}),
    frozenset({"Digital Marketing", "Social Media Marketing", "SEO", "Email Marketing", "Content Writing"}),
    frozenset({"Apache Spark", "Hadoop", "Data Engineering", "ETL", "Apache Airflow", "Data Warehousing"}),
    frozenset({"Statistics", "Data Analysis", "R"}),
)

SKILL_BY_NAME: dict[str, SkillDef] = {s.name: s for s in SKILLS}
_LOWER_INDEX: dict[str, str] = {}
for _skill in SKILLS:
    _LOWER_INDEX[_skill.name.lower()] = _skill.name
    for _alias in _skill.aliases:
        _LOWER_INDEX.setdefault(_alias.lstrip("=").lower(), _skill.name)


def canonicalize(name: str) -> str:
    """Map a user-entered skill name to its canonical form when known.

    Unknown skills are kept (trimmed) so users can add skills the taxonomy
    does not cover yet.
    """
    cleaned = " ".join(name.strip().split())
    return _LOWER_INDEX.get(cleaned.lower(), cleaned)


def category_of(name: str) -> str | None:
    skill = SKILL_BY_NAME.get(name)
    return skill.category if skill else None


def related_skills(name: str) -> set[str]:
    related: set[str] = set()
    for group in RELATED_GROUPS:
        if name in group:
            related |= group
    related.discard(name)
    return related
