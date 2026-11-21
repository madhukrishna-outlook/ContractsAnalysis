# Contract Review with Jev

This utility reads a contract from an HTML or plain-text file, builds a Jev System One request using a separate JSON file of questions, prints a copyable `curl` command, executes the request, and prints Jev's response and the HTTP status.

## Requirements

- Python 3.10 or later
- `curl` available on your `PATH`
- A Jev AI API key

The utility uses only Python's standard library; no Python packages need to be installed.

## Configure the API key

Create a `.env` file next to `analyze_contract_with_jev.py`:

```dotenv
JEV_AI_API_KEY=your-api-key
# Optional overrides:
JEV_AI_MODEL=jev-1.14.0
JEV_AI_API_URL=https://jev-ai.pro/api/v1/systemone
```

The script loads this file automatically if it exists. Variables already set in the process environment take precedence. The `.env` file is ignored by Git; do not commit API keys.

## Run

From the repository root:

```bash
python3 analyze_contract_with_jev.py docs/Downloaded_Contracts/MSA/MSA_Template_1.html
```

Example output:

```text
{"model":"jev-1.14.0","answers":{"q1":{"type":"noul","noul":0.1},"q2":{"type":"score","score":1.31,"confidence":0.36,"legend":{"0":"Low","1":"Medium","2":"High"},"probabilities":{"0":0.06,"1":0.57,"2":0.37}},"q3":{"type":"choice","choice":"In USA outside of California","confidence":1,"probabilities":{"In California":0,"In USA outside of California":1,"Europe":0,"APAC":0}},"q4":{"type":"noul","noul":0.99}},"usage":{"input_tokens":23418,"output_tokens":105}}
HTTP_STATUS:200
```

A plain-text contract can be passed the same way. To select a different questions file, model, or endpoint:

```bash
python3 analyze_contract_with_jev.py path/to/contract.html \
  --questions-file path/to/questions.json \
  --model jev-1.14.0 \
  --api-url https://jev-ai.pro/api/v1/systemone
```

Run `python3 analyze_contract_with_jev.py --help` to see the available options. The API key is required; the program reports an error if it is not present in the environment or `.env` file.

## Questions

By default, the utility loads [`jev_questions.json`](jev_questions.json), located beside the script. It is a JSON object whose keys are answer names and whose values define Jev questions. The included file asks about renewal, overall risk, jurisdiction, and indemnity.

For example:

```json
{
  "renewal": {
    "type": "noul",
    "instructions": "Are there any terms and conditions for renewal?"
  },
  "risk": {
    "type": "score",
    "instructions": "What is the risk assessment score from the terms and conditions?",
    "criteria": ["Low", "Medium", "High"]
  },
  "jurisdiction": {
    "type": "choice",
    "instructions": "What is the jurisdiction?",
    "criteria": {
      "In California": null,
      "In USA outside of California": null,
      "Europe": null,
      "APAC": null
    }
  }
}
```

Use the question types and criteria accepted by your Jev API configuration. Keep the question file valid JSON and non-empty.

## Output and data handling

The output includes the request payload in the printed `curl` command and the API response. The API key is represented as `$JEV_AI_API_KEY` in that command and is not printed. The full extracted contract text is included in the request, so it is sent to Jev AI and may also appear in terminal logs or captured output. Use only documents authorized for this external processing, and handle output as confidential contract data.

HTML extraction removes the page head, scripts, styles, and noscript content, then sends the remaining visible text. Plain-text inputs are sent as-is after trimming leading and trailing whitespace. This utility reports Jev's response; it does not provide legal advice or replace review by a qualified attorney.
