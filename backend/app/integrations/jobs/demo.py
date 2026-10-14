"""DEMO DATA provider — fictional listings for offline demonstrations.

Every company here is invented and every listing is labelled as demo data
throughout the API and UI (``is_demo = true``). Application links point to the
reserved ``example.com`` domain. This provider is disabled automatically when
``APP_ENV=production`` and can be turned off with ``ENABLE_DEMO_PROVIDER=false``.
It exists so the full workflow can be exercised and tested without network
access; it must never be presented as real vacancies.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.integrations.jobs.base import FetchResult, JobProvider, ProviderListing

DEMO_SUFFIX = " (Demo – fictional)"


def _job(
    jid: str,
    title: str,
    company: str,
    location: str,
    workplace: str | None,
    commitment: str,
    department: str,
    intro: str,
    responsibilities: list[str],
    requirements: list[str],
    nice: list[str],
    salary: tuple[int, int] | None = None,
    days_ago: int | None = None,
) -> dict:
    return locals()


_DEMO_JOBS: tuple[dict, ...] = (
    _job("da-intern-01", "Data Analyst Intern", "Bayanihan Analytics", "Makati, Metro Manila", "hybrid", "Internship",
         "Data", "Support our analytics team in turning operational data into insights.",
         ["Clean and prepare datasets for weekly reports", "Build dashboards for internal teams",
          "Document data definitions"],
         ["Currently enrolled in or recently graduated from a Statistics, Computer Science or related program",
          "Working knowledge of SQL", "Experience with Python and Pandas for data cleaning",
          "Proficiency in Microsoft Excel"],
         ["Experience with Power BI or Tableau is a plus", "Basic statistics knowledge"],
         salary=(12000, 15000), days_ago=3),
    _job("da-junior-02", "Junior Data Analyst", "Sampaguita Health Systems", "Quezon City, Metro Manila", "onsite",
         "Full-time", "Analytics", "Help our hospital network measure and improve patient services.",
         ["Write SQL queries against our reporting database", "Maintain Power BI dashboards",
          "Present findings to non-technical stakeholders"],
         ["0-1 years of experience in a data role", "Strong SQL skills", "Power BI or Tableau",
          "Good communication skills"],
         ["Python", "Experience with PostgreSQL"], salary=(25000, 35000), days_ago=8),
    _job("bi-intern-03", "Business Intelligence Intern", "Maharlika Finance Group", "Remote (Philippines)", "remote",
         "Internship", "Finance", "Join our BI team building reporting for lending operations.",
         ["Automate recurring Excel reports", "Prototype dashboards in Looker Studio"],
         ["Advanced Excel (pivot tables, XLOOKUP)", "Basic SQL", "Attention to detail"],
         ["Google Sheets automation", "Data Visualization portfolio"], days_ago=12),
    _job("se-intern-04", "Software Engineer Intern", "Northwind Labs PH", "Taguig, Metro Manila", "hybrid",
         "Internship", "Engineering", "Work with a product squad shipping web features.",
         ["Implement small features end-to-end", "Write unit tests", "Participate in code reviews"],
         ["Programming experience in JavaScript or Python", "Familiarity with Git",
          "Understanding of Data Structures and Algorithms"],
         ["React", "REST APIs", "Docker"], salary=(15000, 20000), days_ago=2),
    _job("fe-junior-05", "Junior Frontend Developer (React)", "Kalye Commerce", "Pasig, Metro Manila", "hybrid",
         "Full-time", "Engineering", "Build the storefront used by thousands of small sellers.",
         ["Build accessible UI components", "Integrate REST APIs", "Improve page performance"],
         ["1+ years of experience building web apps", "Strong JavaScript, HTML and CSS", "React",
          "Git"],
         ["TypeScript", "Tailwind CSS", "Web Accessibility (WCAG)"], salary=(35000, 50000), days_ago=5),
    _job("be-mid-06", "Backend Developer (Python)", "Northwind Labs PH", "Remote (Philippines)", "remote",
         "Full-time", "Engineering", "Own services that power our logistics platform.",
         ["Design and build APIs", "Maintain PostgreSQL schemas", "Operate services in AWS"],
         ["3+ years of professional experience with Python", "Django or FastAPI", "PostgreSQL",
          "REST APIs"],
         ["Docker and Kubernetes", "AWS", "CI/CD"], days_ago=20),
    _job("de-senior-07", "Senior Data Engineer", "Bayanihan Analytics", "Makati, Metro Manila", "hybrid",
         "Full-time", "Data", "Lead the design of our data platform.",
         ["Design ETL pipelines", "Mentor junior engineers", "Own data quality"],
         ["5+ years of experience in data engineering", "Python and SQL", "Apache Spark", "Apache Airflow"],
         ["Data Warehousing (BigQuery or Snowflake)", "Kafka"], days_ago=15),
    _job("ml-intern-08", "Machine Learning Intern", "Tala Research Studio", "Cebu City, Cebu", "onsite",
         "Internship", "Research", "Explore NLP models for Filipino-language text.",
         ["Run experiments and track results", "Prepare labelled datasets", "Summarise findings"],
         ["Python", "Basic Machine Learning knowledge", "scikit-learn or PyTorch"],
         ["Natural Language Processing", "Jupyter", "Statistics"], days_ago=6),
    _job("qa-intern-09", "QA Tester Intern", "Kalye Commerce", "Pasig, Metro Manila", "onsite", "Internship", "QA",
         "Help us ship reliable releases.",
         ["Execute test cases", "Report bugs clearly", "Help automate regression tests"],
         ["Attention to detail", "Basic understanding of Software Testing", "Good written communication"],
         ["Selenium or Playwright", "SQL"], days_ago=9),
    _job("ux-intern-10", "UI/UX Design Intern", "Tala Research Studio", "Remote (Philippines)", "remote",
         "Internship", "Design", "Design research tools used by our scientists.",
         ["Create wireframes and prototypes", "Run usability sessions"],
         ["Figma", "A portfolio of UI/UX Design work"], ["HTML and CSS", "Web Accessibility"], days_ago=4),
    _job("gd-11", "Graphic Designer", "Sampaguita Health Systems", "Quezon City, Metro Manila", "onsite",
         "Full-time", "Marketing", "Create materials for community health campaigns.",
         ["Design social media and print materials", "Maintain brand consistency"],
         ["Adobe Photoshop", "Adobe Illustrator", "1-2 years of experience in graphic design"],
         ["Video Editing", "Canva"], salary=(22000, 28000), days_ago=11),
    _job("it-support-12", "IT Support Associate", "Maharlika Finance Group", "Ortigas, Pasig", "onsite",
         "Full-time", "IT", "Keep our branch offices running smoothly.",
         ["Resolve help desk tickets", "Set up laptops and accounts", "Document fixes"],
         ["Technical Support or help desk experience (internships count)", "Windows and basic Networking",
          "Customer Service mindset"],
         ["Linux", "Active Directory"], salary=(20000, 26000), days_ago=7),
    _job("csr-13", "Customer Service Representative (Voice)", "Kapwa Contact Solutions", "Cebu City, Cebu", "onsite",
         "Full-time", "Operations", "Support customers of an international e-commerce brand.",
         ["Handle inbound calls and chats", "Log interactions in the CRM"],
         ["Excellent English communication skills", "Customer Service", "Fresh graduates welcome"],
         ["Call center experience is a plus", "Zendesk"], salary=(18000, 24000), days_ago=1),
    _job("tsr-14", "Technical Support Representative", "Kapwa Contact Solutions", "Remote (Philippines)", "remote",
         "Full-time", "Operations", "Troubleshoot software issues for SaaS customers.",
         ["Troubleshoot product issues", "Escalate bugs with clear reproduction steps"],
         ["Technical Support or troubleshooting experience", "Excellent English", "Problem Solving"],
         ["Basic SQL", "Jira"], salary=(25000, 32000), days_ago=10),
    _job("acct-15", "Accounting Assistant", "Maharlika Finance Group", "Makati, Metro Manila", "onsite", "Full-time",
         "Finance", "Support month-end close.",
         ["Prepare journal entries", "Reconcile accounts", "Assist auditors"],
         ["Graduate of BS Accountancy or related course", "Bookkeeping", "Microsoft Excel"],
         ["QuickBooks or Xero", "CPA eligibility is an advantage"], days_ago=14),
    _job("mkt-intern-16", "Digital Marketing Intern", "Kalye Commerce", "Remote (Philippines)", "remote",
         "Internship", "Marketing", "Grow our seller community online.",
         ["Plan social posts", "Write blog content", "Report campaign results"],
         ["Social Media Marketing", "Content Writing", "Good written English"],
         ["SEO", "Google Analytics", "Canva"], days_ago=3),
    _job("hr-intern-17", "HR Intern", "Bayanihan Analytics", "Makati, Metro Manila", "hybrid", "Internship", "People",
         "Support recruitment and employee programs.",
         ["Screen applications", "Schedule interviews", "Maintain HR records"],
         ["Psychology, HR or related course", "Microsoft Office", "Communication"],
         ["Recruitment experience", "Google Workspace"], days_ago=18),
    _job("pm-18", "Project Coordinator", "Northwind Labs PH", "Taguig, Metro Manila", "hybrid", "Full-time",
         "Operations", "Keep cross-functional projects on track.",
         ["Track milestones in Jira", "Run stand-ups", "Prepare status reports"],
         ["1+ years of experience in project coordination", "Agile or Scrum familiarity", "Time Management"],
         ["Jira", "Google Sheets"], days_ago=13),
    _job("android-19", "Junior Android Developer", "Tala Research Studio", "Cebu City, Cebu", "hybrid", "Full-time",
         "Engineering", "Build our field data-collection app.",
         ["Build features in Kotlin", "Write unit tests", "Fix crashes"],
         ["Kotlin or Java", "Android Development", "Git"], ["Firebase", "REST APIs"], days_ago=16),
    _job("sales-20", "Sales Associate (Part-time)", "Kalye Commerce", "Calapan, Oriental Mindoro", "onsite",
         "Part-time", "Sales", "Help local sellers join our marketplace.",
         ["Visit local businesses", "Explain our seller programme"],
         ["Communication", "Sales or customer-facing experience"], ["CRM tools"], days_ago=5),
)


class DemoProvider(JobProvider):
    provider = "demo"
    is_demo = True

    def __init__(self) -> None:
        super().__init__("demo", "DEMO DATA (fictional listings)")

    def fetch(self) -> FetchResult:
        now = datetime.now(timezone.utc)
        listings = []
        for job in _DEMO_JOBS:
            html = (
                f"<p><strong>DEMO DATA — this is a fictional listing for demonstration only.</strong></p>"
                f"<p>{job['intro']}</p>"
                "<h3>Responsibilities</h3><ul>" + "".join(f"<li>{x}</li>" for x in job["responsibilities"]) + "</ul>"
                "<h3>Requirements</h3><ul>" + "".join(f"<li>{x}</li>" for x in job["requirements"]) + "</ul>"
                "<h3>Nice to have</h3><ul>" + "".join(f"<li>{x}</li>" for x in job["nice"]) + "</ul>"
            )
            salary = job["salary"]
            listings.append(
                ProviderListing(
                    external_id=job["jid"],
                    title=job["title"],
                    company=job["company"] + DEMO_SUFFIX,
                    apply_url=f"https://example.com/demo-jobs/{job['jid']}",
                    content_html=html,
                    location=job["location"],
                    country="PH",
                    workplace_type=job["workplace"],
                    commitment=job["commitment"],
                    department=job["department"],
                    salary_min=Decimal(salary[0]) if salary else None,
                    salary_max=Decimal(salary[1]) if salary else None,
                    salary_currency="PHP" if salary else None,
                    salary_interval="per-month-salary" if salary else None,
                    posted_at=now - timedelta(days=job["days_ago"]) if job["days_ago"] is not None else None,
                )
            )
        return FetchResult(listings=listings)
