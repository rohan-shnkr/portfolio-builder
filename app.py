import streamlit as st
import requests
import base64
from openai import OpenAI
import io
import zipfile
import re

########################################
# Helper Functions
########################################

def fetch_github_repos(username):
    """Fetch the list of user repos from GitHub API."""
    url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def fetch_repo_readme(owner, repo):
    """Fetch the README contents (in markdown) for a given repo."""
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        content = data.get("content", "")
        # Content is base64-encoded markdown
        decoded = base64.b64decode(content).decode('utf-8', errors='replace')
        return decoded
    return ""

def call_openai_api(prompt, api_key, max_tokens=600):
    """Generic helper to call OpenAI completions API with a given prompt."""
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(model="gpt-4",
    messages=[{"role":"user", "content": prompt}],
    max_tokens=max_tokens,
    temperature=0.7)
    return completion.choices[0].message.content.strip()

def generate_landing_page_text(name, interests, api_key):
    prompt = f"""
You are a professional copywriter. The user is building a personal portfolio landing page.
They have these interests: {interests}.
The main landing page should say "Hi, I'm {name}" and provide a brief by-line of who they are and what this website is about.
Write a short, friendly, and engaging paragraph (3-4 sentences) that gives a welcoming introduction, 
mentions their interests, and sets the tone for the portfolio website.
    """
    return call_openai_api(prompt, api_key)

def generate_about_me_text(name, interests, github_username, api_key):
    prompt = f"""
You are a professional copywriter. Create an 'About Me' section for a personal website.
The subject's name is {name}, GitHub username is {github_username}, and they have the following interests: {interests}.
Write about 2-3 paragraphs that highlight their professional background, personal interests, 
and what they enjoy working on, in a friendly, authentic tone.
    """
    return call_openai_api(prompt, api_key)

def categorize_projects(readmes, api_key):
    # readmes is a list of (repo_name, readme_content)
    # Step 1: Extract keywords/themes from each README individually
    project_keywords = []
    for rname, rmd in readmes:
        prompt = f"""
You are an assistant that extracts keywords and main themes from a project's README.
Given the README below, list a set of keywords or short phrases that represent the main topics, technologies, or domains the project involves. 
Just return a concise list of keywords, max 4 (e.g., ["machine learning", "NLP", "Python"]).

README for {rname}:
{rmd}
"""
        keywords_str = call_openai_api(prompt, api_key, max_tokens=10)
        # Attempt to parse the keywords_str as a list, or if it fails, just store as string
        # The assistant might return something like `["keyword1", "keyword2"]`
        # We'll do a best effort to extract them.
        # If the model returns a JSON-like structure, try parsing, else just store as is.
        import json
        extracted_keywords = []
        # Try JSON parsing
        try:
            extracted_keywords = json.loads(keywords_str)
            if not isinstance(extracted_keywords, list):
                # If it's not a list, fallback
                extracted_keywords = [keywords_str.strip()]
        except:
            # If JSON fails, try splitting by commas
            # This is a fallback. Adjust as needed.
            extracted_keywords = [kw.strip() for kw in keywords_str.replace('"', '').replace('[', '').replace(']', '').split(',') if kw.strip()]

        # Store tuple of (repo_name, [keywords])
        project_keywords.append((rname, extracted_keywords))

    # Step 2: Now we have a list of (repo_name, keywords)
    # We call the LLM again with all keywords to define categories and assign projects.
    # We'll structure a prompt that includes all keywords.
    keywords_description = ""
    for rname, kws in project_keywords:
        keywords_description += f"Project: {rname}\nKeywords: {', '.join(kws)}\n\n"

    prompt_for_categories = f"""
You are an assistant that now has a list of projects with extracted keywords. 
Your task:
1) Identify up to 4 categories that best classify these projects based on their keywords.
2) Assign each project to one of these categories.
3) For each project, produce a short (1 sentence, max 10 words) summary based on the keywords (be creative but consistent with keywords).

Return the results in a structured JSON format as follows:

{{
  "categories": ["Category1", "Category2", ...],
  "projects": [
     {{
       "name": "project_name",
       "category": "CategoryX",
       "summary": "Short summary..."
     }},
     ...
  ]
}}

If a project doesn't fit into main categories, use "Other".
    
Here is the data:
{keywords_description}
"""

    response = call_openai_api(prompt_for_categories, api_key, max_tokens=1500)

    # Parse the response as JSON
    import json
    try:
        data = json.loads(response)
    except:
        # If parsing fails, fallback: just put everything in "Other"
        data = {
            "categories": ["Other"],
            "projects": []
        }
        for rname, _ in project_keywords:
            data["projects"].append({
                "name": rname,
                "category": "Other",
                "summary": "No summary available."
            })
    return data

def get_contrast_text_color(hex_color):
    # Remove '#' if present
    hex_color = hex_color.lstrip('#')
    # Parse hex into RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # Calculate luminance using a standard formula
    # This formula uses relative luminance in sRGB color space
    # Normalize r, g, b to 0.0 - 1.0
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    # Apply sRGB companding
    def srgb_to_lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    R = srgb_to_lin(r_norm)
    G = srgb_to_lin(g_norm)
    B = srgb_to_lin(b_norm)

    # Relative luminance
    luminance = 0.2126 * R + 0.7152 * G + 0.0722 * B

    # Choose white for dark backgrounds and dark grey for light backgrounds
    # A common threshold is around 0.5, but you can tweak it.
    if luminance < 0.5:
        return "#fff"   # Light text if background is dark
    else:
        return "#333"   # Dark text if background is light

def generate_html_files(name, about_me_text, landing_text, resume_filename, categories_data, github_username, color_scheme):
    # categories_data is a dict with keys "categories" and "projects"
    categories = categories_data.get("categories", [])
    projects = categories_data.get("projects", [])
    header_text_color = get_contrast_text_color(color_scheme)

    # Basic styling with color scheme
    # We'll assume color_scheme is something like a hex code or a named color.
    # We'll create a simple CSS using CSS variables:
    css = f"""
:root {{
  --main-color: {color_scheme};
  --text-color: #333;
}}

html, body {{
  margin: 0;
  padding: 0;
}}

body {{
  font-family: 'Roboto', sans-serif;
  background: #f7f7f7;
  color: var(--text-color);
}}

header, nav, footer {{
  background: var(--main-color);
  color: {header_text_color};
  padding: 1em;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}}

header h1 {{
  font-family: 'Rufina', serif;
  font-size: 2.5rem;
  font-weight: 700;
  margin: 0;
  text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
  letter-spacing: 0.5px;
  color: {header_text_color};
}}

nav a {{
  margin-right: 1em;
  color: {header_text_color};
  text-decoration: none;
  font-weight: bold;
}}

nav a:hover {{
  text-decoration: underline;
}}

main {{
  padding: 2em;
  background: #fff;
  max-width: 900px;
  margin: 2em auto;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
}}

main.landing {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 70vh;
}}

h2, h3, h4, h5, h6 {{
  font-family: 'Rufina', serif;
  color: var(--main-color);
  text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
}}

.project-tile {{
  background: #fff;
  border: none;
  padding: 1em;
  margin-bottom: 1em;
  border-radius: 5px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}}

.project-category {{
  font-family: 'Rufina', serif;
  font-weight: bold;
  margin-top: 2em;
  font-size: 1.5em;
  color: var(--main-color);
}}
"""
#     css = f"""
# :root {{
#   --main-color: {color_scheme};
#   --text-color: #333;
# }}

# html, body {{
#   margin: 0;
#   padding: 0;
# }}

# body {{
#   font-family: 'Roboto', sans-serif;
#   background: #f7f7f7;
#   color: var(--text-color);
# }}

# header, nav, footer {{
#   background: var(--main-color);
#   color: #fff;
#   padding: 1em;
#   box-shadow: 0 2px 5px rgba(0,0,0,0.1);
# }}

# nav a {{
#   margin-right: 1em;
#   color: #fff;
#   text-decoration: none;
#   font-weight: bold;
# }}

# nav a:hover {{
#   text-decoration: underline;
# }}

# main {{
#   padding: 2em;
#   background: #fff;
#   max-width: 900px;
#   margin: 2em auto;
#   border-radius: 8px;
#   box-shadow: 0 2px 5px rgba(0,0,0,0.05);
# }}

# main.landing {{
#   display: flex;
#   flex-direction: column;
#   align-items: center;
#   justify-content: center;
#   text-align: center;
#   min-height: 70vh;
# }}

# h1, h2, h3, h4, h5, h6 {{
#   font-family: 'Rufina', serif;
#   color: var(--main-color);
#   text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
# }}

# .project-tile {{
#   background: #fff;
#   border: none;
#   padding: 1em;
#   margin-bottom: 1em;
#   border-radius: 5px;
#   box-shadow: 0 1px 3px rgba(0,0,0,0.1);
# }}

# .project-category {{
#   font-family: 'Rufina', serif;
#   font-weight: bold;
#   margin-top: 2em;
#   font-size: 1.5em;
#   color: var(--main-color);
# }}
# """

    # Simple nav bar
    nav = f"""
<nav>
  <a href="index.html">Home</a>
  <a href="about.html">About Me</a>
  <a href="resume.html">Resume</a>
  <a href="projects.html">Projects</a>
</nav>
"""

    # index.html
    index_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<title>{name}'s Portfolio</title>
<link href="https://fonts.googleapis.com/css2?family=Rufina:wght@400;700&family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>{name}'s Portfolio</h1>
  {nav}
</header>
<main>
  <h2>Hi, I'm {name}</h2>
  <p>{landing_text}</p>
</main>
<footer>
  <p>© {name}'s Portfolio</p>
</footer>
</body>
</html>
"""

    # about.html
    # Fetch github avatar
    avatar_url = f"https://github.com/{github_username}.png"
    about_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<title>About {name}</title>
<link href="https://fonts.googleapis.com/css2?family=Rufina:wght@400;700&family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>About {name}</h1>
  {nav}
</header>
<main>
  <img src="{avatar_url}" alt="{name}'s Avatar" style="max-width:150px;border-radius:50%;margin-bottom:1em;">
  <div>
    {about_me_text}
  </div>
</main>
<footer>
  <p>© {name}'s Portfolio</p>
</footer>
</body>
</html>
"""

    # resume.html
    # We'll embed the PDF in an <iframe> for viewing, and also provide a link to download
    resume_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<title>{name}'s Resume</title>
<link href="https://fonts.googleapis.com/css2?family=Rufina:wght@400;700&family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>{name}'s Resume</h1>
  {nav}
</header>
<main>
  <p>View my resume below:</p>
  <iframe src="{resume_filename}" style="width:100%;height:600px;" title="Resume"></iframe>
  <p><a href="{resume_filename}" download>Download PDF</a></p>
</main>
<footer>
  <p>© {name}'s Portfolio</p>
</footer>
</body>
</html>
"""

    # projects.html
    # We will group projects by category
    # Capitalize the first letter of each repo name
    # Render short summary (already given in plain text)
    # Each project tile: name, summary, links (to repo, to homepage if any)
    # We can attempt to link to a homepage if the repo has a 'homepage' field from GitHub data,
    # but we need to store that info. For simplicity, we'll just store from categories_data if present.
    # We'll rely on original name in `projects`.

    # We need to produce a map of categories to projects
    category_map = {}
    for p in projects:
        cat = p.get("category", "Other")
        category_map.setdefault(cat, []).append(p)

    projects_html_sections = ""
    for cat in categories:
        # cat projects
        cat_projects = category_map.get(cat, [])
        projects_html_sections += f'<div class="project-category">{cat}</div>'
        for proj in cat_projects:
            pname = proj.get("name","")
            summary = proj.get("summary","")
            # We'll guess that the GitHub page is `https://github.com/<username>/<repo>`
            # Also if there's a homepage link, we must have saved it beforehand. But we didn't. Let's skip that.
            repo_url = f"https://github.com/{github_username}/{pname}"
            # We try to handle capitalization:
            display_name = pname.capitalize()
            projects_html_sections += f"""
<div class="project-tile">
  <h3>{display_name}</h3>
  <p>{summary}</p>
  <p><a href="{repo_url}" target="_blank">View Repository</a></p>
</div>
"""

    # If there are categories not recognized or no categories, handle that:
    for cat, cat_projects in category_map.items():
        if cat not in categories:
            # means "Other" or fallback
            projects_html_sections += f'<div class="project-category">{cat}</div>'
            for proj in cat_projects:
                pname = proj.get("name","")
                summary = proj.get("summary","")
                repo_url = f"https://github.com/{github_username}/{pname}"
                display_name = pname.capitalize()
                projects_html_sections += f"""
<div class="project-tile">
  <h3>{display_name}</h3>
  <p>{summary}</p>
  <p><a href="{repo_url}" target="_blank">View Repository</a></p>
</div>
"""

    projects_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<title>{name}'s Projects</title>
<link href="https://fonts.googleapis.com/css2?family=Rufina:wght@400;700&family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>{name}'s Projects</h1>
  {nav}
</header>
<main>
  <p>Below are some of my GitHub projects categorized for easier navigation.</p>
  {projects_html_sections}
</main>
<footer>
  <p>© {name}'s Portfolio</p>
</footer>
</body>
</html>
"""

    # Return a dict of filename->content
    return {
        "index.html": index_html,
        "about.html": about_html,
        "resume.html": resume_html,
        "projects.html": projects_html,
        "style.css": css
    }

########################################
# Streamlit App
########################################

st.title("AI-Generated Portfolio Creator")

st.markdown("""
This app will:
1. Ask you for your OpenAI API key.
2. Ask for your GitHub username.
3. Ask for your interests.
4. Ask you to upload your resume PDF.
5. Ask for a color scheme preference.

It will then generate a static portfolio website that you can host on GitHub Pages.
""")

api_key = st.text_input("OpenAI API Key", type="password")
github_username = st.text_input("GitHub Username")
interests = st.text_area("Your Interests (comma separated)")
resume_file = st.file_uploader("Upload your Resume (PDF)", type=["pdf"])
color_scheme = st.color_picker("Choose your color scheme", value="#4CAF50")

if st.button("Generate Portfolio"):
    if not api_key:
        st.error("Please provide an OpenAI API key.")
    elif not github_username:
        st.error("Please provide a GitHub username.")
    elif not interests:
        st.error("Please provide your interests.")
    elif resume_file is None:
        st.error("Please upload your resume.")
    else:
        # Extract user name from GitHub (if possible) by fetching profile
        try:
            user_profile = requests.get(f"https://api.github.com/users/{github_username}").json()
            name = user_profile.get("name", github_username)
            if not name:
                name = github_username
        except:
            name = github_username

        # Fetch repos and readmes
        st.info("Fetching GitHub Repositories...")
        repos = fetch_github_repos(github_username)
        readmes = []
        for r in repos:
            repo_name = r["name"]
            readme_content = fetch_repo_readme(github_username, repo_name)
            # Only add if there's some content
            if readme_content.strip():
                readmes.append((repo_name, readme_content))

        # Call LLM to generate texts
        st.info("Generating Landing Page Text using LLM...")
        landing_text = generate_landing_page_text(name, interests, api_key)

        st.info("Generating About Me Text using LLM...")
        about_me_text = generate_about_me_text(name, interests, github_username, api_key)

        st.info("Categorizing Projects...")
        categories_data = categorize_projects(readmes, api_key)

        # Generate HTML files
        st.info("Generating HTML files...")
        resume_filename = "resume.pdf"
        # We'll store them in-memory
        files_dict = generate_html_files(name, about_me_text, landing_text, resume_filename, categories_data, github_username, color_scheme)

        # Create a ZIP
        st.info("Preparing ZIP file...")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add the resume PDF
            zf.writestr("resume.pdf", resume_file.read())
            # Add the HTML/CSS files
            for fname, content in files_dict.items():
                zf.writestr(fname, content)

            # Add a simple README for instructions
            instructions = f"""
# {name}'s Portfolio

This is a generated portfolio website. To host it on GitHub Pages:

1. Create a new repository named `{github_username}.github.io` (if not already existing).
2. Unzip these files into that repository.
3. Commit and push to GitHub.
4. GitHub Pages should automatically serve the site at https://{github_username}.github.io

"""
            zf.writestr("README.md", instructions)

        st.success("Portfolio generated successfully!")
        st.download_button("Download Portfolio ZIP", data=zip_buffer.getvalue(), file_name="portfolio.zip", mime="application/zip")
