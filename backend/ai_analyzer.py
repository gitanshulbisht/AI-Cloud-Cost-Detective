import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# We use the OpenAI SDK but point it to NVIDIA's NIM endpoint
client = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

async def analyze_costs(resources: list) -> dict:
    prompt = f"""
    You are an expert Azure Cloud Architect and Cost Optimization Detective.
    Please analyze the following Azure resources for cost optimization opportunities.
    Look for:
    - Over-provisioned resources
    - Unused or idle resources
    - Misconfigurations (wrong pricing tiers, missing auto-shutdown, etc.)

    Resources:
    {json.dumps(resources, indent=2)}

    Return your response strictly as a JSON object with the following structure:
    {{
        "summary": "Overall summary of findings",
        "estimated_savings": "e.g., $150/month",
        "issues_count": 3,
        "issues": [
            {{
                "resource_name": "name of the resource",
                "issue_type": "over-provisioned | unused | misconfigured",
                "severity": "high | medium | low",
                "explanation": "Detailed explanation of why this is an issue",
                "fix_command": "Azure CLI command to fix the issue"
            }}
        ]
    }}
    Ensure the output is ONLY valid JSON without Markdown formatting blocks like ```json.
    """

    try:
        completion = await client.chat.completions.create(
            model="meta/llama3-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1024,
            top_p=1,
            stream=False
        )

        response_content = completion.choices[0].message.content.strip()

        # Handle potential markdown formatting if the model still outputs it
        if response_content.startswith("```json"):
            response_content = response_content[7:]
        if response_content.startswith("```"):
            response_content = response_content[3:]
        if response_content.endswith("```"):
            response_content = response_content[:-3]

        return json.loads(response_content.strip())
    except json.JSONDecodeError as e:
        print(f"Failed to parse AI output: {response_content}")
        return {
            "summary": "Error parsing AI response.",
            "estimated_savings": "$0/month",
            "issues_count": 0,
            "issues": []
        }
    except Exception as e:
        print(f"AI API Error: {str(e)}")
        return {
            "summary": f"AI analysis failed: {str(e)}",
            "estimated_savings": "$0/month",
            "issues_count": 0,
            "issues": []
        }
