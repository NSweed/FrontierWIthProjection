import openai
import anthropic
import os

class ChatSession:
    # 2026 Pricing for High Reasoning Models (Per 1M Tokens)
    PRICING = {
        "gpt-5.2": {"input": 1.75, "output": 14.00, "search": 0.01},
        "gpt-5.1": {"input": 1.25, "output": 10.00, "search": 0.01},
        "gpt-5": {"input": 1.00, "output": 8.00, "search": 0.01},
        "claude-opus-4-5-20251101": {"input": 5.00, "output": 25.00, "search": 0.01},
    }

    def __init__(self, provider, model_name,  api_key, history=None,  web_enabled=False, high_reasoning=True):
        self.provider = provider.lower()
        self.model_name = model_name
        self.history = history if history else []
        self.total_cost = 0
        self.web_enabled = web_enabled
        self.high_reasoning = high_reasoning

        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY")
            self.client = anthropic.Anthropic(api_key=key)

    def send_message(self, prompt, force_search = False):
        self.history.append({"role": "user", "content": prompt})

        if self.provider == "openai":
            return self._openai_logic(force_search)
        elif self.provider == "anthropic":
            return self._claude_logic()

    def _openai_logic(self, force_search = False):
        tools = [{"type": "web_search"}] if self.web_enabled else []

        effort = "xhigh" if self.model_name == "gpt-5.2" and self.high_reasoning else "high"

        # The 'include' list below uses the exact supported values from the 2026 spec
        include_params = ["web_search_call.results"]
        if self.web_enabled:
            include_params.append("web_search_call.action.sources")
        tool_choice = {"type": "web_search"} if force_search else "auto"
        response = self.client.responses.create(
            model=self.model_name,
            tools=tools,
            input=self.history,
            reasoning={"effort": effort},
            include=include_params,  # Corrected field names
            tool_choice = tool_choice
        )


        # DETECTING THE SEARCH
        # The 'output' attribute is an array of items (reasoning, search_calls, message)
        search_occurred = any(item.type == "web_search_call" for item in response.output)

        if search_occurred:
            print("🌐 [OpenAI Web Search Performed]")
            for item in response.output:
                if item.type == "web_search_call":
                    # GPT-5.2 uses 'query' for the search string
                    query = getattr(item, 'query', 'Browsing...')
                    print(f"   -> Query: {query}")

        output = response.output_text
        self._calculate_cost(response.usage)
        self.history.append({"role": "assistant", "content": output})
        return output

    def _claude_logic(self):
        kwargs = {
            "model": "claude-opus-4-5-20251101",
            "max_tokens": 20000,
            "messages": self.history,
        }

        # List for all necessary beta headers
        betas = []

        # 1. Web Search Setup
        if self.web_enabled:
            betas.append("web-search-2025-03-05")
            kwargs["tools"] = [{
                "type": "web_search_20250305",
                "name": "web_search"
            }]

        # 2. Effort Control (Now inside output_config)
        # Note: This requires the effort beta header
        betas.append("effort-2025-11-24")
        kwargs["output_config"] = {
            "effort": "high" if self.high_reasoning else "medium"
        }

        # 3. Thinking Configuration (Now only for the token budget)
        if self.high_reasoning:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": 12000
            }

        # 4. Final Header Assembly
        if betas:
            kwargs["betas"] = betas

        # 5. API Call
        # Since we are using betas, we use the .beta namespace
        response = self.client.beta.messages.create(**kwargs)

        # 6. Extraction
        response_text = "".join([b.text for b in response.content if b.type == "text"])
        self._calculate_cost(response.usage)
        self.history.append({"role": "assistant", "content": response_text})
        return response_text

    def _calculate_cost(self, usage):
        p = self.PRICING.get(self.model_name, {"input": 0, "output": 0, "search": 0})
        # Standard input/output usage
        # Note: reasoning_tokens are billed as output tokens
        input_tokens = getattr(usage, 'input_tokens', getattr(usage, 'prompt_tokens', 0))
        output_tokens = getattr(usage, 'output_tokens', getattr(usage, 'completion_tokens', 0))

        cost = (input_tokens * p["input"] / 1e6) + (output_tokens * p["output"] / 1e6)

        # Add flat search fee if applicable
        if hasattr(usage, 'web_search_calls'):
            cost += (usage.web_search_calls * p["search"])

        self.total_cost += cost
        print(f"--- [Turn Cost: ${cost:.6f} | Total: ${self.total_cost:.4f}] ---")

    def get_history(self):
        return self.history


