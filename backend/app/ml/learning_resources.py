"""Curated, free learning resources and portfolio project ideas.

Only official documentation or free first-party learning portals are listed.
When a skill has no curated entry, the recommendation says so instead of
guessing a link. Paid courses are never the only suggestion.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ml.taxonomy import category_of


@dataclass(frozen=True)
class Resource:
    title: str
    url: str
    provider: str
    cost: str = "free"


R = Resource

RESOURCES: dict[str, list[Resource]] = {
    "Python": [R("The Python Tutorial", "https://docs.python.org/3/tutorial/", "Python Software Foundation")],
    "SQL": [R("PostgreSQL Tutorial", "https://www.postgresql.org/docs/current/tutorial.html", "PostgreSQL Global Development Group")],
    "PostgreSQL": [R("PostgreSQL Tutorial", "https://www.postgresql.org/docs/current/tutorial.html", "PostgreSQL Global Development Group")],
    "MySQL": [R("MySQL Documentation", "https://dev.mysql.com/doc/", "Oracle")],
    "JavaScript": [R("JavaScript Guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "MDN Web Docs")],
    "TypeScript": [R("The TypeScript Handbook", "https://www.typescriptlang.org/docs/handbook/intro.html", "Microsoft")],
    "HTML": [R("Learn web development", "https://developer.mozilla.org/en-US/docs/Learn", "MDN Web Docs")],
    "CSS": [R("Learn web development", "https://developer.mozilla.org/en-US/docs/Learn", "MDN Web Docs")],
    "React": [R("Learn React", "https://react.dev/learn", "React team")],
    "Vue.js": [R("Vue.js Guide", "https://vuejs.org/guide/introduction.html", "Vue.js team")],
    "Angular": [R("Angular Tutorials", "https://angular.dev/tutorials", "Google")],
    "Node.js": [R("Learn Node.js", "https://nodejs.org/en/learn", "OpenJS Foundation")],
    "Django": [R("Writing your first Django app", "https://docs.djangoproject.com/en/stable/intro/tutorial01/", "Django Software Foundation")],
    "Flask": [R("Flask Tutorial", "https://flask.palletsprojects.com/en/stable/tutorial/", "Pallets")],
    "FastAPI": [R("FastAPI Tutorial – User Guide", "https://fastapi.tiangolo.com/tutorial/", "FastAPI")],
    "Tailwind CSS": [R("Tailwind CSS Documentation", "https://tailwindcss.com/docs", "Tailwind Labs")],
    "Java": [R("Learn Java", "https://dev.java/learn/", "Oracle")],
    "Kotlin": [R("Get started with Kotlin", "https://kotlinlang.org/docs/getting-started.html", "JetBrains")],
    "Go": [R("A Tour of Go", "https://go.dev/tour/", "The Go Authors")],
    "Rust": [R("The Rust Programming Language", "https://doc.rust-lang.org/book/", "The Rust Project")],
    "C#": [R("C# documentation", "https://learn.microsoft.com/en-us/dotnet/csharp/", "Microsoft Learn")],
    ".NET": [R(".NET documentation", "https://learn.microsoft.com/en-us/dotnet/", "Microsoft Learn")],
    "PHP": [R("PHP Manual – A simple tutorial", "https://www.php.net/manual/en/tutorial.php", "The PHP Group")],
    "Laravel": [R("Laravel Documentation", "https://laravel.com/docs", "Laravel")],
    "Git": [R("Pro Git (book)", "https://git-scm.com/book/en/v2", "git-scm.com")],
    "Docker": [R("Docker Get Started", "https://docs.docker.com/get-started/", "Docker")],
    "Kubernetes": [R("Kubernetes Basics", "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "CNCF")],
    "Linux": [R("The Linux command line for beginners", "https://ubuntu.com/tutorials/command-line-for-beginners", "Canonical")],
    "AWS": [R("AWS Skill Builder (free digital courses)", "https://skillbuilder.aws/", "Amazon Web Services")],
    "Microsoft Azure": [R("Azure training on Microsoft Learn", "https://learn.microsoft.com/en-us/training/azure/", "Microsoft Learn")],
    "Google Cloud": [R("Google Cloud training", "https://cloud.google.com/learn/training", "Google Cloud")],
    "Pandas": [R("Getting started with pandas", "https://pandas.pydata.org/docs/getting_started/index.html", "pandas")],
    "NumPy": [R("NumPy: the absolute basics for beginners", "https://numpy.org/doc/stable/user/absolute_beginners.html", "NumPy")],
    "scikit-learn": [R("scikit-learn Tutorials", "https://scikit-learn.org/stable/tutorial/index.html", "scikit-learn")],
    "Machine Learning": [R("Machine Learning Crash Course", "https://developers.google.com/machine-learning/crash-course", "Google for Developers")],
    "TensorFlow": [R("TensorFlow Tutorials", "https://www.tensorflow.org/tutorials", "Google")],
    "PyTorch": [R("PyTorch Tutorials", "https://pytorch.org/tutorials/", "PyTorch Foundation")],
    "Statistics": [R("Statistics and probability", "https://www.khanacademy.org/math/statistics-probability", "Khan Academy")],
    "Power BI": [R("Power BI training", "https://learn.microsoft.com/en-us/training/powerplatform/power-bi", "Microsoft Learn")],
    "Tableau": [R("Free Tableau training videos", "https://www.tableau.com/learn/training", "Tableau")],
    "Microsoft Excel": [R("Excel help & learning", "https://support.microsoft.com/en-us/excel", "Microsoft Support")],
    "Google Sheets": [R("Google Docs Editors Help – Sheets", "https://support.google.com/docs/", "Google")],
    "Apache Spark": [R("Spark Quick Start", "https://spark.apache.org/docs/latest/quick-start.html", "Apache Software Foundation")],
    "Apache Airflow": [R("Airflow Tutorials", "https://airflow.apache.org/docs/apache-airflow/stable/tutorial/index.html", "Apache Software Foundation")],
    "dbt": [R("What is dbt?", "https://docs.getdbt.com/docs/introduction", "dbt Labs")],
    "MongoDB": [R("MongoDB University", "https://learn.mongodb.com/", "MongoDB")],
    "Google Analytics": [R("Google Skillshop", "https://skillshop.withgoogle.com/", "Google")],
    "SEO": [R("SEO Starter Guide", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide", "Google Search Central")],
    "Scrum": [R("The Scrum Guide", "https://scrumguides.org/scrum-guide.html", "Scrum.org / Scrum Inc.")],
    "Agile": [R("The Scrum Guide", "https://scrumguides.org/scrum-guide.html", "Scrum.org / Scrum Inc.")],
    "Cybersecurity": [R("OWASP Top Ten", "https://owasp.org/www-project-top-ten/", "OWASP Foundation")],
    "Figma": [R("Figma Learn (help center)", "https://help.figma.com/hc/en-us", "Figma")],
    "Canva": [R("Canva Design School", "https://www.canva.com/designschool/", "Canva")],
    "Flutter": [R("Flutter documentation – Get started", "https://docs.flutter.dev/get-started", "Google")],
    "Android Development": [R("Android Basics with Compose", "https://developer.android.com/courses/android-basics-compose/course", "Google")],
}

PROJECT_IDEAS: dict[str, str] = {
    "Data & Analytics": "Pick a public Philippine dataset (e.g. from the PSA OpenSTAT portal), clean it, and publish an "
                         "analysis notebook plus a dashboard that answers one clear question.",
    "Programming Languages": "Build a small command-line tool that solves a real problem you have, with tests and a README.",
    "Web Development": "Ship a small full-stack app (e.g. a study-group scheduler) with authentication, a REST API and a "
                       "deployed frontend.",
    "Machine Learning & AI": "Train and evaluate a model on an open dataset; report a baseline, your model, the metric on a "
                             "held-out test set, and the limitations.",
    "Databases": "Design a normalised schema for a realistic domain (e.g. a barangay clinic), load sample data and write "
                 "ten documented queries.",
    "Cloud & DevOps": "Containerise one of your projects, add a CI pipeline that runs its tests, and deploy it to a free tier.",
    "Mobile Development": "Build a simple offline-first mobile app (e.g. an expense tracker) and publish the source with screenshots.",
    "Design": "Redesign one screen of a public website you use; document the problem, your research, wireframes and the final design.",
    "Security & IT": "Set up a home-lab or virtual machine, document the configuration and a troubleshooting log of issues you solved.",
    "Business & Office": "Automate a repetitive spreadsheet task (e.g. a monthly report) and write a one-page guide to it.",
    "Marketing & Content": "Plan and run a small content campaign for a student organisation; report reach and what you learned.",
    "Finance & Accounting": "Prepare a sample set of books for a fictional small business for one month, including reconciliations.",
    "Customer Support": "Write a mock knowledge-base article set for a product you know, and practise responses to common tickets.",
    "Project & Product Management": "Run a small team project with a visible board (e.g. Trello/Jira), sprint notes and a retrospective.",
    "Soft Skills": "Lead a student activity or volunteer project and keep a short written record of decisions and outcomes.",
    "Engineering Tools": "Add automated tests and a CI workflow to an existing project and document how to run them.",
}

DEMONSTRATION_TIPS: dict[str, str] = {
    "default": "Link the project from your resume's Projects section, name the skill explicitly, and describe one "
               "measurable outcome (what you built, for whom, and the result).",
    "Soft Skills": "Describe a specific situation, what you did and the result (STAR format) in your resume or interview.",
}


def resources_for(skill: str) -> list[Resource]:
    return RESOURCES.get(skill, [])


def project_idea_for(skill: str) -> str:
    category = category_of(skill) or "Programming Languages"
    return PROJECT_IDEAS.get(category, PROJECT_IDEAS["Programming Languages"])


def demonstration_tip(skill: str) -> str:
    category = category_of(skill)
    return DEMONSTRATION_TIPS.get(category or "", DEMONSTRATION_TIPS["default"])
