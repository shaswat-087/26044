print("Starting the Job and Internship Opportunity Search Engine...")
import json
from unittest import result
from groq import Groq   
from urllib import response
import requests
from flask import Flask,render_template, request,redirect, url_for, session
import os
from dotenv import load_dotenv
from pydantic import BaseModel,Field
from functools import lru_cache
import pandas as pd

load_dotenv()

SERPER_API_KEY = ""
GROQ_API_KEY = ""
app = Flask(__name__)
app.secret_key = 'your_key'

class JobOpportunity(BaseModel):
    title: str = Field(
        description="Exact job or internship title."
    )

    company: str = Field(
        description="Name of the hiring company or organization."
    )

    location: str = Field(
        description="Job location, such as Bangalore, Hyderabad, Remote, etc."
    )

    opportunity_type: str = Field(
        description="Must be one of: Internship, Full-time, Part-time, Contract, Apprenticeship."
    )

    work_mode: str = Field(
        description="Must be one of: On-site, Hybrid, Remote, Unknown."
    )

    eligibility: str = Field(
        description="Eligibility requirements such as degree, branch, year, experience or skills."
    )

    skills: list[str] = Field(
        description="Important technical or professional skills mentioned in the opportunity."
    )

    experience: str = Field(
        description="Required experience level. Use 'Fresher' if explicitly suitable for freshers."
    )

    salary_or_stipend: str = Field(
        description="Salary or stipend if available. Do not invent this information. Use 'Not specified' if unavailable."
    )

    deadline: str = Field(
        description="Application deadline if available. Use 'Not specified' if unavailable."
    )

    application_url: str = Field(
        description="Official application URL if available. Prefer the company's official careers page or official application page."
    )

    source: str = Field(
        description="Website/source where the opportunity was found."
    )

    posted_date: str = Field(
        description="Posting date if available. Use 'Not specified' if unavailable."
    )


class JobSearchResult(BaseModel):
    query: str = Field(
        description="The original search query."
    )

    opportunities: list[JobOpportunity] = Field(
        description="List of currently available relevant jobs and internships found through Google search."
    )


def system_prompt(selected_schema):

    return f"""
You are an expert job and internship information extractor.

Your task is to extract job and internship opportunities from
the Google search results provided to you.

Use ONLY the information present in the supplied search results.
Do not invent companies, salaries, deadlines, locations, skills,
eligibility requirements, or application links.

If a field is not available in the search results, use:
"Not specified"

For skills, return an empty list if no skills are mentioned.

For every opportunity, identify:
- title
- company
- location
- opportunity type
- work mode
- eligibility
- skills
- experience
- salary or stipend
- deadline
- application URL
- source
- posted date

You MUST return valid JSON matching exactly this Pydantic schema:

{json.dumps(selected_schema.model_json_schema(), indent=2)}

Do not return markdown.
Do not return explanations.
Do not return text outside the JSON object.
"""

def search(query: str):

    url = "https://google.serper.dev/search"

    payload = {
        "q": query,
        "num": 10
    }

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response=requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()

        return response.json()
    except Exception as e:
        print(f"Error in search: {str(e)}")
        raise


def fetch_client(selected_schema, system_prompt, search_results, query):
    try:
        client = Groq(
            api_key=GROQ_API_KEY
        )

        user_prompt = f"""
User search query:
{query}

Google search results retrieved through Serper:
{search_results}

Extract the relevant job/internship opportunities from these
search results and return them according to the provided schema.

Use only the information available in the search results.
Do not invent information.
"""

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",

            messages=[
                {
                    "role": "system",
                    "content": system_prompt(selected_schema)
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],

            response_format={
                "type": "json_object"
            },

            temperature=0.1,
            max_tokens=4000
        )

        content = response.choices[0].message.content

        result = selected_schema.model_validate_json(content)

        return result

    except Exception as e:
        print(f"Error in fetch_client: {e}")
        raise
def csv_fallback(query,limit=5,used_jobs=None):

    df=pd.read_csv("jobs.csv").fillna("Not specified")

    if used_jobs is None:
        used_jobs=set()

    query_lower=query.lower()

   
    locations=[
        "chennai","bengaluru","bangalore","hyderabad",
        "mumbai","pune","delhi","noida","gurugram","kolkata"
    ]

    location=""

    for city in locations:
        if city in query_lower:
            location=city
            break

    candidates=df.copy()

    if location:
        location_df=candidates[
            candidates["location"]
            .astype(str)
            .str.lower()
            .str.contains(location,na=False)
        ]

        if not location_df.empty:
            candidates=location_df

   
    stop_words={
        "job","jobs","in","at","for","the",
        "2026","2025","find","current","available"
    }

    keywords=[
        word for word in
        query_lower.replace("-"," ").split()
        if len(word)>2 and word not in stop_words
    ]

    
    aliases={
        "ai":["ai","aiml","artificial","intelligence"],
        "ml":["ml","machine","learning"],
        "genai":["genai","generative","ai"],
        "llm":["llm","language","model"],
        "cse":["software","developer","programmer"],
        "python":["python"],
        "data":["data","analytics","scientist"],
        "cloud":["cloud","aws","azure"],
        "web":["web","frontend","backend","full"],
    }

    expanded_keywords=[]

    for word in keywords:

        expanded_keywords.append(word)

        if word in aliases:
            expanded_keywords.extend(
                aliases[word]
            )

    keywords=list(set(expanded_keywords))

    # -------------------------
    # Relevance score
    # -------------------------
    def score(row):

        title=str(row["title"]).lower()
        skills=str(row["skills"]).lower()
        company=str(row["company"]).lower()

        score=0

        for word in keywords:

            if word in title:
                score+=6

            elif word in skills:
                score+=4

            elif word in company:
                score+=1

        if location:
            if location in str(row["location"]).lower():
                score+=5

        return score

    candidates["match_score"]=candidates.apply(
        score,
        axis=1
    )

    candidates=candidates[
        candidates["match_score"]>0
    ].sort_values(
        "match_score",
        ascending=False
    )

    results=[]

    
    for _,row in candidates.iterrows():

        job_key=(
            str(row["title"]).lower(),
            str(row["company"]).lower(),
            str(row["location"]).lower()
        )

        if job_key in used_jobs:
            continue

        used_jobs.add(job_key)

        results.append(
            row.to_dict()
        )

        if len(results)>=limit:
            break

    return results
def get_job_opportunities(query):

    selected_schema=JobSearchResult

    try:

        search_results=search(query)

        structured_data=fetch_client(
            selected_schema,
            system_prompt,
            search_results,
            query
        )

        final_jobs=[]
        used_jobs=set()

        for job in structured_data.opportunities:

            # -------------------------
            # Count missing fields
            # -------------------------
            missing_count=0

            for value in [
                job.title,
                job.company,
                job.location,
                job.opportunity_type,
                job.work_mode,
                job.eligibility,
                job.skills,
                job.experience,
                job.salary_or_stipend,
                job.deadline,
                job.application_url,
                job.source,
                job.posted_date
            ]:

                if value in ["",None,"Not specified",[]]:
                    missing_count+=1

            # -------------------------
            # GOOD LIVE RESULT
            # -------------------------
            if missing_count<=3:

                job_key=(
                    job.title.lower(),
                    job.company.lower(),
                    job.location.lower()
                )

                used_jobs.add(job_key)

                final_jobs.append(job)

            # -------------------------
            # BAD LIVE RESULT
            # -------------------------
            else:

                matches=csv_fallback(
                    query,
                    limit=5,
                    used_jobs=used_jobs
                )

                for row in matches:

                    skills=[
                        x.strip()
                        for x in str(row["skills"])
                        .replace("|",",")
                        .split(",")
                        if x.strip()
                    ]

                    fallback_job=JobOpportunity(
                        title=str(row["title"]),
                        company=str(row["company"]),
                        location=str(row["location"]),
                        opportunity_type=str(
                            row["opportunity_type"]
                        ),
                        work_mode=str(
                            row["work_mode"]
                        ),
                        eligibility=str(
                            row["eligibility"]
                        ),
                        skills=skills,
                        experience=str(
                            row["experience"]
                        ),
                        salary_or_stipend=str(
                            row["salary_or_stipend"]
                        ),
                        deadline=str(
                            row["deadline"]
                        ),
                        application_url=str(
                            row["application_url"]
                        ),
                        source=str(
                            row["source"]
                        ),
                        posted_date=str(
                            row["posted_date"]
                        )
                    )

                    final_jobs.append(fallback_job)

        # -------------------------
        # Remove accidental duplicates
        # -------------------------
        unique_jobs=[]
        seen=set()

        for job in final_jobs:

            key=(
                job.title.lower(),
                job.company.lower(),
                job.location.lower()
            )

            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        return JobSearchResult(
            query=query,
            opportunities=unique_jobs[:10]
        )

    except Exception as e:

        print(f"Live search failed: {e}")

        # Complete API/Groq failure
        matches=csv_fallback(
            query,
            limit=5
        )

        opportunities=[]

        for row in matches:

            opportunities.append(
                JobOpportunity(
                    title=str(row["title"]),
                    company=str(row["company"]),
                    location=str(row["location"]),
                    opportunity_type=str(
                        row["opportunity_type"]
                    ),
                    work_mode=str(
                        row["work_mode"]
                    ),
                    eligibility=str(
                        row["eligibility"]
                    ),
                    skills=[
                        x.strip()
                        for x in str(row["skills"])
                        .replace("|",",")
                        .split(",")
                        if x.strip()
                    ],
                    experience=str(
                        row["experience"]
                    ),
                    salary_or_stipend=str(
                        row["salary_or_stipend"]
                    ),
                    deadline=str(row["deadline"]),
                    application_url=str(
                        row["application_url"]
                    ),
                    source=str(row["source"]),
                    posted_date=str(
                        row["posted_date"]
                    )
                )
            )

        return JobSearchResult(
            query=query,
            opportunities=opportunities
        )
@app.route("/", methods=["GET"])
def index():

    return render_template("index.html")


@app.route("/jobs", methods=["GET", "POST"])
def jobs():

    if request.method == "GET":

        return render_template("jobs.html")

    query = request.form.get("query", "").strip()

    if not query:

        return render_template(
            "jobs.html",
            error="Please enter a job or internship search query."
        )
    try:
        result=get_job_opportunities(query)
        return render_template(
            "jobs.html",
            message=result.model_dump()
        )
    except Exception as e:
        return render_template(
            "jobs.html",
            error=f"An error occurred while processing your request: {str(e)}"
        )




@app.route("/internships", methods=["GET", "POST"])
def internships():

    if request.method == "GET":

        return render_template("internships.html")

    query = request.form.get("query", "").strip()

    if not query:

        return render_template(
            "internships.html",
            error="Please enter an internship search query."
        )


    internship_query = (
        f"{query} internship 2026 "
        "students freshers apply"
    )
    try:
        result=get_job_opportunities(internship_query)
        return render_template(
            "internships.html",
            message=result.model_dump()
        )
    except Exception as e:
        return render_template(
            "internships.html",
            error=f"An error occurred while processing your request: {str(e)}"
        )






if __name__ == "__main__":

    app.run(
        debug=True
    )