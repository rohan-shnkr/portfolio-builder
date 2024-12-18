# 🖥️ AI-Powered Portfolio Generator

AI Agent to Build your Portfolio Websites

This Streamlit application generates **personal portfolio websites** based on a user's GitHub repositories, interests, and resume. With the help of **OpenAI's GPT models**, the app creates a ready-to-deploy static website that can be hosted on GitHub Pages.

---

## 🚀 Features

- **Landing Page**: Automatically generates an introduction with your name and a friendly bio.
- **About Me Page**: Pulls your GitHub avatar and generates an "About Me" section using your interests.
- **Resume Page**: Displays your resume PDF and allows visitors to download it.
- **Projects Page**: Analyzes your GitHub repositories to:
  - Extract keywords from project READMEs.
  - Categorize projects into up to 4 categories.
  - Summarize and display projects as tiles with links to repositories.

The output is bundled as a **ZIP file** containing the complete static website, which you can host on GitHub Pages.

---

## 🛠️ Requirements

Before running the app, ensure you have the following:

1. **Python 3.8+** installed.
2. **OpenAI API Key**: You need a valid API key from OpenAI.

---

## 📥 Installation

Clone this repository:

```bash
git clone git@github.com:rohan-shnkr/portfolio-builder.git
cd portfolio-builder
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## ▶️ Running the App

Run the Streamlit application using the command:

```bash
streamlit run app.py
```

Once the app starts, it will:

- Prompt for your OpenAI API key.
- Ask for your GitHub username, interests, and resume PDF.
- Let you select a color theme.
- Generate a static website ZIP file that you can download.

## 🌐 Hosting Your Portfolio on GitHub Pages

After generating the ZIP file:

- Extract the contents of the ZIP.

- Create a new repository named <your-github-username>.github.io on GitHub.

- Push the extracted files to this repository:

```bash
git init
git add .
git commit -m "Initial commit: Portfolio site"
git remote add origin https://github.com/<your-username>/<your-username>.github.io.git
git push -u origin master
```

Visit https://<your-username>.github.io to see your portfolio live!

## 🖌️ Customization

The website uses a modern and elegant design:

- Fonts: Rufina (headings) and Roboto (body text).
- Color scheme: Based on your selected color theme.
- Adaptive styling: Text colors automatically adjust for better contrast.
- To further customize the website, edit the HTML and CSS files in the generated ZIP.

## 🤝 Contributions
Feel free to contribute to this project by:

Forking the repository.
Creating a new branch.
Submitting a pull request.

## 🧑‍💻 Author
Developed by Rohan Shankar Srivasstava. For any questions or feedback, feel free to open an issue!