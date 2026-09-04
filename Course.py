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

class CourseOpportunity(BaseModel):
    title: str = Field(
        description="Exact title of the course, specialization, or certification."
    )

    platform: str = Field(
        description="Offering platform or portal (e.g., Coursera, NPTEL, Swayam, Udemy, edX, Udacity, YouTube)."
    )

    instructor_or_org: str = Field(
        description="University, institution, or instructor offering the course (e.g., IIT Kharagpur, Stanford, DeepLearning.AI)."
    )

    difficulty_level: str = Field(
        description="Target skill level. Must be one of: Beginner, Intermediate, Advanced, or All Levels."
    )

    duration: str = Field(
        description="Estimated duration or time commitment (e.g., '12 Weeks', '15 Hours', '3 Months'). Use 'Not specified' if missing."
    )

    skills: list[str] = Field(
        description="Key technical or practical skills covered in the course."
    )

    rating_or_price: str = Field(
        description="Course cost or star rating if available (e.g., 'Free Audit', 'Paid', '4.8 / 5'). Use 'Not specified' if missing."
    )

    deadline_or_start_date: str = Field(
        description="Upcoming start date, enrollment deadline, or 'Self-Paced'. Use 'Not specified' if unavailable."
    )

    course_url: str = Field(
        description="Direct URL to the official course enrollment or landing page."
    )

    source: str = Field(
        description="Website or platform domain where the course was indexed."
    )


class CourseSearchResult(BaseModel):
    query: str = Field(
        description="The original search query."
    )

    opportunities: list[CourseOpportunity] =Field(
        description="List of currently available relevant courses found through Google search."
    )


def system_prompt(selected_schema):

    return f"""
You are an expert course extractor for the users skill profile.

Your task is to extract relevant courses opportunities from
the Google search results provided to you.

Use ONLY the information present in the supplied search results.
Do not invent courses, platforms, deadlines, locations, skills,
eligibility requirements, or application links.

If a field is not available in the search results, use:
"Not specified"

For skills, return an empty list if no skills are mentioned.

For every course, identify:
- title
- platform
- instructor_or_org
- difficulty_level
- duration
- skills
- rating_or_price
- deadline_or_start_date
- course_url
- source

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

Extract the relevant courses opportunities from these
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
def csv_fallback(query: str, limit: int = 5, used_courses: set = None) -> list[dict]:
    """Fallback search over local courses.csv when live API fails or yields incomplete course data."""
    df = pd.read_csv("courses.csv").fillna("Not specified")

    if used_courses is None:
        used_courses = set()

    query_lower = query.lower()

    # -------------------------
    # Query keywords & stop words
    # -------------------------
    stop_words = {
        "course", "courses", "learn", "online", "certification", "certifications",
        "training", "in", "at", "for", "the", "2026", "2025", "find", "current", "available"
    }

    keywords = [
        word for word in query_lower.replace("-", " ").split()
        if len(word) > 2 and word not in stop_words
    ]

    # Domain keyword aliases
    aliases = {
        "ai": ["ai", "aiml", "artificial", "intelligence"],
        "ml": ["ml", "machine", "learning"],
        "genai": ["genai", "generative", "llm"],
        "llm": ["llm", "language", "model"],
        "python": ["python", "py"],
        "data": ["data", "analytics", "science"],
        "cloud": ["cloud", "aws", "azure", "gcp"],
        "web": ["web", "frontend", "backend", "fullstack"],
    }

    expanded_keywords = []
    for word in keywords:
        expanded_keywords.append(word)
        if word in aliases:
            expanded_keywords.extend(aliases[word])

    keywords = list(set(expanded_keywords))

    # -------------------------
    # Relevance scoring
    # -------------------------
    def score(row):
        title = str(row.get("title", "")).lower()
        skills = str(row.get("skills", "")).lower()
        platform = str(row.get("platform", "")).lower()
        instructor = str(row.get("instructor_or_org", "")).lower()

        match_score = 0
        for word in keywords:
            if word in title:
                match_score += 6
            elif word in skills:
                match_score += 4
            elif word in platform or word in instructor:
                match_score += 2

        return match_score

    candidates = df.copy()
    candidates["match_score"] = candidates.apply(score, axis=1)

    candidates = candidates[candidates["match_score"] > 0].sort_values(
        "match_score", ascending=False
    )

    results = []
    for _, row in candidates.iterrows():
        course_key = (
            str(row.get("title", "")).lower(),
            str(row.get("platform", "")).lower(),
            str(row.get("instructor_or_org", "")).lower(),
        )

        if course_key in used_courses:
            continue

        used_courses.add(course_key)
        results.append(row.to_dict())

        if len(results) >= limit:
            break

    return results


def get_course_opportunities(query: str) -> CourseSearchResult:
    """Fetches live course opportunities using Serper + Groq, falling back to local courses.csv on low quality or failure."""
    selected_schema = CourseSearchResult

    try:
        search_results = search(query)

        structured_data = fetch_client(
            selected_schema,
            system_prompt,
            search_results,
            query
        )

        final_courses = []
        used_courses = set()

        for course in structured_data.opportunities:
            # -------------------------
            # Count missing fields
            # -------------------------
            missing_count = 0
            for value in [
                course.title,
                course.platform,
                course.instructor_or_org,
                course.difficulty_level,
                course.duration,
                course.skills,
                course.rating_or_price,
                course.deadline_or_start_date,
                course.course_url,
                course.source,
            ]:
                if value in ["", None, "Not specified", []]:
                    missing_count += 1

            # -------------------------
            # GOOD LIVE RESULT
            # -------------------------
            if missing_count <= 3:
                course_key = (
                    course.title.lower(),
                    course.platform.lower(),
                    course.instructor_or_org.lower(),
                )
                used_courses.add(course_key)
                final_courses.append(course)

            # -------------------------
            # BAD LIVE RESULT (Fallback)
            # -------------------------
            else:
                matches = csv_fallback(
                    query,
                    limit=5,
                    used_courses=used_courses
                )

                for row in matches:
                    skills = [
                        x.strip()
                        for x in str(row.get("skills", ""))
                        .replace("|", ",")
                        .split(",")
                        if x.strip()
                    ]

                    fallback_course = CourseOpportunity(
                        title=str(row.get("title", "Not specified")),
                        platform=str(row.get("platform", "Not specified")),
                        instructor_or_org=str(row.get("instructor_or_org", "Not specified")),
                        difficulty_level=str(row.get("difficulty_level", "All Levels")),
                        duration=str(row.get("duration", "Not specified")),
                        skills=skills,
                        rating_or_price=str(row.get("rating_or_price", "Not specified")),
                        deadline_or_start_date=str(row.get("deadline_or_start_date", "Not specified")),
                        course_url=str(row.get("course_url", "Not specified")),
                        source=str(row.get("source", "Not specified")),
                    )
                    final_courses.append(fallback_course)

        # -------------------------
        # Remove accidental duplicates
        # -------------------------
        unique_courses = []
        seen = set()

        for course in final_courses:
            key = (
                course.title.lower(),
                course.platform.lower(),
                course.instructor_or_org.lower(),
            )
            if key not in seen:
                seen.add(key)
                unique_courses.append(course)

        return CourseSearchResult(
            query=query,
            opportunities=unique_courses[:10]
        )

    except Exception as e:
        print(f"Live search failed: {e}")

        # Complete API/Groq failure fallback
        matches = csv_fallback(query, limit=5)
        opportunities = []

        for row in matches:
            skills = [
                x.strip()
                for x in str(row.get("skills", ""))
                .replace("|", ",")
                .split(",")
                if x.strip()
            ]

            opportunities.append(
                CourseOpportunity(
                    title=str(row.get("title", "Not specified")),
                    platform=str(row.get("platform", "Not specified")),
                    instructor_or_org=str(row.get("instructor_or_org", "Not specified")),
                    difficulty_level=str(row.get("difficulty_level", "All Levels")),
                    duration=str(row.get("duration", "Not specified")),
                    skills=skills,
                    rating_or_price=str(row.get("rating_or_price", "Not specified")),
                    deadline_or_start_date=str(row.get("deadline_or_start_date", "Not specified")),
                    course_url=str(row.get("course_url", "Not specified")),
                    source=str(row.get("source", "Not specified")),
                )
            )

        return CourseSearchResult(
            query=query,
            opportunities=opportunities
        )
@app.route("/", methods=["GET"])
def index():

    return render_template("index.html")
@app.route("/courses",methods=["GET","POST"])
def courses():
    if request.method == "GET":
        return render_template("courses.html")

    query = request.form.get("query", "").strip()
    if not query:
        return render_template(
            "courses.html",
            error="Please enter a course search query."
        )
    try:
        result = get_course_opportunities(query)
        return render_template(
            "courses.html",
            message=result.model_dump()
        )
    except Exception as e:
        return render_template(
            "courses.html",
            error=f"An error occurred while processing your request: {str(e)}"
        )

    


if __name__ == "__main__":

    app.run(
        debug=True
    )