import os
from openai import OpenAI

def gen_report(hostname: str, is_spam_count: int, not_spam_count: int) -> str:
   
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return "AI report unavailable: GROQ_API_KEY not set."

    client = OpenAI(
        api_key=key,
        base_url="https://api.groq.com/openai/v1",
    )

    response = client.responses.create(
        input=f"""
You are an academic technical writer.

Write a short and professional report in formal English for a Final Year Project.

Project Description:
A network monitoring application was developed to track live network packets in real time. The system inspects each packet and classifies it as spam or non spam. Summary information is stored in a database for analysis.

Stored Parameters:
Hostname: {hostname}
Spam packet count: {is_spam_count}
Legitimate packet count: {not_spam_count}

Report Scope:
Briefly explain the packet analysis results, including total packets processed, the proportion of spam versus legitimate packets, and a short interpretation of overall network traffic quality.

Writing Requirements:
Formal academic tone suitable for FYP. Very concise (1 to 2 short paragraphs). Clear and objective language.
""",
        model="openai/gpt-oss-20b",
    )
    return response.output_text.strip()
