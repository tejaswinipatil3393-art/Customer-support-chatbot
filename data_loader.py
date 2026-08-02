import json
import os
import pandas as pd
import time
from dotenv import load_dotenv
from tavily import TavilyClient
from read_csv import read_and_search_csv
from Validators import check_response_contains_keywords,evaluate_ai_response
from reports import generate_report

load_dotenv()
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


"""with open('data.json', 'r') as file:
    data = json.load(file)

csv_file = "chatbot_testing_prompts.csv"  # Replace with your CSV file path
column_to_search = "Prompt"  # Replace with the column you want to search
keyword = ""  # Replace with your search term

data = read_and_search_csv(csv_file, column_to_search, keyword)
if not data.empty:
        print("Search Results:")
        print(data)
else:
        print("No matching records found.")

"""
with open("chatbot_testing_prompts.csv", "r") as f:
    data = pd.read_csv(f,usecols=["Prompt"])
print(data)

evaluation_results = []
for prompt in data["Prompt"]:
    start = time.time()
    try:
        response = client.search(query=prompt, max_results=10)
        result = check_response_contains_keywords(response)
        print("result:", result)
        time.sleep(0.5)  # Simulated model latency
        evaluation = evaluate_ai_response(response, start, time.time())
    except Exception as error:
        print(f"Evaluation failed for {prompt!r}: {error}")
        evaluation = {
            "schema_ok": False,
            "response_time_ok": False,
            "length_ok": False,
            "groundedness_ok": False,
            "hallucination_detected": True,
            "refusal_detected": False,
            "toxicity_detected": False,
            "bias_detected": False,
            "error": str(error),
        }

    evaluation["prompt"] = prompt
    evaluation["response_time"] = time.time() - start
    print("Evaluation Results:", evaluation)
    evaluation_results.append(evaluation)

html_file, pdf_file = generate_report(evaluation_results)
print("HTML report generated:", html_file)
if pdf_file:
    print("PDF report generated:", pdf_file)
else:
    print("PDF generation skipped; install WeasyPrint to enable it.")


   