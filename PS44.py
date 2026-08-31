from groq import Groq
from flask import Flask,render_template,redirect,url_for,jsonify,request
import json
import os

class TreeNode:
    def __init__(self,name,node_type="Course",payload="None"):
        self.name=name
        self.node_type=node_type
        self.children=[]
        self.payload=payload
    def add_child(self,child_node):
        self.children.append(child_node)

    def to_dict(self):
        formatted_children = []
        for child in self.children:
            if isinstance(child, TreeNode):
                formatted_children.append(child.to_dict())
            else:
                # Converts string children into structured nodes automatically
                formatted_children.append({
                    "name": str(child),
                    "node_type": "Topic",
                    "children": []
                })

        return {
            "name": self.name,
            "node_type": self.node_type,
            "payload": self.payload,
            "children": formatted_children
        }
       
#Level 1: Major Academic Courses
root=TreeNode("Academic Major Course","Root")
sub1=TreeNode("Engineering & Technology")
sub2=TreeNode("Management & Bussiness")
sub3=TreeNode("Pure & Applied Sciences")
sub4=TreeNode("Humanities & Arts")
sub5=TreeNode("Medical & Healthcare")

root.add_child(sub1)
root.add_child(sub2)
root.add_child(sub3)
root.add_child(sub4)
root.add_child(sub5)
#Level 2: Department/Specializations 

#Engineering Departments
sub1.add_child("Aerospace Engineering")
sub1.add_child("Biotechnology Engineering")
sub1.add_child("Chemical Engineering")
sub1.add_child("Civil Engineering")
sub1.add_child("Computer Science and Engineering")
sub1.add_child("Electrical Engineering")
sub1.add_child("Electronics and Communication Engineering")
sub1.add_child("Mathematics and Computing")
sub1.add_child("Mechanical Engineering")
sub1.add_child("Metallurgical and Materials Engineering")
sub1.add_child("Other Engineering Disciplines")

# Commerce/Management Courses
sub2.add_child("Accounting and Finance")
sub2.add_child("Business Analytics")
sub2.add_child("Financial Management")
sub2.add_child("Healthcare Management")
sub2.add_child("Human Resource Management")
sub2.add_child("Information Technology Management")
sub2.add_child("International Business")
sub2.add_child("Marketing Management")
sub2.add_child("Operations Management")
sub2.add_child("Supply Chain Management")
sub2.add_child("Other Management & Commerce Fields")

#Pure and Applied Science Courses

sub3.add_child("Mathematics")
sub3.add_child("Physics")
sub3.add_child("Botany")
sub3.add_child("Zoology")
sub3.add_child("Chemistry")
sub3.add_child("Geology")
sub3.add_child("Statistics")
sub3.add_child("Microbiology")
sub3.add_child("Applied Mathematics")
sub3.add_child("Applied Physics")
sub3.add_child("Applied Chemistry")
sub3.add_child("Environmental Science")
sub3.add_child("Other Natural & Applied Sciences")

#Humanities and Arts Subjects

sub4.add_child("Anthropology")
sub4.add_child("Economics")
sub4.add_child("English")
sub4.add_child("Fine Arts")
sub4.add_child("Geography")
sub4.add_child("History")
sub4.add_child("Indian Languages")
sub4.add_child("Linguistics")
sub4.add_child("Performing Arts")
sub4.add_child("Philosophy")
sub4.add_child("Political Science")
sub4.add_child("Psychology")
sub4.add_child("Sociology")
sub4.add_child("Other Humanities & Arts Disciplines")


#Medical & Healthcare subjects

sub5.add_child("Ayurveda")
sub5.add_child("Homeopathy & Complementary medicines") 
sub5.add_child("Clinical Medicine")
sub5.add_child("Dental Sciences")
sub5.add_child("Surgical Sciences")
sub5.add_child("Women & Child Health") 
sub5.add_child("Nursing")
sub5.add_child("Pathology & Diagnostics")
sub5.add_child("Pharmaceutical Sciences")
sub5.add_child("Physical Therapy & Rehabilitation")
sub5.add_child("Psychiatry & Behavioral Health")
sub5.add_child("Public Health & Community Medicine")
sub5.add_child("Other Medical & Healthcare Disciplines")


   

def system_prompt1(subject_node,subdomain_list,year):
    return f""" You are an expert AI analyst and skill assessment engine. Generate ONLY ONE subdomain
    under {subject_node.name} which is taught in standard academic courses under {subject_node.name}
    and used in modern industry practices.
    DO NOT repeat subdomain which is already present in {subdomain_list}.
    Target audience: Year {year} college student.
    For instance  if {subject_node.name} is Computer Science & Engineering , the subdomain maybe any programming language such as
    OOPS,Web development,AI/ML,Data Structures and more. 
    if {subject_node.name}  is Mechanical Engineering ,then subdomains may include - CAD/CAM, FEA, CFD, Automobile etc.
    Similar thing will be followed for all the chosen {subject_node.name}.
    Year Guidance for Subdomains:
   - Year 1/2: Core foundations (e.g., Basic OOP, Data Types, Arrays, Elementary Algorithms, Basic SQL).
-   Year 3/4: Applied/Advanced topics (e.g., System Design, Cloud Architecture, ML Deployment, Microservices).
    STRICT REQUIREMENT: Output must be a valid JSON object matching this schema:
   {{
  "subdomain": "Name of Subdomain"
   }}
    
    """

def fetch_client1(subject_node,subdomain_list,year):
     client=Groq(api_key="YOUR_API_KEY") #Replace this with your actual API key here     
     user_prompt=f"Generate one subdomain for {subject_node.name}."
     response=client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role":"system",
                "content":system_prompt1(subject_node,subdomain_list,year),
            },
            {
                "role":"user",
                "content":user_prompt,
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=1000,
       )
     return response.choices[0].message.content

def system_prompt2(current_depth,subject_node,subdomain_list,tool,year):
    topic=subdomain_list[current_depth]
    return f"""
    You are an expert AI skill assessment engine for 'Portal for Academia- Industry collaboration'.
    PROBLEM STATEMENT:
    A significant gap exists between the skills acquired in academic institutions and the competencies expected by industries. Students often struggle to identify the skills required for their desired career paths, while industries face challenges in finding candidates with the right skill sets. Similarly, academicians have limited visibility into industry internship opportunities that could help them gain practical exposure and align teaching with current industry practices. There is a need for a unified platform that connects students, industries, and academicians, enabling seamless collaboration and skill development.
    
    Generate a question based on {topic} to assess the skills of the user in following topic in STRICT JSON format.
    Target audience: Year {year} college student.
    INSTRUCTIONS:
       1. If the user answered "No Idea" or "skip",DO NOT ask deeper questions on that tool. Ask questions from a completely different sub-topic under {subject_node.name}.
       2.There will be two types of questions-
       a.SKILL_PICKER: To ask about awareness and skills about a specific subdomain under {subject_node.name} for in general questions. 
       b.CONCEPT:One concept based question from {topic} ,relevant to {tool} to evaluate if the user really has some knowledge about it. It must involve questions that bridge the academics-industry gap and fit current requirements.
       3. The difficulty level of questions should be based on {year}. 
       a. Ask extremely basic level questions for Year==1, 
       b. Basic to intermediate level questions for Year==2, 
       c. Intern level questions for Year==3, 
       d. Production or Industry level questions for Year==4 and above.
       JSON Schema:
       {{
         "question_type": "CONCEPT",
         "question": "The question string",
         "options": ["Option A","Option B","Option C","Option D","No idea"],
         "correct_option_index": 0,
         "difficulty": "{year} Year"
       

       }}
    """

def fetch_client2(current_depth,subject_node,subdomain_list,tool,year):
     client=Groq(api_key="YOUR_API_KEY") #Replace your actual Groq API key here     
     
     user_prompt2=f"Generate one question for assessment."
     response=client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role":"system",
                "content":system_prompt2(current_depth,subject_node,subdomain_list,tool,year),
            },
            {
                "role":"user",
                "content":user_prompt2,
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=2000,
       )
     return response.choices[0].message.content

app=Flask(__name__)
@app.route("/")
def home():
    return render_template('register2.html',
        academic_tree=root.to_dict(),
     )

@app.route('/register',methods=['POST'])
def register():
    data=request.form
    username=data.get('username')
    year=data.get('class')
    domain=data.get('domain')
    subject=data.get('stream')
    tool=data.get('section')

    current_depth=0
    subject_node=TreeNode(name=subject,node_type="Specialization")
    
    subdomain_list=[]
    raw_subdomain=fetch_client1(subject_node, subdomain_list,year)
    subdomain_data=json.loads(raw_subdomain) if isinstance(raw_subdomain, str) else raw_subdomain
    subdomain=subdomain_data.get("subdomain", raw_subdomain)

    subdomain_list.append(subdomain)
    subject_node.add_child(TreeNode(name=subdomain, node_type="Subdomain"))

    question_raw=fetch_client2(
        current_depth=current_depth,
        subject_node=subject_node,
        subdomain_list=subdomain_list,
        tool=tool,
        
        year=year
    )
    
    question_data=json.loads(question_raw) if isinstance(question_raw,str) else question_raw

    return render_template(
        'register.html',
        academic_tree=subject_node.to_dict(),
        target_subdomain=subdomain,
        subdomain_list=subdomain_list,
        assessment_question=question_data,
        subject=subject,
        current_depth=current_depth)
@app.route('/next_question',methods=['POST'])
def next_question():
    data=request.form
    current_depth=int(data.get('current_depth',0))+1
    max_depth=12
    raw_subdomains=data.get('subdomain_list','[]')
    subdomain_list=json.loads(raw_subdomains) if isinstance(raw_subdomains,str) else raw_subdomains
    username=data.get('username')
    year=data.get('class')
    domain=data.get('domain')
    subject=data.get('stream')
    tool=data.get('section')
    message=[]
    if current_depth>=max_depth:
        message="<h1>Assessment Complete!</h1><p>Great job, {username}!</p>"
        return render_template('register.html',message=message)
    subject_node=TreeNode(name=subject,node_type="Specialization")
    raw_subdomain=fetch_client1(subject_node,subdomain_list,year)
    subdomain_data=json.loads(raw_subdomain) if isinstance(raw_subdomain,str) else raw_subdomain
    subdomain=subdomain_data.get("subdomain",raw_subdomain)
    subdomain_list.append(subdomain)
    subject_node.add_child(TreeNode(name=subdomain,node_type="Subdomain"))
    question_raw=fetch_client2(
        current_depth=current_depth,
        subject_node=subject_node,
        subdomain_list=subdomain_list,
        tool=tool,
        year=year
    )
    question_data=json.loads(question_raw) if isinstance(question_raw,str) else question_raw
    return render_template('register.html',
        academic_tree=subject_node.to_dict(),
        target_subdomain=subdomain,
        username=username,
        year=year,
        subject=subject,
        subdomain_list=subdomain_list,
        assessment_question=question_data,
        current_depth=current_depth,
        )

if __name__=="__main__":
    app.run(debug=True)
